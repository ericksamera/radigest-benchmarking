#!/usr/bin/env python3
"""Summarize DDRADSEQTOOLS rsitesearch.py timing replicates.

Expected input time files are GNU time -v outputs, for example:

  benchmark/memory/ddradseqtools/ddradseqtools_yeast_B1_wide_run1.time

The script writes:
  - run-level timing table;
  - aggregate median/Q1/Q3/IQR table.

This summarizes digest-level rsitesearch.py timing only. It does not summarize
DDRADSEQTOOLS read simulation, adapter simulation, PCR duplicate modelling,
allele dropout modelling, or preprocessing workflows.
"""

from __future__ import annotations

import argparse
import csv
import glob
import re
import statistics
import sys
from pathlib import Path

RUN_FIELDS = [
    "dataset",
    "condition",
    "tool",
    "task",
    "replicate",
    "elapsed_wall_seconds",
    "user_seconds",
    "system_seconds",
    "percent_cpu",
    "max_rss_kb",
    "exit_status",
    "time_file",
    "notes",
]

SUMMARY_FIELDS = [
    "dataset",
    "condition",
    "tool",
    "task",
    "n_runs",
    "median_elapsed_wall_seconds",
    "q1_elapsed_wall_seconds",
    "q3_elapsed_wall_seconds",
    "iqr_elapsed_wall_seconds",
    "median_max_rss_kb",
    "q1_max_rss_kb",
    "q3_max_rss_kb",
    "iqr_max_rss_kb",
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


def write_tsv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_run_rows(
    time_glob: str,
    dataset: str,
    condition: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    files = sorted(Path(p) for p in glob.glob(time_glob))
    if not files:
        raise FileNotFoundError(f"no time files matched: {time_glob}")

    for path in files:
        timing = parse_time_file(path)

        match = re.search(r"run(\d+)", path.name)
        replicate = f"run{match.group(1)}" if match else path.stem

        rows.append(
            {
                "dataset": dataset,
                "condition": condition,
                "tool": "DDRADSEQTOOLS",
                "task": "rsitesearch_digest",
                "replicate": replicate,
                "elapsed_wall_seconds": timing.get("elapsed_wall_seconds", ""),
                "user_seconds": timing.get("user_seconds", ""),
                "system_seconds": timing.get("system_seconds", ""),
                "percent_cpu": timing.get("percent_cpu", ""),
                "max_rss_kb": timing.get("max_rss_kb", ""),
                "exit_status": timing.get("exit_status", ""),
                "time_file": str(path),
                "notes": (
                    "Timing for DDRADSEQTOOLS Package/rsitesearch.py only; "
                    "digest-level fragment generation, not read simulation."
                ),
            }
        )

    return rows


def build_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    elapsed = [
        x
        for x in (to_float(row.get("elapsed_wall_seconds", "")) for row in rows)
        if x is not None
    ]
    rss = [
        x
        for x in (to_float(row.get("max_rss_kb", "")) for row in rows)
        if x is not None
    ]

    elapsed_stats = stat_bundle(elapsed)
    rss_stats = stat_bundle(rss)

    dataset = rows[0]["dataset"]
    condition = rows[0]["condition"]

    return [
        {
            "dataset": dataset,
            "condition": condition,
            "tool": "DDRADSEQTOOLS",
            "task": "rsitesearch_digest",
            "n_runs": str(len(rows)),
            "median_elapsed_wall_seconds": elapsed_stats[0],
            "q1_elapsed_wall_seconds": elapsed_stats[1],
            "q3_elapsed_wall_seconds": elapsed_stats[2],
            "iqr_elapsed_wall_seconds": elapsed_stats[3],
            "median_max_rss_kb": rss_stats[0],
            "q1_max_rss_kb": rss_stats[1],
            "q3_max_rss_kb": rss_stats[2],
            "iqr_max_rss_kb": rss_stats[3],
            "notes": (
                "DDRADSEQTOOLS timing is restricted to rsitesearch.py digest-level "
                "fragment generation. Broader simulation tasks are excluded."
            ),
        }
    ]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--time-glob", required=True)
    parser.add_argument("--dataset", default="yeast_small_plain")
    parser.add_argument("--condition", default="B1")
    parser.add_argument(
        "--out-runs",
        type=Path,
        default=Path("results/tables/ddradseqtools_timing_runs.tsv"),
    )
    parser.add_argument(
        "--out-summary",
        type=Path,
        default=Path("results/tables/ddradseqtools_timing_summary.tsv"),
    )
    args = parser.parse_args(argv)

    try:
        run_rows = build_run_rows(
            time_glob=args.time_glob,
            dataset=args.dataset,
            condition=args.condition,
        )
        summary_rows = build_summary(run_rows)

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
