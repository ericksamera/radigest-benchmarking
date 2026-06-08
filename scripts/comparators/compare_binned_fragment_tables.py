#!/usr/bin/env python3
"""Compare two binned fragment-count tables without making coordinate claims."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

DETAIL_FIELDS = [
    "enzyme_pair",
    "bin_lower",
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
    "bins_with_difference",
    "max_abs_bin_difference",
    "status",
    "claim_boundary",
    "notes",
]


def canonical_pair(label: str) -> str:
    text = label.strip().replace("_", "+").replace(",", "+").replace("/", "+")
    parts = [part.strip() for part in text.split("+") if part.strip()]
    if len(parts) == 2:
        return "+".join(parts)
    return label.strip()


def read_bins(path: Path) -> dict[tuple[str, int], tuple[int, int]]:
    out: dict[tuple[str, int], tuple[int, int]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        required = {"enzyme_pair", "bin_upper", "fragment_count"}
        missing = sorted(required - set(reader.fieldnames))
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(missing)}")
        for row in reader:
            pair = canonical_pair(row["enzyme_pair"])
            upper = int(float(row["bin_upper"]))
            lower = int(float(row.get("bin_lower") or max(0, upper - 10)))
            count = int(float(row["fragment_count"]))
            out[(pair, upper)] = (lower, count)
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
    parser.add_argument("--fail-on-difference", action="store_true")
    args = parser.parse_args(argv)

    try:
        first = read_bins(args.first)
        second = read_bins(args.second)
        keys = sorted(set(first) | set(second))
        detail_rows: list[dict[str, str]] = []
        for pair, upper in keys:
            lower = first.get(
                (pair, upper), second.get((pair, upper), (max(0, upper - 10), 0))
            )[0]
            first_count = first.get((pair, upper), (lower, 0))[1]
            second_count = second.get((pair, upper), (lower, 0))[1]
            detail_rows.append(
                {
                    "enzyme_pair": pair,
                    "bin_lower": str(lower),
                    "bin_upper": str(upper),
                    "first_count": str(first_count),
                    "second_count": str(second_count),
                    "difference_second_minus_first": str(second_count - first_count),
                }
            )

        summary_rows: list[dict[str, str]] = []
        failed = False
        for pair in sorted({key[0] for key in keys}):
            rows = [row for row in detail_rows if row["enzyme_pair"] == pair]
            first_total = sum(int(row["first_count"]) for row in rows)
            second_total = sum(int(row["second_count"]) for row in rows)
            diffs = [int(row["difference_second_minus_first"]) for row in rows]
            bins_with_difference = sum(1 for diff in diffs if diff != 0)
            max_abs_bin_difference = max((abs(diff) for diff in diffs), default=0)
            diff_total = second_total - first_total
            status = (
                "PASS" if diff_total == 0 and bins_with_difference == 0 else "DIFFER"
            )
            failed = failed or status != "PASS"
            summary_rows.append(
                {
                    "first_name": args.first_name,
                    "second_name": args.second_name,
                    "enzyme_pair": pair,
                    "bins_compared": str(len(rows)),
                    "first_total": str(first_total),
                    "second_total": str(second_total),
                    "difference_second_minus_first": str(diff_total),
                    "bins_with_difference": str(bins_with_difference),
                    "max_abs_bin_difference": str(max_abs_bin_difference),
                    "status": status,
                    "claim_boundary": "binned_screening_only_no_coordinate_equivalence",
                    "notes": "Compares 10 bp binned fragment-count distributions only.",
                }
            )

        write_tsv(args.out_detail, detail_rows, DETAIL_FIELDS)
        write_tsv(args.out_summary, summary_rows, SUMMARY_FIELDS)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out_detail}", file=sys.stderr)
    print(f"wrote {args.out_summary}", file=sys.stderr)
    if args.fail_on_difference and failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
