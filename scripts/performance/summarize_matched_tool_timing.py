#!/usr/bin/env python3
"""Summarize semantics-aware matched-tool timing runs."""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import NoReturn

RUN_COLUMNS = [
    "case_id",
    "tool_id",
    "dataset_id",
    "condition_id",
    "reference_path",
    "enzyme_1",
    "enzyme_2",
    "min_size",
    "max_size",
    "timing_scope",
    "run_index",
    "wall_seconds",
    "exit_code",
    "primary_output_type",
    "primary_count",
    "primary_output",
    "stdout_log",
    "stderr_log",
    "status",
    "command",
    "notes",
]

SUMMARY_COLUMNS = [
    "case_id",
    "tool_id",
    "tool",
    "dataset_id",
    "condition_id",
    "comparison_group",
    "reference_path",
    "comparison_level",
    "primary_output_type",
    "allowed_claim",
    "timing_scope",
    "configured_runs",
    "observed_runs",
    "successful_runs",
    "primary_count",
    "primary_count_consistency",
    "wall_seconds_min",
    "wall_seconds_median",
    "wall_seconds_mean",
    "wall_seconds_max",
    "wall_seconds_stdev",
    "relative_to_radigest_median",
    "status",
    "notes",
]

INTERPRETATION_COLUMNS = SUMMARY_COLUMNS + ["interpretation"]

RADIGEST_METADATA = {
    "tool_id": "radigest",
    "display_name": "radigest",
    "comparison_level": "native_digest",
    "primary_output_type": "interval_set",
    "allowed_claim": "native_digest_anchor",
}

INTERPRETATIONS = {
    "radigest": (
        "Native radigest digest anchor timing. Use as the within-repository "
        "reference point, not as an external-tool equivalence claim."
    ),
    "digital_rads": (
        "Digital_RADs.py raw wrapper timing. Coordinate-equivalence claims require "
        "the separate normalized-interval comparator workflow."
    ),
    "ddradseqtools": (
        "DDRADSEQTOOLS rsitesearch.py raw wrapper timing. Coordinate-equivalence "
        "claims require the separate normalized-interval comparator workflow."
    ),
    "simrad": (
        "SimRAD count-only timing. This supports count-level digest comparison "
        "only, not coordinate-equivalent interval timing."
    ),
    "ddgrader": (
        "ddgRADer backend binned-screening timing. This supports binned screening "
        "behavior only, not coordinate-equivalent interval timing."
    ),
}


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_tsv(path: Path, required_columns: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames
        if fieldnames is None:
            fail(f"{path}: missing header")
        missing = [
            column for column in required_columns if column not in set(fieldnames)
        ]
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


def index_rows(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        out[row[key]] = row
    return out


def tool_metadata(registry: dict[str, dict[str, str]], tool_id: str) -> dict[str, str]:
    if tool_id == "radigest":
        return RADIGEST_METADATA
    if tool_id not in registry:
        fail(f"unknown tool_id in matched timing runs: {tool_id}")
    return registry[tool_id]


def fmt_float(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{value:.6f}"


def numeric(value: str, label: str) -> float:
    try:
        return float(value)
    except ValueError:
        fail(f"{label}: expected numeric value, observed {value!r}")


def summarize_case(
    case: dict[str, str],
    runs: list[dict[str, str]],
    registry: dict[str, dict[str, str]],
) -> dict[str, str]:
    case_id = case["case_id"]
    tool_id = case["tool_id"]
    metadata = tool_metadata(registry, tool_id)
    configured_runs = int(case["runs"])
    successful = [row for row in runs if row["status"] == "PASS"]
    wall_times = [
        numeric(row["wall_seconds"], f"{case_id} wall_seconds") for row in successful
    ]
    primary_counts = [
        row["primary_count"] for row in successful if row["primary_count"] != "NA"
    ]
    unique_counts = sorted(set(primary_counts))
    primary_count = unique_counts[0] if len(unique_counts) == 1 else "NA"
    primary_consistency = (
        "PASS" if len(unique_counts) == 1 and bool(successful) else "FAIL"
    )

    status = "PASS"
    if len(runs) != configured_runs or len(successful) != configured_runs:
        status = "FAIL"
    if primary_consistency != "PASS":
        status = "FAIL"
    if not wall_times:
        status = "FAIL"

    comparison_group = f"{case['dataset_id']}__{case['condition_id']}"
    return {
        "case_id": case_id,
        "tool_id": tool_id,
        "tool": metadata["display_name"],
        "dataset_id": case["dataset_id"],
        "condition_id": case["condition_id"],
        "comparison_group": comparison_group,
        "reference_path": case["reference_path"],
        "comparison_level": metadata["comparison_level"],
        "primary_output_type": metadata["primary_output_type"],
        "allowed_claim": metadata["allowed_claim"],
        "timing_scope": case["timing_scope"],
        "configured_runs": str(configured_runs),
        "observed_runs": str(len(runs)),
        "successful_runs": str(len(successful)),
        "primary_count": primary_count,
        "primary_count_consistency": primary_consistency,
        "wall_seconds_min": fmt_float(min(wall_times) if wall_times else None),
        "wall_seconds_median": fmt_float(
            statistics.median(wall_times) if wall_times else None
        ),
        "wall_seconds_mean": fmt_float(
            statistics.fmean(wall_times) if wall_times else None
        ),
        "wall_seconds_max": fmt_float(max(wall_times) if wall_times else None),
        "wall_seconds_stdev": fmt_float(
            statistics.stdev(wall_times)
            if len(wall_times) > 1
            else 0.0 if wall_times else None
        ),
        "relative_to_radigest_median": "NA",
        "status": status,
        "notes": case["notes"],
    }


def add_radigest_relative_timings(rows: list[dict[str, str]]) -> None:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["comparison_group"]].append(row)
    for group, group_rows in grouped.items():
        radigest = [
            row
            for row in group_rows
            if row["tool_id"] == "radigest" and row["status"] == "PASS"
        ]
        if len(radigest) != 1 or radigest[0]["wall_seconds_median"] == "NA":
            for row in group_rows:
                row["status"] = "FAIL"
                row["notes"] += f" Missing valid radigest baseline for {group}."
            continue
        baseline = float(radigest[0]["wall_seconds_median"])
        if baseline <= 0:
            for row in group_rows:
                row["status"] = "FAIL"
                row["notes"] += f" Invalid radigest baseline for {group}."
            continue
        for row in group_rows:
            if row["wall_seconds_median"] == "NA":
                continue
            row["relative_to_radigest_median"] = fmt_float(
                float(row["wall_seconds_median"]) / baseline
            )


def interpretation_rows(summary_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in summary_rows:
        out = dict(row)
        out["interpretation"] = INTERPRETATIONS.get(
            row["tool_id"], "Timing interpretation is declared by the tool registry."
        )
        rows.append(out)
    return rows


def write_rows(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--comparators", required=True, type=Path)
    parser.add_argument("--runs", required=True, nargs="+", type=Path)
    parser.add_argument("--merged-runs", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--interpretation", required=True, type=Path)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = index_rows(read_tsv(args.cases, ["case_id", "tool_id", "runs"]), "case_id")
    registry = index_rows(
        read_tsv(args.comparators, ["tool_id", "display_name"]), "tool_id"
    )
    run_rows: list[dict[str, str]] = []
    for path in args.runs:
        run_rows.extend(read_tsv(path, RUN_COLUMNS))
    runs_by_case: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in run_rows:
        runs_by_case[row["case_id"]].append(row)
    summary = [
        summarize_case(case, runs_by_case.get(case_id, []), registry)
        for case_id, case in sorted(cases.items())
    ]
    add_radigest_relative_timings(summary)
    interpretation = interpretation_rows(summary)
    write_rows(args.merged_runs, run_rows, RUN_COLUMNS)
    write_rows(args.summary, summary, SUMMARY_COLUMNS)
    write_rows(args.interpretation, interpretation, INTERPRETATION_COLUMNS)

    failed = [row for row in summary if row["status"] != "PASS"]
    if args.require_pass and failed:
        print(
            f"{len(failed)} of {len(summary)} matched-tool timing summaries failed; "
            f"see {args.summary}",
            file=sys.stderr,
        )
        return 1
    print(f"Wrote matched-tool timing summary to {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
