"""
Vision Engine for P&ID Assistant

Processes visual queries using vision-enabled LLMs with P&ID diagram images.
"""

import os
import base64
import sqlite3
from typing import List, Tuple, Dict
from pathlib import Path

try:
    from app.llm_adapter import LLMAdapter
except ModuleNotFoundError:
    from llm_adapter import LLMAdapter


class VisionEngine:
    """Vision query engine for image-based P&ID queries"""

    def __init__(self):
        # Get project root and database paths
        self.project_root = Path(__file__).parent.parent
        self.sqlite_db_path = os.getenv("SQLITE_DB_PATH", str(self.project_root / "database/assets.db"))

        # Initialize LLM adapter
        self.llm_adapter = LLMAdapter()

        print(f"👁️  Vision Engine initialized")
        print(f"   SQLite DB: {self.sqlite_db_path}")
        print()

    def select_relevant_pages(
        self,
        query: str,
        max_pages: int = 3
    ) -> List[str]:
        """
        Determine which P&ID pages to send to vision API

        Enhanced logic:
        - Extract equipment tags from query (V-101, C-104, PSV-101, etc.)
        - Search page text content for those tags
        - Return only pages containing the mentioned equipment
        - Fallback to equipment pages if no matches

        Returns:
            List of (image_path, document_id) tuples
        """
        import re

        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()

        # Extract equipment tags from query (pattern: Letter(s)-Number(s) with optional letter)
        # Examples: V-101, C-104, PSV-101, FT-103A
        tag_pattern = r'\b[A-Z]+-\d+[A-Z]?\b'
        equipment_tags = re.findall(tag_pattern, query.upper())

        relevant_pages = []

        if equipment_tags:
            print(f"   🔍 Found equipment tags in query: {equipment_tags}")

            # Search for pages containing ANY of the mentioned tags
            for tag in equipment_tags:
                cursor.execute("""
                    SELECT DISTINCT image_path, page_number, page_title, document_id
                    FROM document_pages
                    WHERE text_content LIKE ? AND has_equipment = 1
                    ORDER BY page_number
                """, (f'%{tag}%',))

                tag_pages = cursor.fetchall()
                for page in tag_pages:
                    if page not in relevant_pages:
                        relevant_pages.append(page)

        # If we found relevant pages, use those
        if relevant_pages:
            print(f"   ✓ Found {len(relevant_pages)} page(s) containing the equipment")
            # Limit to max_pages
            relevant_pages = relevant_pages[:max_pages]
        else:
            # Fallback: Get first few equipment pages
            print(f"   ℹ️  No specific equipment found, using default pages")
            cursor.execute("""
                SELECT image_path, page_number, page_title, document_id
                FROM document_pages
                WHERE has_equipment = 1
                ORDER BY page_number
                LIMIT ?
            """, (max_pages,))
            relevant_pages = cursor.fetchall()

        conn.close()

        if not relevant_pages:
            # Final fallback: get any pages
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT image_path, page_number, page_title, document_id
                FROM document_pages
                ORDER BY page_number
                LIMIT ?
            """, (max_pages,))
            relevant_pages = cursor.fetchall()
            conn.close()

        # Extract (image_path, document_id) pairs
        return [(page[0], page[3]) for page in relevant_pages]

    def load_images(self, image_paths: List[str]) -> List[str]:
        """
        Load images and encode as base64

        Returns:
            List of base64-encoded image strings
        """
        encoded_images = []

        for path in image_paths:
            # Convert to absolute path if needed
            if not Path(path).is_absolute():
                path = self.project_root / path

            try:
                with open(path, 'rb') as f:
                    image_data = f.read()
                    encoded = base64.b64encode(image_data).decode('utf-8')
                    encoded_images.append(encoded)
            except Exception as e:
                print(f"⚠️  Error loading image {path}: {e}")
                continue

        return encoded_images

    def query_vision(
        self,
        query: str,
        max_pages: int = 3,
        history: str = ""
    ) -> Tuple[str, Dict]:
        """
        Main vision query function

        Args:
            query: User question requiring visual understanding
            max_pages: Maximum number of pages to analyze
            history: Optional prior-conversation text block for multi-turn coherence

        Returns:
            Tuple of (answer, metadata)
        """
        print(f"🔍 Processing Vision query: \"{query}\"")
        print(f"   Selecting relevant pages...")

        # 1. Identify relevant pages
        pages_with_docs = self.select_relevant_pages(query, max_pages)
        page_paths = [path for path, _ in pages_with_docs]
        document_ids = [doc_id for _, doc_id in pages_with_docs]
        print(f"   ✓ Selected {len(page_paths)} pages")

        if not page_paths:
            return "I couldn't find any P&ID diagrams to analyze.", {}

        # 2. Load and encode images
        print(f"   📷 Loading images...")
        images = self.load_images(page_paths)
        print(f"   ✓ Loaded {len(images)} images")

        if not images:
            return "Error loading P&ID images.", {}

        # 3. Build enhanced vision prompt
        history_block = f"{history}\n\n" if history else ""
        prompt = f"""You are an expert P&ID (Piping and Instrumentation Diagram) analyst for oil and gas facilities.

{history_block}User question: {query}

⚠️ CRITICAL ANTI-HALLUCINATION INSTRUCTIONS ⚠️

1. **ONLY report what you can ACTUALLY READ in the diagrams**
   - If you cannot read a tag number clearly, DO NOT guess or invent one
   - DO NOT assume standard naming conventions or infer tags
   - DO NOT use examples like "FI-101" unless you can LITERALLY see those exact characters

2. **When identifying equipment**:
   - State the EXACT tag as written on the diagram (e.g., "V-101", "C-104", "PSV-101")
   - If a tag is blurry or not visible, say "equipment tag not clearly visible" or "untagged equipment"
   - NEVER fabricate tag numbers based on equipment type

3. **For counting equipment** (e.g., "how many orifice meters"):
   - Count ONLY equipment you can clearly identify visually
   - Describe their location (e.g., "on the left side of the diagram", "between V-101 and C-104")
   - If tags are readable, include them. If not readable, say "tag not visible"
   - If unsure whether something is the requested equipment type, state your uncertainty

4. **Verification requirement**:
   - Before mentioning ANY equipment tag, mentally verify: "Can I actually SEE this exact text in the image?"
   - If the answer is no, do not include that tag

5. **For flow path questions**:
   - Only trace connections you can actually see
   - Use descriptive references if tags aren't visible (e.g., "the separator on the left" instead of inventing a tag)

6. **If you cannot answer confidently**, say:
   "I cannot clearly identify [item] in the provided diagrams" or
   "The resolution/visibility does not allow me to read the tag numbers clearly"

Remember: It is BETTER to say "tag not visible" than to invent a plausible-sounding but incorrect tag number.

Answer:"""

        # 4. Call LLM with vision
        print(f"   🤖 Analyzing diagrams with vision model...")
        answer = self.llm_adapter.call_llm(
            prompt,
            images=images,
            query_type="vision"
        )

        # Prepare metadata (include absolute paths for display)
        absolute_paths = []
        for path in page_paths:
            if not Path(path).is_absolute():
                absolute_paths.append(str(self.project_root / path))
            else:
                absolute_paths.append(str(path))

        metadata = {
            'num_pages_analyzed': len(images),
            'page_paths': page_paths,
            'image_paths': absolute_paths,  # For display in UI
            'document_ids': document_ids    # Parallel to page_paths/image_paths
        }

        print(f"   ✓ Analysis complete\n")

        return answer, metadata


# Test function
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Testing Vision Engine")
    print("="*60 + "\n")

    # Initialize vision engine
    vision = VisionEngine()

    # Test queries
    test_queries = [
        "Show me where V-101 is on the diagram",
        "What equipment is connected to the high pressure separator?",
        "Describe the flow path from V-101 to the compressor"
    ]

    for query in test_queries:
        print("\n" + "="*60)
        answer, metadata = vision.query_vision(query, max_pages=2)

        print(f"Query: {query}")
        print(f"\nAnswer:\n{answer}")
        print(f"\nMetadata:")
        print(f"  Pages analyzed: {metadata['num_pages_analyzed']}")
        print("="*60)

    # Display session summary
    print("\n" + vision.llm_adapter.get_session_summary())

    print("\n" + "="*60)
    print("✅ Vision Engine test complete!")
    print("="*60 + "\n")
