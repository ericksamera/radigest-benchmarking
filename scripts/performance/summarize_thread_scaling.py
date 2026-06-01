#!/usr/bin/env python3
"""Summarize radigest thread-scaling timing rows."""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import NoReturn

SUMMARY_COLUMNS = [
    "case_id",
    "category",
    "dataset_id",
    "condition_id",
    "comparison_group",
    "output_mode",
    "input_format",
    "reference_path",
    "threads",
    "configured_runs",
    "observed_runs",
    "successful_runs",
    "retained_fragments",
    "retained_fragment_consistency",
    "wall_seconds_min",
    "wall_seconds_median",
    "wall_seconds_mean",
    "wall_seconds_max",
    "wall_seconds_stdev",
    "speedup_vs_1_thread_median",
    "parallel_efficiency_vs_1_thread",
    "status",
    "notes",
]

REQUIRED_CASE_COLUMNS = [
    "case_id",
    "category",
    "dataset_id",
    "reference_path",
    "condition_id",
    "threads",
    "runs",
    "comparison_group",
    "output_mode",
    "input_format",
    "required_for_nonempirical",
    "notes",
]

REQUIRED_RUN_COLUMNS = [
    "case_id",
    "dataset_id",
    "condition_id",
    "input_format",
    "output_mode",
    "wall_seconds",
    "exit_code",
    "retained_fragments",
    "threads",
    "status",
]


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_tsv(path: Path, required_columns: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames
        if fieldnames is None:
            fail(f"{path}: missing header")
        fieldname_set = set(fieldnames)
        missing = [column for column in required_columns if column not in fieldname_set]
        if missing:
            fail(f"{path}: missing columns: {', '.join(missing)}")
        rows: list[dict[str, str]] = []
        for raw_row in reader:
            if not any((value or "").strip() for value in raw_row.values()):
                continue
            row: dict[str, str] = {}
            for key, value in raw_row.items():
                if key is not None:
                    row[key] = "" if value is None else value
            rows.append(row)
    return rows


def read_case_rows(path: Path) -> dict[str, dict[str, str]]:
    rows = read_tsv(path, REQUIRED_CASE_COLUMNS)
    selected = {
        row["case_id"]: row
        for row in rows
        if row["category"] == "thread_scaling"
        and row["required_for_nonempirical"].lower() == "true"
    }
    if not selected:
        fail(f"{path}: no required thread_scaling rows")
    return selected


def read_run_rows(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        rows.extend(read_tsv(path, REQUIRED_RUN_COLUMNS))
    return rows


def parse_float(value: str, *, path_label: str) -> float:
    try:
        return float(value)
    except ValueError:
        fail(f"{path_label}: expected float, observed {value!r}")


def parse_int(value: str, *, path_label: str) -> int:
    try:
        return int(value)
    except ValueError:
        fail(f"{path_label}: expected integer, observed {value!r}")


def fmt_float(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{value:.6f}"


def summarize_case(
    case: dict[str, str], run_rows: list[dict[str, str]]
) -> dict[str, str]:
    case_id = case["case_id"]
    configured_runs = parse_int(case["runs"], path_label=f"case {case_id} runs")
    configured_threads = parse_int(
        case["threads"], path_label=f"case {case_id} threads"
    )
    successes = [row for row in run_rows if row.get("status") == "PASS"]
    durations = [
        parse_float(row["wall_seconds"], path_label=f"case {case_id} wall_seconds")
        for row in successes
    ]
    retained_counts = [
        parse_int(
            row["retained_fragments"],
            path_label=f"case {case_id} retained_fragments",
        )
        for row in successes
    ]

    retained_unique = sorted(set(retained_counts))
    retained_consistency = "PASS" if len(retained_unique) == 1 else "FAIL"
    retained_value = str(retained_unique[0]) if len(retained_unique) == 1 else "NA"

    wall_min: float | None = None
    wall_median: float | None = None
    wall_mean: float | None = None
    wall_max: float | None = None
    wall_stdev: float | None = None

    if durations:
        wall_min = min(durations)
        wall_median = statistics.median(durations)
        wall_mean = statistics.fmean(durations)
        wall_max = max(durations)
        wall_stdev = statistics.stdev(durations) if len(durations) > 1 else 0.0

    run_thread_values = {
        parse_int(row["threads"], path_label=f"case {case_id} run threads")
        for row in run_rows
        if row.get("threads")
    }

    status = "PASS"
    if len(run_rows) != configured_runs:
        status = "FAIL"
    if len(successes) != configured_runs:
        status = "FAIL"
    if retained_consistency != "PASS":
        status = "FAIL"
    if run_thread_values and run_thread_values != {configured_threads}:
        status = "FAIL"

    return {
        "case_id": case_id,
        "category": case["category"],
        "dataset_id": case["dataset_id"],
        "condition_id": case["condition_id"],
        "comparison_group": case["comparison_group"],
        "output_mode": case["output_mode"],
        "input_format": case["input_format"],
        "reference_path": case["reference_path"],
        "threads": case["threads"],
        "configured_runs": str(configured_runs),
        "observed_runs": str(len(run_rows)),
        "successful_runs": str(len(successes)),
        "retained_fragments": retained_value,
        "retained_fragment_consistency": retained_consistency,
        "wall_seconds_min": fmt_float(wall_min),
        "wall_seconds_median": fmt_float(wall_median),
        "wall_seconds_mean": fmt_float(wall_mean),
        "wall_seconds_max": fmt_float(wall_max),
        "wall_seconds_stdev": fmt_float(wall_stdev),
        "speedup_vs_1_thread_median": "NA",
        "parallel_efficiency_vs_1_thread": "NA",
        "status": status,
        "notes": case["notes"],
    }


def add_group_consistency_and_speedups(rows: list[dict[str, str]]) -> None:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["comparison_group"]].append(row)

    for group, group_rows in grouped.items():
        retained_values = {
            row["retained_fragments"]
            for row in group_rows
            if row["retained_fragments"] != "NA"
        }
        if len(retained_values) != 1:
            for row in group_rows:
                row["status"] = "FAIL"
                row["notes"] = (
                    row["notes"]
                    + " Group retained-fragment counts differ across thread counts."
                )

        baselines = [
            row
            for row in group_rows
            if row["threads"] == "1"
            and row["status"] == "PASS"
            and row["wall_seconds_median"] != "NA"
        ]
        if len(baselines) != 1:
            for row in group_rows:
                row["status"] = "FAIL"
                row["notes"] = row["notes"] + f" Missing valid 1-thread baseline for {group}."
            continue

        baseline_median = float(baselines[0]["wall_seconds_median"])
        for row in group_rows:
            if row["wall_seconds_median"] == "NA":
                continue
            threads = int(row["threads"])
            median = float(row["wall_seconds_median"])
            speedup = baseline_median / median
            row["speedup_vs_1_thread_median"] = fmt_float(speedup)
            row["parallel_efficiency_vs_1_thread"] = fmt_float(speedup / threads)


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--runs", required=True, nargs="+", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    case_by_id = read_case_rows(args.cases)
    rows_by_case: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_run_rows(args.runs):
        rows_by_case[row["case_id"]].append(row)

    summaries = [
        summarize_case(case, rows_by_case.get(case_id, []))
        for case_id, case in sorted(case_by_id.items())
    ]
    add_group_consistency_and_speedups(summaries)
    write_rows(args.out, summaries)

    failed = [row for row in summaries if row["status"] != "PASS"]
    if args.require_pass and failed:
        print(
            f"{len(failed)} of {len(summaries)} thread-scaling summaries failed; "
            f"see {args.out}",
            file=sys.stderr,
        )
        return 1

    print(f"Wrote {len(summaries)} thread-scaling summary rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
