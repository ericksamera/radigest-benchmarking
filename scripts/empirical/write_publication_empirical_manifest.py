#!/usr/bin/env python3
"""Write a local empirical manifest with one publication library enabled."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit(f"ERROR: {path}: missing header")
        rows = [
            {key: (value or "") for key, value in row.items() if key}
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]
    return list(reader.fieldnames), rows


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, delimiter="\t", fieldnames=fieldnames, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--library-id", required=True)
    parser.add_argument("--include-for-manuscript", action="store_true")
    parser.add_argument("--disable-other-libraries", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fieldnames, rows = read_rows(args.input)
    found = False
    for row in rows:
        if args.disable_other_libraries:
            row["enabled"] = "false"
            row["include_for_manuscript"] = "false"
        if row.get("library_id") == args.library_id:
            row["enabled"] = "true"
            row["include_for_manuscript"] = (
                "true"
                if args.include_for_manuscript
                else row.get("include_for_manuscript", "false")
            )
            found = True
    if not found:
        print(
            f"ERROR: library_id {args.library_id!r} not found in {args.input}",
            file=sys.stderr,
        )
        return 1
    write_rows(args.out, fieldnames, rows)
    print(f"Wrote publication empirical manifest to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
