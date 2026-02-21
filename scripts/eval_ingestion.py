"""
Level 1 Ingestion Evaluation — measures extraction quality from SQLite.

Usage:
    python scripts/eval_ingestion.py                     # print report
    python scripts/eval_ingestion.py --model gemini-2.5-flash
    python scripts/eval_ingestion.py --out results/baseline.json

Workflow for model comparison:
    1. Ingest with model A → python scripts/eval_ingestion.py --model A --out results/model_a.json
    2. Clear DB, ingest with model B → python scripts/eval_ingestion.py --model B --out results/model_b.json
    3. Compare the two JSON files
"""

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "database" / "assets.db"
GT_PATH = ROOT / "tests" / "ground_truth.json"

PASS_SYM = "PASS"
FAIL_SYM = "FAIL"


def pct(n, d):
    return round(100 * n / d, 1) if d else 0.0


def contains_ci(value, substring):
    if value is None:
        return False
    return substring.lower() in str(value).lower()


def flag(ok):
    return PASS_SYM if ok else FAIL_SYM


# ── metric collectors ─────────────────────────────────────────────────────────

def equipment_tag_recall(cur, gt):
    expected = set(gt["expected_equipment_tags"])
    cur.execute("SELECT tag FROM equipment")
    extracted = {r[0] for r in cur.fetchall()}
    found = expected & extracted
    missing = expected - extracted
    extra = extracted - expected
    return {
        "expected": len(expected),
        "extracted": len(extracted),
        "found": len(found),
        "missing_tags": sorted(missing),
        "extra_tags": sorted(extra),
        "recall_pct": pct(len(found), len(expected)),
        "precision_pct": pct(len(found), len(extracted)),
    }


def instrument_tag_recall(cur, gt):
    expected_sample = set(gt["expected_instrument_tags_sample"])
    cur.execute("SELECT tag FROM instruments")
    extracted = {r[0] for r in cur.fetchall()}
    found = expected_sample & extracted
    missing = expected_sample - extracted
    return {
        "expected_in_sample": len(expected_sample),
        "total_extracted": len(extracted),
        "sample_found": len(found),
        "sample_missing_tags": sorted(missing),
        "sample_recall_pct": pct(len(found), len(expected_sample)),
    }


def field_coverage(cur, gt):
    targets = gt.get("field_coverage_targets", {})
    results = {}
    for field_key, target in targets.items():
        table, col = field_key.split(".")
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NOT NULL AND {col} != ''")
        non_null = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        total = cur.fetchone()[0]
        actual_pct = pct(non_null, total) / 100
        results[field_key] = {
            "non_null": non_null,
            "total": total,
            "coverage_pct": round(actual_pct * 100, 1),
            "target_pct": round(target * 100, 1),
            "meets_target": actual_pct >= target,
        }
    return results


def instrument_mapping(cur):
    cur.execute("SELECT COUNT(DISTINCT instrument_id) FROM equipment_instruments")
    mapped = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM instruments")
    total = cur.fetchone()[0]
    return {
        "total_instruments": total,
        "mapped_to_equipment": mapped,
        "mapping_pct": pct(mapped, total),
    }


def connection_count(cur, gt):
    cur.execute("SELECT COUNT(*) FROM connections")
    total = cur.fetchone()[0]
    min_expected = gt.get("expected_connections_min", 0)

    expected_pairs = gt.get("expected_connections", [])
    found_pairs = []
    missing_pairs = []
    for pair in expected_pairs:
        src, dst = pair["source"], pair["destination"]
        cur.execute(
            "SELECT COUNT(*) FROM connections WHERE source_tag=? AND destination_tag=?",
            (src, dst),
        )
        if cur.fetchone()[0] > 0:
            found_pairs.append(f"{src}->{dst}")
        else:
            missing_pairs.append(f"{src}->{dst}")

    return {
        "total_extracted": total,
        "min_expected": min_expected,
        "meets_min": total >= min_expected,
        "specific_found": found_pairs,
        "specific_missing": missing_pairs,
    }


def per_equipment_checks(cur, gt):
    results = {}
    for tag, spec in gt.get("per_equipment", {}).items():
        cur.execute(
            "SELECT equipment_type, design_pressure, design_temperature, operating_pressure FROM equipment WHERE tag=?",
            (tag,),
        )
        row = cur.fetchone()
        if row is None:
            results[tag] = {"found": False}
            continue

        eq_type, dp, dt, op = row

        cur.execute(
            """SELECT COUNT(*) FROM equipment_instruments ei
               JOIN equipment e ON e.equipment_id = ei.equipment_id
               WHERE e.tag = ?""",
            (tag,),
        )
        instr_count = cur.fetchone()[0]

        checks = {"found": True, "instrument_count": instr_count}

        if "equipment_type_contains" in spec:
            checks["equipment_type_ok"] = contains_ci(eq_type, spec["equipment_type_contains"])
            checks["equipment_type_extracted"] = eq_type
        if "design_pressure_contains" in spec:
            checks["design_pressure_ok"] = contains_ci(dp, spec["design_pressure_contains"])
            checks["design_pressure_extracted"] = dp
        if "design_temperature_contains" in spec:
            checks["design_temperature_ok"] = contains_ci(dt, spec["design_temperature_contains"])
            checks["design_temperature_extracted"] = dt
        if "instrument_count_min" in spec:
            checks["instrument_count_min"] = spec["instrument_count_min"]
            checks["instrument_count_ok"] = instr_count >= spec["instrument_count_min"]

        results[tag] = checks
    return results


# ── scoring ───────────────────────────────────────────────────────────────────

def compute_overall_score(metrics):
    """Weighted score 0-100 for quick model comparison."""
    eq = metrics["equipment_tag_recall"]
    instr = metrics["instrument_tag_recall"]
    conn = metrics["connections"]
    mapping = metrics["instrument_mapping"]
    cov = metrics["field_coverage"]

    conn_score = 100.0 if conn["meets_min"] else pct(conn["total_extracted"], conn["min_expected"])
    cov_vals = [v["coverage_pct"] for v in cov.values()]
    avg_cov = sum(cov_vals) / len(cov_vals) if cov_vals else 0.0

    components = [
        ("eq_recall",     eq["recall_pct"],                30),
        ("eq_precision",  eq["precision_pct"],             10),
        ("instr_recall",  instr["sample_recall_pct"],      20),
        ("connections",   conn_score,                      15),
        ("mapping",       mapping["mapping_pct"],          15),
        ("field_coverage", avg_cov,                        10),
    ]
    total_weight = sum(w for _, _, w in components)
    weighted_sum = sum(s * w for _, s, w in components)
    return {
        "overall_score": round(weighted_sum / total_weight, 1),
        "breakdown": {name: {"score": s, "weight": w} for name, s, w in components},
    }


# ── reporting ─────────────────────────────────────────────────────────────────

def print_report(metrics, score, model_info=None):
    divider = "-" * 62
    print()
    print("=" * 62)
    print("  P&ID INGESTION EVAL  (Level 1 — SQLite metrics)")
    print("=" * 62)
    if model_info:
        print(f"  Model  : {model_info}")
    print(f"  Run at : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  DB     : {DB_PATH}")
    print()

    eq = metrics["equipment_tag_recall"]
    print("[Equipment Tags]")
    print(f"  Recall     : {eq['found']}/{eq['expected']} ({eq['recall_pct']}%)  [{flag(eq['recall_pct'] >= 80)}]")
    print(f"  Precision  : {eq['found']}/{eq['extracted']} ({eq['precision_pct']}%)  (extra = hallucinated)")
    if eq["missing_tags"]:
        print(f"  Missing    : {', '.join(eq['missing_tags'])}")
    if eq["extra_tags"]:
        print(f"  Extra      : {', '.join(eq['extra_tags'])}")
    print()

    instr = metrics["instrument_tag_recall"]
    print("[Instrument Tags]")
    print(f"  Total extracted  : {instr['total_extracted']}")
    print(f"  Sample recall    : {instr['sample_found']}/{instr['expected_in_sample']} ({instr['sample_recall_pct']}%)  [{flag(instr['sample_recall_pct'] >= 80)}]")
    if instr["sample_missing_tags"]:
        print(f"  Sample missing   : {', '.join(instr['sample_missing_tags'])}")
    print()

    print("[Field Coverage]")
    for field, v in metrics["field_coverage"].items():
        print(f"  {field:<42} {v['coverage_pct']:5.1f}%  (target {v['target_pct']:.0f}%)  [{flag(v['meets_target'])}]")
    print()

    mapping = metrics["instrument_mapping"]
    print("[Instrument->Equipment Mapping]")
    print(f"  Mapped : {mapping['mapped_to_equipment']}/{mapping['total_instruments']} = {mapping['mapping_pct']}%  [{flag(mapping['mapping_pct'] >= 50)}]")
    print()

    conn = metrics["connections"]
    print("[Connections]")
    print(f"  Extracted : {conn['total_extracted']}  (min expected {conn['min_expected']})  [{flag(conn['meets_min'])}]")
    if conn["specific_found"]:
        print(f"  Found     : {', '.join(conn['specific_found'])}")
    if conn["specific_missing"]:
        print(f"  Missing   : {', '.join(conn['specific_missing'])}  [{FAIL_SYM}]")
    print()

    print("[Per-Equipment Spot Checks]")
    for tag, checks in metrics["per_equipment_checks"].items():
        if not checks["found"]:
            print(f"  {tag}: NOT IN DB  [{FAIL_SYM}]")
            continue
        items = []
        for k, v in checks.items():
            if k.endswith("_ok"):
                label = k.replace("_ok", "").replace("_", "-")
                items.append(f"{label}:[{flag(v)}]")
        instr_count = checks.get("instrument_count", 0)
        instr_min = checks.get("instrument_count_min")
        instr_note = f"instruments:{instr_count}"
        if instr_min:
            instr_note += f"/{instr_min} [{flag(instr_count >= instr_min)}]"
        print(f"  {tag}: {', '.join(items)}, {instr_note}")
    print()

    print(divider)
    print(f"  OVERALL SCORE : {score['overall_score']} / 100")
    print(divider)
    for name, v in score["breakdown"].items():
        bar = "#" * int(v["score"] / 5)
        print(f"  {name:<20} {v['score']:5.1f}  w={v['weight']}  {bar}")
    print()


# ── main ──────────────────────────────────────────────────────────────────────

def run_evaluation(db_path=DB_PATH, gt_path=GT_PATH):
    with open(gt_path) as f:
        gt = json.load(f)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    metrics = {
        "equipment_tag_recall":   equipment_tag_recall(cur, gt),
        "instrument_tag_recall":  instrument_tag_recall(cur, gt),
        "field_coverage":         field_coverage(cur, gt),
        "instrument_mapping":     instrument_mapping(cur),
        "connections":            connection_count(cur, gt),
        "per_equipment_checks":   per_equipment_checks(cur, gt),
    }
    conn.close()
    score = compute_overall_score(metrics)
    return metrics, score


def main():
    parser = argparse.ArgumentParser(description="Ingestion quality metrics (Level 1)")
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument("--gt", default=str(GT_PATH))
    parser.add_argument("--model", default=None, help="Label for the report (e.g. gemini-2.5-flash)")
    parser.add_argument("--json", action="store_true", help="Also print JSON to stdout")
    parser.add_argument("--out", default=None, help="Save JSON result to this path")
    args = parser.parse_args()

    metrics, score = run_evaluation(db_path=args.db, gt_path=args.gt)
    print_report(metrics, score, model_info=args.model)

    result = {
        "run_at": datetime.now().isoformat(),
        "model": args.model,
        "db": args.db,
        "overall_score": score["overall_score"],
        "score_breakdown": score["breakdown"],
        "metrics": metrics,
    }

    if args.json:
        print(json.dumps(result, indent=2))

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Result saved to {out_path}")


if __name__ == "__main__":
    main()
