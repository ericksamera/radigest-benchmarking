#!/usr/bin/env python3
"""Compare radigest aggregate fragment counts with SimRAD count-level output.

This comparison is intentionally limited to aggregate retained-fragment counts
and retained bases. It does not compare coordinates or fragment interval sets.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

FIELDNAMES = [
    "dataset",
    "condition",
    "metric",
    "radigest_value",
    "simrad_value",
    "difference_simrad_minus_radigest",
    "relative_difference_vs_radigest",
    "status",
    "claim_boundary",
    "radigest_json",
    "radigest_fragments",
    "simrad_tsv",
    "notes",
]
TRUE_VALUES = {"1", "true", "yes", "y"}


def read_one_row(path: Path, tool_label: str) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = [
            {
                key: "" if value is None else value
                for key, value in row.items()
                if key is not None
            }
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]
    if len(rows) != 1:
        raise ValueError(
            f"{path}: expected exactly one {tool_label} row, found {len(rows)}"
        )
    return rows[0]


def read_radigest_fragments(path: Path) -> tuple[int, int]:
    count = 0
    bases = 0
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        if "length" not in reader.fieldnames:
            raise ValueError(f"{path}: missing length column")
        for row in reader:
            kept = row.get("hard_kept", row.get("hard_kept?", ""))
            if kept and kept.strip().lower() not in TRUE_VALUES:
                continue
            length = int(float(row["length"]))
            count += 1
            bases += length
    return count, bases


def read_json_dict(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def to_float(value: object) -> float:
    if value is None:
        return 0.0
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0.0
        return float(text)
    return float(value)  # type: ignore[arg-type]


def fmt(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.10g}"


def row(
    dataset: str,
    condition: str,
    metric: str,
    radigest_value: float,
    simrad_value: float,
    radigest_json: Path | None,
    radigest_fragments: Path,
    simrad_tsv: Path,
    notes: str,
) -> dict[str, str]:
    diff = simrad_value - radigest_value
    if radigest_value == 0:
        rel = "" if simrad_value == 0 else "inf"
    else:
        rel = f"{diff / radigest_value:.8f}"
    return {
        "dataset": dataset,
        "condition": condition,
        "metric": metric,
        "radigest_value": fmt(radigest_value),
        "simrad_value": fmt(simrad_value),
        "difference_simrad_minus_radigest": fmt(diff),
        "relative_difference_vs_radigest": rel,
        "status": "PASS" if abs(diff) < 1e-9 else "DIFFER",
        "claim_boundary": "count_level_digest_only_no_coordinate_equivalence",
        "radigest_json": "" if radigest_json is None else str(radigest_json),
        "radigest_fragments": str(radigest_fragments),
        "simrad_tsv": str(simrad_tsv),
        "notes": notes,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radigest-json", type=Path)
    parser.add_argument("--radigest-fragments", required=True, type=Path)
    parser.add_argument("--simrad-tsv", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--condition", required=True)
    parser.add_argument("--fail-on-difference", action="store_true")
    args = parser.parse_args(argv)

    try:
        if not args.radigest_fragments.exists():
            raise FileNotFoundError(
                f"missing radigest fragments TSV: {args.radigest_fragments}"
            )
        if not args.simrad_tsv.exists():
            raise FileNotFoundError(f"missing SimRAD TSV: {args.simrad_tsv}")
        radigest_count, radigest_bases = read_radigest_fragments(
            args.radigest_fragments
        )
        radigest_json = read_json_dict(args.radigest_json)
        if radigest_json:
            # JSON is retained for traceability. Fragment TSV remains source of
            # truth because it is stable across radigest JSON schema changes.
            radigest_count = radigest_count
        simrad = read_one_row(args.simrad_tsv, "SimRAD")
        notes = simrad.get("notes", "")
        rows = [
            row(
                args.dataset,
                args.condition,
                "fragments",
                float(radigest_count),
                to_float(simrad.get("size_selected_fragments")),
                args.radigest_json,
                args.radigest_fragments,
                args.simrad_tsv,
                notes,
            ),
            row(
                args.dataset,
                args.condition,
                "bases",
                float(radigest_bases),
                to_float(simrad.get("total_bases")),
                args.radigest_json,
                args.radigest_fragments,
                args.simrad_tsv,
                notes,
            ),
        ]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out}", file=sys.stderr)
    if args.fail_on_difference and any(r["status"] != "PASS" for r in rows):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
