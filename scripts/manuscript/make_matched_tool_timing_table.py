#!/usr/bin/env python3
"""Build manuscript-facing matched-tool timing table."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import NoReturn

TABLE_COLUMNS = [
    "dataset_id",
    "condition_id",
    "tool_id",
    "tool",
    "comparison_level",
    "primary_output_type",
    "allowed_claim",
    "timing_scope",
    "runs",
    "primary_count",
    "primary_count_consistency",
    "median_wall_seconds",
    "relative_to_radigest_median",
    "status",
    "interpretation",
]

REQUIRED_COLUMNS = [
    "dataset_id",
    "condition_id",
    "tool_id",
    "tool",
    "comparison_level",
    "primary_output_type",
    "allowed_claim",
    "timing_scope",
    "configured_runs",
    "successful_runs",
    "primary_count",
    "primary_count_consistency",
    "wall_seconds_median",
    "relative_to_radigest_median",
    "status",
    "interpretation",
]


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames
        if fieldnames is None:
            fail(f"{path}: missing header")
        missing = [
            column for column in REQUIRED_COLUMNS if column not in set(fieldnames)
        ]
        if missing:
            fail(f"{path}: missing columns: {', '.join(missing)}")
        rows: list[dict[str, str]] = []
        for raw_row in reader:
            if not any((value or "").strip() for value in raw_row.values()):
                continue
            row: dict[str, str] = {}
            for key, value in raw_row.items():
                if key is not None:
                    row[key] = "" if value is None else value
            rows.append(row)
    if not rows:
        fail(f"{path}: no data rows")
    return rows


def table_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "dataset_id": row["dataset_id"],
        "condition_id": row["condition_id"],
        "tool_id": row["tool_id"],
        "tool": row["tool"],
        "comparison_level": row["comparison_level"],
        "primary_output_type": row["primary_output_type"],
        "allowed_claim": row["allowed_claim"],
        "timing_scope": row["timing_scope"],
        "runs": f"{row['successful_runs']}/{row['configured_runs']}",
        "primary_count": row["primary_count"],
        "primary_count_consistency": row["primary_count_consistency"],
        "median_wall_seconds": row["wall_seconds_median"],
        "relative_to_radigest_median": row["relative_to_radigest_median"],
        "status": row["status"],
        "interpretation": row["interpretation"],
    }


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=TABLE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interpretation", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = [table_row(row) for row in read_tsv(args.interpretation)]
    write_rows(args.out, rows)
    failed = [row for row in rows if row["status"] != "PASS"]
    if args.require_pass and failed:
        print(
            f"{len(failed)} of {len(rows)} matched-tool timing table rows failed; "
            f"see {args.out}",
            file=sys.stderr,
        )
        return 1
    print(f"Wrote {len(rows)} matched-tool timing table rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
