"""
Check if embeddings were properly generated and stored in ChromaDB
"""
import chromadb


def check_embeddings():
    """Verify embeddings in ChromaDB"""
    print("\n" + "=" * 60)
    print("  Checking Embeddings in ChromaDB")
    print("=" * 60 + "\n")

    # Connect to ChromaDB
    client = chromadb.PersistentClient(path="database/vector_store")
    collection = client.get_collection("pid_chunks")

    # Get collection info
    total_chunks = collection.count()
    print(f"📊 Total chunks in database: {total_chunks}\n")

    if total_chunks == 0:
        print("⚠️  No chunks found in database!")
        return

    # Get a sample chunk with its embedding
    results = collection.get(
        limit=3,
        include=["embeddings", "documents", "metadatas"]
    )

    print("🔍 Sample Chunks:\n")

    for i in range(min(3, len(results['ids']))):
        chunk_id = results['ids'][i]
        document = results['documents'][i]
        metadata = results['metadatas'][i]
        embedding = results['embeddings'][i]

        print(f"Chunk {i+1}:")
        print(f"  ID: {chunk_id}")
        print(f"  Document ID: {metadata.get('document_id')}")
        print(f"  Page Number: {metadata.get('page_number')}")
        print(f"  Page Title: {metadata.get('page_title')}")
        print(f"  Text Length: {len(document)} characters")
        print(f"  Text Preview: {document[:100]}...")

        # Check embedding
        if embedding is not None and len(embedding) > 0:
            print(f"  ✅ Embedding: {len(embedding)} dimensions")
            print(f"     First 5 values: {embedding[:5]}")
        else:
            print(f"  ❌ No embedding found!")

        print()

    # Test a simple query
    print("🔎 Testing Vector Search:\n")
    print("   Query: 'pressure separator'\n")

    query_results = collection.query(
        query_texts=["pressure separator"],
        n_results=2
    )

    if query_results['documents']:
        print(f"   Found {len(query_results['documents'][0])} relevant chunks:\n")

        for i, doc in enumerate(query_results['documents'][0][:2]):
            meta = query_results['metadatas'][0][i]
            distance = query_results['distances'][0][i]

            print(f"   Result {i+1}:")
            print(f"     Page: {meta.get('page_number')}")
            print(f"     Relevance Score: {1 - distance:.4f}")
            print(f"     Preview: {doc[:150]}...")
            print()

    print("=" * 60)
    print("✅ Embeddings verification complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    check_embeddings()
