"""
PDF Ingestion Pipeline for P&ID Assistant

This script processes P&ID PDF documents and prepares data for querying:
1. Extract text from each page
2. Extract page images (300 DPI PNG)
3. Chunk text content
4. Generate embeddings
5. Store in ChromaDB and SQLite
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Tuple, Dict
import sqlite3
import base64
from datetime import datetime

# PDF processing
import fitz  # PyMuPDF
from PIL import Image
import io

# Embeddings and vector DB
import chromadb
from openai import OpenAI

# Environment
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class PDFIngestionPipeline:
    """Pipeline for ingesting P&ID PDF documents"""

    def __init__(self):
        self.sqlite_db_path = os.getenv("SQLITE_DB_PATH", "database/assets.db")
        self.vector_db_path = os.getenv("VECTOR_DB_PATH", "database/vector_store")
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
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

        print(f"📁 Initialized PDF Ingestion Pipeline")
        print(f"   SQLite: {self.sqlite_db_path}")
        print(f"   ChromaDB: {self.vector_db_path}")
        print(f"   Chunk size: {self.chunk_size} tokens")
        print(f"   Image DPI: {self.image_dpi}")
        print(f"   Embedding model: {self.embedding_model}")
        print()

    def extract_page_text(self, pdf_document: fitz.Document, page_num: int) -> str:
        """Extract text from a single PDF page"""
        page = pdf_document[page_num]
        text = page.get_text()
        return text.strip()

    def extract_page_image(
        self,
        pdf_document: fitz.Document,
        page_num: int,
        output_path: str
    ) -> str:
        """
        Extract page as PNG image

        Returns:
            Path to saved image
        """
        page = pdf_document[page_num]

        # Calculate zoom factor for target DPI
        # PyMuPDF default is 72 DPI
        zoom = self.image_dpi / 72
        mat = fitz.Matrix(zoom, zoom)

        # Render page to pixmap
        pix = page.get_pixmap(matrix=mat)

        # Save as PNG
        pix.save(output_path)

        return output_path

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks

        For MVP: Simple approach - split on double newlines (paragraphs)
        If chunks are too large, split further on single newlines
        """
        if not text.strip():
            return []

        # Split on double newlines first (paragraphs)
        paragraphs = text.split('\n\n')

        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            # Rough token estimate: ~4 characters per token
            estimated_tokens = len(current_chunk + paragraph) / 4

            if estimated_tokens < self.chunk_size:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + "\n\n"

        # Add remaining chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # If no chunks created (single large text), split by lines
        if not chunks and text:
            lines = text.split('\n')
            current_chunk = ""
            for line in lines:
                estimated_tokens = len(current_chunk + line) / 4
                if estimated_tokens < self.chunk_size:
                    current_chunk += line + "\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = line + "\n"
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

        return chunks if chunks else [text]  # Return original if chunking fails

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API"""
        if not texts:
            return []

        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            embeddings = [item.embedding for item in response.data]
            return embeddings
        except Exception as e:
            print(f"   ⚠️  Error generating embeddings: {e}")
            raise

    def store_in_sqlite(
        self,
        doc_metadata: Dict,
        pages_metadata: List[Dict]
    ) -> int:
        """
        Store document and page records in SQLite

        Returns:
            document_id
        """
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
                page_meta.get('text_content'),
                page_meta.get('has_equipment', 1)  # Default to True for MVP
            ))

        conn.commit()
        conn.close()

        return document_id

    def store_in_chromadb(
        self,
        chunks: List[str],
        embeddings: List[List[float]],
        document_id: int,
        page_number: int,
        page_title: str = None
    ):
        """Store chunks and embeddings in ChromaDB"""
        if not chunks:
            return

        # Generate unique IDs for each chunk
        ids = [f"doc{document_id}_page{page_number}_chunk{i}"
               for i in range(len(chunks))]

        # Prepare metadata
        metadatas = [
            {
                "document_id": document_id,
                "page_number": page_number,
                "page_title": page_title or f"Page {page_number}",
                "chunk_index": i
            }
            for i in range(len(chunks))
        ]

        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )

    def ingest_pdf(self, pdf_path: str) -> Dict:
        """
        Main ingestion function for a single PDF

        Returns:
            Ingestion statistics
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        print(f"📄 Processing: {pdf_path.name}")
        print(f"   Path: {pdf_path}")

        start_time = time.time()

        # Open PDF
        pdf_document = fitz.open(pdf_path)
        total_pages = len(pdf_document)

        print(f"   Pages: {total_pages}")
        print()

        # Extract document metadata from filename
        # Expected format: D-254-001_Gas_Production_Facility_Rev1.pdf
        file_name = pdf_path.name
        file_stem = pdf_path.stem

        # Simple parsing (can be enhanced)
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

        # Process each page
        pages_metadata = []
        total_chunks = 0

        for page_num in range(total_pages):
            print(f"   📑 Page {page_num + 1}/{total_pages}...")

            # 1. Extract text
            text = self.extract_page_text(pdf_document, page_num)
            print(f"      ✓ Extracted text ({len(text)} characters)")

            # 2. Extract image
            image_path = output_dir / f"page_{page_num + 1}.png"
            self.extract_page_image(pdf_document, page_num, str(image_path))
            print(f"      ✓ Saved image: {image_path}")

            # 3. Chunk text
            chunks = self.chunk_text(text)
            print(f"      ✓ Created {len(chunks)} text chunks")
            total_chunks += len(chunks)

            # Store page metadata
            pages_metadata.append({
                'page_number': page_num + 1,
                'page_type': 'Detail_PID' if page_num > 1 else ('PFD' if page_num == 0 else 'Legend'),
                'page_title': f"Page {page_num + 1}",
                'sheet_number': f"{page_num + 1} OF {total_pages}",
                'image_path': str(image_path),
                'text_content': text,
                'has_equipment': 1 if page_num > 1 else 0  # Simplified logic
            })

        print()
        print(f"   💾 Storing in databases...")

        # Store in SQLite
        document_id = self.store_in_sqlite(doc_metadata, pages_metadata)
        print(f"      ✓ SQLite: Document ID {document_id}")

        # Generate embeddings and store in ChromaDB
        print(f"      🔄 Generating embeddings for {total_chunks} chunks...")

        embedding_start = time.time()

        for page_idx, page_meta in enumerate(pages_metadata):
            page_num = page_meta['page_number']
            chunks = self.chunk_text(page_meta['text_content'])

            if chunks:
                # Generate embeddings
                embeddings = self.generate_embeddings(chunks)

                # Store in ChromaDB
                self.store_in_chromadb(
                    chunks=chunks,
                    embeddings=embeddings,
                    document_id=document_id,
                    page_number=page_num,
                    page_title=page_meta['page_title']
                )

        embedding_time = time.time() - embedding_start
        print(f"      ✓ ChromaDB: {total_chunks} chunks stored ({embedding_time:.1f}s)")

        # Close PDF
        pdf_document.close()

        elapsed = time.time() - start_time

        print()
        print(f"   ✅ Ingestion complete!")
        print(f"      Time: {elapsed:.1f} seconds")
        print(f"      Pages processed: {total_pages}")
        print(f"      Images saved: {total_pages}")
        print(f"      Text chunks: {total_chunks}")
        print()

        return {
            'document_id': document_id,
            'file_name': file_name,
            'total_pages': total_pages,
            'total_chunks': total_chunks,
            'elapsed_time': elapsed
        }

    def process_all_pdfs(self) -> List[Dict]:
        """Process all PDFs in data/pdfs directory"""
        pdf_dir = Path("data/pdfs")

        if not pdf_dir.exists():
            print(f"⚠️  PDF directory not found: {pdf_dir}")
            return []

        pdf_files = list(pdf_dir.glob("*.pdf"))

        if not pdf_files:
            print(f"⚠️  No PDF files found in {pdf_dir}")
            return []

        print(f"🔍 Found {len(pdf_files)} PDF(s) to process")
        print("=" * 60)
        print()

        results = []

        for pdf_path in pdf_files:
            try:
                result = self.ingest_pdf(pdf_path)
                results.append(result)
            except Exception as e:
                print(f"❌ Error processing {pdf_path.name}: {e}")
                import traceback
                traceback.print_exc()

        print("=" * 60)
        print(f"✅ Ingestion pipeline complete!")
        print(f"   Processed: {len(results)}/{len(pdf_files)} PDFs")
        print(f"   Total pages: {sum(r['total_pages'] for r in results)}")
        print(f"   Total chunks: {sum(r['total_chunks'] for r in results)}")
        print()

        return results


def main():
    """Main entry point"""
    print()
    print("=" * 60)
    print("  P&ID Assistant - PDF Ingestion Pipeline")
    print("=" * 60)
    print()

    # Initialize pipeline
    pipeline = PDFIngestionPipeline()

    # Process all PDFs
    results = pipeline.process_all_pdfs()

    if not results:
        print("⚠️  No PDFs were processed. Please add PDF files to data/pdfs/")
        sys.exit(1)

    print("✅ All done! Ready for querying.")
    print()


if __name__ == "__main__":
    main()
