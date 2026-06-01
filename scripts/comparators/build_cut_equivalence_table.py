#!/usr/bin/env python3
"""Build manuscript-facing interval-comparator equivalence tables.

This table deliberately includes only normalized interval comparators. Count-only
and binned comparators are represented in the comparator semantics and case
matrix tables because they support different claims.
"""

from __future__ import annotations

import argparse
import csv
import sys
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
TRUE_VALUES = {"1", "true", "yes", "y"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return [
            {
                key: "" if value is None else value
                for key, value in row.items()
                if key is not None
            }
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]


def index_rows(
    rows: list[dict[str, str]], key: str, source: Path
) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        value = row.get(key, "")
        if not value:
            raise ValueError(f"{source}: row has empty {key}")
        if value in out:
            raise ValueError(f"{source}: duplicate {key}={value}")
        out[value] = row
    return out


def is_true(value: str) -> bool:
    return value.strip().lower() in TRUE_VALUES


def summary_path(case: dict[str, str]) -> Path:
    tool_id = case["tool_id"]
    case_id = case["case_id"]
    if tool_id == "digital_rads":
        return Path(f"results/comparators/digital_rads/{case_id}.summary.tsv")
    if tool_id == "ddradseqtools":
        return Path(
            f"results/comparators/ddradseqtools/"
            f"{case_id}.interval_compare.summary.tsv"
        )
    raise ValueError(f"unsupported interval comparator tool_id={tool_id!r}")


def interval_row(
    *,
    case: dict[str, str],
    registry: dict[str, dict[str, str]],
) -> dict[str, str]:
    tool_id = case["tool_id"]
    if tool_id not in registry:
        raise ValueError(f"unknown comparator tool_id={tool_id!r}")
    tool = registry[tool_id]
    source = summary_path(case)
    rows = read_rows(source) if source.exists() else []
    dataset_condition = f"{case['dataset_id']} {case['condition_id']}"
    notes = case.get("notes", "")

    if not rows:
        return {
            "tool": tool["display_name"],
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
            "notes": f"Missing comparator summary. {notes}".strip(),
        }

    row = rows[0]
    return {
        "tool": tool["display_name"],
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
        "--cases",
        "--comparator-cases",
        type=Path,
        default=Path("config/comparator_cases.tsv"),
    )
    parser.add_argument(
        "--comparators", type=Path, default=Path("config/comparators.tsv")
    )
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
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args(argv)

    try:
        registry = index_rows(read_rows(args.comparators), "tool_id", args.comparators)
        cases = [
            row
            for row in read_rows(args.cases)
            if is_true(row.get("required_for_nonempirical", ""))
        ]
        rows = [interval_row(case=case, registry=registry) for case in cases]
        write_rows(args.out, rows)
        write_rows(args.manuscript_table, rows)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    failures = [row for row in rows if row.get("status") != "PASS"]
    if failures:
        message = ", ".join(
            f"{row['tool']} {row['dataset_condition']}={row.get('status', '')}"
            for row in failures
        )
        if args.require_pass:
            print(
                f"error: interval comparator rows are not PASS: {message}",
                file=sys.stderr,
            )
            return 1
        print(
            f"warning: one or more interval comparator rows are not PASS: {message}",
            file=sys.stderr,
        )

    print(f"wrote {args.out}")
    print(f"wrote {args.manuscript_table}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
