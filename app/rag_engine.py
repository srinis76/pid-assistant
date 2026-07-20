"""
RAG Engine for P&ID Assistant

Retrieves relevant context from vector database and generates answers using LLM.
"""

import os
from typing import List, Dict, Tuple
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

try:
    from app.llm_adapter import LLMAdapter
    from app.phoenix_tracer import init_tracing
    from app.hybrid_retriever import HybridRetriever
except ModuleNotFoundError:
    from llm_adapter import LLMAdapter
    from phoenix_tracer import init_tracing
    from hybrid_retriever import HybridRetriever

load_dotenv()

# Initialize Phoenix tracing if enabled
_ENABLE_TRACING = os.getenv("ENABLE_PHOENIX_TRACING", "false").lower() == "true"
if _ENABLE_TRACING:
    init_tracing(project_name="pid-assistant")


class RAGEngine:
    """RAG query engine with vector search and LLM generation"""

    def __init__(self):
        # Initialize ChromaDB (use absolute path)
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        vector_db_path = os.getenv("VECTOR_DB_PATH", str(project_root / "database/vector_store"))
        self.chroma_client = chromadb.PersistentClient(path=vector_db_path)
        self.collection = self.chroma_client.get_collection("pid_chunks")

        # Initialize OpenAI for query embeddings
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

        # Initialize LLM adapter
        self.llm_adapter = LLMAdapter()

        # Retrieval mode: "vector" (dense only) or "hybrid" (dense + BM25 via RRF)
        self.retrieval_mode = os.getenv("RETRIEVAL_MODE", "vector").lower()
        self.candidate_k = int(os.getenv("HYBRID_CANDIDATE_K", "10"))
        self.hybrid_retriever = None
        if self.retrieval_mode == "hybrid":
            self.hybrid_retriever = HybridRetriever(
                self.collection,
                dense_weight=float(os.getenv("HYBRID_DENSE_WEIGHT", "1.0")),
                sparse_weight=float(os.getenv("HYBRID_SPARSE_WEIGHT", "1.0")),
                rrf_k=int(os.getenv("HYBRID_RRF_K", "60")),
            )

        print(f"📚 RAG Engine initialized")
        print(f"   Vector DB: {vector_db_path}")
        print(f"   Collection: pid_chunks ({self.collection.count()} chunks)")
        print(f"   Embedding model: {self.embedding_model}")
        print(f"   Retrieval mode: {self.retrieval_mode}")
        print()

    def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for query using OpenAI API"""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=query
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"⚠️  Error generating query embedding: {e}")
            raise

    def search_vector_db(
        self,
        query_embedding: List[float],
        top_k: int = 3
    ) -> List[Dict]:
        """
        Search ChromaDB for similar chunks

        Returns:
            List of dicts with 'text', 'metadata', 'distance'
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    formatted_results.append({
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i]
                    })

            return formatted_results

        except Exception as e:
            print(f"⚠️  Error searching vector DB: {e}")
            raise

    def assemble_context(self, results: List[Dict]) -> str:
        """
        Format retrieved chunks into context string

        Include: chunk text, page number, document name
        """
        if not results:
            return "No relevant context found."

        context_parts = []
        for i, result in enumerate(results):
            metadata = result['metadata']
            text = result['text']
            # Dense results carry 'distance' (cosine); hybrid results carry a
            # 'fusion_score' from RRF. Prefer the similarity when available.
            if 'distance' in result:
                relevance = 1 - result['distance']
            else:
                relevance = result.get('fusion_score', 0.0)

            context_parts.append(
                f"[Source {i+1} - Page {metadata.get('page_number', 'N/A')} - Relevance: {relevance:.2f}]\n"
                f"{text}\n"
            )

        return "\n---\n".join(context_parts)

    def query_rag(self, query: str, top_k: int = 3) -> Tuple[str, Dict]:
        """
        Main RAG query function

        Args:
            query: User question
            top_k: Number of chunks to retrieve

        Returns:
            Tuple of (answer, metadata)
        """
        print(f"🔍 Processing RAG query: \"{query}\"")
        print(f"   Retrieving top {top_k} relevant chunks...")

        # 1. Generate query embedding
        query_embedding = self.generate_query_embedding(query)
        print(f"   ✓ Generated query embedding ({len(query_embedding)} dimensions)")

        # 2. Retrieve — hybrid (dense + BM25 via RRF) or dense-only
        if self.hybrid_retriever is not None:
            results = self.hybrid_retriever.retrieve(
                query, query_embedding, top_k=top_k, candidate_k=self.candidate_k
            )
            print(f"   ✓ Hybrid retrieval found {len(results)} chunks "
                  f"(dense+BM25 fused, candidate_k={self.candidate_k})")
        else:
            results = self.search_vector_db(query_embedding, top_k)
            print(f"   ✓ Found {len(results)} relevant chunks")

        if not results:
            return "I couldn't find any relevant information in the P&ID documents.", {}

        # 3. Assemble context
        context = self.assemble_context(results)
        print(f"   ✓ Assembled context ({len(context)} characters)")

        # 4. Build prompt
        prompt = f"""You are a technical assistant helping with P&ID (Piping and Instrumentation Diagram) documents for oil and gas operations.

Context from P&ID documentation:
{context}

User question: {query}

Instructions:
- Provide a clear, technical answer based ONLY on the context above
- If the context doesn't contain enough information, say so
- Include specific tag numbers, equipment IDs, or specifications when mentioned
- Keep the answer concise and professional

Answer:"""

        # 5. Call LLM
        print(f"   🤖 Generating answer...")
        answer = self.llm_adapter.call_llm(prompt, images=None, query_type="rag")

        # Prepare metadata
        metadata = {
            'num_chunks_retrieved': len(results),
            'retrieval_mode': self.retrieval_mode,
            'sources': [r['metadata'] for r in results],
            'relevance_scores': [
                (1 - r['distance']) if 'distance' in r else r.get('fusion_score', 0.0)
                for r in results
            ]
        }

        print(f"   ✓ Answer generated\n")

        return answer, metadata


# Test function
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Testing RAG Engine")
    print("="*60 + "\n")

    # Initialize RAG engine
    rag = RAGEngine()

    # Test queries
    test_queries = [
        "What is V-101?",
        "What are the operating conditions for the high pressure separator?",
        "Tell me about PSV-101"
    ]

    for query in test_queries:
        print("\n" + "="*60)
        answer, metadata = rag.query_rag(query, top_k=3)

        print(f"Query: {query}")
        print(f"\nAnswer:\n{answer}")
        print(f"\nMetadata:")
        print(f"  Sources: {len(metadata['sources'])} chunks")
        print(f"  Relevance scores: {[f'{s:.2f}' for s in metadata['relevance_scores']]}")
        print("="*60)

    # Display session summary
    print("\n" + rag.llm_adapter.get_session_summary())

    print("\n" + "="*60)
    print("✅ RAG Engine test complete!")
    print("="*60 + "\n")
