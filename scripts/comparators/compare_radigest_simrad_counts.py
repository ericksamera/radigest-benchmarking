#!/usr/bin/env python3
"""Compare radigest JSON counts with SimRAD count-level summary.

This script compares only shared aggregate digest-level quantities:
  - fragment count;
  - retained genomic bases.

It does not compare coordinates, read simulation, PCR/adapters, SNPs,
population simulation, or downstream loci/genotypes.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, cast

FIELDNAMES = [
    "dataset",
    "condition",
    "metric",
    "radigest_value",
    "simrad_value",
    "difference_simrad_minus_radigest",
    "relative_difference_vs_radigest",
    "status",
    "radigest_json",
    "simrad_tsv",
    "notes",
]

NumericValue = str | int | float | None


def load_json_dict(path: Path) -> dict[str, Any]:
    """Load a JSON document and require a top-level object."""
    with path.open(encoding="utf-8") as handle:
        data: Any = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected top-level JSON object")

    return cast(dict[str, Any], data)


def read_simrad_row(path: Path) -> dict[str, str]:
    """Read a one-row SimRAD TSV summary."""
    rows: list[dict[str, str]] = []

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for raw_row in reader:
            row = {
                key: "" if value is None else value
                for key, value in raw_row.items()
                if key is not None
            }
            rows.append(row)

    if len(rows) != 1:
        raise ValueError(f"{path}: expected exactly one SimRAD row, found {len(rows)}")

    return rows[0]


def to_float(value: NumericValue) -> float:
    """Convert numeric or numeric-string values to float.

    Missing values are treated as 0.0 because absent count fields represent
    unavailable zero-valued metrics in the current comparison summaries.
    """
    if value is None:
        return 0.0

    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return 0.0
        return float(stripped)

    return float(value)


def format_number(value: float) -> str:
    """Format integer-like floats without a decimal point."""
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.10g}"


def comparison_row(
    dataset: str,
    condition: str,
    metric: str,
    radigest_value: float,
    simrad_value: float,
    radigest_json: Path,
    simrad_tsv: Path,
    notes: str,
) -> dict[str, str]:
    diff = simrad_value - radigest_value

    if radigest_value == 0:
        rel = "" if simrad_value == 0 else "inf"
    else:
        rel = f"{diff / radigest_value:.8f}"

    status = "PASS" if abs(diff) < 1e-9 else "DIFFER"

    return {
        "dataset": dataset,
        "condition": condition,
        "metric": metric,
        "radigest_value": format_number(radigest_value),
        "simrad_value": format_number(simrad_value),
        "difference_simrad_minus_radigest": format_number(diff),
        "relative_difference_vs_radigest": rel,
        "status": status,
        "radigest_json": str(radigest_json),
        "simrad_tsv": str(simrad_tsv),
        "notes": notes,
    }


def infer_dataset_condition(path: Path) -> tuple[str, str]:
    """Infer dataset and condition from <dataset>__<condition> filenames."""
    stem = path.stem
    parts = stem.split("__")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return "", ""


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Compare radigest JSON counts to SimRAD count-level TSV output."
    )
    parser.add_argument("--radigest-json", required=True, type=Path)
    parser.add_argument("--simrad-tsv", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--dataset", default="")
    parser.add_argument("--condition", default="")
    args = parser.parse_args(argv)

    if not args.radigest_json.exists():
        print(f"error: missing radigest JSON: {args.radigest_json}", file=sys.stderr)
        return 2

    if not args.simrad_tsv.exists():
        print(f"error: missing SimRAD TSV: {args.simrad_tsv}", file=sys.stderr)
        return 2

    try:
        radigest = load_json_dict(args.radigest_json)
        simrad = read_simrad_row(args.simrad_tsv)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    dataset = args.dataset
    condition = args.condition
    if not dataset or not condition:
        inferred_dataset, inferred_condition = infer_dataset_condition(
            args.radigest_json
        )
        dataset = dataset or inferred_dataset
        condition = condition or inferred_condition

    notes = simrad.get("notes", "")

    rows = [
        comparison_row(
            dataset=dataset,
            condition=condition,
            metric="fragments",
            radigest_value=to_float(radigest.get("total_fragments", 0)),
            simrad_value=to_float(simrad.get("size_selected_fragments", 0)),
            radigest_json=args.radigest_json,
            simrad_tsv=args.simrad_tsv,
            notes=notes,
        ),
        comparison_row(
            dataset=dataset,
            condition=condition,
            metric="bases",
            radigest_value=to_float(radigest.get("total_bases", 0)),
            simrad_value=to_float(simrad.get("total_bases", 0)),
            radigest_json=args.radigest_json,
            simrad_tsv=args.simrad_tsv,
            notes=notes,
        ),
    ]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
