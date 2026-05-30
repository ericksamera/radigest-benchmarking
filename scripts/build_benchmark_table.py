#!/usr/bin/env python3
"""Build run-level and aggregate radigest benchmark tables.

Inputs:
  - results/tables/radigest_json_summary.tsv
  - results/tables/radigest_memory_summary.tsv

Outputs:
  - run-level TSV
  - aggregate TSV grouped by dataset, condition, output_mode

Expected benchmark filenames:

  <dataset>__<condition>__<output_mode>__run<replicate>.json
  <dataset>__<condition>__<output_mode>__run<replicate>.time

The aggregate table reports medians, Q1, Q3, and IQR. These are intended for
small-N reproducible benchmark summaries and figure error bars.
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
    "q1_elapsed_wall_seconds",
    "q3_elapsed_wall_seconds",
    "iqr_elapsed_wall_seconds",
    "median_max_rss_kb",
    "q1_max_rss_kb",
    "q3_max_rss_kb",
    "iqr_max_rss_kb",
    "median_primary_output_size_bytes",
    "q1_primary_output_size_bytes",
    "q3_primary_output_size_bytes",
    "iqr_primary_output_size_bytes",
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
    """Convert GNU time elapsed format to seconds."""
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


def median_value(values: list[float]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


def quartiles(values: list[float]) -> tuple[float | None, float | None]:
    """Return Q1 and Q3 using exclusive halves around the median.

    For n=1, Q1 and Q3 equal the single observed value.
    For n=2, Q1 and Q3 equal the two observations.
    For n>=3, use median of lower and upper halves.
    """
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


def numeric_values(rows: list[dict[str, str]], column: str) -> list[float]:
    vals = [to_float(row.get(column, "")) for row in rows]
    return [v for v in vals if v is not None]


def stat_bundle(values: list[float]) -> tuple[str, str, str, str]:
    med = median_value(values)
    q1, q3 = quartiles(values)
    iqr = None if q1 is None or q3 is None else q3 - q1
    return fmt(med), fmt(q1), fmt(q3), fmt(iqr)


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


def aggregate_runs(run_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)

    for row in run_rows:
        key = (row["dataset"], row["condition"], row["output_mode"])
        groups[key].append(row)

    out: list[dict[str, str]] = []

    for (dataset, condition, mode), rows in sorted(groups.items()):
        elapsed = stat_bundle(numeric_values(rows, "elapsed_wall_seconds"))
        rss = stat_bundle(numeric_values(rows, "max_rss_kb"))
        output_size = stat_bundle(numeric_values(rows, "primary_output_size_bytes"))

        out.append(
            {
                "dataset": dataset,
                "condition": condition,
                "output_mode": mode,
                "n_runs": str(len(rows)),
                "median_elapsed_wall_seconds": elapsed[0],
                "q1_elapsed_wall_seconds": elapsed[1],
                "q3_elapsed_wall_seconds": elapsed[2],
                "iqr_elapsed_wall_seconds": elapsed[3],
                "median_max_rss_kb": rss[0],
                "q1_max_rss_kb": rss[1],
                "q3_max_rss_kb": rss[2],
                "iqr_max_rss_kb": rss[3],
                "median_primary_output_size_bytes": output_size[0],
                "q1_primary_output_size_bytes": output_size[1],
                "q3_primary_output_size_bytes": output_size[2],
                "iqr_primary_output_size_bytes": output_size[3],
                "median_total_fragments": fmt(
                    median_value(numeric_values(rows, "total_fragments"))
                ),
                "median_total_bases": fmt(
                    median_value(numeric_values(rows, "total_bases"))
                ),
                "median_weighted_fragments": fmt(
                    median_value(numeric_values(rows, "weighted_fragments"))
                ),
                "median_weighted_bases": fmt(
                    median_value(numeric_values(rows, "weighted_bases"))
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
