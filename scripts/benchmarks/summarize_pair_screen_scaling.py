#!/usr/bin/env python3
"""Summarize radigest-screen-pairs job-scaling benchmarks."""

from __future__ import annotations

import argparse
import csv
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

RUN_FIELDS = [
    "dataset",
    "jobs",
    "replicate",
    "elapsed_wall_seconds",
    "user_seconds",
    "system_seconds",
    "percent_cpu",
    "max_rss_kb",
    "exit_status",
    "completed_pairs",
    "time_file",
    "output_dir",
]

SUMMARY_FIELDS = [
    "dataset",
    "jobs",
    "n_runs",
    "median_elapsed_wall_seconds",
    "q1_elapsed_wall_seconds",
    "q3_elapsed_wall_seconds",
    "iqr_elapsed_wall_seconds",
    "median_max_rss_kb",
    "q1_max_rss_kb",
    "q3_max_rss_kb",
    "iqr_max_rss_kb",
    "median_completed_pairs",
    "median_pairs_per_second",
    "speedup_vs_jobs1",
    "parallel_efficiency_vs_jobs1",
    "notes",
]

TIME_PATTERNS = {
    "elapsed_wall_time": re.compile(r"Elapsed \(wall clock\) time.*: (.+)"),
    "user_seconds": re.compile(r"User time \(seconds\): (.+)"),
    "system_seconds": re.compile(r"System time \(seconds\): (.+)"),
    "percent_cpu": re.compile(r"Percent of CPU this job got: (.+)"),
    "max_rss_kb": re.compile(r"Maximum resident set size \(kbytes\): (.+)"),
    "exit_status": re.compile(r"Exit status: (.+)"),
}


def elapsed_to_seconds(value: str) -> str:
    value = value.strip()
    if value == "":
        return ""

    try:
        if ":" not in value:
            return f"{float(value):.6f}"

        parts = [float(x) for x in value.split(":")]
        if len(parts) == 3:
            seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            seconds = parts[0] * 60 + parts[1]
        else:
            return ""

        return f"{seconds:.6f}"
    except ValueError:
        return ""


def parse_time_file(path: Path) -> dict[str, str]:
    text = path.read_text(errors="replace")
    out = {key: "" for key in TIME_PATTERNS}

    for key, pattern in TIME_PATTERNS.items():
        match = pattern.search(text)
        if match:
            out[key] = match.group(1).strip()

    out["elapsed_wall_seconds"] = elapsed_to_seconds(out["elapsed_wall_time"])
    return out


def parse_name(path: Path) -> tuple[int, str] | None:
    match = re.search(r"jobs(\d+)_run(\d+)", path.name)
    if not match:
        return None
    jobs = int(match.group(1))
    replicate = f"run{match.group(2)}"
    return jobs, replicate


def count_completed_pairs(output_dir: Path) -> int:
    """Count completed pair JSONs.

    radigest-screen-pairs commonly writes per-pair JSONs under json/. Fall back
    to top-level JSON files if needed.
    """
    json_dir = output_dir / "json"
    if json_dir.exists():
        return len(list(json_dir.glob("*.json")))

    return len(list(output_dir.glob("*.json")))


def to_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"


def numeric_values(rows: list[dict[str, str]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = to_float(row.get(key, ""))
        if value is not None:
            values.append(value)
    return values


def median_numeric(rows: list[dict[str, str]], key: str) -> float | None:
    values = numeric_values(rows, key)
    if not values:
        return None
    return float(statistics.median(values))


def quartiles(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None

    values = sorted(values)

    if len(values) == 1:
        return values[0], values[0]

    if len(values) == 2:
        return values[0], values[1]

    mid = len(values) // 2

    if len(values) % 2 == 0:
        lower = values[:mid]
        upper = values[mid:]
    else:
        lower = values[:mid]
        upper = values[mid + 1 :]

    return float(statistics.median(lower)), float(statistics.median(upper))


def stat_bundle(values: list[float]) -> tuple[str, str, str, str]:
    if not values:
        return "", "", "", ""

    median = float(statistics.median(values))
    q1, q3 = quartiles(values)
    iqr = None if q1 is None or q3 is None else q3 - q1

    return fmt(median), fmt(q1), fmt(q3), fmt(iqr)


def build_run_rows(
    dataset: str,
    time_dir: Path,
    output_root: Path,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for time_file in sorted(time_dir.glob("cannabis_jobs*_run*.time")):
        parsed = parse_name(time_file)
        if parsed is None:
            print(
                f"warning: skipped unrecognized time file: {time_file}", file=sys.stderr
            )
            continue

        jobs, replicate = parsed
        run_number = replicate.removeprefix("run")
        output_dir = output_root / f"cannabis_jobs{jobs}_run{run_number}"
        timing = parse_time_file(time_file)
        completed_pairs = count_completed_pairs(output_dir)

        rows.append(
            {
                "dataset": dataset,
                "jobs": str(jobs),
                "replicate": replicate,
                "elapsed_wall_seconds": timing.get("elapsed_wall_seconds", ""),
                "user_seconds": timing.get("user_seconds", ""),
                "system_seconds": timing.get("system_seconds", ""),
                "percent_cpu": timing.get("percent_cpu", ""),
                "max_rss_kb": timing.get("max_rss_kb", ""),
                "exit_status": timing.get("exit_status", ""),
                "completed_pairs": str(completed_pairs),
                "time_file": str(time_file),
                "output_dir": str(output_dir),
            }
        )

    return rows


def summarize(run_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[int, list[dict[str, str]]] = defaultdict(list)

    for row in run_rows:
        groups[int(row["jobs"])].append(row)

    baseline = None
    if 1 in groups:
        baseline = median_numeric(groups[1], "elapsed_wall_seconds")

    out: list[dict[str, str]] = []

    for jobs, rows in sorted(groups.items()):
        elapsed = stat_bundle(numeric_values(rows, "elapsed_wall_seconds"))
        rss = stat_bundle(numeric_values(rows, "max_rss_kb"))

        median_elapsed = to_float(elapsed[0])
        median_pairs = median_numeric(rows, "completed_pairs")

        pairs_per_second = None
        if (
            median_elapsed is not None
            and median_elapsed > 0
            and median_pairs is not None
        ):
            pairs_per_second = median_pairs / median_elapsed

        speedup = None
        efficiency = None
        if baseline is not None and median_elapsed is not None and median_elapsed > 0:
            speedup = baseline / median_elapsed
            efficiency = speedup / float(jobs)

        out.append(
            {
                "dataset": rows[0]["dataset"],
                "jobs": str(jobs),
                "n_runs": str(len(rows)),
                "median_elapsed_wall_seconds": elapsed[0],
                "q1_elapsed_wall_seconds": elapsed[1],
                "q3_elapsed_wall_seconds": elapsed[2],
                "iqr_elapsed_wall_seconds": elapsed[3],
                "median_max_rss_kb": rss[0],
                "q1_max_rss_kb": rss[1],
                "q3_max_rss_kb": rss[2],
                "iqr_max_rss_kb": rss[3],
                "median_completed_pairs": fmt(median_pairs),
                "median_pairs_per_second": fmt(pairs_per_second),
                "speedup_vs_jobs1": fmt(speedup),
                "parallel_efficiency_vs_jobs1": fmt(efficiency),
                "notes": (
                    "radigest-screen-pairs job-level scaling; "
                    "radigest-threads fixed at 1"
                ),
            }
        )

    return out


def write_tsv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="cannabis_pink_pepper_plain")
    parser.add_argument(
        "--time-dir",
        type=Path,
        default=Path("benchmark/memory/pair_screen_scaling"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("results/raw/pair_screen_scaling"),
    )
    parser.add_argument(
        "--out-runs",
        type=Path,
        default=Path("results/tables/pair_screen_scaling_runs.tsv"),
    )
    parser.add_argument(
        "--out-summary",
        type=Path,
        default=Path("results/tables/pair_screen_scaling_summary.tsv"),
    )
    args = parser.parse_args(argv)

    try:
        run_rows = build_run_rows(
            dataset=args.dataset,
            time_dir=args.time_dir,
            output_root=args.output_root,
        )
        if not run_rows:
            raise ValueError("no pair-screen scaling runs found")

        summary_rows = summarize(run_rows)

        write_tsv(args.out_runs, run_rows, RUN_FIELDS)
        write_tsv(args.out_summary, summary_rows, SUMMARY_FIELDS)

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out_runs}", file=sys.stderr)
    print(f"wrote {args.out_summary}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
