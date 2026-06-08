#!/usr/bin/env python3
"""Build a release output index from artifact-status rows."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn

STATUS_COLUMNS = [
    "claim_id",
    "category",
    "required_output",
    "manuscript_artifact",
    "producer_rule",
    "required_for_release",
    "output_exists",
    "output_bytes",
    "output_mtime_utc",
    "manuscript_artifact_exists",
    "manuscript_artifact_bytes",
    "manuscript_artifact_mtime_utc",
    "status",
    "notes",
]

OUTPUT_COLUMNS = [
    "path",
    "roles",
    "claim_ids",
    "categories",
    "producer_rules",
    "required_for_release",
    "exists",
    "bytes",
    "mtime_utc",
    "status",
    "notes",
]
TRUE_VALUES = {"true", "1", "yes", "y"}


@dataclass
class IndexedPath:
    path: str
    roles: set[str] = field(default_factory=set)
    claim_ids: set[str] = field(default_factory=set)
    categories: set[str] = field(default_factory=set)
    producer_rules: set[str] = field(default_factory=set)
    required_for_release: bool = False
    exists: str = "false"
    bytes: str = "0"
    mtime_utc: str = "NA"
    notes: list[str] = field(default_factory=list)


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
    if not rows:
        fail(f"{path}: no rows")
    return rows


def is_true(value: str) -> bool:
    return value.strip().lower() in TRUE_VALUES


def update_index(
    index: dict[str, IndexedPath],
    *,
    path: str,
    role: str,
    row: dict[str, str],
    exists: str,
    bytes_value: str,
    mtime: str,
) -> None:
    item = index.setdefault(path, IndexedPath(path=path))
    item.roles.add(role)
    item.claim_ids.add(row["claim_id"])
    item.categories.add(row["category"])
    item.producer_rules.add(row["producer_rule"])
    item.required_for_release = item.required_for_release or is_true(
        row["required_for_release"]
    )
    item.exists = exists
    item.bytes = bytes_value
    item.mtime_utc = mtime
    notes = row.get("notes", "")
    if notes and notes not in item.notes:
        item.notes.append(notes)


def status_for(item: IndexedPath) -> str:
    try:
        bytes_i = int(item.bytes)
    except ValueError:
        bytes_i = 0
    present = item.exists == "true" and bytes_i > 0
    if present:
        return "PASS"
    return "FAIL" if item.required_for_release else "WARN"


def build_index(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    index: dict[str, IndexedPath] = {}
    for row in rows:
        update_index(
            index,
            path=row["required_output"],
            role="required_output",
            row=row,
            exists=row["output_exists"],
            bytes_value=row["output_bytes"],
            mtime=row["output_mtime_utc"],
        )
        update_index(
            index,
            path=row["manuscript_artifact"],
            role="manuscript_artifact",
            row=row,
            exists=row["manuscript_artifact_exists"],
            bytes_value=row["manuscript_artifact_bytes"],
            mtime=row["manuscript_artifact_mtime_utc"],
        )

    output_rows: list[dict[str, str]] = []
    for path, item in sorted(index.items()):
        output_rows.append(
            {
                "path": path,
                "roles": ";".join(sorted(item.roles)),
                "claim_ids": ";".join(sorted(item.claim_ids)),
                "categories": ";".join(sorted(item.categories)),
                "producer_rules": ";".join(sorted(item.producer_rules)),
                "required_for_release": (
                    "true" if item.required_for_release else "false"
                ),
                "exists": item.exists,
                "bytes": item.bytes,
                "mtime_utc": item.mtime_utc,
                "status": status_for(item),
                "notes": " ".join(item.notes),
            }
        )
    return output_rows


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-status", required=True, type=Path)
    parser.add_argument("--claim-audit", type=Path)
    parser.add_argument("--environment", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--root", default=Path("."), type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    del args.root  # kept for CLI consistency with the other audit builders
    del args.claim_audit
    del args.environment
    output_rows = build_index(read_tsv(args.artifact_status, STATUS_COLUMNS))
    write_tsv(args.out, output_rows)
    print(f"Wrote {len(output_rows)} output-index rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
