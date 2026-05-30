#!/usr/bin/env python3
"""Summarize DDRADSEQTOOLS interval timing and append to tool timing table."""

from __future__ import annotations

import argparse
import csv
import glob
import re
import statistics
import sys
from pathlib import Path

INTERPRETATION_FIELDS = [
    "dataset",
    "condition",
    "tool",
    "task",
    "timing_scope",
    "output_object",
    "n_runs",
    "median_elapsed_wall_seconds",
    "q1_elapsed_wall_seconds",
    "q3_elapsed_wall_seconds",
    "iqr_elapsed_wall_seconds",
    "median_max_rss_kb",
    "process_max_rss_kb",
    "median_fragments",
    "median_bases",
    "notes",
    "source",
]

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


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            return []
        return [
            {
                key: "" if value is None else value
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]


def write_rows(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_normalization_summary(path: Path | None) -> tuple[str, str]:
    if path is None or not path.exists():
        return "", ""

    rows = read_rows(path)
    if not rows:
        return "", ""

    row = rows[0]
    return row.get("filtered_records", ""), row.get("total_cut_bases", "")


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
                "task": "rsitesearch_interval",
                "replicate": replicate,
                "elapsed_wall_seconds": timing.get("elapsed_wall_seconds", ""),
                "user_seconds": timing.get("user_seconds", ""),
                "system_seconds": timing.get("system_seconds", ""),
                "percent_cpu": timing.get("percent_cpu", ""),
                "max_rss_kb": timing.get("max_rss_kb", ""),
                "exit_status": timing.get("exit_status", ""),
                "time_file": str(path),
            }
        )

    return rows


def build_summary_row(
    run_rows: list[dict[str, str]],
    fragments: str,
    bases: str,
) -> dict[str, str]:
    elapsed_values = [
        x
        for x in (to_float(row.get("elapsed_wall_seconds", "")) for row in run_rows)
        if x is not None
    ]
    rss_values = [
        x
        for x in (to_float(row.get("max_rss_kb", "")) for row in run_rows)
        if x is not None
    ]

    elapsed = stat_bundle(elapsed_values)
    rss = stat_bundle(rss_values)

    dataset = run_rows[0]["dataset"]
    condition = run_rows[0]["condition"]

    notes = (
        "DDRADSEQTOOLS timing includes Package/rsitesearch.py digest-level "
        "fragment generation plus coordinate normalization; broader "
        "read simulation, adapter, PCR, allele-dropout, and preprocessing "
        "workflows are excluded."
    )

    return {
        "dataset": dataset,
        "condition": condition,
        "tool": "DDRADSEQTOOLS",
        "task": "rsitesearch_interval",
        "n_runs": str(len(run_rows)),
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


def interpretation_row(summary: dict[str, str], source: Path) -> dict[str, str]:
    return {
        "dataset": summary["dataset"],
        "condition": summary["condition"],
        "tool": summary["tool"],
        "task": summary["task"],
        "timing_scope": "cold_command",
        "output_object": "normalized interval set",
        "n_runs": summary["n_runs"],
        "median_elapsed_wall_seconds": summary["median_elapsed_wall_seconds"],
        "q1_elapsed_wall_seconds": summary["q1_elapsed_wall_seconds"],
        "q3_elapsed_wall_seconds": summary["q3_elapsed_wall_seconds"],
        "iqr_elapsed_wall_seconds": summary["iqr_elapsed_wall_seconds"],
        "median_max_rss_kb": summary["median_max_rss_kb"],
        "process_max_rss_kb": "",
        "median_fragments": summary["median_fragments"],
        "median_bases": summary["median_bases"],
        "notes": summary["notes"],
        "source": str(source),
    }


def append_or_replace(
    existing_rows: list[dict[str, str]],
    new_row: dict[str, str],
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []

    for row in existing_rows:
        same = (
            row.get("dataset") == new_row["dataset"]
            and row.get("condition") == new_row["condition"]
            and row.get("tool") == new_row["tool"]
            and row.get("task") == new_row["task"]
        )
        if not same:
            out.append(row)

    out.append(new_row)
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--time-glob", required=True)
    parser.add_argument("--dataset", default="yeast_small_plain")
    parser.add_argument("--condition", default="B1")
    parser.add_argument(
        "--normalize-summary",
        type=Path,
        default=None,
        help=(
            "A representative normalize_summary.tsv with filtered_records "
            "and total_cut_bases."
        ),
    )
    parser.add_argument(
        "--timing-table",
        type=Path,
        default=Path("results/tables/tool_timing_interpretation.tsv"),
    )
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
    parser.add_argument(
        "--out-timing-table",
        type=Path,
        default=Path("results/tables/tool_timing_interpretation.tsv"),
    )
    args = parser.parse_args(argv)

    try:
        fragments, bases = read_normalization_summary(args.normalize_summary)
        run_rows = build_run_rows(args.time_glob, args.dataset, args.condition)
        summary_row = build_summary_row(run_rows, fragments, bases)

        write_rows(args.out_runs, run_rows, RUN_FIELDS)
        write_rows(args.out_summary, [summary_row], SUMMARY_FIELDS)

        existing = read_rows(args.timing_table)
        appended = append_or_replace(
            existing,
            interpretation_row(summary_row, args.out_summary),
        )
        write_rows(args.out_timing_table, appended, INTERPRETATION_FIELDS)

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out_runs}", file=sys.stderr)
    print(f"wrote {args.out_summary}", file=sys.stderr)
    print(f"wrote {args.out_timing_table}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
