#!/usr/bin/env python3
"""Fail if the release checklist contains blocking failures."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import NoReturn

REQUIRED_COLUMNS = ["check_id", "status", "blocking", "notes"]


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames
        if fieldnames is None:
            fail(f"{path}: missing header")
        fieldname_set = set(fieldnames)
        missing = [column for column in REQUIRED_COLUMNS if column not in fieldname_set]
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
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-checklist", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_tsv(args.release_checklist)
    failures = [
        row
        for row in rows
        if row["status"] == "FAIL" and row["blocking"].lower() == "true"
    ]
    if failures:
        for row in failures:
            notes = row.get("notes", "") or "release checklist failure"
            print(f"{row['check_id']} FAIL: {notes}", file=sys.stderr)
        return 1
    print(f"Release checklist passed: {args.release_checklist}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
