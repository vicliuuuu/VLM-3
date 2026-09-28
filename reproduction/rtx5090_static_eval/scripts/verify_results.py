#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path
import sys


EXPECTED_METRICS = (
    "vsibench_score,none",
    "vsi_obj_count,none",
    "vsi_abs_dist,none",
    "vsi_obj_size,none",
    "vsi_room_size,none",
    "vsi_rel_dist,none",
    "vsi_rel_dir,none",
    "vsi_route_plan,none",
    "vsi_appr_order,none",
)


def fail(message: str) -> None:
    print(f"[FAIL] {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--expected-samples", type=int, default=5130)
    args = parser.parse_args()

    result_files = list(args.result_dir.rglob("*_results.json"))
    sample_files = list(args.result_dir.rglob("*_samples_vsibench.jsonl"))
    if len(result_files) != 1:
        fail(f"expected one result JSON, found {len(result_files)}")
    if len(sample_files) != 1:
        fail(f"expected one sample JSONL, found {len(sample_files)}")

    result = json.loads(result_files[0].read_text(encoding="utf-8"))
    metrics = result["results"]["vsibench"]
    for name in EXPECTED_METRICS:
        value = metrics.get(name)
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            fail(f"missing or invalid metric: {name}")

    rows = []
    with sample_files[0].open(encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
    if len(rows) != args.expected_samples:
        fail(f"expected {args.expected_samples} samples, got {len(rows)}")
    unique_doc_ids = {row.get("doc_id") for row in rows}
    if len(unique_doc_ids) != args.expected_samples:
        fail(f"expected {args.expected_samples} unique doc IDs, got {len(unique_doc_ids)}")

    print(f"[OK] result: {result_files[0]}")
    print(f"[OK] samples: {sample_files[0]}")
    print(f"[OK] sample_count={len(rows)}, unique_doc_ids={len(unique_doc_ids)}")
    for name in EXPECTED_METRICS:
        print(f"{name.removesuffix(',none')}: {metrics[name]:.4f}")
    print("[OK] all result checks passed")


if __name__ == "__main__":
    main()
