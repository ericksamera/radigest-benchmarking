#!/usr/bin/env python3
"""Export the manuscript-facing synthetic validation table."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

TABLE_COLUMNS = [
    "case_id",
    "record_id",
    "enzymes",
    "min",
    "max",
    "options",
    "expected",
    "observed",
    "status",
    "command",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames
        if fieldnames is None:
            raise ValueError(f"{path}: missing header")
        fieldname_set = set(fieldnames)
        missing = [column for column in TABLE_COLUMNS if column not in fieldname_set]
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(missing)}")
        rows: list[dict[str, str]] = []
        for row in reader:
            if not any((value or "").strip() for value in row.values()):
                continue
            clean_row: dict[str, str] = {}
            for column in TABLE_COLUMNS:
                value = row.get(column)
                clean_row[column] = "" if value is None else value
            rows.append(clean_row)
        return rows


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=TABLE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--require-pass",
        action="store_true",
        help="Fail if any synthetic validation row is not PASS.",
    )
    args = parser.parse_args(argv)

    try:
        rows = read_rows(args.input)
        if not rows:
            raise ValueError(f"{args.input}: no validation rows")
        if args.require_pass:
            failed = [row["case_id"] for row in rows if row.get("status") != "PASS"]
            if failed:
                raise ValueError(
                    "synthetic validation has failing rows: " + ", ".join(failed)
                )
        write_rows(args.out, rows)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
