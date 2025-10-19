"""
Verify that ingestion completed successfully
"""
import sqlite3
import chromadb
from pathlib import Path


def verify_sqlite():
    """Verify SQLite database"""
    print("🔍 Verifying SQLite Database...")
    print("-" * 50)

    conn = sqlite3.connect("database/assets.db")
    cursor = conn.cursor()

    # Check documents
    cursor.execute("SELECT COUNT(*) FROM documents")
    doc_count = cursor.fetchone()[0]
    print(f"   Documents: {doc_count}")

    # Check pages
    cursor.execute("SELECT COUNT(*) FROM document_pages")
    page_count = cursor.fetchone()[0]
    print(f"   Pages: {page_count}")

    # Check mock tickets
    cursor.execute("SELECT COUNT(*) FROM mock_tickets")
    ticket_count = cursor.fetchone()[0]
    print(f"   Mock Tickets: {ticket_count}")

    # Get document details
    cursor.execute("""
        SELECT file_name, document_title, total_pages
        FROM documents
    """)
    docs = cursor.fetchall()

    print("\n   Document Details:")
    for doc in docs:
        print(f"      - {doc[0]}")
        print(f"        Title: {doc[1]}")
        print(f"        Pages: {doc[2]}")

    conn.close()
    print()


def verify_chromadb():
    """Verify ChromaDB vector database"""
    print("🔍 Verifying ChromaDB Vector Database...")
    print("-" * 50)

    client = chromadb.PersistentClient(path="database/vector_store")
    collection = client.get_collection("pid_chunks")

    chunk_count = collection.count()
    print(f"   Total chunks: {chunk_count}")

    # Get sample chunk
    if chunk_count > 0:
        results = collection.peek(limit=1)
        if results['documents']:
            sample_doc = results['documents'][0]
            sample_meta = results['metadatas'][0]

            print(f"\n   Sample Chunk:")
            print(f"      Document ID: {sample_meta.get('document_id')}")
            print(f"      Page: {sample_meta.get('page_number')}")
            print(f"      Text preview: {sample_doc[:100]}...")

    print()


def verify_images():
    """Verify extracted images"""
    print("🔍 Verifying Extracted Images...")
    print("-" * 50)

    processed_dir = Path("data/processed")

    if not processed_dir.exists():
        print("   ⚠️  No processed directory found")
        return

    doc_dirs = list(processed_dir.iterdir())

    for doc_dir in doc_dirs:
        if doc_dir.is_dir():
            images = list(doc_dir.glob("*.png"))
            print(f"   {doc_dir.name}:")
            print(f"      Images: {len(images)}")

            for img in sorted(images):
                size_mb = img.stat().st_size / (1024 * 1024)
                print(f"         - {img.name} ({size_mb:.1f} MB)")

    print()


def main():
    """Main verification"""
    print()
    print("=" * 50)
    print("  Ingestion Verification Report")
    print("=" * 50)
    print()

    verify_sqlite()
    verify_chromadb()
    verify_images()

    print("=" * 50)
    print("✅ Verification Complete!")
    print("=" * 50)
    print()


if __name__ == "__main__":
    main()
