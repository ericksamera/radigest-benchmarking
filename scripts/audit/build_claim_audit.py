#!/usr/bin/env python3
"""Build claim-audit rows from artifact status output."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import NoReturn

OUTPUT_COLUMNS = [
    "claim_id",
    "category",
    "required_for_release",
    "producer_rule",
    "required_output",
    "manuscript_artifact",
    "claim_boundary",
    "artifact_status",
    "release_status",
    "blocking_reason",
]
STATUS_COLUMNS = [
    "claim_id",
    "category",
    "required_output",
    "manuscript_artifact",
    "producer_rule",
    "required_for_release",
    "status",
    "notes",
]


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


def claim_boundary(row: dict[str, str]) -> str:
    category = row["category"]
    notes = row.get("notes", "")
    if category == "validation":
        return "Synthetic validation evidence generated from tracked synthetic FASTA cases."
    if category == "comparators":
        if "does not support coordinate" in notes:
            return "Lower-resolution comparator claim; not coordinate-equivalence evidence."
        return "Comparator claim with semantics defined by comparator registry and manuscript semantics table."
    if category == "performance":
        return "Performance timing or throughput claim; no empirical recovery or cross-tool equivalence claim unless explicitly stated."
    if category == "empirical":
        return "Optional empirical recovery claim; not required for nonempirical release while required_for_release=false."
    return "Claim boundary is declared by config/artifacts.tsv notes."


def release_status(row: dict[str, str]) -> tuple[str, str]:
    artifact_status = row["status"]
    required = row["required_for_release"].lower() == "true"
    notes = row.get("notes", "")
    if artifact_status == "PASS":
        return "PASS", ""
    if artifact_status == "WARN" and not required:
        return "WARN", notes
    if required:
        return "FAIL", notes or "required release artifact is missing or empty"
    return "WARN", notes


def build_row(row: dict[str, str]) -> dict[str, str]:
    status, reason = release_status(row)
    return {
        "claim_id": row["claim_id"],
        "category": row["category"],
        "required_for_release": row["required_for_release"],
        "producer_rule": row["producer_rule"],
        "required_output": row["required_output"],
        "manuscript_artifact": row["manuscript_artifact"],
        "claim_boundary": claim_boundary(row),
        "artifact_status": row["status"],
        "release_status": status,
        "blocking_reason": reason,
    }


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-status", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_tsv(args.artifact_status, STATUS_COLUMNS)
    audit_rows = [build_row(row) for row in rows]
    write_tsv(args.out, audit_rows)
    print(f"Wrote {len(audit_rows)} claim-audit rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
