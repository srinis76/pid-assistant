"""
V1 vs V2 Ingestion Comparison Script

Captures structural metrics and RAG answer quality for the current
state of the database, to enable before/after comparison.

Usage:
    # Capture V1 baseline (run BEFORE V2 ingestion)
    python scripts/eval_v1_v2_comparison.py --label v1

    # Capture V2 results (run AFTER V2 ingestion)
    python scripts/eval_v1_v2_comparison.py --label v2

    # Generate comparison report from saved results
    python scripts/eval_v1_v2_comparison.py --compare
"""

import os
import sys
import json
import time
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import chromadb
from app.rag_engine import RAGEngine


RESULTS_DIR = Path("results")
EVAL_DATASET = Path("tests/eval_dataset.json")
SQLITE_DB = Path("database/assets.db")
VECTOR_DB = Path("database/vector_store")


def capture_structural_metrics() -> Dict:
    """Capture ChromaDB and SQLite structural metrics."""
    metrics = {}

    # ChromaDB metrics
    client = chromadb.PersistentClient(path=str(VECTOR_DB))
    collection = client.get_collection("pid_chunks")
    all_data = collection.get(include=["documents", "metadatas"])

    metrics["chromadb"] = {
        "total_chunks": collection.count(),
        "chunk_ids": all_data["ids"],
        "metadata_fields": list(all_data["metadatas"][0].keys()) if all_data["metadatas"] else [],
        "avg_chunk_length": (
            sum(len(doc) for doc in all_data["documents"]) / len(all_data["documents"])
            if all_data["documents"] else 0
        ),
        "min_chunk_length": min((len(doc) for doc in all_data["documents"]), default=0),
        "max_chunk_length": max((len(doc) for doc in all_data["documents"]), default=0),
        "sample_metadata": all_data["metadatas"][:3] if all_data["metadatas"] else [],
    }

    # Check for V2-style metadata
    has_equipment_tag = any(
        "equipment_tag" in m for m in all_data["metadatas"]
    ) if all_data["metadatas"] else False
    has_chunk_type = any(
        "chunk_type" in m for m in all_data["metadatas"]
    ) if all_data["metadatas"] else False
    metrics["chromadb"]["has_v2_metadata"] = has_equipment_tag or has_chunk_type

    # SQLite metrics
    conn = sqlite3.connect(str(SQLITE_DB))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM documents")
    metrics["sqlite_documents"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM document_pages")
    metrics["sqlite_pages"] = cursor.fetchone()[0]

    # V2 tables (may not exist or may be empty)
    for table in ["equipment", "instruments", "equipment_instruments", "connections"]:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            metrics[f"sqlite_{table}"] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            metrics[f"sqlite_{table}"] = "table_not_found"

    conn.close()
    return metrics


def compute_keyword_score(answer: str, expected_context: List[str]) -> float:
    """Compute keyword match rate for a single query."""
    if not expected_context:
        return 0.0
    answer_lower = answer.lower()
    matches = sum(1 for kw in expected_context if kw.lower() in answer_lower)
    return matches / len(expected_context)


def run_eval_queries(rag_engine: RAGEngine, test_cases: List[Dict]) -> List[Dict]:
    """Run all test queries and capture results."""
    results = []

    for i, tc in enumerate(test_cases, 1):
        question = tc["question"]
        print(f"  [{i}/{len(test_cases)}] {question}")

        start = time.time()
        try:
            answer, metadata = rag_engine.query_rag(question, top_k=3)
            elapsed = time.time() - start

            # Get retrieved chunk texts
            query_embedding = rag_engine.generate_query_embedding(question)
            search_results = rag_engine.search_vector_db(query_embedding, top_k=3)
            contexts = [r["text"] for r in search_results]

            keyword_score = compute_keyword_score(answer, tc.get("expected_context", []))

            results.append({
                "id": tc["id"],
                "question": question,
                "category": tc["category"],
                "ground_truth": tc["ground_truth"],
                "answer": answer,
                "contexts_retrieved": len(contexts),
                "context_snippets": [c[:200] for c in contexts],
                "relevance_scores": metadata.get("relevance_scores", []),
                "keyword_score": round(keyword_score, 3),
                "response_time_s": round(elapsed, 2),
                "status": "success",
            })

        except Exception as e:
            elapsed = time.time() - start
            results.append({
                "id": tc["id"],
                "question": question,
                "category": tc["category"],
                "ground_truth": tc["ground_truth"],
                "answer": f"ERROR: {e}",
                "contexts_retrieved": 0,
                "context_snippets": [],
                "relevance_scores": [],
                "keyword_score": 0.0,
                "response_time_s": round(elapsed, 2),
                "status": "error",
            })

    return results


def compute_aggregate_scores(query_results: List[Dict]) -> Dict:
    """Compute aggregate metrics from query results."""
    total = len(query_results)
    successful = [r for r in query_results if r["status"] == "success"]

    avg_keyword = sum(r["keyword_score"] for r in successful) / len(successful) if successful else 0
    avg_relevance = (
        sum(sum(r["relevance_scores"]) / len(r["relevance_scores"])
            for r in successful if r["relevance_scores"])
        / len([r for r in successful if r["relevance_scores"]])
        if any(r["relevance_scores"] for r in successful) else 0
    )
    avg_time = sum(r["response_time_s"] for r in successful) / len(successful) if successful else 0

    # Per-category breakdown
    categories = {}
    for r in query_results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"count": 0, "keyword_scores": [], "times": []}
        categories[cat]["count"] += 1
        if r["status"] == "success":
            categories[cat]["keyword_scores"].append(r["keyword_score"])
            categories[cat]["times"].append(r["response_time_s"])

    category_summary = {}
    for cat, data in categories.items():
        category_summary[cat] = {
            "count": data["count"],
            "avg_keyword_score": round(
                sum(data["keyword_scores"]) / len(data["keyword_scores"]), 3
            ) if data["keyword_scores"] else 0,
            "avg_response_time_s": round(
                sum(data["times"]) / len(data["times"]), 2
            ) if data["times"] else 0,
        }

    return {
        "total_queries": total,
        "success_rate": round(len(successful) / total, 3) if total else 0,
        "avg_keyword_match_score": round(avg_keyword, 3),
        "avg_relevance_score": round(avg_relevance, 3),
        "avg_response_time_s": round(avg_time, 2),
        "by_category": category_summary,
    }


def capture(label: str):
    """Capture metrics and query results for the current DB state."""
    print(f"\n{'=' * 60}")
    print(f"  Capturing {label.upper()} Metrics")
    print(f"{'=' * 60}\n")

    # Load test dataset
    with open(EVAL_DATASET) as f:
        dataset = json.load(f)
    test_cases = dataset["test_cases"]
    print(f"Loaded {len(test_cases)} test queries\n")

    # 1. Structural metrics
    print("Collecting structural metrics...")
    structural = capture_structural_metrics()
    print(f"  ChromaDB chunks: {structural['chromadb']['total_chunks']}")
    print(f"  Avg chunk length: {structural['chromadb']['avg_chunk_length']:.0f} chars")
    print(f"  V2 metadata present: {structural['chromadb']['has_v2_metadata']}")
    print(f"  SQLite equipment: {structural.get('sqlite_equipment', 'N/A')}")
    print(f"  SQLite instruments: {structural.get('sqlite_instruments', 'N/A')}")
    print()

    # 2. RAG query evaluation
    print("Initializing RAG engine...")
    rag_engine = RAGEngine()
    print()

    print("Running evaluation queries...")
    query_results = run_eval_queries(rag_engine, test_cases)
    print()

    # 3. Aggregate scores
    scores = compute_aggregate_scores(query_results)

    # 4. Build output
    output = {
        "label": label,
        "timestamp": datetime.now().isoformat(),
        "structural_metrics": structural,
        "aggregate_scores": scores,
        "query_results": query_results,
    }

    # Save
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULTS_DIR / f"{label}_baseline.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    # Print summary
    print(f"{'=' * 60}")
    print(f"  {label.upper()} RESULTS SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Chunks:              {structural['chromadb']['total_chunks']}")
    print(f"  Avg chunk length:    {structural['chromadb']['avg_chunk_length']:.0f} chars")
    print(f"  V2 metadata:         {structural['chromadb']['has_v2_metadata']}")
    print(f"  Equipment records:   {structural.get('sqlite_equipment', 'N/A')}")
    print(f"  Instrument records:  {structural.get('sqlite_instruments', 'N/A')}")
    print(f"  ---")
    print(f"  Success rate:        {scores['success_rate']:.1%}")
    print(f"  Avg keyword match:   {scores['avg_keyword_match_score']:.1%}")
    print(f"  Avg relevance:       {scores['avg_relevance_score']:.3f}")
    print(f"  Avg response time:   {scores['avg_response_time_s']:.2f}s")
    print(f"{'=' * 60}")
    print(f"\nSaved to: {output_path}")


def compare():
    """Generate side-by-side comparison from saved V1 and V2 results."""
    v1_path = RESULTS_DIR / "v1_baseline.json"
    v2_path = RESULTS_DIR / "v2_baseline.json"

    if not v1_path.exists():
        print(f"Error: V1 results not found at {v1_path}")
        print("Run first: python scripts/eval_v1_v2_comparison.py --label v1")
        sys.exit(1)

    if not v2_path.exists():
        print(f"Error: V2 results not found at {v2_path}")
        print("Run first: python scripts/eval_v1_v2_comparison.py --label v2")
        sys.exit(1)

    with open(v1_path) as f:
        v1 = json.load(f)
    with open(v2_path) as f:
        v2 = json.load(f)

    v1s = v1["structural_metrics"]
    v2s = v2["structural_metrics"]
    v1a = v1["aggregate_scores"]
    v2a = v2["aggregate_scores"]

    # Build comparison
    comparison = {
        "generated": datetime.now().isoformat(),
        "structural": {
            "chromadb_chunks": {"v1": v1s["chromadb"]["total_chunks"], "v2": v2s["chromadb"]["total_chunks"]},
            "avg_chunk_length": {"v1": round(v1s["chromadb"]["avg_chunk_length"]), "v2": round(v2s["chromadb"]["avg_chunk_length"])},
            "v2_metadata": {"v1": v1s["chromadb"]["has_v2_metadata"], "v2": v2s["chromadb"]["has_v2_metadata"]},
            "equipment_records": {"v1": v1s.get("sqlite_equipment", 0), "v2": v2s.get("sqlite_equipment", 0)},
            "instrument_records": {"v1": v1s.get("sqlite_instruments", 0), "v2": v2s.get("sqlite_instruments", 0)},
            "connection_records": {"v1": v1s.get("sqlite_connections", 0), "v2": v2s.get("sqlite_connections", 0)},
        },
        "quality": {
            "keyword_match_score": {"v1": v1a["avg_keyword_match_score"], "v2": v2a["avg_keyword_match_score"]},
            "avg_relevance": {"v1": v1a["avg_relevance_score"], "v2": v2a["avg_relevance_score"]},
            "avg_response_time_s": {"v1": v1a["avg_response_time_s"], "v2": v2a["avg_response_time_s"]},
            "success_rate": {"v1": v1a["success_rate"], "v2": v2a["success_rate"]},
        },
        "per_query": [],
    }

    # Per-query comparison
    v1_by_id = {r["id"]: r for r in v1["query_results"]}
    v2_by_id = {r["id"]: r for r in v2["query_results"]}

    for qid in sorted(v1_by_id.keys()):
        r1 = v1_by_id[qid]
        r2 = v2_by_id.get(qid, {})
        comparison["per_query"].append({
            "id": qid,
            "question": r1["question"],
            "category": r1["category"],
            "v1_answer": r1["answer"][:300],
            "v2_answer": r2.get("answer", "N/A")[:300],
            "v1_keyword_score": r1["keyword_score"],
            "v2_keyword_score": r2.get("keyword_score", 0),
            "v1_relevance": r1["relevance_scores"],
            "v2_relevance": r2.get("relevance_scores", []),
            "v1_time": r1["response_time_s"],
            "v2_time": r2.get("response_time_s", 0),
        })

    # Save
    comp_path = RESULTS_DIR / "v1_v2_comparison.json"
    with open(comp_path, "w") as f:
        json.dump(comparison, f, indent=2)

    # Print comparison table
    print(f"\n{'=' * 70}")
    print(f"  V1 vs V2 COMPARISON")
    print(f"{'=' * 70}\n")

    print(f"{'STRUCTURAL METRICS':<35} {'V1':>12} {'V2':>12} {'Delta':>10}")
    print(f"{'-' * 70}")
    for key, vals in comparison["structural"].items():
        v1v = vals["v1"]
        v2v = vals["v2"]
        if isinstance(v1v, (int, float)) and isinstance(v2v, (int, float)):
            delta = v2v - v1v
            sign = "+" if delta > 0 else ""
            print(f"  {key:<33} {str(v1v):>12} {str(v2v):>12} {sign}{delta:>9}")
        else:
            print(f"  {key:<33} {str(v1v):>12} {str(v2v):>12}")

    print()
    print(f"{'QUALITY METRICS':<35} {'V1':>12} {'V2':>12} {'Delta':>10}")
    print(f"{'-' * 70}")
    for key, vals in comparison["quality"].items():
        v1v = vals["v1"]
        v2v = vals["v2"]
        delta = v2v - v1v
        sign = "+" if delta > 0 else ""
        print(f"  {key:<33} {v1v:>12.3f} {v2v:>12.3f} {sign}{delta:>9.3f}")

    print()
    print(f"{'PER-QUERY KEYWORD SCORES':<35} {'V1':>12} {'V2':>12} {'Delta':>10}")
    print(f"{'-' * 70}")
    for q in comparison["per_query"]:
        label = q["question"][:33]
        v1k = q["v1_keyword_score"]
        v2k = q["v2_keyword_score"]
        delta = v2k - v1k
        sign = "+" if delta > 0 else ""
        print(f"  {label:<33} {v1k:>12.3f} {v2k:>12.3f} {sign}{delta:>9.3f}")

    print(f"\n{'=' * 70}")
    print(f"Saved to: {comp_path}")


def main():
    parser = argparse.ArgumentParser(description="V1 vs V2 Ingestion Comparison")
    parser.add_argument("--label", choices=["v1", "v2"],
                        help="Capture metrics for this version label")
    parser.add_argument("--compare", action="store_true",
                        help="Generate comparison from saved v1 and v2 results")
    args = parser.parse_args()

    if args.compare:
        compare()
    elif args.label:
        capture(args.label)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
