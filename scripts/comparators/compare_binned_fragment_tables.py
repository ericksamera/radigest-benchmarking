#!/usr/bin/env python3
"""Compare two binned fragment-count tables."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

FIELDS = [
    "enzyme_pair",
    "bin_upper",
    "first_count",
    "second_count",
    "difference_second_minus_first",
]

SUMMARY_FIELDS = [
    "first_name",
    "second_name",
    "enzyme_pair",
    "bins_compared",
    "first_total",
    "second_total",
    "difference_second_minus_first",
    "status",
]


def read_bins(path: Path) -> dict[tuple[str, int], int]:
    out: dict[tuple[str, int], int] = {}

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            key = (row["enzyme_pair"], int(row["bin_upper"]))
            out[key] = int(float(row["fragment_count"]))

    return out


def write_tsv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", required=True, type=Path)
    parser.add_argument("--second", required=True, type=Path)
    parser.add_argument("--first-name", default="first")
    parser.add_argument("--second-name", default="second")
    parser.add_argument("--out-detail", required=True, type=Path)
    parser.add_argument("--out-summary", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        first = read_bins(args.first)
        second = read_bins(args.second)

        keys = sorted(set(first) | set(second))
        detail_rows: list[dict[str, str]] = []

        for enzyme_pair, upper in keys:
            a = first.get((enzyme_pair, upper), 0)
            b = second.get((enzyme_pair, upper), 0)
            detail_rows.append(
                {
                    "enzyme_pair": enzyme_pair,
                    "bin_upper": str(upper),
                    "first_count": str(a),
                    "second_count": str(b),
                    "difference_second_minus_first": str(b - a),
                }
            )

        summary_rows: list[dict[str, str]] = []
        for enzyme_pair in sorted({key[0] for key in keys}):
            pair_rows = [
                row for row in detail_rows if row["enzyme_pair"] == enzyme_pair
            ]
            first_total = sum(int(row["first_count"]) for row in pair_rows)
            second_total = sum(int(row["second_count"]) for row in pair_rows)
            diff = second_total - first_total
            status = "PASS" if diff == 0 else "DIFFER"
            summary_rows.append(
                {
                    "first_name": args.first_name,
                    "second_name": args.second_name,
                    "enzyme_pair": enzyme_pair,
                    "bins_compared": str(len(pair_rows)),
                    "first_total": str(first_total),
                    "second_total": str(second_total),
                    "difference_second_minus_first": str(diff),
                    "status": status,
                }
            )

        write_tsv(args.out_detail, detail_rows, FIELDS)
        write_tsv(args.out_summary, summary_rows, SUMMARY_FIELDS)

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out_detail}", file=sys.stderr)
    print(f"wrote {args.out_summary}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
