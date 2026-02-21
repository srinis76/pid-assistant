"""
End-to-end RAG evaluation with LLM-as-judge scoring.

Metrics (each scored 0-5 by an LLM judge, then normalized to 0-100):
  - answer_correctness : How accurately the answer matches the ground truth
  - faithfulness       : Is the answer grounded in retrieved context (no hallucinations)
  - context_relevance  : Did the retriever fetch chunks relevant to the question

Usage:
  python scripts/eval_e2e.py [--dataset tests/eval_dataset.json]
                             [--out results/eval_e2e_<timestamp>.json]
                             [--top-k 3]
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

# Project root on path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import google.generativeai as genai

JUDGE_MODEL = "gemini-2.5-flash-lite"

JUDGE_PROMPT = """You are an expert evaluator for a P&ID (Piping and Instrumentation Diagram) question-answering system.

Score the following RAG system response on THREE dimensions. Return ONLY a JSON object.

---
QUESTION: {question}

GROUND TRUTH: {ground_truth}

RETRIEVED CONTEXT (what the system had access to):
{context}

SYSTEM ANSWER: {answer}
---

Score each dimension from 0 to 5 using these rubrics:

answer_correctness (0-5):
  5 = Fully correct, matches ground truth exactly or with equivalent meaning
  4 = Mostly correct, minor omission or imprecise wording
  3 = Partially correct, core fact right but missing key details
  2 = Partially incorrect, some right but a significant error
  1 = Mostly wrong, only tangentially related to ground truth
  0 = Completely wrong or irrelevant

faithfulness (0-5):
  5 = Every claim is directly supported by the retrieved context
  4 = Nearly all claims supported, one minor unsupported detail
  3 = Most claims supported but one moderate hallucination
  2 = Some claims supported but significant hallucination present
  1 = Mostly hallucinated, barely grounded in context
  0 = Completely hallucinated, nothing from context

context_relevance (0-5):
  5 = Retrieved context directly answers the question with all needed info
  4 = Context mostly relevant, one irrelevant chunk or missing minor detail
  3 = Context partially relevant, answer possible but incomplete
  2 = Context marginally relevant, requires significant inference
  1 = Context mostly irrelevant to the question
  0 = Context entirely irrelevant

Return this exact JSON structure:
{{
  "answer_correctness": <int 0-5>,
  "faithfulness": <int 0-5>,
  "context_relevance": <int 0-5>,
  "reasoning": {{
    "answer_correctness": "<one sentence explaining the score>",
    "faithfulness": "<one sentence explaining the score>",
    "context_relevance": "<one sentence explaining the score>"
  }}
}}"""


def init_judge():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(JUDGE_MODEL)


def judge_response(model, question, ground_truth, context, answer):
    """Call LLM judge. Returns scores dict or error dict."""
    prompt = JUDGE_PROMPT.format(
        question=question,
        ground_truth=ground_truth,
        context=context,
        answer=answer,
    )
    for attempt in range(3):
        try:
            resp = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"},
            )
            return json.loads(resp.text)
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                return {
                    "answer_correctness": None,
                    "faithfulness": None,
                    "context_relevance": None,
                    "error": str(e),
                    "reasoning": {},
                }


def run_eval(dataset_path, out_path, top_k):
    from app.rag_engine import RAGEngine

    print("\n" + "=" * 60)
    print("  End-to-End RAG Eval with LLM-as-Judge")
    print("=" * 60)

    with open(dataset_path) as f:
        dataset = json.load(f)

    test_cases = dataset["test_cases"]
    print(f"\nDataset : {dataset_path}  ({len(test_cases)} questions)")
    print(f"RAG top_k: {top_k}  |  Judge: {JUDGE_MODEL}\n")

    rag = RAGEngine()
    judge = init_judge()

    results = []
    for tc in test_cases:
        qid = tc["id"]
        question = tc["question"]
        ground_truth = tc["ground_truth"]
        category = tc["category"]

        print(f"[{qid}/{len(test_cases)}] {question}")

        # --- RAG query ---
        t0 = time.time()
        try:
            answer, meta = rag.query_rag(question, top_k=top_k)
            latency = round(time.time() - t0, 2)
            # Re-retrieve context string for the judge
            q_emb = rag.generate_query_embedding(question)
            chunks = rag.search_vector_db(q_emb, top_k)
            context = rag.assemble_context(chunks)
            retrieval_scores = meta.get("relevance_scores", [])
        except Exception as e:
            print(f"  RAG error: {e}")
            results.append({
                "id": qid, "question": question, "category": category,
                "ground_truth": ground_truth,
                "answer": None, "context": None,
                "scores": {"answer_correctness": 0, "faithfulness": 0, "context_relevance": 0},
                "error": str(e),
            })
            continue

        # --- Judge ---
        scores = judge_response(judge, question, ground_truth, context, answer)
        time.sleep(0.5)  # stay under rate limits

        ac = scores.get("answer_correctness")
        fa = scores.get("faithfulness")
        cr = scores.get("context_relevance")

        avg_rel = round(sum(retrieval_scores) / len(retrieval_scores), 3) if retrieval_scores else None
        print(f"  correctness={ac}/5  faithfulness={fa}/5  ctx_relevance={cr}/5  latency={latency}s")

        results.append({
            "id": qid,
            "question": question,
            "category": category,
            "ground_truth": ground_truth,
            "answer": answer,
            "context_snippet": context[:500] + "..." if len(context) > 500 else context,
            "retrieval": {
                "num_chunks": len(retrieval_scores),
                "relevance_scores": [round(s, 3) for s in retrieval_scores],
                "avg_cosine_similarity": avg_rel,
            },
            "latency_s": latency,
            "scores": {"answer_correctness": ac, "faithfulness": fa, "context_relevance": cr},
            "reasoning": scores.get("reasoning", {}),
            "error": scores.get("error"),
        })

    # --- Aggregate ---
    valid = [r for r in results if r["scores"].get("answer_correctness") is not None]
    n = len(valid)

    def pct(key):
        vals = [r["scores"][key] for r in valid if r["scores"].get(key) is not None]
        return round(sum(vals) / len(vals) * 20, 1) if vals else None

    def raw_avg(key):
        vals = [r["scores"][key] for r in valid if r["scores"].get(key) is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    agg = {
        "answer_correctness_pct": pct("answer_correctness"),
        "faithfulness_pct": pct("faithfulness"),
        "context_relevance_pct": pct("context_relevance"),
        "raw_avg_5": {
            "answer_correctness": raw_avg("answer_correctness"),
            "faithfulness": raw_avg("faithfulness"),
            "context_relevance": raw_avg("context_relevance"),
        },
    }
    overall = [v for v in [agg["answer_correctness_pct"], agg["faithfulness_pct"], agg["context_relevance_pct"]] if v is not None]
    agg["overall_pct"] = round(sum(overall) / len(overall), 1) if overall else None

    # --- Per-category ---
    cats = {}
    for r in valid:
        cat = r["category"]
        cats.setdefault(cat, {"count": 0, "answer_correctness": [], "faithfulness": [], "context_relevance": []})
        cats[cat]["count"] += 1
        for k in ["answer_correctness", "faithfulness", "context_relevance"]:
            if r["scores"].get(k) is not None:
                cats[cat][k].append(r["scores"][k])

    per_category = {}
    for cat, d in cats.items():
        per_category[cat] = {
            "count": d["count"],
            "answer_correctness_pct": round(sum(d["answer_correctness"]) / len(d["answer_correctness"]) * 20, 1) if d["answer_correctness"] else None,
            "faithfulness_pct": round(sum(d["faithfulness"]) / len(d["faithfulness"]) * 20, 1) if d["faithfulness"] else None,
            "context_relevance_pct": round(sum(d["context_relevance"]) / len(d["context_relevance"]) * 20, 1) if d["context_relevance"] else None,
        }

    avg_latency = round(sum(r["latency_s"] for r in results if r.get("latency_s")) / max(len(results), 1), 2)

    output = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "dataset": dataset_path,
            "judge_model": JUDGE_MODEL,
            "rag_top_k": top_k,
            "test_cases": len(test_cases),
            "valid_cases": n,
        },
        "aggregate_scores": agg,
        "per_category": per_category,
        "avg_latency_s": avg_latency,
        "detailed_results": results,
    }

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    # --- Print summary ---
    print("\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)
    print(f"  Questions evaluated  : {n}/{len(test_cases)}")
    print(f"  Avg latency          : {avg_latency}s")
    print()
    print(f"  Answer correctness   : {agg['answer_correctness_pct']}%  ({agg['raw_avg_5']['answer_correctness']}/5)")
    print(f"  Faithfulness         : {agg['faithfulness_pct']}%  ({agg['raw_avg_5']['faithfulness']}/5)")
    print(f"  Context relevance    : {agg['context_relevance_pct']}%  ({agg['raw_avg_5']['context_relevance']}/5)")
    print(f"  OVERALL              : {agg['overall_pct']}%")
    print()
    print("  Per-category breakdown:")
    for cat, s in per_category.items():
        print(f"    {cat:<30} correctness={s['answer_correctness_pct']}%  faith={s['faithfulness_pct']}%  ctx={s['context_relevance_pct']}%")
    print()
    print(f"  Saved → {out_path}")
    print("=" * 60 + "\n")

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="End-to-end RAG eval with LLM-as-judge")
    parser.add_argument("--dataset", default="tests/eval_dataset.json")
    parser.add_argument("--out", default=f"results/eval_e2e_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    run_eval(args.dataset, args.out, args.top_k)
