"""
Vision Engine for P&ID Digital Assistant

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

        For MVP: Simple heuristics
        - Search for equipment mentions in query (V-101, P-103, etc.)
        - Look up which pages contain that equipment
        - Or default to sending all equipment pages

        Returns:
            List of image file paths
        """
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()

        # For MVP: Get all pages with equipment
        cursor.execute("""
            SELECT image_path, page_number, page_title
            FROM document_pages
            WHERE has_equipment = 1
            ORDER BY page_number
            LIMIT ?
        """, (max_pages,))

        pages = cursor.fetchall()
        conn.close()

        if not pages:
            # Fallback: get any pages
            cursor = conn.cursor()
            cursor.execute("""
                SELECT image_path, page_number, page_title
                FROM document_pages
                ORDER BY page_number
                LIMIT ?
            """, (max_pages,))
            pages = cursor.fetchall()
            conn.close()

        # Extract image paths
        image_paths = [page[0] for page in pages]

        return image_paths

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
        max_pages: int = 3
    ) -> Tuple[str, Dict]:
        """
        Main vision query function

        Args:
            query: User question requiring visual understanding
            max_pages: Maximum number of pages to analyze

        Returns:
            Tuple of (answer, metadata)
        """
        print(f"🔍 Processing Vision query: \"{query}\"")
        print(f"   Selecting relevant pages...")

        # 1. Identify relevant pages
        page_paths = self.select_relevant_pages(query, max_pages)
        print(f"   ✓ Selected {len(page_paths)} pages")

        if not page_paths:
            return "I couldn't find any P&ID diagrams to analyze.", {}

        # 2. Load and encode images
        print(f"   📷 Loading images...")
        images = self.load_images(page_paths)
        print(f"   ✓ Loaded {len(images)} images")

        if not images:
            return "Error loading P&ID images.", {}

        # 3. Build vision prompt
        prompt = f"""You are analyzing P&ID (Piping and Instrumentation Diagram) documents for an oil and gas facility.

User question: {query}

Instructions:
- Examine the P&ID diagram(s) provided carefully
- Identify equipment, instruments, valves, and piping shown in the diagrams
- Answer the question based on what you can see in the diagrams
- Be specific about locations, connections, and equipment identifiers (tags)
- If you cannot find relevant information in the diagrams, say so
- Use technical terminology appropriate for P&IDs

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
            'image_paths': absolute_paths  # For display in UI
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
