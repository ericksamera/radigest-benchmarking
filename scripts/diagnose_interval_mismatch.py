#!/usr/bin/env python3
"""Diagnose mismatches between two normalized interval TSV files.

Inputs must contain at least:

  seqid
  start0
  end0
  length

The script reports whether interval mismatch is driven by seqid naming,
coordinate offsets, length distribution, or true interval-set differences.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

FIELDS = [
    "comparison",
    "first_count",
    "second_count",
    "matching",
    "only_first",
    "only_second",
    "jaccard",
    "notes",
]


def read_intervals(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")

        required = {"seqid", "start0", "end0", "length"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"{path}: missing required columns: {sorted(missing)}")

        for raw_row in reader:
            row = {
                key: "" if value is None else value
                for key, value in raw_row.items()
                if key is not None
            }
            rows.append(row)

    return rows


def canonical_seqid(seqid: str, mode: str) -> str:
    seqid = seqid.strip()

    if mode == "unchanged":
        return seqid

    if mode == "first-token":
        return seqid.split()[0]

    if mode == "strip-pipe-description":
        return seqid.split()[0].split("|")[-1]

    raise ValueError(f"unknown seqid mode: {mode}")


def interval_counter(
    rows: list[dict[str, str]], seqid_mode: str
) -> Counter[tuple[str, int, int]]:
    out: Counter[tuple[str, int, int]] = Counter()

    for row in rows:
        seqid = canonical_seqid(row["seqid"], seqid_mode)
        start0 = int(row["start0"])
        end0 = int(row["end0"])
        out[(seqid, start0, end0)] += 1

    return out


def coordinate_counter(rows: list[dict[str, str]]) -> Counter[tuple[int, int]]:
    out: Counter[tuple[int, int]] = Counter()

    for row in rows:
        out[(int(row["start0"]), int(row["end0"]))] += 1

    return out


def length_counter(rows: list[dict[str, str]]) -> Counter[int]:
    out: Counter[int] = Counter()

    for row in rows:
        out[int(row["length"])] += 1

    return out


def summarize_counter(
    first: Counter,
    second: Counter,
) -> tuple[int, int, int, int, int, float]:
    matching_counter = first & second
    only_first_counter = first - second
    only_second_counter = second - first

    first_n = sum(first.values())
    second_n = sum(second.values())
    matching = sum(matching_counter.values())
    only_first = sum(only_first_counter.values())
    only_second = sum(only_second_counter.values())
    union = matching + only_first + only_second
    jaccard = matching / union if union else 1.0

    return first_n, second_n, matching, only_first, only_second, jaccard


def row_for(
    comparison: str,
    first: Counter,
    second: Counter,
    notes: str,
) -> dict[str, str]:
    first_n, second_n, matching, only_first, only_second, jaccard = summarize_counter(
        first, second
    )

    return {
        "comparison": comparison,
        "first_count": str(first_n),
        "second_count": str(second_n),
        "matching": str(matching),
        "only_first": str(only_first),
        "only_second": str(only_second),
        "jaccard": f"{jaccard:.8f}",
        "notes": notes,
    }


def seqid_summary(rows: list[dict[str, str]], mode: str) -> list[str]:
    return sorted({canonical_seqid(row["seqid"], mode) for row in rows})


def write_examples(
    path: Path,
    first_counter: Counter[tuple[str, int, int]],
    second_counter: Counter[tuple[str, int, int]],
    limit: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    only_first = first_counter - second_counter
    only_second = second_counter - first_counter

    with path.open("w", encoding="utf-8") as handle:
        handle.write("section\tseqid\tstart0\tend0\tcount\n")

        for i, (key, count) in enumerate(only_first.items()):
            if i >= limit:
                break
            seqid, start0, end0 = key
            handle.write(f"only_first\t{seqid}\t{start0}\t{end0}\t{count}\n")

        for i, (key, count) in enumerate(only_second.items()):
            if i >= limit:
                break
            seqid, start0, end0 = key
            handle.write(f"only_second\t{seqid}\t{start0}\t{end0}\t{count}\n")


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", required=True, type=Path)
    parser.add_argument("--second", required=True, type=Path)
    parser.add_argument("--out-summary", required=True, type=Path)
    parser.add_argument("--out-examples", required=True, type=Path)
    parser.add_argument("--example-limit", type=int, default=20)
    args = parser.parse_args(argv)

    try:
        first_rows = read_intervals(args.first)
        second_rows = read_intervals(args.second)

        summary_rows: list[dict[str, str]] = []

        for mode in ["unchanged", "first-token", "strip-pipe-description"]:
            first = interval_counter(first_rows, mode)
            second = interval_counter(second_rows, mode)

            first_seqids = seqid_summary(first_rows, mode)
            second_seqids = seqid_summary(second_rows, mode)
            seqid_overlap = len(set(first_seqids) & set(second_seqids))

            summary_rows.append(
                row_for(
                    comparison=f"exact_intervals_seqid_mode={mode}",
                    first=first,
                    second=second,
                    notes=(
                        f"first_seqids={len(first_seqids)}; "
                        f"second_seqids={len(second_seqids)}; "
                        f"shared_seqids={seqid_overlap}"
                    ),
                )
            )

            if mode == "unchanged":
                write_examples(
                    args.out_examples,
                    first,
                    second,
                    args.example_limit,
                )

        summary_rows.append(
            row_for(
                comparison="coordinate_pairs_ignoring_seqid",
                first=coordinate_counter(first_rows),
                second=coordinate_counter(second_rows),
                notes=(
                    "compares start0/end0 only; useful for detecting "
                    "seqid-only mismatch"
                ),
            )
        )

        summary_rows.append(
            row_for(
                comparison="length_multiset",
                first=length_counter(first_rows),
                second=length_counter(second_rows),
                notes="compares length distribution only",
            )
        )

        write_tsv(args.out_summary, summary_rows)

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out_summary}", file=sys.stderr)
    print(f"wrote {args.out_examples}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
