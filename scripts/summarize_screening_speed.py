#!/usr/bin/env python3
"""Summarize screening-speed benchmarks for radigest and ddgRADer."""

from __future__ import annotations

import argparse
import csv
import glob
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

RUN_FIELDS = [
    "dataset",
    "tool",
    "task",
    "replicate",
    "candidate_pairs",
    "completed_pairs",
    "elapsed_wall_seconds",
    "user_seconds",
    "system_seconds",
    "percent_cpu",
    "max_rss_kb",
    "exit_status",
    "output_dir",
    "time_file",
    "notes",
]

SUMMARY_FIELDS = [
    "dataset",
    "tool",
    "task",
    "n_runs",
    "candidate_pairs",
    "median_completed_pairs",
    "median_elapsed_wall_seconds",
    "q1_elapsed_wall_seconds",
    "q3_elapsed_wall_seconds",
    "iqr_elapsed_wall_seconds",
    "median_max_rss_kb",
    "q1_max_rss_kb",
    "q3_max_rss_kb",
    "iqr_max_rss_kb",
    "median_pairs_per_second",
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


def parse_time(path: Path) -> dict[str, str]:
    text = path.read_text(errors="replace")
    out = {key: "" for key in TIME_PATTERNS}
    for key, pattern in TIME_PATTERNS.items():
        match = pattern.search(text)
        if match:
            out[key] = match.group(1).strip()
    out["elapsed_wall_seconds"] = elapsed_to_seconds(out["elapsed_wall_time"])
    return out


def parse_time_name(path: Path) -> tuple[str, str, str] | None:
    stem = path.name.removesuffix(".time")
    parts = stem.split("__")
    if len(parts) != 3:
        return None
    task, dataset, replicate = parts
    return task, dataset, replicate


def count_candidate_pairs(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return sum(1 for _ in reader)


def count_radigest_pairs(output_dir: Path) -> int:
    return len(glob.glob(str(output_dir / "json" / "*.json")))


def count_ddgrader_pairs(output_dir: Path) -> int:
    summary = output_dir / "ddgrader.summary.tsv"
    if not summary.exists():
        return 0
    with summary.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return sum(1 for _ in reader)


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


def quartiles(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    vals = sorted(values)
    if len(vals) == 1:
        return vals[0], vals[0]
    if len(vals) == 2:
        return vals[0], vals[1]
    mid = len(vals) // 2
    if len(vals) % 2 == 0:
        lower = vals[:mid]
        upper = vals[mid:]
    else:
        lower = vals[:mid]
        upper = vals[mid + 1 :]
    return float(statistics.median(lower)), float(statistics.median(upper))


def fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"


def stat_bundle(values: list[float]) -> tuple[str, str, str, str]:
    if not values:
        return "", "", "", ""
    median = float(statistics.median(values))
    q1, q3 = quartiles(values)
    iqr = None if q1 is None or q3 is None else q3 - q1
    return fmt(median), fmt(q1), fmt(q3), fmt(iqr)


def build_runs(
    root: Path, time_dir: Path, pair_tsv: Path, dataset_filter: str
) -> list[dict[str, str]]:
    candidate_pairs = count_candidate_pairs(pair_tsv)
    rows: list[dict[str, str]] = []

    for time_file in sorted(time_dir.glob("*.time")):
        parsed = parse_time_name(time_file)
        if parsed is None:
            continue

        task, dataset, replicate = parsed
        if dataset_filter and dataset != dataset_filter:
            continue

        if task == "radigest_screen_pairs":
            tool = "radigest"
            output_dir = root / f"radigest__{dataset}__{replicate}"
            completed = count_radigest_pairs(output_dir)
            notes = "radigest-screen-pairs over unordered candidate enzyme pairs"
        elif task == "ddgrader_backend":
            tool = "ddgRADer_backend"
            output_dir = root / f"ddgrader__{dataset}__{replicate}"
            completed = count_ddgrader_pairs(output_dir)
            notes = "ddgRADer backend binned fragment distribution over same pairs"
        else:
            continue

        timing = parse_time(time_file)

        rows.append(
            {
                "dataset": dataset,
                "tool": tool,
                "task": task,
                "replicate": replicate,
                "candidate_pairs": str(candidate_pairs),
                "completed_pairs": str(completed),
                "elapsed_wall_seconds": timing.get("elapsed_wall_seconds", ""),
                "user_seconds": timing.get("user_seconds", ""),
                "system_seconds": timing.get("system_seconds", ""),
                "percent_cpu": timing.get("percent_cpu", ""),
                "max_rss_kb": timing.get("max_rss_kb", ""),
                "exit_status": timing.get("exit_status", ""),
                "output_dir": str(output_dir),
                "time_file": str(time_file),
                "notes": notes,
            }
        )

    return rows


def summarize(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        groups[(row["dataset"], row["tool"], row["task"])].append(row)

    out: list[dict[str, str]] = []

    for (dataset, tool, task), group in sorted(groups.items()):
        elapsed = [to_float(row["elapsed_wall_seconds"]) for row in group]
        elapsed_vals = [x for x in elapsed if x is not None]
        rss = [to_float(row["max_rss_kb"]) for row in group]
        rss_vals = [x for x in rss if x is not None]
        completed = [to_float(row["completed_pairs"]) for row in group]
        completed_vals = [x for x in completed if x is not None]
        pair_rates: list[float] = []

        for row in group:
            pairs = to_float(row["completed_pairs"])
            seconds = to_float(row["elapsed_wall_seconds"])
            if pairs is not None and seconds is not None and seconds > 0:
                pair_rates.append(pairs / seconds)

        elapsed_stats = stat_bundle(elapsed_vals)
        rss_stats = stat_bundle(rss_vals)

        out.append(
            {
                "dataset": dataset,
                "tool": tool,
                "task": task,
                "n_runs": str(len(group)),
                "candidate_pairs": group[0].get("candidate_pairs", ""),
                "median_completed_pairs": (
                    fmt(float(statistics.median(completed_vals)))
                    if completed_vals
                    else ""
                ),
                "median_elapsed_wall_seconds": elapsed_stats[0],
                "q1_elapsed_wall_seconds": elapsed_stats[1],
                "q3_elapsed_wall_seconds": elapsed_stats[2],
                "iqr_elapsed_wall_seconds": elapsed_stats[3],
                "median_max_rss_kb": rss_stats[0],
                "q1_max_rss_kb": rss_stats[1],
                "q3_max_rss_kb": rss_stats[2],
                "iqr_max_rss_kb": rss_stats[3],
                "median_pairs_per_second": (
                    fmt(float(statistics.median(pair_rates))) if pair_rates else ""
                ),
                "notes": "; ".join(sorted({row["notes"] for row in group})),
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
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--time-dir", required=True, type=Path)
    parser.add_argument("--pair-tsv", required=True, type=Path)
    parser.add_argument("--dataset", default="")
    parser.add_argument("--out-runs", required=True, type=Path)
    parser.add_argument("--out-summary", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        run_rows = build_runs(args.root, args.time_dir, args.pair_tsv, args.dataset)
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
