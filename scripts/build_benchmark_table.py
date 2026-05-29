#!/usr/bin/env python3
"""Build run-level and aggregate radigest benchmark tables.

Inputs:
  - results/tables/radigest_json_summary.tsv
  - results/tables/radigest_memory_summary.tsv

Outputs:
  - run-level TSV
  - aggregate TSV grouped by dataset, condition, output_mode

This script is intentionally filename-driven. It expects benchmark files named:

  <dataset>__<condition>__<output_mode>__run<replicate>.json
  <dataset>__<condition>__<output_mode>__run<replicate>.time

where output_mode is one of:
  json
  gff
  fragments_tsv
  fragments_fasta
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

RUN_COLUMNS = [
    "dataset",
    "condition",
    "output_mode",
    "replicate",
    "json_file",
    "time_file",
    "primary_output_file",
    "primary_output_size_bytes",
    "total_fragments",
    "total_bases",
    "size_model",
    "weighted_fragments",
    "weighted_bases",
    "mean_weighted_length",
    "elapsed_wall_seconds",
    "user_seconds",
    "system_seconds",
    "percent_cpu",
    "max_rss_kb",
    "exit_status",
    "warnings",
]

SUMMARY_COLUMNS = [
    "dataset",
    "condition",
    "output_mode",
    "n_runs",
    "median_elapsed_wall_seconds",
    "iqr_elapsed_wall_seconds",
    "median_max_rss_kb",
    "iqr_max_rss_kb",
    "median_primary_output_size_bytes",
    "median_total_fragments",
    "median_total_bases",
    "median_weighted_fragments",
    "median_weighted_bases",
]


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing input TSV: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def parse_stem(path_text: str) -> tuple[str, str, str, str]:
    """Parse dataset/condition/mode/run from a benchmark file path."""
    stem = Path(path_text).name
    for suffix in [".json", ".time", ".gff3", ".fragments.tsv", ".fragments.fa"]:
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break

    parts = stem.split("__")
    if len(parts) < 4:
        return "", "", "", ""

    dataset = parts[0]
    condition = parts[1]
    run = parts[-1]
    output_mode = "__".join(parts[2:-1])
    return dataset, condition, output_mode, run


def elapsed_to_seconds(value: str) -> str:
    """Convert GNU time elapsed format to seconds.

    GNU time may emit:
      H:MM:SS
      M:SS
      seconds-like values
    """
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


def to_float(value: str) -> float | None:
    if value is None:
        return None
    value = str(value).strip()
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def median_text(values: list[float]) -> str:
    if not values:
        return ""
    return f"{statistics.median(values):.6f}"


def iqr_text(values: list[float]) -> str:
    if len(values) < 2:
        return "0.000000" if values else ""

    sorted_values = sorted(values)
    mid = len(sorted_values) // 2

    if len(sorted_values) % 2 == 0:
        lower = sorted_values[:mid]
        upper = sorted_values[mid:]
    else:
        lower = sorted_values[:mid]
        upper = sorted_values[mid + 1 :]

    if not lower or not upper:
        return "0.000000"

    q1 = statistics.median(lower)
    q3 = statistics.median(upper)
    return f"{q3 - q1:.6f}"


def primary_output_for_json(json_file: str, output_mode: str) -> str:
    path = Path(json_file)
    if output_mode == "json":
        return json_file
    if output_mode == "gff":
        return str(path.with_suffix(".gff3"))
    if output_mode == "fragments_tsv":
        return str(Path(str(path).removesuffix(".json") + ".fragments.tsv"))
    if output_mode == "fragments_fasta":
        return str(Path(str(path).removesuffix(".json") + ".fragments.fa"))
    return ""


def file_size_text(path_text: str) -> str:
    if path_text == "":
        return ""
    path = Path(path_text)
    if not path.exists():
        return ""
    return str(path.stat().st_size)


def build_run_table(
    json_rows: list[dict[str, str]],
    time_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    time_by_key: dict[tuple[str, str, str, str], dict[str, str]] = {}

    for row in time_rows:
        dataset, condition, mode, run = parse_stem(row.get("file", ""))
        if dataset and condition and mode and run:
            time_by_key[(dataset, condition, mode, run)] = row

    out: list[dict[str, str]] = []

    for row in json_rows:
        json_file = row.get("file", "")
        dataset, condition, mode, run = parse_stem(json_file)
        if not dataset:
            dataset = row.get("dataset", "")
        if not condition:
            condition = row.get("condition", "")

        key = (dataset, condition, mode, run)
        time_row = time_by_key.get(key, {})

        primary_output = primary_output_for_json(json_file, mode)
        elapsed_seconds = elapsed_to_seconds(time_row.get("elapsed_wall_time", ""))

        out.append(
            {
                "dataset": dataset,
                "condition": condition,
                "output_mode": mode,
                "replicate": run,
                "json_file": json_file,
                "time_file": time_row.get("file", ""),
                "primary_output_file": primary_output,
                "primary_output_size_bytes": file_size_text(primary_output),
                "total_fragments": row.get("total_fragments", ""),
                "total_bases": row.get("total_bases", ""),
                "size_model": row.get("size_model", ""),
                "weighted_fragments": row.get("weighted_fragments", ""),
                "weighted_bases": row.get("weighted_bases", ""),
                "mean_weighted_length": row.get("mean_weighted_length", ""),
                "elapsed_wall_seconds": elapsed_seconds,
                "user_seconds": time_row.get("user_seconds", ""),
                "system_seconds": time_row.get("system_seconds", ""),
                "percent_cpu": time_row.get("percent_cpu", ""),
                "max_rss_kb": time_row.get("max_rss_kb", ""),
                "exit_status": time_row.get("exit_status", ""),
                "warnings": row.get("warnings", ""),
            }
        )

    return out


def numeric_values(rows: list[dict[str, str]], column: str) -> list[float]:
    vals = [to_float(row.get(column, "")) for row in rows]
    return [v for v in vals if v is not None]


def aggregate_runs(run_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)

    for row in run_rows:
        key = (row["dataset"], row["condition"], row["output_mode"])
        groups[key].append(row)

    out: list[dict[str, str]] = []

    for (dataset, condition, mode), rows in sorted(groups.items()):
        out.append(
            {
                "dataset": dataset,
                "condition": condition,
                "output_mode": mode,
                "n_runs": str(len(rows)),
                "median_elapsed_wall_seconds": median_text(
                    numeric_values(rows, "elapsed_wall_seconds")
                ),
                "iqr_elapsed_wall_seconds": iqr_text(
                    numeric_values(rows, "elapsed_wall_seconds")
                ),
                "median_max_rss_kb": median_text(numeric_values(rows, "max_rss_kb")),
                "iqr_max_rss_kb": iqr_text(numeric_values(rows, "max_rss_kb")),
                "median_primary_output_size_bytes": median_text(
                    numeric_values(rows, "primary_output_size_bytes")
                ),
                "median_total_fragments": median_text(
                    numeric_values(rows, "total_fragments")
                ),
                "median_total_bases": median_text(numeric_values(rows, "total_bases")),
                "median_weighted_fragments": median_text(
                    numeric_values(rows, "weighted_fragments")
                ),
                "median_weighted_bases": median_text(
                    numeric_values(rows, "weighted_bases")
                ),
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
    parser.add_argument("--json-summary", required=True, type=Path)
    parser.add_argument("--time-summary", required=True, type=Path)
    parser.add_argument("--out-runs", required=True, type=Path)
    parser.add_argument("--out-summary", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        json_rows = read_tsv(args.json_summary)
        time_rows = read_tsv(args.time_summary)
        run_rows = build_run_table(json_rows, time_rows)
        summary_rows = aggregate_runs(run_rows)
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
