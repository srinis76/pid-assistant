"""
Initialize ChromaDB vector database for P&ID Assistant
"""
import chromadb
from pathlib import Path


def init_chromadb():
    """Initialize ChromaDB with collection for P&ID document chunks"""

    # Ensure database directory exists
    db_dir = Path("database/vector_store")
    db_dir.mkdir(parents=True, exist_ok=True)

    print(f"Initializing ChromaDB at: {db_dir}")

    # Create persistent client
    client = chromadb.PersistentClient(path=str(db_dir))

    # Get or create collection
    try:
        # Try to get existing collection
        collection = client.get_collection("pid_chunks")
        print(f"✓ Collection 'pid_chunks' already exists")
        print(f"  - Current document count: {collection.count()}")
    except Exception:
        # Create new collection if it doesn't exist
        collection = client.create_collection(
            name="pid_chunks",
            metadata={"description": "P&ID document chunks with embeddings"}
        )
        print(f"✓ Created new collection 'pid_chunks'")
        print(f"  - Ready for document ingestion")

    # Display collection info
    print(f"\nChromaDB initialized successfully!")
    print(f"  - Path: {db_dir}")
    print(f"  - Collection: pid_chunks")
    print(f"  - Status: Ready")

    return collection


if __name__ == "__main__":
    init_chromadb()
