#!/usr/bin/env python3
"""Fail if the claim audit or release checklist contains blocking failures."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import NoReturn

CLAIM_AUDIT_COLUMNS = [
    "claim_id",
    "required_for_release",
    "release_status",
    "blocking_reason",
]
RELEASE_CHECKLIST_COLUMNS = ["check_id", "status", "blocking", "notes"]


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_tsv(path: Path, required_columns: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames
        if fieldnames is None:
            fail(f"{path}: missing header")
        fieldname_set = set(fieldnames)
        missing = [column for column in required_columns if column not in fieldname_set]
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
    parser.add_argument("--claim-audit", required=True, type=Path)
    parser.add_argument("--release-checklist", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    claim_rows = read_tsv(args.claim_audit, CLAIM_AUDIT_COLUMNS)
    claim_failures = [row for row in claim_rows if row["release_status"] == "FAIL"]

    checklist_failures: list[dict[str, str]] = []
    if args.release_checklist is not None:
        checklist_rows = read_tsv(args.release_checklist, RELEASE_CHECKLIST_COLUMNS)
        checklist_failures = [
            row
            for row in checklist_rows
            if row["status"] == "FAIL" and row["blocking"].lower() == "true"
        ]

    if claim_failures or checklist_failures:
        for row in claim_failures:
            reason = row.get("blocking_reason", "") or "release artifact failed"
            print(f"{row['claim_id']} FAIL: {reason}", file=sys.stderr)
        for row in checklist_failures:
            notes = row.get("notes", "") or "release checklist failure"
            print(f"{row['check_id']} FAIL: {notes}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("PASS\n", encoding="utf-8")
    print(f"Audit release gate passed; wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
