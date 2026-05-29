#!/usr/bin/env python3
"""Normalize radigest fragment TSV output to a BED-like interval table.

Input:
  radigest -fragments-tsv output with columns similar to:
    chrom  start0  end0  length  hard_kept  size_weight

Output:
  seqid  start0  end0  length  source_tool  raw_id  hard_kept  size_weight

The output coordinate convention is always zero-based half-open [start0, end0).

This script is intentionally conservative:
  - end0 must be >= start0;
  - length is recomputed as end0 - start0;
  - if the input length disagrees with the coordinate-derived length, the
    coordinate-derived value is written and a warning is emitted;
  - zero-length intervals are allowed by default because coincident cut sites can
    produce them when min size includes zero.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

OUTPUT_COLUMNS = [
    "seqid",
    "start0",
    "end0",
    "length",
    "source_tool",
    "raw_id",
    "hard_kept",
    "size_weight",
]


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def get_first(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        if name in row and row[name] != "":
            return row[name]
    return ""


def normalize_row(
    row: dict[str, str],
    row_number: int,
    source_tool: str,
    hard_kept_only: bool,
    drop_zero: bool,
    strict_length: bool,
) -> dict[str, str] | None:
    seqid = get_first(row, ["seqid", "chrom", "record_id", "contig", "scaffold"])
    if not seqid:
        raise ValueError(f"row {row_number}: missing seqid/chrom column")

    start_raw = get_first(row, ["start0", "start", "start_zero_based"])
    end_raw = get_first(row, ["end0", "end", "end_zero_based"])
    if start_raw == "" or end_raw == "":
        raise ValueError(f"row {row_number}: missing start0/end0 columns")

    try:
        start0 = int(start_raw)
        end0 = int(end_raw)
    except ValueError as exc:
        raise ValueError(
            f"row {row_number}: start0/end0 must be integers, "
            f"got {start_raw!r}/{end_raw!r}"
        ) from exc

    if start0 < 0:
        raise ValueError(f"row {row_number}: start0 is negative: {start0}")
    if end0 < start0:
        raise ValueError(f"row {row_number}: end0 < start0: {start0}, {end0}")

    length = end0 - start0
    if length == 0 and drop_zero:
        return None

    length_raw = get_first(row, ["length", "len", "fragment_length"])
    if length_raw not in {"", str(length)}:
        msg = (
            f"warning: row {row_number}: input length {length_raw!r} disagrees "
            f"with end0-start0={length}; writing coordinate-derived length"
        )
        if strict_length:
            raise ValueError(msg.replace("warning: ", ""))
        print(msg, file=sys.stderr)

    hard_kept = get_first(row, ["hard_kept", "kept", "in_hard_window"])
    if hard_kept_only and hard_kept != "" and not parse_bool(hard_kept):
        return None

    size_weight = get_first(row, ["size_weight", "weight", "recovery_weight"])
    raw_id = get_first(row, ["raw_id", "id", "fragment_id"])
    if not raw_id:
        raw_id = f"{seqid}:{start0}-{end0}:row{row_number}"

    return {
        "seqid": seqid,
        "start0": str(start0),
        "end0": str(end0),
        "length": str(length),
        "source_tool": source_tool,
        "raw_id": raw_id,
        "hard_kept": hard_kept,
        "size_weight": size_weight,
    }


def normalize_file(
    input_path: Path,
    output_path: Path,
    source_tool: str,
    hard_kept_only: bool,
    drop_zero: bool,
    strict_length: bool,
) -> tuple[int, int]:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows_seen = 0
    rows_written = 0

    with (
        input_path.open(newline="", encoding="utf-8") as in_handle,
        output_path.open("w", newline="", encoding="utf-8") as out_handle,
    ):
        reader = csv.DictReader(in_handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{input_path}: missing header")

        writer = csv.DictWriter(out_handle, delimiter="\t", fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()

        for row_number, row in enumerate(reader, start=2):
            rows_seen += 1
            normalized = normalize_row(
                row=row,
                row_number=row_number,
                source_tool=source_tool,
                hard_kept_only=hard_kept_only,
                drop_zero=drop_zero,
                strict_length=strict_length,
            )
            if normalized is None:
                continue
            writer.writerow(normalized)
            rows_written += 1

    return rows_seen, rows_written


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize radigest fragment TSV to zero-based half-open " "interval TSV."
        )
    )
    parser.add_argument(
        "-i", "--input", required=True, type=Path, help="Input radigest fragments TSV"
    )
    parser.add_argument(
        "-o", "--output", required=True, type=Path, help="Output normalized TSV"
    )
    parser.add_argument(
        "--source-tool",
        default="radigest",
        help="Value to write in source_tool column. Default: radigest",
    )
    parser.add_argument(
        "--hard-kept-only",
        action="store_true",
        help="Keep only rows whose hard_kept field is true when that field is present.",
    )
    parser.add_argument(
        "--drop-zero",
        action="store_true",
        help="Drop zero-length intervals.",
    )
    parser.add_argument(
        "--strict-length",
        action="store_true",
        help="Fail if input length disagrees with end0-start0.",
    )

    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"error: input file does not exist: {args.input}", file=sys.stderr)
        return 2

    try:
        rows_seen, rows_written = normalize_file(
            input_path=args.input,
            output_path=args.output,
            source_tool=args.source_tool,
            hard_kept_only=args.hard_kept_only,
            drop_zero=args.drop_zero,
            strict_length=args.strict_length,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        f"normalized {rows_written} of {rows_seen} interval row(s) "
        f"from {args.input} to {args.output}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
