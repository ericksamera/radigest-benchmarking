#!/usr/bin/env python3
"""Build manuscript-facing interval-comparator equivalence tables.

This Stage 4 table deliberately includes only exact normalized interval
comparisons. Count-only and binned comparators are added in later performance
stages because they support different claims.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import TypedDict

FIELDS = [
    "tool",
    "dataset_condition",
    "comparison_scope",
    "output_resolution",
    "radigest_units",
    "tool_units",
    "matching_units",
    "agreement_metric",
    "metric_value",
    "status",
    "source",
    "notes",
]


class SourceSpec(TypedDict):
    tool: str
    dataset_condition: str
    source: Path
    notes: str


SOURCES: list[SourceSpec] = [
    {
        "tool": "Digital_RADs.py",
        "dataset_condition": "digital_rads_smoke_single D1",
        "source": Path(
            "results/comparators/digital_rads/"
            "digital_rads_smoke_single__D1.summary.tsv"
        ),
        "notes": (
            "Digital_RADs.py motif-bounded output normalized to cut-to-cut "
            "zero-based half-open intervals."
        ),
    },
    {
        "tool": "DDRADSEQTOOLS rsitesearch.py",
        "dataset_condition": "small_yeast_s288c B1",
        "source": Path(
            "results/comparators/ddradseqtools/"
            "small_yeast_s288c_B1.interval_compare.summary.tsv"
        ),
        "notes": (
            "rsitesearch.py FASTA header coordinates normalized with enzyme cut "
            "offsets and first-token sequence identifiers."
        ),
    },
]


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            return []
        return [
            {key: "" if value is None else value for key, value in row.items()}
            for row in reader
        ]


def interval_row(
    *, tool: str, dataset_condition: str, source: Path, notes: str
) -> dict[str, str]:
    rows = read_rows(source)
    if not rows:
        return {
            "tool": tool,
            "dataset_condition": dataset_condition,
            "comparison_scope": "cut/digest equivalence",
            "output_resolution": "exact normalized interval set",
            "radigest_units": "",
            "tool_units": "",
            "matching_units": "",
            "agreement_metric": "jaccard",
            "metric_value": "",
            "status": "MISSING",
            "source": str(source),
            "notes": f"Missing comparator summary. {notes}",
        }

    row = rows[0]
    return {
        "tool": tool,
        "dataset_condition": dataset_condition,
        "comparison_scope": "cut/digest equivalence",
        "output_resolution": "exact normalized interval set",
        "radigest_units": row.get("first_intervals", ""),
        "tool_units": row.get("second_intervals", ""),
        "matching_units": row.get("matching_intervals", ""),
        "agreement_metric": "jaccard",
        "metric_value": row.get("jaccard", ""),
        "status": row.get("status", ""),
        "source": str(source),
        "notes": notes,
    }


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("results/comparators/cut_equivalence_summary.tsv"),
    )
    parser.add_argument(
        "--manuscript-table",
        type=Path,
        default=Path("results/manuscript/tables/table_03_interval_comparisons.tsv"),
    )
    args = parser.parse_args(argv)

    rows = [interval_row(**source) for source in SOURCES]
    write_rows(args.out, rows)
    write_rows(args.manuscript_table, rows)

    failures = [row for row in rows if row.get("status") != "PASS"]
    if failures:
        print(
            "warning: one or more interval comparator rows are not PASS: "
            + ", ".join(f"{row['tool']}={row.get('status', '')}" for row in failures),
            file=sys.stderr,
        )
    print(f"wrote {args.out}")
    print(f"wrote {args.manuscript_table}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
