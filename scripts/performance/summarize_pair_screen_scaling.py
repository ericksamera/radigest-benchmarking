#!/usr/bin/env python3
"""Summarize cached pair-screen score-phase job-scaling timing rows."""

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
    "dataset_id",
    "condition_id",
    "comparison_group",
    "reference_path",
    "candidate_enzymes",
    "candidate_enzyme_count",
    "candidate_pairs_evaluated",
    "min_size",
    "max_size",
    "score_min",
    "score_max",
    "size_model",
    "jobs",
    "radigest_threads",
    "build_workers",
    "configured_runs",
    "observed_runs",
    "successful_runs",
    "candidate_pairs_reported",
    "reported_pair_consistency",
    "reported_pair_coverage",
    "screening_binary",
    "timing_backend",
    "timed_phase",
    "wall_seconds_min",
    "wall_seconds_median",
    "wall_seconds_mean",
    "wall_seconds_max",
    "wall_seconds_stdev",
    "score_pairs_seconds_median",
    "score_pairs_seconds_stdev",
    "total_seconds_median",
    "total_seconds_stdev",
    "candidate_pairs_per_second_median",
    "candidate_pairs_per_second_stdev",
    "pairs_per_second_score_phase_median",
    "pairs_per_second_score_phase_stdev",
    "speedup_vs_1_job_median",
    "speedup_vs_1_job_stdev",
    "job_scaling_efficiency_vs_1_job",
    "status",
    "notes",
]

REQUIRED_CASE_COLUMNS = [
    "case_id",
    "dataset_id",
    "reference_path",
    "condition_id",
    "candidate_enzymes",
    "min_size",
    "max_size",
    "score_min",
    "score_max",
    "size_model",
    "jobs",
    "radigest_threads",
    "runs",
    "comparison_group",
    "required_for_nonempirical",
    "notes",
]

REQUIRED_RUN_COLUMNS = [
    "case_id",
    "dataset_id",
    "condition_id",
    "wall_seconds",
    "timing_backend",
    "timed_phase",
    "score_pairs_seconds",
    "total_seconds",
    "pairs_per_second_score_phase",
    "exit_code",
    "candidate_pairs_reported",
    "candidate_pairs_evaluated",
    "candidate_enzyme_count",
    "screening_binary",
    "jobs",
    "radigest_threads",
    "build_workers",
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
    selected = {
        row["case_id"]: row
        for row in read_tsv(path, REQUIRED_CASE_COLUMNS)
        if row["required_for_nonempirical"].lower() == "true"
    }
    if not selected:
        fail(f"{path}: no required pair-screen scaling rows")
    return selected


def read_run_rows(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        rows.extend(read_tsv(path, REQUIRED_RUN_COLUMNS))
    return rows


def parse_int(value: str, *, path_label: str) -> int:
    try:
        return int(value)
    except ValueError:
        fail(f"{path_label}: expected integer, observed {value!r}")


def parse_float(value: str, *, path_label: str) -> float:
    try:
        return float(value)
    except ValueError:
        fail(f"{path_label}: expected float, observed {value!r}")


def maybe_float(value: str, *, path_label: str) -> float | None:
    if value in {"", "NA"}:
        return None
    return parse_float(value, path_label=path_label)


def fmt_float(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{value:.6f}"


def median_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return statistics.median(values)


def stdev_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return statistics.stdev(values) if len(values) > 1 else 0.0


def summarize_case(
    case: dict[str, str], run_rows: list[dict[str, str]]
) -> dict[str, str]:
    case_id = case["case_id"]
    configured_runs = parse_int(case["runs"], path_label=f"case {case_id} runs")
    configured_jobs = parse_int(case["jobs"], path_label=f"case {case_id} jobs")
    configured_radigest_threads = parse_int(
        case["radigest_threads"], path_label=f"case {case_id} radigest_threads"
    )
    successes = [row for row in run_rows if row.get("status") == "PASS"]
    durations = [
        parse_float(row["wall_seconds"], path_label=f"case {case_id} wall_seconds")
        for row in successes
        if row.get("wall_seconds") not in {"", "NA"}
    ]
    score_pair_durations = [
        value
        for value in (
            maybe_float(
                row.get("score_pairs_seconds", "NA"),
                path_label=f"case {case_id} score_pairs_seconds",
            )
            for row in successes
        )
        if value is not None
    ]
    total_durations = [
        value
        for value in (
            maybe_float(
                row.get("total_seconds", "NA"),
                path_label=f"case {case_id} total_seconds",
            )
            for row in successes
        )
        if value is not None
    ]
    score_phase_rates = [
        value
        for value in (
            maybe_float(
                row.get("pairs_per_second_score_phase", "NA"),
                path_label=f"case {case_id} pairs_per_second_score_phase",
            )
            for row in successes
        )
        if value is not None
    ]
    evaluated_values = [
        parse_int(
            row["candidate_pairs_evaluated"],
            path_label=f"case {case_id} candidate_pairs_evaluated",
        )
        for row in successes
    ]
    reported_values = [
        parse_int(
            row["candidate_pairs_reported"],
            path_label=f"case {case_id} candidate_pairs_reported",
        )
        for row in successes
        if row["candidate_pairs_reported"] != "NA"
    ]
    candidate_enzyme_counts = {
        row["candidate_enzyme_count"]
        for row in successes
        if row.get("candidate_enzyme_count") not in {None, "", "NA"}
    }
    screening_binaries = {
        row["screening_binary"]
        for row in successes
        if row.get("screening_binary") not in {None, "", "NA"}
    }
    timing_backends = {
        row["timing_backend"]
        for row in successes
        if row.get("timing_backend") not in {None, "", "NA"}
    }
    timed_phases = {
        row["timed_phase"]
        for row in successes
        if row.get("timed_phase") not in {None, "", "NA"}
    }
    run_job_values = {
        parse_int(row["jobs"], path_label=f"case {case_id} run jobs")
        for row in run_rows
        if row.get("jobs")
    }
    run_radigest_thread_values = {
        parse_int(
            row["radigest_threads"],
            path_label=f"case {case_id} run radigest_threads",
        )
        for row in run_rows
        if row.get("radigest_threads")
    }
    run_build_worker_values = {
        parse_int(
            row["build_workers"],
            path_label=f"case {case_id} run build_workers",
        )
        for row in run_rows
        if row.get("build_workers") not in {None, "", "NA"}
    }
    build_workers = (
        str(sorted(run_build_worker_values)[0])
        if len(run_build_worker_values) == 1
        else "NA"
    )

    evaluated_unique = sorted(set(evaluated_values))
    reported_unique = sorted(set(reported_values))
    reported_pair_consistency = "PASS" if len(reported_unique) == 1 else "FAIL"
    if evaluated_unique and reported_unique and reported_unique == evaluated_unique:
        reported_pair_coverage = "PASS"
    else:
        reported_pair_coverage = "FAIL"

    wall_min: float | None = None
    wall_median: float | None = None
    wall_mean: float | None = None
    wall_max: float | None = None
    wall_stdev: float | None = None
    pairs_per_second: float | None = None
    pairs_per_second_stdev: float | None = None

    if durations:
        wall_min = min(durations)
        wall_median = statistics.median(durations)
        wall_mean = statistics.fmean(durations)
        wall_max = max(durations)
        wall_stdev = statistics.stdev(durations) if len(durations) > 1 else 0.0
        if evaluated_unique and len(evaluated_unique) == 1 and wall_median > 0:
            pairs_per_second = evaluated_unique[0] / wall_median
            rate_values = [
                evaluated_unique[0] / value for value in durations if value > 0
            ]
            pairs_per_second_stdev = stdev_or_none(rate_values)

    status = "PASS"
    if len(run_rows) != configured_runs:
        status = "FAIL"
    if len(successes) != configured_runs:
        status = "FAIL"
    if reported_pair_consistency != "PASS" or reported_pair_coverage != "PASS":
        status = "FAIL"
    if run_job_values and run_job_values != {configured_jobs}:
        status = "FAIL"
    if run_radigest_thread_values and run_radigest_thread_values != {
        configured_radigest_threads
    }:
        status = "FAIL"
    if run_build_worker_values != {configured_radigest_threads}:
        status = "FAIL"
    if len(timing_backends) != 1 or len(timed_phases) != 1:
        status = "FAIL"
    if timed_phases and timed_phases != {"score_pairs_seconds"}:
        status = "FAIL"

    return {
        "case_id": case_id,
        "dataset_id": case["dataset_id"],
        "condition_id": case["condition_id"],
        "comparison_group": case["comparison_group"],
        "reference_path": case["reference_path"],
        "candidate_enzymes": case["candidate_enzymes"],
        "candidate_enzyme_count": next(iter(sorted(candidate_enzyme_counts)), "NA"),
        "candidate_pairs_evaluated": (
            str(evaluated_unique[0]) if len(evaluated_unique) == 1 else "NA"
        ),
        "min_size": case["min_size"],
        "max_size": case["max_size"],
        "score_min": case["score_min"],
        "score_max": case["score_max"],
        "size_model": case["size_model"],
        "jobs": case["jobs"],
        "radigest_threads": case["radigest_threads"],
        "build_workers": build_workers,
        "configured_runs": str(configured_runs),
        "observed_runs": str(len(run_rows)),
        "successful_runs": str(len(successes)),
        "candidate_pairs_reported": (
            str(reported_unique[0]) if len(reported_unique) == 1 else "NA"
        ),
        "reported_pair_consistency": reported_pair_consistency,
        "reported_pair_coverage": reported_pair_coverage,
        "screening_binary": next(iter(sorted(screening_binaries)), "NA"),
        "timing_backend": next(iter(sorted(timing_backends)), "NA"),
        "timed_phase": next(iter(sorted(timed_phases)), "NA"),
        "wall_seconds_min": fmt_float(wall_min),
        "wall_seconds_median": fmt_float(wall_median),
        "wall_seconds_mean": fmt_float(wall_mean),
        "wall_seconds_max": fmt_float(wall_max),
        "wall_seconds_stdev": fmt_float(wall_stdev),
        "score_pairs_seconds_median": fmt_float(median_or_none(score_pair_durations)),
        "score_pairs_seconds_stdev": fmt_float(stdev_or_none(score_pair_durations)),
        "total_seconds_median": fmt_float(median_or_none(total_durations)),
        "total_seconds_stdev": fmt_float(stdev_or_none(total_durations)),
        "candidate_pairs_per_second_median": fmt_float(pairs_per_second),
        "candidate_pairs_per_second_stdev": fmt_float(pairs_per_second_stdev),
        "pairs_per_second_score_phase_median": fmt_float(
            median_or_none(score_phase_rates)
        ),
        "pairs_per_second_score_phase_stdev": fmt_float(
            stdev_or_none(score_phase_rates)
        ),
        "speedup_vs_1_job_median": "NA",
        "speedup_vs_1_job_stdev": "NA",
        "job_scaling_efficiency_vs_1_job": "NA",
        "status": status,
        "notes": case["notes"],
    }


def add_group_consistency_and_speedups(rows: list[dict[str, str]]) -> None:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["comparison_group"]].append(row)

    for group, group_rows in grouped.items():
        pair_counts = {
            row["candidate_pairs_evaluated"]
            for row in group_rows
            if row["candidate_pairs_evaluated"] != "NA"
        }
        if len(pair_counts) != 1:
            for row in group_rows:
                row["status"] = "FAIL"
                row["notes"] = (
                    row["notes"]
                    + " Group candidate-pair counts differ across job counts."
                )

        phases = {
            row["timed_phase"] for row in group_rows if row["timed_phase"] != "NA"
        }
        if phases != {"score_pairs_seconds"}:
            for row in group_rows:
                row["status"] = "FAIL"
                row["notes"] = (
                    row["notes"] + " Pair-screen scaling must use score_pairs_seconds."
                )

        baselines = [
            row
            for row in group_rows
            if row["jobs"] == "1"
            and row["status"] == "PASS"
            and row["wall_seconds_median"] != "NA"
        ]
        if len(baselines) != 1:
            for row in group_rows:
                row["status"] = "FAIL"
                row["notes"] = (
                    row["notes"] + f" Missing valid 1-job baseline for {group}."
                )
            continue

        baseline_median = float(baselines[0]["wall_seconds_median"])
        for row in group_rows:
            if row["wall_seconds_median"] == "NA":
                continue
            jobs = int(row["jobs"])
            median = float(row["wall_seconds_median"])
            speedup = baseline_median / median
            row["speedup_vs_1_job_median"] = fmt_float(speedup)
            if row.get("wall_seconds_stdev", "NA") != "NA" and median > 0:
                row["speedup_vs_1_job_stdev"] = fmt_float(
                    speedup * float(row["wall_seconds_stdev"]) / median
                )
            row["job_scaling_efficiency_vs_1_job"] = fmt_float(speedup / jobs)


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
    cases = read_case_rows(args.cases)
    run_rows = read_run_rows(args.runs)
    grouped_runs: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in run_rows:
        if row["case_id"] in cases:
            grouped_runs[row["case_id"]].append(row)

    summary_rows = [
        summarize_case(case, grouped_runs.get(case_id, []))
        for case_id, case in sorted(cases.items())
    ]
    add_group_consistency_and_speedups(summary_rows)
    write_rows(args.out, summary_rows)

    failed = [row for row in summary_rows if row["status"] != "PASS"]
    if args.require_pass and failed:
        print(
            f"{len(failed)} of {len(summary_rows)} pair-screen scaling summaries failed; "
            f"see {args.out}",
            file=sys.stderr,
        )
        return 1

    print(f"Wrote {len(summary_rows)} pair-screen scaling summaries to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
