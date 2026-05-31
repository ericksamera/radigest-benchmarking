#!/usr/bin/env python3
"""Summarize radigest thread-scaling benchmark outputs."""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

RUN_FIELDS = [
    "dataset",
    "condition",
    "mode",
    "threads",
    "replicate",
    "elapsed_wall_seconds",
    "user_seconds",
    "system_seconds",
    "percent_cpu",
    "max_rss_kb",
    "exit_status",
    "json_file",
    "primary_output_file",
    "primary_output_size_bytes",
    "total_fragments",
    "total_bases",
    "time_file",
    "notes",
]

SUMMARY_FIELDS = [
    "dataset",
    "condition",
    "mode",
    "threads",
    "n_runs",
    "median_elapsed_wall_seconds",
    "q1_elapsed_wall_seconds",
    "q3_elapsed_wall_seconds",
    "iqr_elapsed_wall_seconds",
    "median_max_rss_kb",
    "q1_max_rss_kb",
    "q3_max_rss_kb",
    "iqr_max_rss_kb",
    "median_primary_output_size_bytes",
    "median_total_fragments",
    "median_total_bases",
    "speedup_vs_threads1",
    "parallel_efficiency_vs_threads1",
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


def parse_base_name(path: Path) -> dict[str, str] | None:
    stem = path.name.removesuffix(".time")
    parts = stem.split("__")

    if len(parts) != 5:
        return None

    dataset, condition, mode, threads_part, replicate = parts

    if not threads_part.startswith("threads"):
        return None

    return {
        "dataset": dataset,
        "condition": condition,
        "mode": mode,
        "threads": threads_part.removeprefix("threads"),
        "replicate": replicate,
        "base": stem,
    }


def read_json_summary(path: Path) -> dict[str, str]:
    if not path.exists():
        return {"total_fragments": "", "total_bases": ""}

    with path.open(encoding="utf-8") as handle:
        obj = json.load(handle)

    def get_number(*keys: str) -> str:
        for key in keys:
            value = obj.get(key)
            if isinstance(value, (int, float)):
                if abs(value - round(value)) < 1e-9:
                    return str(int(round(value)))
                return f"{value:.6f}"
        return ""

    return {
        "total_fragments": get_number("total_fragments", "fragments_kept"),
        "total_bases": get_number("total_bases", "bases_covered"),
    }


def primary_output(root: Path, base: str, mode: str, json_file: Path) -> Path:
    if mode == "json":
        return json_file
    if mode == "gff":
        return root / f"{base}.gff3"
    if mode == "fragments_tsv":
        return root / f"{base}.fragments.tsv"
    if mode == "fragments_fasta":
        return root / f"{base}.fragments.fa"
    return json_file


def to_float(value: str | None) -> float | None:
    if value is None:
        return None

    value = str(value).strip()
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


def build_run_rows(root: Path, time_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for time_file in sorted(time_dir.glob("*.time")):
        parsed = parse_base_name(time_file)
        if parsed is None:
            print(
                f"warning: skipping unrecognized time file: {time_file}",
                file=sys.stderr,
            )
            continue

        base = parsed["base"]
        mode = parsed["mode"]

        json_file = root / f"{base}.json"
        primary = primary_output(root, base, mode, json_file)
        timing = parse_time_file(time_file)
        json_summary = read_json_summary(json_file)

        rows.append(
            {
                "dataset": parsed["dataset"],
                "condition": parsed["condition"],
                "mode": mode,
                "threads": parsed["threads"],
                "replicate": parsed["replicate"],
                "elapsed_wall_seconds": timing.get("elapsed_wall_seconds", ""),
                "user_seconds": timing.get("user_seconds", ""),
                "system_seconds": timing.get("system_seconds", ""),
                "percent_cpu": timing.get("percent_cpu", ""),
                "max_rss_kb": timing.get("max_rss_kb", ""),
                "exit_status": timing.get("exit_status", ""),
                "json_file": str(json_file),
                "primary_output_file": str(primary),
                "primary_output_size_bytes": (
                    str(primary.stat().st_size) if primary.exists() else ""
                ),
                "total_fragments": json_summary["total_fragments"],
                "total_bases": json_summary["total_bases"],
                "time_file": str(time_file),
                "notes": "radigest thread-scaling benchmark",
            }
        )

    return rows


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


def build_summary_rows(run_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[tuple[str, str, str, int], list[dict[str, str]]] = defaultdict(list)

    for row in run_rows:
        groups[
            (
                row["dataset"],
                row["condition"],
                row["mode"],
                int(row["threads"]),
            )
        ].append(row)

    thread1_median_by_mode: dict[tuple[str, str, str], float] = {}

    for (dataset, condition, mode, threads), rows in groups.items():
        if threads == 1:
            med = median_numeric(rows, "elapsed_wall_seconds")
            if med is not None:
                thread1_median_by_mode[(dataset, condition, mode)] = med

    summary_rows: list[dict[str, str]] = []

    for (dataset, condition, mode, threads), rows in sorted(groups.items()):
        elapsed_values = [
            value
            for value in (to_float(row.get("elapsed_wall_seconds", "")) for row in rows)
            if value is not None
        ]
        rss_values = [
            value
            for value in (to_float(row.get("max_rss_kb", "")) for row in rows)
            if value is not None
        ]
        output_size_values = numeric_values(rows, "primary_output_size_bytes")

        elapsed = stat_bundle(elapsed_values)
        rss = stat_bundle(rss_values)
        median_elapsed = to_float(elapsed[0])

        baseline = thread1_median_by_mode.get((dataset, condition, mode))
        speedup = None
        efficiency = None

        if baseline is not None and median_elapsed is not None and median_elapsed > 0:
            speedup = baseline / median_elapsed
            efficiency = speedup / float(threads)

        summary_rows.append(
            {
                "dataset": dataset,
                "condition": condition,
                "mode": mode,
                "threads": str(threads),
                "n_runs": str(len(rows)),
                "median_elapsed_wall_seconds": elapsed[0],
                "q1_elapsed_wall_seconds": elapsed[1],
                "q3_elapsed_wall_seconds": elapsed[2],
                "iqr_elapsed_wall_seconds": elapsed[3],
                "median_max_rss_kb": rss[0],
                "q1_max_rss_kb": rss[1],
                "q3_max_rss_kb": rss[2],
                "iqr_max_rss_kb": rss[3],
                "median_primary_output_size_bytes": fmt(
                    float(statistics.median(output_size_values))
                    if output_size_values
                    else None
                ),
                "median_total_fragments": fmt(median_numeric(rows, "total_fragments")),
                "median_total_bases": fmt(median_numeric(rows, "total_bases")),
                "speedup_vs_threads1": fmt(speedup),
                "parallel_efficiency_vs_threads1": fmt(efficiency),
                "notes": (
                    "speedup and efficiency are calculated within each "
                    "dataset/condition/mode relative to threads=1"
                ),
            }
        )

    return summary_rows


def write_tsv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("results/raw/radigest_thread_scaling"),
    )
    parser.add_argument(
        "--time-dir",
        type=Path,
        default=Path("benchmark/memory/radigest_thread_scaling"),
    )
    parser.add_argument(
        "--out-runs",
        type=Path,
        default=Path("results/tables/radigest_thread_scaling_runs.tsv"),
    )
    parser.add_argument(
        "--out-summary",
        type=Path,
        default=Path("results/tables/radigest_thread_scaling_summary.tsv"),
    )
    args = parser.parse_args(argv)

    try:
        run_rows = build_run_rows(args.root, args.time_dir)
        summary_rows = build_summary_rows(run_rows)

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
