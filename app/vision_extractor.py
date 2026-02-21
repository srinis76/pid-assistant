"""
Vision-Based Structured Extraction for P&ID Documents

Uses Gemini Vision to extract structured equipment, instrument, and
connection data from P&ID images.
"""

import os
import json
import base64
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

from app.models.equipment import (
    Equipment,
    Instrument,
    Connection,
    PFDExtraction,
    LegendExtraction,
    PIDExtraction,
    DocumentExtraction,
)

load_dotenv()


# ============================================================
# Extraction Prompts
# ============================================================

PFD_EXTRACTION_PROMPT = """You are analyzing a Process Flow Diagram (PFD) for an oil and gas facility.

Extract ALL visible information and return it as valid JSON with this exact structure:

{
  "page_type": "PFD",
  "facility_name": "string or null",
  "drawing_number": "string or null",
  "major_equipment": [
    {
      "tag": "V-101",
      "equipment_type": "Separator",
      "name": "High Pressure Separator",
      "service": "Oil/Gas Separation",
      "design_pressure": "1200 PSIG",
      "design_temperature": "300°F",
      "operating_pressure": "350 PSIG",
      "operating_temperature": "70°F",
      "capacity": "string or null",
      "size": "60 inch ID x 18'-6 S/S"
    }
  ],
  "process_streams": [
    {
      "stream_number": "1",
      "from_equipment": "V-101",
      "to_equipment": "V-102",
      "flow_rate": "100 MMSCFD",
      "pressure": "714.69 PSIA",
      "temperature": "70°F",
      "phase": "gas"
    }
  ],
  "stream_table_headers": ["Parameter", "Units", "1", "2", "3"],
  "stream_table_data": [
    {"parameter": "Temperature", "units": "°F", "1": "70.00", "2": "70.00"}
  ],
  "notes": ["list of any visible notes"]
}

CRITICAL INSTRUCTIONS:
1. Extract ONLY what you can clearly read - use null for unclear values
2. Include ALL major equipment visible (vessels, pumps, compressors, heat exchangers)
3. Capture the stream data table if present
4. Include units with all values (e.g., "350 PSIG", "70°F", "100 GPM")
5. For equipment tags, use exact format shown (e.g., V-101, P-103, C-104)

Return ONLY the JSON object, no markdown formatting or explanation."""


LEGEND_EXTRACTION_PROMPT = """You are analyzing a P&ID Legend Sheet containing symbol definitions.

Extract ALL visible information and return it as valid JSON with this exact structure:

{
  "page_type": "Legend",
  "instrument_symbols": [
    {
      "symbol_code": "PT",
      "description": "Pressure Transmitter",
      "category": "Pressure"
    },
    {
      "symbol_code": "PSV",
      "description": "Pressure Safety Valve",
      "category": "Pressure"
    }
  ],
  "piping_classes": [
    {
      "class_code": "A",
      "description": "ANSI 150#",
      "material": "Carbon Steel",
      "pressure_rating": "230 psi",
      "temperature_rating": "300°F"
    }
  ],
  "valve_symbols": [
    {"symbol_name": "Gate Valve", "description": "Manual isolation"}
  ],
  "line_types": [
    {"line_style": "solid", "description": "Process piping"},
    {"line_style": "dashed", "description": "Instrument signal"}
  ],
  "general_notes": ["list of any notes visible"]
}

CRITICAL INSTRUCTIONS:
1. Extract ALL instrument abbreviations (PT, LT, FT, TT, PSV, PSH, LSH, etc.)
2. Extract ALL piping class definitions with pressure ratings
3. Include valve symbols and their descriptions
4. This data helps interpret the detailed P&ID pages

Return ONLY the JSON object, no markdown formatting or explanation."""


DETAILED_PID_EXTRACTION_PROMPT = """You are analyzing a detailed P&ID (Piping and Instrumentation Diagram) page.

Extract ALL equipment and instruments visible and return as valid JSON with this exact structure:

{
  "page_type": "Detail_PID",
  "page_title": "High Pressure Separator",
  "drawing_number": "D-254-002",
  "primary_equipment": [
    {
      "tag": "V-101",
      "equipment_type": "Separator",
      "name": "High Pressure Separator",
      "design_pressure": "1200 PSIG (82.7 BAR)/FV",
      "design_temperature": "300°F (149°C)",
      "operating_pressure": "350 PSIG (24.2 BAR)",
      "operating_temperature": "70°F (21°C)",
      "size": "60 inch I.D. x 18'-6 S/S",
      "capacity": "3 MIN liquid residence time"
    }
  ],
  "instruments": [
    {
      "tag": "PSV-101",
      "instrument_type": "Pressure Safety Valve",
      "function": "Over-pressure protection",
      "parent_equipment": "V-101",
      "setpoint": null,
      "relationship_type": "protects"
    },
    {
      "tag": "PT-101A",
      "instrument_type": "Pressure Transmitter",
      "function": "Pressure measurement",
      "parent_equipment": "V-101",
      "setpoint": null,
      "relationship_type": "monitors"
    },
    {
      "tag": "LIC-101A",
      "instrument_type": "Level Indicator Controller",
      "function": "Level control",
      "parent_equipment": "V-101",
      "setpoint": null,
      "relationship_type": "controls"
    }
  ],
  "piping_connections": [
    {
      "source_tag": "Production Header",
      "destination_tag": "V-101",
      "pipe_size": "6 inch",
      "pipe_class": "D",
      "service": "Inlet"
    }
  ],
  "control_loops": [
    {
      "loop_id": "LIC-101",
      "controlled_variable": "Level",
      "sensor_tag": "LT-101A",
      "controller_tag": "LIC-101A",
      "final_element_tag": "LV-101A"
    }
  ],
  "sheet_references": ["SHT 3", "SHT 5"],
  "extraction_status": "success",
  "extraction_notes": []
}

CRITICAL INSTRUCTIONS:
1. Extract EVERY instrument tag visible on the page (PSV, PT, LT, FT, TT, PIC, LIC, FIC, SDV, etc.)
2. Group instruments by their parent equipment - determine this from proximity and connections
3. For instrument types, decode the tag:
   - First letter(s): measured variable (P=Pressure, L=Level, F=Flow, T=Temperature)
   - Middle letters: function (T=Transmitter, I=Indicator, C=Controller, SV/V=Valve)
   - Last letters: modifier (H=High, L=Low, HH/LL=Very High/Low)
4. Common instrument types:
   - PSV = Pressure Safety Valve (protects)
   - PT = Pressure Transmitter (monitors)
   - PIC = Pressure Indicator Controller (controls)
   - LT = Level Transmitter (monitors)
   - LIC = Level Indicator Controller (controls)
   - FT = Flow Transmitter (monitors)
   - SDV = Shutdown Valve (protects/isolates)
5. Include piping connections with sizes (e.g., 6"-D means 6 inch, class D)
6. Note sheet references (SHT 2, SHT 3, etc.)
7. If a tag is not clearly readable, use "TAG_NOT_VISIBLE" as the tag value
8. CROSS-PAGE CONNECTIONS - trace ALL piping lines including those that exit the page
   boundary. For lines going off-page, set destination_tag to the equipment or header the
   line is labelled as going to (e.g., "TO V-102", "FROM PRODUCTION HEADER"). Never omit
   a connection just because the destination is on another sheet.
9. PARENT EQUIPMENT - every instrument must have a parent_equipment value. Assign it based
   on: (a) the signal line connecting the instrument to equipment, (b) the equipment bubble
   cluster the instrument appears inside, or (c) the equipment data table the instrument is
   listed under. If genuinely ambiguous, assign the nearest major equipment tag on the page.

Return ONLY the JSON object, no markdown formatting or explanation."""


# ============================================================
# Vision Extractor Class
# ============================================================

class VisionExtractor:
    """
    Vision-based structured extraction for P&ID documents.

    Uses Gemini Vision to analyze P&ID page images and extract
    structured equipment, instrument, and connection data.
    """

    def __init__(self):
        """Initialize the vision extractor"""
        import google.generativeai as genai

        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        genai.configure(api_key=self.api_key)
        # Use gemini-2.5-flash for vision extraction
        self.model_name = os.getenv("VISION_MODEL", "gemini-2.5-flash")
        self.model = genai.GenerativeModel(self.model_name)

        self.prompts = {
            "PFD": PFD_EXTRACTION_PROMPT,
            "Legend": LEGEND_EXTRACTION_PROMPT,
            "Detail_PID": DETAILED_PID_EXTRACTION_PROMPT,
        }

        # Token tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0

        print(f"VisionExtractor initialized with {self.model_name}")

    def _load_image(self, image_path: str) -> bytes:
        """Load image file as bytes"""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        with open(path, "rb") as f:
            return f.read()

    def _call_gemini_json(
        self,
        prompt: str,
        image_bytes: bytes
    ) -> Tuple[Dict, Dict]:
        """
        Call Gemini with image and return JSON response.

        Returns:
            Tuple of (parsed_json, token_usage)
        """
        import google.generativeai as genai
        import PIL.Image
        import io

        # Convert bytes to PIL Image
        img = PIL.Image.open(io.BytesIO(image_bytes))

        # Configure for JSON output
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1,  # Low temperature for consistent extraction
        )

        # Call API
        response = self.model.generate_content(
            [img, prompt],
            generation_config=generation_config,
        )

        # Extract token usage
        tokens = {
            "input_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
            "output_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
        }

        # Update totals
        self.total_input_tokens += tokens["input_tokens"]
        self.total_output_tokens += tokens["output_tokens"]

        # Parse JSON response
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse JSON response: {e}")
            print(f"Response text: {response.text[:500]}...")
            result = {"extraction_status": "failed", "error": str(e)}

        return result, tokens

    def determine_page_type(self, page_number: int, total_pages: int) -> str:
        """
        Determine the page type based on position.

        Standard P&ID document structure:
        - Page 1: PFD (Process Flow Diagram)
        - Page 2: Legend Sheet
        - Pages 3+: Detailed P&IDs
        """
        if page_number == 1:
            return "PFD"
        elif page_number == 2:
            return "Legend"
        else:
            return "Detail_PID"

    def extract_page(
        self,
        image_path: str,
        page_type: str,
        page_number: int = 0
    ) -> Dict:
        """
        Extract structured data from a single P&ID page image.

        Args:
            image_path: Path to the page image (PNG)
            page_type: Type of page ("PFD", "Legend", "Detail_PID")
            page_number: Page number for metadata

        Returns:
            Extracted data as dictionary
        """
        print(f"  Extracting page {page_number} ({page_type})...")

        # Load image
        image_bytes = self._load_image(image_path)

        # Get appropriate prompt
        prompt = self.prompts.get(page_type, self.prompts["Detail_PID"])

        # Call Gemini
        start_time = time.time()
        result, tokens = self._call_gemini_json(prompt, image_bytes)
        elapsed = time.time() - start_time

        # Add metadata
        result["page_number"] = page_number
        result["extraction_time_seconds"] = round(elapsed, 2)
        result["input_tokens"] = tokens["input_tokens"]
        result["output_tokens"] = tokens["output_tokens"]

        print(f"    ✓ Extracted in {elapsed:.1f}s ({tokens['input_tokens']} in, {tokens['output_tokens']} out)")

        return result

    def extract_document(
        self,
        image_paths: List[str],
        file_name: str = "unknown"
    ) -> DocumentExtraction:
        """
        Extract structured data from all pages of a P&ID document.

        Args:
            image_paths: List of paths to page images (in order)
            file_name: Name of the source PDF

        Returns:
            DocumentExtraction with consolidated data
        """
        print(f"\nExtracting document: {file_name}")
        print(f"  Pages: {len(image_paths)}")
        print("=" * 50)

        total_pages = len(image_paths)
        pfd_pages = []
        legend_pages = []
        pid_pages = []

        # Extract each page
        for i, image_path in enumerate(image_paths):
            page_number = i + 1
            page_type = self.determine_page_type(page_number, total_pages)

            try:
                result = self.extract_page(image_path, page_type, page_number)

                # Route to appropriate list based on type
                if page_type == "PFD":
                    pfd_pages.append(PFDExtraction(**result))
                elif page_type == "Legend":
                    legend_pages.append(LegendExtraction(**result))
                else:
                    pid_pages.append(PIDExtraction(**result))

            except Exception as e:
                print(f"    ✗ Error extracting page {page_number}: {e}")
                # Add empty extraction with error
                if page_type == "Detail_PID":
                    pid_pages.append(PIDExtraction(
                        page_number=page_number,
                        extraction_status="failed",
                        extraction_notes=[str(e)]
                    ))

        # Consolidate all equipment and instruments
        all_instruments = []
        all_connections = []
        equipment_instrument_map = {}

        # Collect equipment from different page types
        pfd_equipment = [e for pfd in pfd_pages for e in pfd.major_equipment]
        pid_equipment = [e for pid in pid_pages for e in pid.primary_equipment]

        # MERGE equipment across pages (PFD + P&ID) - avoids duplicates
        all_equipment = merge_equipment_across_pages(pfd_equipment, pid_equipment)

        print(f"  Merged equipment: {len(pfd_equipment)} (PFD) + {len(pid_equipment)} (P&ID) -> {len(all_equipment)} unique")

        # From P&ID pages: collect instruments and connections
        for pid in pid_pages:
            all_instruments.extend(pid.instruments)
            # Skip connections where source or destination is null
            valid_connections = [
                c for c in pid.piping_connections
                if c.source_tag and c.destination_tag
            ]
            all_connections.extend(valid_connections)

            # Build equipment-instrument map
            for inst in pid.instruments:
                if inst.parent_equipment:
                    if inst.parent_equipment not in equipment_instrument_map:
                        equipment_instrument_map[inst.parent_equipment] = []
                    equipment_instrument_map[inst.parent_equipment].append(inst.tag)

        # Create document extraction result
        doc_extraction = DocumentExtraction(
            file_name=file_name,
            total_pages=total_pages,
            pfd_pages=pfd_pages,
            legend_pages=legend_pages,
            pid_pages=pid_pages,
            all_equipment=all_equipment,
            all_instruments=all_instruments,
            all_connections=all_connections,
            equipment_instrument_map=equipment_instrument_map,
        )

        # Print summary
        print("=" * 50)
        print(f"Extraction complete!")
        print(f"  Equipment: {len(all_equipment)}")
        print(f"  Instruments: {len(all_instruments)}")
        print(f"  Connections: {len(all_connections)}")
        print(f"  Total tokens: {self.total_input_tokens} in, {self.total_output_tokens} out")

        return doc_extraction

    def get_usage_summary(self) -> Dict:
        """Get token usage summary"""
        # Gemini Flash pricing (per million tokens)
        input_cost = self.total_input_tokens * 0.075 / 1_000_000
        output_cost = self.total_output_tokens * 0.30 / 1_000_000

        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "estimated_cost_usd": round(input_cost + output_cost, 4),
        }


# ============================================================
# Cross-Page Equipment Merging
# ============================================================

def merge_equipment_across_pages(
    pfd_equipment: List[Equipment],
    pid_equipment: List[Equipment]
) -> List[Equipment]:
    """
    Merge equipment data from PFD and P&ID pages by tag.

    Same equipment (e.g., V-101) may appear on multiple pages:
    - PFD (Page 1): Basic specs, stream connections
    - Detailed P&ID (Page 3+): Instruments, control loops, detailed specs

    Conflict resolution: P&ID data wins (more detailed).

    Args:
        pfd_equipment: Equipment list from PFD pages
        pid_equipment: Equipment list from detailed P&ID pages

    Returns:
        Merged equipment list (no duplicates)
    """
    merged: Dict[str, Equipment] = {}

    # First pass: Add PFD equipment as base
    for equip in pfd_equipment:
        merged[equip.tag] = equip

    # Second pass: Merge/override with P&ID equipment
    for equip in pid_equipment:
        if equip.tag in merged:
            # Merge: P&ID values take precedence, PFD as fallback
            base = merged[equip.tag]
            merged[equip.tag] = Equipment(
                tag=equip.tag,
                equipment_type=equip.equipment_type or base.equipment_type,
                name=equip.name or base.name,
                service=equip.service or base.service,
                design_pressure=equip.design_pressure or base.design_pressure,
                design_temperature=equip.design_temperature or base.design_temperature,
                operating_pressure=equip.operating_pressure or base.operating_pressure,
                operating_temperature=equip.operating_temperature or base.operating_temperature,
                size=equip.size or base.size,
                capacity=equip.capacity or base.capacity,
                material=equip.material or base.material,
                # Merge additional specs
                additional_specs={**base.additional_specs, **equip.additional_specs}
            )
        else:
            # New equipment from P&ID only
            merged[equip.tag] = equip

    return list(merged.values())


# ============================================================
# Equipment-Centric Chunk Generator
# ============================================================

def generate_equipment_chunks(
    doc_extraction: DocumentExtraction,
    document_id: int = 0
) -> List[Dict]:
    """
    Generate equipment-centric text chunks from extraction results.

    Creates one rich chunk per equipment containing all associated
    instruments, connections, and specifications.

    Args:
        doc_extraction: DocumentExtraction from vision extraction
        document_id: Database document ID

    Returns:
        List of chunk dictionaries ready for embedding
    """
    chunks = []

    for equipment in doc_extraction.all_equipment:
        # Find associated instruments
        associated_instruments = doc_extraction.equipment_instrument_map.get(
            equipment.tag, []
        )
        instrument_details = [
            inst for inst in doc_extraction.all_instruments
            if inst.tag in associated_instruments
        ]

        # Find connections involving this equipment
        connections = [
            conn for conn in doc_extraction.all_connections
            if conn.source_tag == equipment.tag or conn.destination_tag == equipment.tag
        ]

        # Build chunk text
        chunk_text = _build_equipment_chunk_text(
            equipment, instrument_details, connections
        )

        chunks.append({
            "chunk_id": f"equip_{equipment.tag}",
            "chunk_type": "equipment",
            "equipment_tag": equipment.tag,
            "chunk_text": chunk_text,
            "metadata": {
                "document_id": document_id,
                "equipment_type": equipment.equipment_type,
                "equipment_name": equipment.name,
                "instrument_count": len(instrument_details),
                "connection_count": len(connections),
            }
        })

    return chunks


def _build_equipment_chunk_text(
    equipment: Equipment,
    instruments: List[Instrument],
    connections: List[Connection]
) -> str:
    """Build rich text content for an equipment chunk"""

    lines = []

    # Header
    lines.append(f"{equipment.tag} - {equipment.name.upper() if equipment.name else 'EQUIPMENT'}")
    lines.append(f"Type: {equipment.equipment_type}")
    if equipment.service:
        lines.append(f"Service: {equipment.service}")
    lines.append("")

    # Specifications
    lines.append("SPECIFICATIONS:")
    if equipment.size:
        lines.append(f"- Size: {equipment.size}")
    if equipment.design_pressure:
        lines.append(f"- Design Pressure: {equipment.design_pressure}")
    if equipment.design_temperature:
        lines.append(f"- Design Temperature: {equipment.design_temperature}")
    if equipment.operating_pressure:
        lines.append(f"- Operating Pressure: {equipment.operating_pressure}")
    if equipment.operating_temperature:
        lines.append(f"- Operating Temperature: {equipment.operating_temperature}")
    if equipment.capacity:
        lines.append(f"- Capacity: {equipment.capacity}")
    if equipment.material:
        lines.append(f"- Material: {equipment.material}")
    lines.append("")

    # Instruments
    if instruments:
        lines.append("ASSOCIATED INSTRUMENTS:")
        for inst in instruments:
            setpoint_str = f" (Set: {inst.setpoint})" if inst.setpoint else ""
            lines.append(f"- {inst.tag}: {inst.instrument_type}{setpoint_str} - {inst.function}")
        lines.append("")

    # Connections
    if connections:
        lines.append("CONNECTIONS:")
        for conn in connections:
            if conn.source_tag == equipment.tag:
                direction = "Outlet"
                other = conn.destination_tag
            else:
                direction = "Inlet"
                other = conn.source_tag

            size_str = f"{conn.pipe_size}" if conn.pipe_size else ""
            class_str = f" (Class {conn.pipe_class})" if conn.pipe_class else ""
            lines.append(f"- {direction}: {size_str}{class_str} {'to' if direction == 'Outlet' else 'from'} {other}")

    return "\n".join(lines)


# ============================================================
# Test Function
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Testing Vision Extractor")
    print("=" * 60 + "\n")

    # Check for test images
    test_dir = Path("data/processed")
    if not test_dir.exists():
        print("No processed images found. Run ingestion first.")
        exit(1)

    # Find first available document
    doc_dirs = list(test_dir.iterdir())
    if not doc_dirs:
        print("No document directories found.")
        exit(1)

    doc_dir = doc_dirs[0]
    image_paths = sorted(doc_dir.glob("page_*.png"))

    if not image_paths:
        print(f"No page images found in {doc_dir}")
        exit(1)

    print(f"Found {len(image_paths)} pages in {doc_dir.name}")

    # Initialize extractor
    extractor = VisionExtractor()

    # Test single page extraction
    print("\n--- Testing single page extraction ---")
    result = extractor.extract_page(
        str(image_paths[2]),  # Page 3 (first detailed P&ID)
        "Detail_PID",
        page_number=3
    )

    print(f"\nExtracted {len(result.get('primary_equipment', []))} equipment")
    print(f"Extracted {len(result.get('instruments', []))} instruments")

    # Print usage
    usage = extractor.get_usage_summary()
    print(f"\nToken usage: {usage}")

    print("\n" + "=" * 60)
    print("  Test complete!")
    print("=" * 60 + "\n")
