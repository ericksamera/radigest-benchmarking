#!/usr/bin/env python3
"""Bin radigest fragment TSV lengths into ddgRADer-style 10 bp bins.

The output is deliberately binned rather than coordinate-resolved. It is used
only for ddgRADer backend screening-behavior comparison.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

BIN_COLUMNS = ["enzyme_pair", "bin_lower", "bin_upper", "fragment_count"]
SUMMARY_COLUMNS = [
    "tool",
    "input",
    "enzyme_pair",
    "min_size",
    "max_size",
    "total_binned_fragments_0_1010",
    "binned_fragments_in_window",
    "approx_bases_in_window",
    "bins_tsv",
    "notes",
]
TRUE_VALUES = {"1", "true", "yes", "y"}


def bin_upper(length: int, max_bin: int = 1010, step: int = 10) -> int | None:
    if length <= 0:
        return None
    upper = ((length + step - 1) // step) * step
    if upper > max_bin:
        return None
    return upper


def read_lengths(path: Path) -> list[int]:
    lengths: list[int] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        if "length" not in reader.fieldnames:
            raise ValueError(f"{path}: missing length column")
        for row in reader:
            kept = row.get("hard_kept", row.get("hard_kept?", ""))
            if kept and kept.strip().lower() not in TRUE_VALUES:
                continue
            lengths.append(int(row["length"]))
    return lengths


def build_bins(lengths: list[int], enzyme_pair: str) -> list[dict[str, str]]:
    counts = {upper: 0 for upper in range(10, 1020, 10)}
    for length in lengths:
        upper = bin_upper(length)
        if upper is not None:
            counts[upper] += 1
    return [
        {
            "enzyme_pair": enzyme_pair,
            "bin_lower": str(max(0, upper - 10)),
            "bin_upper": str(upper),
            "fragment_count": str(counts[upper]),
        }
        for upper in sorted(counts)
    ]


def write_tsv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(
    path: Path,
    rows: list[dict[str, str]],
    input_path: Path,
    bins_path: Path,
    enzyme_pair: str,
    min_size: int,
    max_size: int,
) -> None:
    total = sum(int(row["fragment_count"]) for row in rows)
    in_window = [row for row in rows if min_size <= int(row["bin_upper"]) <= max_size]
    window_count = sum(int(row["fragment_count"]) for row in in_window)
    approx_bases = sum(
        int(row["fragment_count"]) * int(row["bin_upper"]) for row in in_window
    )
    write_tsv(
        path,
        [
            {
                "tool": "radigest_binned",
                "input": str(input_path),
                "enzyme_pair": enzyme_pair,
                "min_size": str(min_size),
                "max_size": str(max_size),
                "total_binned_fragments_0_1010": str(total),
                "binned_fragments_in_window": str(window_count),
                "approx_bases_in_window": str(approx_bases),
                "bins_tsv": str(bins_path),
                "notes": (
                    "radigest fragment lengths binned to ddgRADer 10 bp bins; "
                    "bin_upper is used for approximate in-window base totals; "
                    "not coordinate-level output"
                ),
            }
        ],
        SUMMARY_COLUMNS,
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--enzyme-pair", required=True)
    parser.add_argument("--min", dest="min_size", required=True, type=int)
    parser.add_argument("--max", dest="max_size", required=True, type=int)
    parser.add_argument("--out-bins", required=True, type=Path)
    parser.add_argument("--out-summary", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.min_size > args.max_size:
            raise ValueError("--min must be <= --max")
        lengths = read_lengths(args.input)
        rows = build_bins(lengths, args.enzyme_pair)
        write_tsv(args.out_bins, rows, BIN_COLUMNS)
        write_summary(
            args.out_summary,
            rows,
            args.input,
            args.out_bins,
            args.enzyme_pair,
            args.min_size,
            args.max_size,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {args.out_bins}", file=sys.stderr)
    print(f"wrote {args.out_summary}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
