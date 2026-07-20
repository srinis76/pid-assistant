"""
Cross-model evaluation matrix (via OpenRouter).

Runs the SAME RAG pipeline across multiple LLMs — swapping only the generation
model through OpenRouter — and reports quality, latency, and cost side by side.
Retrieval (embeddings + vector store) is identical for every model, so any
difference in the numbers is the model, not the pipeline.

This is the "swap any model, let the evals guard quality" story: model choice
becomes a data-driven decision instead of a guess.

Quality is scored 0-5 by a fixed LLM judge (answer_correctness + faithfulness),
normalized to 0-100. Cost is the real per-call cost reported by OpenRouter.

Usage:
  python scripts/eval_matrix.py
  python scripts/eval_matrix.py --models openai/gpt-4o-mini google/gemini-2.5-flash-lite
  python scripts/eval_matrix.py --dataset tests/eval_dataset.json --top-k 3
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from openai import OpenAI


# Default line-up: cheap + diverse across providers, all via OpenRouter.
DEFAULT_MODELS = [
    "openai/gpt-4o-mini",
    "google/gemini-2.5-flash-lite",
    "meta-llama/llama-3.3-70b-instruct",
]

# Fixed judge — kept constant so scores are comparable across candidate models.
JUDGE_MODEL = "openai/gpt-4o-mini"

JUDGE_PROMPT = """You are an expert evaluator for a P&ID (Piping and Instrumentation Diagram) QA system.

Score the SYSTEM ANSWER on two dimensions. Return ONLY a JSON object.

---
QUESTION: {question}

GROUND TRUTH: {ground_truth}

RETRIEVED CONTEXT (what the system had access to):
{context}

SYSTEM ANSWER: {answer}
---

answer_correctness (0-5): 5=matches ground truth in meaning; 3=core fact right, details missing; 0=wrong/irrelevant.
faithfulness (0-5): 5=every claim supported by context; 3=one moderate hallucination; 0=entirely hallucinated.

Return exactly:
{{"answer_correctness": <int 0-5>, "faithfulness": <int 0-5>, "reason": "<one sentence>"}}"""


def get_judge_client():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")
    return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")


def judge(client, question, ground_truth, context, answer):
    """Score one answer 0-5 on correctness + faithfulness. Returns dict."""
    prompt = JUDGE_PROMPT.format(
        question=question, ground_truth=ground_truth, context=context, answer=answer
    )
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=JUDGE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0,
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                return {"answer_correctness": None, "faithfulness": None, "error": str(e)}


def build_context_text(rag, meta):
    """
    Reconstruct the retrieved chunks' full text from query_rag metadata.

    query_rag returns source *metadata* (tags), not the chunk text. To score
    faithfulness the judge needs the actual text the model was grounded on, so
    we map each source back to its ChromaDB chunk id and fetch the document.
    Equipment chunk ids follow `v2_equip_<TAG>`; we fall back to the tag label
    if a document can't be fetched.
    """
    sources = meta.get("sources", [])
    chunk_ids, labels = [], []
    for s in sources:
        tag = s.get("equipment_tag")
        labels.append(tag or str(s.get("page_number", "?")))
        if tag:
            chunk_ids.append(f"v2_equip_{tag}")

    texts = []
    if chunk_ids:
        try:
            fetched = rag.collection.get(ids=chunk_ids, include=["documents"])
            texts = [d for d in fetched.get("documents", []) if d]
        except Exception:
            texts = []

    if texts:
        return "\n---\n".join(texts)
    # Fallback: at least tell the judge which chunks were retrieved.
    return "\n".join(f"[{lbl}]" for lbl in labels)


def run_model(model_slug, test_cases, top_k, judge_client):
    """Run the full RAG pipeline for one model and score every question."""
    # Point the adapter at this model via OpenRouter BEFORE building the engine
    # (LLMAdapter reads these in __init__).
    os.environ["LLM_PROVIDER"] = "openrouter"
    os.environ["LLM_MODEL"] = model_slug

    # Import here so each construction picks up the env we just set.
    from app.rag_engine import RAGEngine
    rag = RAGEngine()

    per_q = []
    for tc in test_cases:
        q, gt = tc["question"], tc["ground_truth"]
        before = rag.llm_adapter.session_stats["total_cost"]
        before_tok = (rag.llm_adapter.session_stats["total_input_tokens"]
                      + rag.llm_adapter.session_stats["total_output_tokens"])

        t0 = time.time()
        answer, meta = rag.query_rag(q, top_k=top_k)
        latency = time.time() - t0

        cost = rag.llm_adapter.session_stats["total_cost"] - before
        toks = (rag.llm_adapter.session_stats["total_input_tokens"]
                + rag.llm_adapter.session_stats["total_output_tokens"] - before_tok)

        # Reconstruct the ACTUAL retrieved chunk text (not just tags) so the
        # judge can properly assess faithfulness — i.e. whether the answer's
        # claims are grounded in what the retriever actually surfaced. This is
        # the same text the model saw via assemble_context(); we re-fetch it
        # from ChromaDB by chunk id (cheap, no embedding call).
        context = build_context_text(rag, meta)
        scores = judge(judge_client, q, gt, context, answer)

        per_q.append({
            "id": tc["id"], "question": q,
            "answer": answer,
            "answer_correctness": scores.get("answer_correctness"),
            "faithfulness": scores.get("faithfulness"),
            "latency_s": round(latency, 2),
            "tokens": toks,
            "cost_usd": round(cost, 8),
        })

    return per_q


def _avg(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    return round(sum(vals) / len(vals), 3) if vals else None


def main():
    ap = argparse.ArgumentParser(description="Cross-model eval matrix via OpenRouter")
    ap.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    ap.add_argument("--dataset", default="tests/eval_dataset.json")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--out", default=f"results/eval_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    args = ap.parse_args()

    with open(ROOT / args.dataset) as f:
        test_cases = json.load(f)["test_cases"]

    judge_client = get_judge_client()

    print(f"\n{'='*72}")
    print(f"  CROSS-MODEL EVAL MATRIX  ({len(test_cases)} questions, top_k={args.top_k})")
    print(f"  Judge: {JUDGE_MODEL} (fixed)  |  Retrieval: identical across models")
    print(f"{'='*72}\n")

    summary = {}
    detailed = {}
    for model in args.models:
        print(f"\n>>> Running {model} ...")
        per_q = run_model(model, test_cases, args.top_k, judge_client)
        detailed[model] = per_q

        correctness = _avg([r["answer_correctness"] for r in per_q])   # 0-5
        faithfulness = _avg([r["faithfulness"] for r in per_q])        # 0-5
        summary[model] = {
            "correctness_pct": round(correctness / 5 * 100, 1) if correctness is not None else None,
            "faithfulness_pct": round(faithfulness / 5 * 100, 1) if faithfulness is not None else None,
            "avg_latency_s": _avg([r["latency_s"] for r in per_q]),
            "total_tokens": sum(r["tokens"] for r in per_q),
            "total_cost_usd": round(sum(r["cost_usd"] for r in per_q), 6),
        }

    # Print comparison table
    print(f"\n{'='*72}")
    print("  RESULTS")
    print(f"{'='*72}")
    hdr = f"  {'model':<38} {'correct':>8} {'faithful':>9} {'lat(s)':>7} {'cost($)':>10}"
    print(hdr)
    print(f"  {'-'*36:<38} {'-'*8:>8} {'-'*9:>9} {'-'*7:>7} {'-'*10:>10}")
    for model, s in summary.items():
        print(f"  {model:<38} "
              f"{(str(s['correctness_pct'])+'%'):>8} "
              f"{(str(s['faithfulness_pct'])+'%'):>9} "
              f"{s['avg_latency_s']:>7} "
              f"{s['total_cost_usd']:>10.6f}")
    print()

    output = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "dataset": args.dataset,
            "judge_model": JUDGE_MODEL,
            "top_k": args.top_k,
            "num_questions": len(test_cases),
            "models": args.models,
        },
        "summary": summary,
        "detailed": detailed,
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Saved -> {args.out}\n")


if __name__ == "__main__":
    main()
