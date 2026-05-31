#!/usr/bin/env python3
"""Compare radigest JSON summary with DDRADSEQTOOLS rsitesearch summary."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

FIELDS = [
    "dataset",
    "condition",
    "metric",
    "radigest_value",
    "ddradseqtools_value",
    "difference_ddradseqtools_minus_radigest",
    "relative_difference_vs_radigest",
    "status",
    "radigest_json",
    "ddradseqtools_summary",
    "notes",
]


def read_ddrad_summary(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    if len(rows) != 1:
        raise ValueError(f"{path}: expected one row, found {len(rows)}")

    return {
        key: "" if value is None else value
        for key, value in rows[0].items()
        if key is not None
    }


def read_radigest_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        obj = json.load(handle)

    if not isinstance(obj, dict):
        raise ValueError(f"{path}: expected JSON object")

    return obj


def numeric_text(value) -> str:
    if value is None or value == "":
        return ""
    try:
        f = float(value)
    except Exception:
        return ""
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return f"{f:.6f}"


def comparison_row(
    dataset: str,
    condition: str,
    metric: str,
    radigest_value,
    ddrad_value,
    radigest_json: Path,
    ddrad_summary: Path,
    notes: str,
) -> dict[str, str]:
    r_text = numeric_text(radigest_value)
    d_text = numeric_text(ddrad_value)

    if r_text == "" or d_text == "":
        diff_text = ""
        rel_text = ""
        status = "UNPARSEABLE"
    else:
        r = float(r_text)
        d = float(d_text)
        diff = d - r
        diff_text = numeric_text(diff)
        rel_text = "" if r == 0 else f"{diff / r:.8f}"
        status = "PASS" if abs(diff) < 1e-9 else "DIFFER"

    return {
        "dataset": dataset,
        "condition": condition,
        "metric": metric,
        "radigest_value": r_text,
        "ddradseqtools_value": d_text,
        "difference_ddradseqtools_minus_radigest": diff_text,
        "relative_difference_vs_radigest": rel_text,
        "status": status,
        "radigest_json": str(radigest_json),
        "ddradseqtools_summary": str(ddrad_summary),
        "notes": notes,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radigest-json", required=True, type=Path)
    parser.add_argument("--ddrad-summary", required=True, type=Path)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--condition", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        radigest = read_radigest_json(args.radigest_json)
        ddrad = read_ddrad_summary(args.ddrad_summary)

        notes = (
            "DDRADSEQTOOLS rsitesearch.py reports fragment FASTA records. "
            "Count/base differences may reflect output-definition, size-selection, "
            "or boundary-semantics differences."
        )

        rows = [
            comparison_row(
                dataset=args.dataset,
                condition=args.condition,
                metric="fragments",
                radigest_value=radigest.get("total_fragments"),
                ddrad_value=ddrad.get("fragments"),
                radigest_json=args.radigest_json,
                ddrad_summary=args.ddrad_summary,
                notes=notes,
            ),
            comparison_row(
                dataset=args.dataset,
                condition=args.condition,
                metric="bases",
                radigest_value=radigest.get("total_bases"),
                ddrad_value=ddrad.get("total_bases"),
                radigest_json=args.radigest_json,
                ddrad_summary=args.ddrad_summary,
                notes=notes,
            ),
        ]

        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
