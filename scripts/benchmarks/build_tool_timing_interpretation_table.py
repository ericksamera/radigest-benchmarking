#!/usr/bin/env python3
"""Build an interpretation table for matched-tool timing results.

This table intentionally separates timing scopes:

- cold_command:
    executable/script starts from the shell for each replicate.

- warm_package_reload_reference:
    SimRAD and R dependencies are loaded once; each timed run reloads the
    reference and performs digest/adapt/size-selection.

- warm_package_reuse_reference:
    SimRAD and the reference are loaded once; each timed run performs only
    digest/adapt/size-selection.

Do not treat these timing scopes as identical.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

FIELDNAMES = [
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

GNU_TIME_PATTERNS = {
    "process_max_rss_kb": re.compile(r"Maximum resident set size \(kbytes\): (.+)"),
    "process_elapsed": re.compile(r"Elapsed \(wall clock\) time.*: (.+)"),
    "process_exit_status": re.compile(r"Exit status: (.+)"),
}


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            return []
        rows: list[dict[str, str]] = []
        for raw_row in reader:
            row = {
                key: "" if value is None else value
                for key, value in raw_row.items()
                if key is not None
            }
            rows.append(row)
    return rows


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def parse_gnu_time(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {
            "process_max_rss_kb": "",
            "process_elapsed": "",
            "process_exit_status": "",
        }

    text = path.read_text(errors="replace")
    out: dict[str, str] = {}

    for key, pattern in GNU_TIME_PATTERNS.items():
        match = pattern.search(text)
        out[key] = match.group(1).strip() if match else ""

    return out


def matched_rows(path: Path) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []

    for row in read_rows(path):
        task = row.get("task", "")
        tool = row.get("tool", "")
        notes = row.get("notes", "")

        if row.get("exit_status", "0") not in {"", "0"}:
            notes = f"{notes}; failed row excluded from interpretation".strip("; ")
            continue

        if "metric_parse_error" in notes:
            continue

        out.append(
            {
                "dataset": row.get("dataset", ""),
                "condition": row.get("condition", ""),
                "tool": tool,
                "task": task,
                "timing_scope": "cold_command",
                "output_object": row.get("output_object", ""),
                "n_runs": row.get("n_runs", ""),
                "median_elapsed_wall_seconds": row.get(
                    "median_elapsed_wall_seconds", ""
                ),
                "q1_elapsed_wall_seconds": row.get("q1_elapsed_wall_seconds", ""),
                "q3_elapsed_wall_seconds": row.get("q3_elapsed_wall_seconds", ""),
                "iqr_elapsed_wall_seconds": row.get("iqr_elapsed_wall_seconds", ""),
                "median_max_rss_kb": row.get("median_max_rss_kb", ""),
                "process_max_rss_kb": "",
                "median_fragments": row.get("median_fragments", ""),
                "median_bases": row.get("median_bases", ""),
                "notes": notes,
                "source": str(path),
            }
        )

    return out


def simrad_warm_rows(
    path: Path,
    time_path: Path | None,
    dataset: str,
    condition: str,
) -> list[dict[str, str]]:
    rows = read_rows(path)
    if not rows:
        return []

    time_values = parse_gnu_time(time_path)
    out: list[dict[str, str]] = []

    for row in rows:
        benchmark_mode = row.get("benchmark_mode", "")
        if benchmark_mode == "reuse_reference":
            timing_scope = "warm_package_reuse_reference"
            task = "simrad_warm_reuse_reference"
        else:
            timing_scope = "warm_package_reload_reference"
            task = "simrad_warm_reload_reference"

        notes = row.get("notes", "")
        if time_values.get("process_max_rss_kb", ""):
            notes = (
                notes
                + "; process_max_rss_kb is peak RSS for the whole warm R session, "
                "not a per-run median"
            )

        out.append(
            {
                "dataset": dataset,
                "condition": condition,
                "tool": row.get("tool", "SimRAD"),
                "task": task,
                "timing_scope": timing_scope,
                "output_object": "aggregate count",
                "n_runs": row.get("runs", ""),
                "median_elapsed_wall_seconds": row.get("median_elapsed_seconds", ""),
                "q1_elapsed_wall_seconds": row.get("q1_elapsed_seconds", ""),
                "q3_elapsed_wall_seconds": row.get("q3_elapsed_seconds", ""),
                "iqr_elapsed_wall_seconds": row.get("iqr_elapsed_seconds", ""),
                "median_max_rss_kb": "",
                "process_max_rss_kb": time_values.get("process_max_rss_kb", ""),
                "median_fragments": row.get("median_size_selected_fragments", ""),
                "median_bases": row.get("median_total_bases", ""),
                "notes": notes,
                "source": str(path),
            }
        )

    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--matched-summary",
        type=Path,
        default=Path("results/tables/matched_tool_benchmark_summary.tsv"),
    )
    parser.add_argument(
        "--simrad-warm-summary",
        type=Path,
        default=Path("results/tables/simrad_warm_summary.tsv"),
    )
    parser.add_argument(
        "--simrad-warm-time",
        type=Path,
        default=Path(
            "benchmark/memory/matched_tools/simrad_warm_package_reload_reference.time"
        ),
    )
    parser.add_argument(
        "--simrad-reuse-summary",
        type=Path,
        default=Path("results/tables/simrad_reuse_reference_summary.tsv"),
    )
    parser.add_argument(
        "--simrad-reuse-time",
        type=Path,
        default=Path("benchmark/memory/matched_tools/simrad_reuse_reference.time"),
    )
    parser.add_argument("--dataset", default="yeast_small")
    parser.add_argument("--condition", default="B1")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("results/tables/tool_timing_interpretation.tsv"),
    )
    args = parser.parse_args(argv)

    rows: list[dict[str, str]] = []
    rows.extend(matched_rows(args.matched_summary))
    rows.extend(
        simrad_warm_rows(
            path=args.simrad_warm_summary,
            time_path=args.simrad_warm_time,
            dataset=args.dataset,
            condition=args.condition,
        )
    )
    rows.extend(
        simrad_warm_rows(
            path=args.simrad_reuse_summary,
            time_path=args.simrad_reuse_time,
            dataset=args.dataset,
            condition=args.condition,
        )
    )

    if not rows:
        print("error: no rows available for interpretation table", file=sys.stderr)
        return 2

    write_rows(args.out, rows)
    print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
