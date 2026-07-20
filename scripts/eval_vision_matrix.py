"""
Cross-model VISION-EXTRACTION eval matrix.

The RAG matrix (eval_matrix.py) scores the *generation* layer with an LLM judge.
This scores the *vision extraction* layer — how well each model reads the P&ID
image into structured equipment/instrument/connection data — against a
DETERMINISTIC ground truth (tests/ground_truth.json). No LLM judge: metrics are
tag recall / field coverage / mapping, so the numbers are objective.

How it works (production data is never touched):
  For each vision model:
    1. spin up a TEMP SQLite DB (schema copied from production) + temp vector dir
    2. point the ingestion pipeline at the temp DBs and VISION_MODEL at the model
    3. run extraction on the same P&ID PDF
    4. score the temp DB with the existing eval_ingestion metrics
    5. record extraction score + latency + tokens + cost, then delete the temp DB

Models come from config/models.json (vision_models). Usage:
  python scripts/eval_vision_matrix.py
  python scripts/eval_vision_matrix.py --models gemini-2.5-flash-lite gemini-2.5-pro
"""

import os
import sys
import json
import time
import shutil
import sqlite3
import tempfile
import argparse
import statistics
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from scripts.eval_ingestion import run_evaluation

CONFIG_PATH = ROOT / "config" / "models.json"
PROD_DB = ROOT / "database" / "assets.db"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def create_temp_schema(temp_db, src_db):
    """Copy the table/index schema (structure only, no rows) into a temp DB."""
    src = sqlite3.connect(str(src_db))
    # Each statement from sqlite_master lacks a trailing ';' — add one so
    # executescript can run them as separate statements.
    schema_sql = ";\n".join(
        r[0] for r in src.execute(
            "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL "
            "AND name NOT LIKE 'sqlite_%'"
        )
    ) + ";"
    src.close()
    dst = sqlite3.connect(str(temp_db))
    dst.executescript(schema_sql)
    dst.commit()
    dst.close()


def cost_of(usage, rates):
    """USD cost from token counts and [input, output] per-million rates."""
    if not rates:
        return None
    cin, cout = rates
    return round(
        usage["total_input_tokens"] * cin / 1e6
        + usage["total_output_tokens"] * cout / 1e6,
        6,
    )


def run_vision_model(model, pdf_path, pricing):
    """Extract with one vision model into a temp DB and score it. Returns dict."""
    tmpdir = Path(tempfile.mkdtemp(prefix=f"vmatrix_{model.replace('/', '_')}_"))
    temp_db = tmpdir / "assets.db"
    temp_vec = tmpdir / "vector_store"
    try:
        create_temp_schema(temp_db, PROD_DB)

        # Redirect the pipeline BEFORE constructing it (env is read in __init__).
        os.environ["VISION_MODEL"] = model
        os.environ["SQLITE_DB_PATH"] = str(temp_db)
        os.environ["VECTOR_DB_PATH"] = str(temp_vec)

        from scripts.ingest_pdfs_v2 import PDFIngestionPipelineV2
        pipeline = PDFIngestionPipelineV2()

        t0 = time.time()
        result = pipeline.ingest_pdf(str(pdf_path))
        latency = time.time() - t0

        usage = result["token_usage"]
        metrics, score = run_evaluation(db_path=str(temp_db))

        return {
            "model": model,
            "extraction_score": score["overall_score"],
            "eq_recall_pct": metrics["equipment_tag_recall"]["recall_pct"],
            "eq_precision_pct": metrics["equipment_tag_recall"]["precision_pct"],
            "instr_recall_pct": metrics["instrument_tag_recall"]["sample_recall_pct"],
            "mapping_pct": metrics["instrument_mapping"]["mapping_pct"],
            "connections": metrics["connections"]["total_extracted"],
            "latency_s": round(latency, 1),
            "input_tokens": usage["total_input_tokens"],
            "output_tokens": usage["total_output_tokens"],
            "cost_usd": cost_of(usage, pricing.get(model)),
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


SUMMARY_METRICS = [
    "extraction_score", "eq_recall_pct", "eq_precision_pct",
    "instr_recall_pct", "mapping_pct", "connections",
    "latency_s", "cost_usd",
]


def aggregate_runs(model, runs):
    """Mean + stdev + min/max across N runs of one model. Ignores None costs."""
    agg = {"model": model, "n_runs": len(runs)}
    for m in SUMMARY_METRICS:
        vals = [r[m] for r in runs if isinstance(r.get(m), (int, float))]
        if not vals:
            agg[m] = {"mean": None, "std": None, "min": None, "max": None}
            continue
        agg[m] = {
            "mean": round(statistics.mean(vals), 3),
            "std": round(statistics.pstdev(vals), 3) if len(vals) > 1 else 0.0,
            "min": round(min(vals), 3),
            "max": round(max(vals), 3),
        }
    return agg


def main():
    cfg = load_config()
    ap = argparse.ArgumentParser(description="Cross-model vision-extraction eval matrix")
    ap.add_argument("--models", nargs="+", default=cfg["vision_models"])
    ap.add_argument("--runs", type=int, default=3,
                    help="Runs per model; results are averaged (extraction is stochastic)")
    ap.add_argument("--pdf", default=None, help="P&ID PDF (defaults to the one in data/pdfs)")
    ap.add_argument("--out", default=f"results/eval_vision_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    args = ap.parse_args()

    pricing = cfg.get("vision_pricing_per_million", {})

    pdf_path = args.pdf
    if pdf_path is None:
        pdfs = list((ROOT / "data" / "pdfs").glob("*.pdf"))
        if not pdfs:
            print("No PDF found in data/pdfs/"); sys.exit(1)
        pdf_path = pdfs[0]

    print(f"\n{'='*76}")
    print(f"  VISION-EXTRACTION EVAL MATRIX  ({len(args.models)} models x {args.runs} runs)")
    print(f"  PDF: {Path(pdf_path).name}  |  Ground truth: tests/ground_truth.json")
    print(f"  Scoring: deterministic tag recall / coverage / mapping (no LLM judge)")
    print(f"  Extraction is stochastic — reporting mean +/- std over {args.runs} runs")
    print(f"{'='*76}\n")

    summary = []
    detailed = {}
    for model in args.models:
        runs = []
        for i in range(args.runs):
            print(f"\n>>> {model}  run {i+1}/{args.runs} ...")
            try:
                runs.append(run_vision_model(model, pdf_path, pricing))
            except Exception as e:
                print(f"    ERROR on {model} run {i+1}: {e}")
                runs.append({"model": model, "error": str(e)})
        detailed[model] = runs
        ok_runs = [r for r in runs if "error" not in r]
        if ok_runs:
            summary.append(aggregate_runs(model, ok_runs))
        else:
            summary.append({"model": model, "n_runs": 0, "error": "all runs failed"})

    # Table — mean (std) for score/recall, mean for the rest.
    print(f"\n{'='*76}")
    print("  RESULTS  (extraction quality vs ground truth, mean over runs)")
    print(f"{'='*76}")
    print(f"  {'model':<24}{'score(std)':>13}{'eq_rec':>9}{'instr':>8}{'map':>7}{'conn':>6}{'lat(s)':>8}{'cost($)':>10}")
    print(f"  {'-'*22:<24}{'-'*13:>13}{'-'*9:>9}{'-'*8:>8}{'-'*7:>7}{'-'*6:>6}{'-'*8:>8}{'-'*10:>10}")
    for s in summary:
        if s.get("error"):
            print(f"  {s['model']:<24}  ERROR: {s['error'][:44]}")
            continue
        def mean(m): return s[m]["mean"]
        score_cell = f"{mean('extraction_score')} ({s['extraction_score']['std']})"
        cost = mean("cost_usd")
        cost_cell = f"{cost:.6f}" if cost is not None else "n/a"
        print(f"  {s['model']:<24}{score_cell:>13}{mean('eq_recall_pct'):>8}%"
              f"{mean('instr_recall_pct'):>7}%{mean('mapping_pct'):>6}%{mean('connections'):>6}"
              f"{mean('latency_s'):>8}{cost_cell:>10}")
    print()

    out = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "pdf": str(Path(pdf_path).name),
            "ground_truth": "tests/ground_truth.json",
            "models": args.models,
            "runs_per_model": args.runs,
            "scoring": "deterministic (eval_ingestion metrics), mean +/- std over runs",
        },
        "summary": summary,
        "detailed": detailed,
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"  Saved -> {args.out}\n")


if __name__ == "__main__":
    main()
