#!/usr/bin/env python3
"""Summarize matched tool benchmark outputs.

This script summarizes benchmark outputs from scripts/run_matched_tool_benchmarks.sh.

It reports runtime and memory from GNU time -v files and combines them with
task-specific fragment/bases metrics.

Tasks:
  radigest_count
  simrad_count
  radigest_interval
  digital_rads_interval
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

RUN_COLUMNS = [
    "dataset",
    "condition",
    "task",
    "tool",
    "output_object",
    "replicate",
    "elapsed_wall_seconds",
    "user_seconds",
    "system_seconds",
    "percent_cpu",
    "max_rss_kb",
    "exit_status",
    "fragments",
    "bases",
    "output_dir",
    "time_file",
    "notes",
]

SUMMARY_COLUMNS = [
    "dataset",
    "condition",
    "task",
    "tool",
    "output_object",
    "n_runs",
    "median_elapsed_wall_seconds",
    "q1_elapsed_wall_seconds",
    "q3_elapsed_wall_seconds",
    "iqr_elapsed_wall_seconds",
    "median_max_rss_kb",
    "q1_max_rss_kb",
    "q3_max_rss_kb",
    "iqr_max_rss_kb",
    "median_fragments",
    "median_bases",
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

TASK_METADATA = {
    "radigest_count": ("radigest", "aggregate JSON count"),
    "simrad_count": ("SimRAD", "aggregate count"),
    "radigest_interval": ("radigest", "normalized interval set"),
    "digital_rads_interval": ("Digital_RADs.py", "normalized interval set"),
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


def load_json_dict(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        obj = json.load(handle)

    if not isinstance(obj, dict):
        raise ValueError(f"{path}: expected JSON object")

    return obj


def read_one_tsv_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    if len(rows) != 1:
        raise ValueError(f"{path}: expected one row, found {len(rows)}")

    return {key: "" if value is None else value for key, value in rows[0].items()}


def interval_metrics(path: Path) -> tuple[str, str]:
    count = 0
    bases = 0

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            count += 1
            bases += int(row["length"])

    return str(count), str(bases)


def metrics_for_task(task: str, output_dir: Path) -> tuple[str, str, str]:
    if task == "radigest_count":
        doc = load_json_dict(output_dir / "radigest.json")
        return (
            str(doc.get("total_fragments", "")),
            str(doc.get("total_bases", "")),
            "",
        )

    if task == "simrad_count":
        row = read_one_tsv_row(output_dir / "simrad.tsv")
        return (
            row.get("size_selected_fragments", ""),
            row.get("total_bases", ""),
            row.get("notes", ""),
        )

    if task == "radigest_interval":
        fragments, bases = interval_metrics(output_dir / "radigest.normalized.tsv")
        return fragments, bases, ""

    if task == "digital_rads_interval":
        fragments, bases = interval_metrics(output_dir / "digital.normalized.tsv")
        return fragments, bases, ""

    raise ValueError(f"unknown task: {task}")


def parse_time_filename(path: Path) -> tuple[str, str, str, str] | None:
    """Parse matched-tool benchmark time filename.

    Expected:
      <task>__<dataset>__<condition>__<replicate>.time

    Unrelated timing files are ignored rather than treated as fatal errors.
    This allows warm-session SimRAD timing files to live in the same directory
    without breaking matched-tool summaries.
    """
    stem = path.name.removesuffix(".time")
    parts = stem.split("__")

    if len(parts) != 4:
        return None

    task, dataset, condition, replicate = parts

    if task not in TASK_METADATA:
        return None

    return task, dataset, condition, replicate


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
    n = len(vals)

    if n == 1:
        return vals[0], vals[0]

    if n == 2:
        return vals[0], vals[1]

    mid = n // 2
    if n % 2 == 0:
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


def numeric_values(rows: list[dict[str, str]], column: str) -> list[float]:
    values = [to_float(row.get(column, "")) for row in rows]
    return [value for value in values if value is not None]


def build_run_rows(
    root: Path,
    time_dir: Path,
    dataset_filter: str,
    condition_filter: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for time_file in sorted(time_dir.glob("*.time")):
        parsed = parse_time_filename(time_file)
        if parsed is None:
            print(
                f"warning: skipping unmatched time file: {time_file}",
                file=sys.stderr,
            )
            continue

        task, dataset, condition, replicate = parsed

        if dataset_filter and dataset != dataset_filter:
            continue
        if condition_filter and condition != condition_filter:
            continue

        output_dir = root / f"{task}__{dataset}__{condition}__{replicate}"
        tool, output_object = TASK_METADATA.get(task, (task, ""))

        time_values = parse_time(time_file)

        try:
            fragments, bases, notes = metrics_for_task(task, output_dir)
        except Exception as exc:
            fragments, bases, notes = "", "", f"metric_parse_error: {exc}"

        rows.append(
            {
                "dataset": dataset,
                "condition": condition,
                "task": task,
                "tool": tool,
                "output_object": output_object,
                "replicate": replicate,
                "elapsed_wall_seconds": time_values.get("elapsed_wall_seconds", ""),
                "user_seconds": time_values.get("user_seconds", ""),
                "system_seconds": time_values.get("system_seconds", ""),
                "percent_cpu": time_values.get("percent_cpu", ""),
                "max_rss_kb": time_values.get("max_rss_kb", ""),
                "exit_status": time_values.get("exit_status", ""),
                "fragments": fragments,
                "bases": bases,
                "output_dir": str(output_dir),
                "time_file": str(time_file),
                "notes": notes,
            }
        )

    return rows


def summarize_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, str]]] = defaultdict(
        list
    )

    for row in rows:
        key = (
            row["dataset"],
            row["condition"],
            row["task"],
            row["tool"],
            row["output_object"],
        )
        grouped[key].append(row)

    out: list[dict[str, str]] = []

    for (dataset, condition, task, tool, output_object), group in sorted(
        grouped.items()
    ):
        elapsed = stat_bundle(numeric_values(group, "elapsed_wall_seconds"))
        rss = stat_bundle(numeric_values(group, "max_rss_kb"))
        fragments = stat_bundle(numeric_values(group, "fragments"))[0]
        bases = stat_bundle(numeric_values(group, "bases"))[0]

        notes = "; ".join(
            sorted({row.get("notes", "") for row in group if row.get("notes", "")})
        )

        out.append(
            {
                "dataset": dataset,
                "condition": condition,
                "task": task,
                "tool": tool,
                "output_object": output_object,
                "n_runs": str(len(group)),
                "median_elapsed_wall_seconds": elapsed[0],
                "q1_elapsed_wall_seconds": elapsed[1],
                "q3_elapsed_wall_seconds": elapsed[2],
                "iqr_elapsed_wall_seconds": elapsed[3],
                "median_max_rss_kb": rss[0],
                "q1_max_rss_kb": rss[1],
                "q3_max_rss_kb": rss[2],
                "iqr_max_rss_kb": rss[3],
                "median_fragments": fragments,
                "median_bases": bases,
                "notes": notes,
            }
        )

    return out


def write_tsv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path("results/raw/matched_tool_benchmarks")
    )
    parser.add_argument(
        "--time-dir", type=Path, default=Path("benchmark/memory/matched_tools")
    )
    parser.add_argument("--dataset", default="")
    parser.add_argument("--condition", default="")
    parser.add_argument(
        "--out-runs",
        type=Path,
        default=Path("results/tables/matched_tool_benchmark_runs.tsv"),
    )
    parser.add_argument(
        "--out-summary",
        type=Path,
        default=Path("results/tables/matched_tool_benchmark_summary.tsv"),
    )
    args = parser.parse_args(argv)

    try:
        run_rows = build_run_rows(
            root=args.root,
            time_dir=args.time_dir,
            dataset_filter=args.dataset,
            condition_filter=args.condition,
        )
        summary_rows = summarize_rows(run_rows)

        write_tsv(args.out_runs, run_rows, RUN_COLUMNS)
        write_tsv(args.out_summary, summary_rows, SUMMARY_COLUMNS)

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out_runs}", file=sys.stderr)
    print(f"wrote {args.out_summary}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
