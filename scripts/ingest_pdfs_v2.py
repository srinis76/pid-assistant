"""
PDF Ingestion Pipeline V2 - Vision-Based Extraction

This script processes P&ID PDF documents using vision-based extraction:
1. Extract page images from PDF (300 DPI PNG)
2. Use Gemini Vision to extract structured equipment/instrument data
3. Store equipment and instrument relationships in SQLite
4. Generate equipment-centric chunks for embeddings
5. Store chunks in ChromaDB

Usage:
    python scripts/ingest_pdfs_v2.py

This is an enhanced version of ingest_pdfs.py that uses vision AI
to better extract equipment-instrument relationships.
"""

import os
import sys
import time
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# PDF processing
import fitz  # PyMuPDF

# Embeddings and vector DB
import chromadb
from openai import OpenAI

# Environment
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.vision_extractor import VisionExtractor, generate_equipment_chunks
from app.models.equipment import DocumentExtraction

load_dotenv()


class PDFIngestionPipelineV2:
    """
    Vision-based PDF ingestion pipeline.

    Uses Gemini Vision to extract structured equipment and instrument
    data from P&ID images, then generates equipment-centric chunks
    for better RAG retrieval.
    """

    def __init__(self):
        self.sqlite_db_path = os.getenv("SQLITE_DB_PATH", "database/assets.db")
        self.vector_db_path = os.getenv("VECTOR_DB_PATH", "database/vector_store")
        self.image_dpi = int(os.getenv("IMAGE_DPI", "300"))
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

        # Initialize OpenAI client for embeddings
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=self.vector_db_path)
        self.collection = self.chroma_client.get_or_create_collection(
            name="pid_chunks",
            metadata={"description": "P&ID document chunks with embeddings"}
        )

        # Initialize vision extractor
        self.vision_extractor = VisionExtractor()

        print(f"PDF Ingestion Pipeline V2 (Vision-Based)")
        print(f"   SQLite: {self.sqlite_db_path}")
        print(f"   ChromaDB: {self.vector_db_path}")
        print(f"   Image DPI: {self.image_dpi}")
        print(f"   Embedding model: {self.embedding_model}")
        print()

    def extract_page_image(
        self,
        pdf_document: fitz.Document,
        page_num: int,
        output_path: str
    ) -> str:
        """Extract page as PNG image at configured DPI"""
        page = pdf_document[page_num]
        zoom = self.image_dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        pix.save(output_path)
        return output_path

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API"""
        if not texts:
            return []

        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"   Error generating embeddings: {e}")
            raise

    def store_document_metadata(
        self,
        doc_metadata: Dict,
        pages_metadata: List[Dict]
    ) -> int:
        """Store document and page records in SQLite, return document_id"""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()

        # Insert document record
        cursor.execute("""
            INSERT INTO documents
            (file_name, file_path, document_number, document_title, revision,
             total_pages, facility)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_metadata['file_name'],
            doc_metadata['file_path'],
            doc_metadata.get('document_number'),
            doc_metadata.get('document_title'),
            doc_metadata.get('revision'),
            doc_metadata['total_pages'],
            doc_metadata.get('facility')
        ))

        document_id = cursor.lastrowid

        # Insert page records
        for page_meta in pages_metadata:
            cursor.execute("""
                INSERT INTO document_pages
                (document_id, page_number, page_type, page_title, sheet_number,
                 image_path, text_content, has_equipment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                document_id,
                page_meta['page_number'],
                page_meta.get('page_type'),
                page_meta.get('page_title'),
                page_meta.get('sheet_number'),
                page_meta['image_path'],
                page_meta.get('text_content', ''),
                page_meta.get('has_equipment', 1)
            ))

        conn.commit()
        conn.close()

        return document_id

    def store_equipment_data(
        self,
        document_id: int,
        doc_extraction: DocumentExtraction
    ):
        """Store extracted equipment and instrument data in SQLite"""
        conn = sqlite3.connect(self.sqlite_db_path)
        cursor = conn.cursor()

        equipment_id_map = {}  # tag -> equipment_id
        instrument_id_map = {}  # tag -> instrument_id

        # Store equipment
        for equip in doc_extraction.all_equipment:
            cursor.execute("""
                INSERT INTO equipment
                (document_id, tag, equipment_type, name, service,
                 design_pressure, design_temperature, operating_pressure,
                 operating_temperature, capacity, size, material, specs_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                document_id,
                equip.tag,
                equip.equipment_type,
                equip.name,
                equip.service,
                equip.design_pressure,
                equip.design_temperature,
                equip.operating_pressure,
                equip.operating_temperature,
                equip.capacity,
                equip.size,
                equip.material,
                json.dumps(equip.additional_specs) if equip.additional_specs else None
            ))
            equipment_id_map[equip.tag] = cursor.lastrowid

        # Store instruments
        for inst in doc_extraction.all_instruments:
            cursor.execute("""
                INSERT INTO instruments
                (document_id, tag, instrument_type, function, setpoint,
                 range_min, range_max)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                document_id,
                inst.tag,
                inst.instrument_type,
                inst.function,
                inst.setpoint,
                inst.range_min,
                inst.range_max
            ))
            instrument_id_map[inst.tag] = cursor.lastrowid

        # Store equipment-instrument relationships
        for equip_tag, inst_tags in doc_extraction.equipment_instrument_map.items():
            if equip_tag not in equipment_id_map:
                continue

            equip_id = equipment_id_map[equip_tag]
            for inst_tag in inst_tags:
                if inst_tag not in instrument_id_map:
                    continue

                inst_id = instrument_id_map[inst_tag]

                # Find relationship type
                rel_type = "monitors"
                for inst in doc_extraction.all_instruments:
                    if inst.tag == inst_tag:
                        rel_type = inst.relationship_type
                        break

                cursor.execute("""
                    INSERT INTO equipment_instruments
                    (equipment_id, instrument_id, relationship_type)
                    VALUES (?, ?, ?)
                """, (equip_id, inst_id, rel_type))

        # Store connections
        for conn_data in doc_extraction.all_connections:
            cursor.execute("""
                INSERT INTO connections
                (document_id, source_tag, destination_tag, line_number,
                 pipe_size, pipe_class, service)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                document_id,
                conn_data.source_tag,
                conn_data.destination_tag,
                conn_data.line_number,
                conn_data.pipe_size,
                conn_data.pipe_class,
                conn_data.service
            ))

        conn.commit()
        conn.close()

        print(f"      Stored {len(equipment_id_map)} equipment records")
        print(f"      Stored {len(instrument_id_map)} instrument records")
        print(f"      Stored {len(doc_extraction.all_connections)} connection records")

    def store_chunks_in_chromadb(
        self,
        chunks: List[Dict],
        document_id: int
    ):
        """Store equipment-centric chunks with embeddings in ChromaDB"""
        if not chunks:
            return

        # Extract texts for embedding
        texts = [chunk['chunk_text'] for chunk in chunks]

        # Generate embeddings
        print(f"      Generating embeddings for {len(texts)} chunks...")
        embeddings = self.generate_embeddings(texts)

        # Prepare for ChromaDB
        ids = [f"v2_{chunk['chunk_id']}" for chunk in chunks]
        metadatas = [
            {
                "document_id": document_id,
                "chunk_type": chunk["chunk_type"],
                "equipment_tag": chunk.get("equipment_tag", ""),
                **chunk["metadata"]
            }
            for chunk in chunks
        ]

        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )

        print(f"      Stored {len(chunks)} chunks in ChromaDB")

    def ingest_pdf(self, pdf_path: str) -> Dict:
        """
        Main ingestion function for a single PDF.

        Returns:
            Ingestion statistics
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        print(f"Processing: {pdf_path.name}")
        print(f"   Path: {pdf_path}")

        start_time = time.time()

        # Open PDF
        pdf_document = fitz.open(pdf_path)
        total_pages = len(pdf_document)

        print(f"   Pages: {total_pages}")
        print()

        # Parse document metadata from filename
        file_name = pdf_path.name
        file_stem = pdf_path.stem

        doc_metadata = {
            'file_name': file_name,
            'file_path': str(pdf_path),
            'document_number': file_stem.split('_')[0] if '_' in file_stem else None,
            'document_title': ' '.join(file_stem.split('_')[1:-1]) if '_' in file_stem else file_stem,
            'revision': file_stem.split('_')[-1].replace('Rev', '') if 'Rev' in file_stem else None,
            'total_pages': total_pages,
            'facility': ' '.join(file_stem.split('_')[1:-1]) if '_' in file_stem else None
        }

        # Create output directory for images
        output_dir = Path("data/processed") / file_stem
        output_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Extract page images
        print("Step 1: Extracting page images...")
        pages_metadata = []
        image_paths = []

        for page_num in range(total_pages):
            image_path = output_dir / f"page_{page_num + 1}.png"
            self.extract_page_image(pdf_document, page_num, str(image_path))
            image_paths.append(str(image_path))

            page_type = self.vision_extractor.determine_page_type(page_num + 1, total_pages)

            pages_metadata.append({
                'page_number': page_num + 1,
                'page_type': page_type,
                'page_title': f"Page {page_num + 1}",
                'sheet_number': f"{page_num + 1} OF {total_pages}",
                'image_path': str(image_path),
                'has_equipment': 1 if page_type == "Detail_PID" else 0
            })

            print(f"   Page {page_num + 1}: {page_type} -> {image_path.name}")

        pdf_document.close()

        # Step 2: Store document metadata
        print("\nStep 2: Storing document metadata...")
        document_id = self.store_document_metadata(doc_metadata, pages_metadata)
        print(f"   Document ID: {document_id}")

        # Step 3: Vision-based extraction
        print("\nStep 3: Vision-based extraction (Gemini)...")
        doc_extraction = self.vision_extractor.extract_document(
            image_paths,
            file_name=file_name
        )

        # Step 4: Store equipment/instrument data
        print("\nStep 4: Storing equipment and instrument data...")
        self.store_equipment_data(document_id, doc_extraction)

        # Step 5: Generate equipment-centric chunks
        print("\nStep 5: Generating equipment-centric chunks...")
        chunks = generate_equipment_chunks(doc_extraction, document_id)
        print(f"   Generated {len(chunks)} equipment chunks")

        # Step 6: Store chunks with embeddings
        print("\nStep 6: Storing chunks in ChromaDB...")
        self.store_chunks_in_chromadb(chunks, document_id)

        elapsed = time.time() - start_time

        # Get usage summary
        usage = self.vision_extractor.get_usage_summary()

        print()
        print("=" * 50)
        print(f"Ingestion complete!")
        print(f"   Time: {elapsed:.1f} seconds")
        print(f"   Pages: {total_pages}")
        print(f"   Equipment: {len(doc_extraction.all_equipment)}")
        print(f"   Instruments: {len(doc_extraction.all_instruments)}")
        print(f"   Chunks: {len(chunks)}")
        print(f"   Tokens: {usage['total_input_tokens']} in, {usage['total_output_tokens']} out")
        print(f"   Cost: ${usage['estimated_cost_usd']:.4f}")
        print("=" * 50)

        return {
            'document_id': document_id,
            'file_name': file_name,
            'total_pages': total_pages,
            'equipment_count': len(doc_extraction.all_equipment),
            'instrument_count': len(doc_extraction.all_instruments),
            'chunk_count': len(chunks),
            'elapsed_time': elapsed,
            'token_usage': usage
        }

    def process_all_pdfs(self) -> List[Dict]:
        """Process all PDFs in data/pdfs directory"""
        pdf_dir = Path("data/pdfs")

        if not pdf_dir.exists():
            print(f"PDF directory not found: {pdf_dir}")
            return []

        pdf_files = list(pdf_dir.glob("*.pdf"))

        if not pdf_files:
            print(f"No PDF files found in {pdf_dir}")
            return []

        print(f"Found {len(pdf_files)} PDF(s) to process")
        print("=" * 60)
        print()

        results = []

        for pdf_path in pdf_files:
            try:
                result = self.ingest_pdf(pdf_path)
                results.append(result)
            except Exception as e:
                print(f"Error processing {pdf_path.name}: {e}")
                import traceback
                traceback.print_exc()

        print()
        print("=" * 60)
        print("All documents processed!")
        print(f"   Documents: {len(results)}")
        print(f"   Total equipment: {sum(r['equipment_count'] for r in results)}")
        print(f"   Total instruments: {sum(r['instrument_count'] for r in results)}")
        print(f"   Total chunks: {sum(r['chunk_count'] for r in results)}")

        total_cost = sum(r['token_usage']['estimated_cost_usd'] for r in results)
        print(f"   Total cost: ${total_cost:.4f}")
        print("=" * 60)

        return results


def main():
    """Main entry point"""
    print()
    print("=" * 60)
    print("  P&ID Assistant - Vision-Based Ingestion V2")
    print("=" * 60)
    print()

    # Initialize pipeline
    pipeline = PDFIngestionPipelineV2()

    # Process all PDFs
    results = pipeline.process_all_pdfs()

    if not results:
        print("No PDFs were processed. Add PDF files to data/pdfs/")
        sys.exit(1)

    print("\nReady for querying!")
    print()


if __name__ == "__main__":
    main()
