"""
RAG Top-K Retrieval Accuracy evaluation.

For each question, embeds the query, retrieves top-K chunks, and checks
whether ALL gold chunk IDs appear in the results (hit@K).

Metrics reported:
  hit@1, hit@3, hit@5   — fraction of questions where gold chunk(s) are found
  MRR@10                — Mean Reciprocal Rank (position of first gold chunk)
  answer_coverage       — of questions where retrieval hits, what % have answer_in_chunk=True
                          (separates retrieval failure from extraction failure)

Usage:
  python scripts/eval_retrieval.py [--dataset tests/retrieval_eval_dataset.json]
                                   [--out results/retrieval_eval.json]
                                   [--k 1 3 5]
"""

import os, sys, json, argparse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import chromadb
from openai import OpenAI


def run_eval(dataset_path, out_path, k_values):
    with open(dataset_path) as f:
        ds = json.load(f)
    questions = ds["questions"]

    # Init retriever
    client = chromadb.PersistentClient(
        path=os.getenv("VECTOR_DB_PATH", str(ROOT / "database/vector_store"))
    )
    coll = client.get_collection("pid_chunks")
    openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    emb_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    max_k = max(k_values)
    results = []

    print(f"\n{'='*60}")
    print("  RAG Top-K Retrieval Accuracy Eval")
    print(f"{'='*60}")
    print(f"Dataset : {dataset_path}  ({len(questions)} questions)")
    print(f"K values: {k_values}  |  Collection: {coll.count()} chunks\n")

    for q in questions:
        qid = q["id"]
        question = q["question"]
        gold_ids = set(q["gold_chunk_ids"])
        answer_in_chunk = q["answer_in_chunk"]

        # Embed
        emb = openai.embeddings.create(model=emb_model, input=question).data[0].embedding

        # Retrieve top max_k
        res = coll.query(
            query_embeddings=[emb],
            n_results=min(max_k, coll.count()),
            include=["metadatas", "distances"]
        )
        retrieved_ids = [res["ids"][0][i] for i in range(len(res["ids"][0]))]
        distances = res["distances"][0]
        similarities = [round(1 - d, 4) for d in distances]

        # Hit@K for each K
        hits = {}
        for k in k_values:
            top_k_ids = set(retrieved_ids[:k])
            hits[f"hit@{k}"] = gold_ids.issubset(top_k_ids)

        # MRR: rank of FIRST gold chunk found
        mrr_rank = None
        for rank, rid in enumerate(retrieved_ids, start=1):
            if rid in gold_ids:
                mrr_rank = rank
                break

        # Rank of each gold chunk
        gold_ranks = {}
        for gid in gold_ids:
            if gid in retrieved_ids:
                gold_ranks[gid] = retrieved_ids.index(gid) + 1
            else:
                gold_ranks[gid] = None

        result = {
            "id": qid,
            "question": question,
            "category": q["category"],
            "gold_chunk_ids": list(gold_ids),
            "answer_in_chunk": answer_in_chunk,
            "retrieved_ids": retrieved_ids[:max_k],
            "similarities": similarities[:max_k],
            "gold_ranks": gold_ranks,
            "mrr_rank": mrr_rank,
            "mrr_score": round(1 / mrr_rank, 4) if mrr_rank else 0.0,
            "hits": hits,
        }
        results.append(result)

        status = " ".join(
            f"hit@{k}={'Y' if hits[f'hit@{k}'] else 'N'}" for k in k_values
        )
        rank_str = ", ".join(
            f"{gid}=rank{r}" if r else f"{gid}=MISS"
            for gid, r in gold_ranks.items()
        )
        print(f"  Q{qid:2d} [{q['category'][:12]:<12}] {status}  ranks:[{rank_str}]")

    # Aggregate
    n = len(results)
    agg = {}
    for k in k_values:
        key = f"hit@{k}"
        agg[key] = round(sum(1 for r in results if r["hits"][key]) / n, 4)

    agg["MRR@10"] = round(sum(r["mrr_score"] for r in results) / n, 4)

    # Answer coverage: among hit@3, how many have answer_in_chunk=True
    hit3_results = [r for r in results if r["hits"].get("hit@3", False)]
    agg["answer_coverage_at_3"] = round(
        sum(1 for r in hit3_results if next(
            (q["answer_in_chunk"] for q in questions if q["id"] == r["id"]), False
        )) / len(hit3_results), 4
    ) if hit3_results else 0.0

    # Per-category
    cats = {}
    for r in results:
        cat = r["category"]
        cats.setdefault(cat, [])
        cats[cat].append(r)

    per_category = {}
    for cat, rs in cats.items():
        per_category[cat] = {
            "count": len(rs),
            "hit@3": round(sum(1 for r in rs if r["hits"].get("hit@3", False)) / len(rs), 3),
        }

    output = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "dataset": dataset_path,
            "embedding_model": emb_model,
            "k_values": k_values,
            "total_questions": n,
            "collection_size": coll.count(),
        },
        "aggregate": agg,
        "per_category": per_category,
        "detailed_results": results,
    }

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print("  RETRIEVAL ACCURACY SUMMARY")
    print(f"{'='*60}")
    for k in k_values:
        pct = round(agg[f"hit@{k}"] * 100, 1)
        bar = "#" * int(pct / 5)
        print(f"  hit@{k:<2}  {pct:5.1f}%  {bar}")
    print(f"  MRR@10  {round(agg['MRR@10']*100,1):5.1f}%")
    print(f"  Answer coverage @3 (retrieval OK + answer in chunk): {round(agg['answer_coverage_at_3']*100,1)}%")
    print()
    print("  Per-category hit@3:")
    for cat, s in per_category.items():
        pct = round(s["hit@3"] * 100, 1)
        print(f"    {cat:<20} {pct:5.1f}%  (n={s['count']})")
    print()

    # Misses
    misses = [r for r in results if not r["hits"].get("hit@3", False)]
    if misses:
        print("  Retrieval misses at K=3:")
        for r in misses:
            ranks = ", ".join(
                f"{gid}=rank{rank}" if rank else f"{gid}=NOT_FOUND"
                for gid, rank in r["gold_ranks"].items()
            )
            print(f"    Q{r['id']:2d}: {r['question'][:55]} [{ranks}]")
    else:
        print("  No misses at K=3")

    print(f"\n  Saved -> {out_path}")
    print(f"{'='*60}\n")

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG Top-K retrieval accuracy eval")
    parser.add_argument("--dataset", default="tests/retrieval_eval_dataset.json")
    parser.add_argument("--out", default=f"results/retrieval_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    parser.add_argument("--k", nargs="+", type=int, default=[1, 3, 5])
    args = parser.parse_args()

    run_eval(args.dataset, args.out, args.k)
