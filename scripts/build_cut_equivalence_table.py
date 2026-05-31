#!/usr/bin/env python3
"""Build a unified cut/digest equivalence table.

This table separates exact interval equivalence from binned digest-distribution
equivalence.

Digital_RADs.py and DDRADSEQTOOLS are exact normalized interval comparisons.
ddgRADer is a binned fragment-distribution comparison because its backend
performs digestion but does not expose native genomic intervals.
"""

from __future__ import annotations

import csv
from pathlib import Path

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


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [
            {key: "" if value is None else value for key, value in row.items()}
            for row in reader
        ]


def interval_row(
    *,
    tool: str,
    dataset_condition: str,
    source: Path,
    notes: str,
) -> dict[str, str] | None:
    rows = read_rows(source)
    if not rows:
        return None

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


def ddgrader_row(summary: Path, detail: Path) -> dict[str, str] | None:
    rows = read_rows(summary)
    if not rows:
        return None

    row = rows[0]
    detail_rows = read_rows(detail)
    matching_bins = ""

    if detail_rows:
        matching_bins = str(
            sum(
                1
                for drow in detail_rows
                if drow.get("difference_second_minus_first", "") in {"0", "0.0"}
            )
        )

    diff = row.get("difference_second_minus_first", "")

    return {
        "tool": "ddgRADer backend",
        "dataset_condition": "yeast_small_plain B1 EcoRI+MseI",
        "comparison_scope": "cut/digest equivalence",
        "output_resolution": "10-bp binned fragment distribution",
        "radigest_units": row.get("first_total", ""),
        "tool_units": row.get("second_total", ""),
        "matching_units": matching_bins or row.get("bins_compared", ""),
        "agreement_metric": "total_binned_count_difference",
        "metric_value": diff,
        "status": row.get("status", ""),
        "source": str(summary),
        "notes": (
            "ddgRADer backend performs digestion and reports binned fragment "
            "distributions; compare binned output, not genomic coordinates."
        ),
    }


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    rows: list[dict[str, str]] = []

    digital = interval_row(
        tool="Digital_RADs.py",
        dataset_condition="synthetic/smoke",
        source=Path(
            "results/processed/comparisons/digital_rads/"
            "digital_rads_smoke_single__D1.summary.tsv"
        ),
        notes=(
            "Digital_RADs.py motif-bounded output normalized to cut-to-cut "
            "intervals."
        ),
    )
    if digital:
        rows.append(digital)

    ddradseqtools = interval_row(
        tool="DDRADSEQTOOLS rsitesearch.py",
        dataset_condition="yeast_small_plain B1",
        source=Path(
            "results/processed/comparisons/ddradseqtools/"
            "yeast_B1.interval_compare.summary.tsv"
        ),
        notes=(
            "rsitesearch.py FASTA header coordinates normalized with enzyme "
            "cut offsets and first-token sequence identifiers."
        ),
    )
    if ddradseqtools:
        rows.append(ddradseqtools)

    ddgrader = ddgrader_row(
        summary=Path(
            "results/processed/comparisons/ddgrader/"
            "yeast_B1.binned.summary.tsv"
        ),
        detail=Path(
            "results/processed/comparisons/ddgrader/"
            "yeast_B1.binned.detail.tsv"
        ),
    )
    if ddgrader:
        rows.append(ddgrader)

    write_rows(Path("results/tables/cut_equivalence_summary.tsv"), rows)
    write_rows(Path("manuscript_tables/table_03_interval_comparisons.tsv"), rows)

    print("wrote results/tables/cut_equivalence_summary.tsv")
    print("wrote manuscript_tables/table_03_interval_comparisons.tsv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
