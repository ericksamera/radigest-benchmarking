#!/usr/bin/env python3
"""Compare two normalized interval files.

Expected input columns:
  seqid  start0  end0  length  source_tool  raw_id

Only seqid/start0/end0/length are required. Extra columns are ignored.

Modes:
  exact:
    Compares intervals as multisets of (seqid, start0, end0).

  length-only:
    Compares intervals as multisets of length values. This is useful for
    comparators that expose fragment lengths or counts but not coordinates.

Outputs:
  <out-prefix>.summary.tsv
  <out-prefix>.matching.tsv
  <out-prefix>.only_first.tsv
  <out-prefix>.only_second.tsv
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

SUMMARY_COLUMNS = [
    "first_name",
    "second_name",
    "mode",
    "first_intervals",
    "second_intervals",
    "matching_intervals",
    "only_first",
    "only_second",
    "multiset_union",
    "jaccard",
    "status",
]

DETAIL_COLUMNS = [
    "seqid",
    "start0",
    "end0",
    "length",
    "count",
    "first_count",
    "second_count",
    "key",
]


def get_first(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        if name in row and row[name] != "":
            return row[name]
    return ""


def read_interval_counter(path: Path, mode: str) -> Counter[tuple[str, ...]]:
    if not path.exists():
        raise FileNotFoundError(f"interval file not found: {path}")

    counts: Counter[tuple[str, ...]] = Counter()

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")

        for row_number, row in enumerate(reader, start=2):
            seqid = get_first(
                row, ["seqid", "chrom", "record_id", "contig", "scaffold"]
            )
            start_raw = get_first(row, ["start0", "start", "start_zero_based"])
            end_raw = get_first(row, ["end0", "end", "end_zero_based"])
            length_raw = get_first(row, ["length", "len", "fragment_length"])

            if mode == "exact":
                if seqid == "" or start_raw == "" or end_raw == "":
                    raise ValueError(
                        f"{path}: row {row_number}: exact mode requires seqid/start0/end0"
                    )
                try:
                    start0 = int(start_raw)
                    end0 = int(end_raw)
                except ValueError as exc:
                    raise ValueError(
                        f"{path}: row {row_number}: start0/end0 must be integers"
                    ) from exc
                if end0 < start0:
                    raise ValueError(f"{path}: row {row_number}: end0 < start0")
                counts[(seqid, str(start0), str(end0))] += 1

            elif mode == "length-only":
                if length_raw == "":
                    if start_raw == "" or end_raw == "":
                        raise ValueError(
                            f"{path}: row {row_number}: length-only mode requires length or start0/end0"
                        )
                    try:
                        length = int(end_raw) - int(start_raw)
                    except ValueError as exc:
                        raise ValueError(
                            f"{path}: row {row_number}: start0/end0 must be integers"
                        ) from exc
                else:
                    try:
                        length = int(length_raw)
                    except ValueError as exc:
                        raise ValueError(
                            f"{path}: row {row_number}: length must be an integer"
                        ) from exc
                if length < 0:
                    raise ValueError(f"{path}: row {row_number}: negative length")
                counts[(str(length),)] += 1

            else:
                raise ValueError(f"unsupported mode: {mode}")

    return counts


def key_to_detail_row(
    key: tuple[str, ...],
    mode: str,
    count: int,
    first_count: int,
    second_count: int,
) -> dict[str, str]:
    if mode == "exact":
        seqid, start0, end0 = key
        length = str(int(end0) - int(start0))
        key_text = f"{seqid}:{start0}-{end0}"
        return {
            "seqid": seqid,
            "start0": start0,
            "end0": end0,
            "length": length,
            "count": str(count),
            "first_count": str(first_count),
            "second_count": str(second_count),
            "key": key_text,
        }

    length = key[0]
    return {
        "seqid": "*",
        "start0": "",
        "end0": "",
        "length": length,
        "count": str(count),
        "first_count": str(first_count),
        "second_count": str(second_count),
        "key": f"length:{length}",
    }


def write_detail(
    path: Path,
    keys: Iterable[tuple[tuple[str, ...], int]],
    mode: str,
    first: Counter[tuple[str, ...]],
    second: Counter[tuple[str, ...]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=DETAIL_COLUMNS)
        writer.writeheader()
        for key, count in keys:
            writer.writerow(
                key_to_detail_row(
                    key=key,
                    mode=mode,
                    count=count,
                    first_count=first.get(key, 0),
                    second_count=second.get(key, 0),
                )
            )


def sorted_counter_items(counter: Counter[tuple[str, ...]], mode: str):
    if mode == "exact":
        return sorted(
            counter.items(),
            key=lambda item: (item[0][0], int(item[0][1]), int(item[0][2])),
        )
    return sorted(counter.items(), key=lambda item: int(item[0][0]))


def compare(
    first: Counter[tuple[str, ...]],
    second: Counter[tuple[str, ...]],
) -> tuple[
    Counter[tuple[str, ...]],
    Counter[tuple[str, ...]],
    Counter[tuple[str, ...]],
    int,
    int,
    int,
]:
    all_keys = set(first) | set(second)

    matching: Counter[tuple[str, ...]] = Counter()
    only_first: Counter[tuple[str, ...]] = Counter()
    only_second: Counter[tuple[str, ...]] = Counter()

    for key in all_keys:
        a = first.get(key, 0)
        b = second.get(key, 0)
        m = min(a, b)
        if m:
            matching[key] = m
        if a > b:
            only_first[key] = a - b
        if b > a:
            only_second[key] = b - a

    intersection_n = sum(matching.values())
    only_first_n = sum(only_first.values())
    only_second_n = sum(only_second.values())

    return (
        matching,
        only_first,
        only_second,
        intersection_n,
        only_first_n,
        only_second_n,
    )


def write_summary(
    path: Path,
    first_name: str,
    second_name: str,
    mode: str,
    first_n: int,
    second_n: int,
    matching_n: int,
    only_first_n: int,
    only_second_n: int,
) -> None:
    union_n = matching_n + only_first_n + only_second_n
    jaccard = 1.0 if union_n == 0 else matching_n / union_n
    status = "PASS" if only_first_n == 0 and only_second_n == 0 else "DIFFER"

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerow(
            {
                "first_name": first_name,
                "second_name": second_name,
                "mode": mode,
                "first_intervals": first_n,
                "second_intervals": second_n,
                "matching_intervals": matching_n,
                "only_first": only_first_n,
                "only_second": only_second_n,
                "multiset_union": union_n,
                "jaccard": f"{jaccard:.8f}",
                "status": status,
            }
        )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Compare normalized interval sets.")
    parser.add_argument("--first", required=True, type=Path, help="First interval TSV")
    parser.add_argument(
        "--second", required=True, type=Path, help="Second interval TSV"
    )
    parser.add_argument("--first-name", default="first", help="Name for first input")
    parser.add_argument("--second-name", default="second", help="Name for second input")
    parser.add_argument(
        "--mode",
        choices=["exact", "length-only"],
        default="exact",
        help="Comparison mode. Default: exact",
    )
    parser.add_argument(
        "--out-prefix",
        required=True,
        type=Path,
        help="Output prefix. Suffixes .summary.tsv, .matching.tsv, .only_first.tsv, .only_second.tsv are added.",
    )
    parser.add_argument(
        "--fail-on-difference",
        action="store_true",
        help="Exit with status 1 if interval sets differ.",
    )
    args = parser.parse_args(argv)

    try:
        first = read_interval_counter(args.first, args.mode)
        second = read_interval_counter(args.second, args.mode)
        matching, only_first, only_second, matching_n, only_first_n, only_second_n = (
            compare(first, second)
        )

        summary_path = args.out_prefix.with_suffix(
            args.out_prefix.suffix + ".summary.tsv"
        )
        matching_path = args.out_prefix.with_suffix(
            args.out_prefix.suffix + ".matching.tsv"
        )
        only_first_path = args.out_prefix.with_suffix(
            args.out_prefix.suffix + ".only_first.tsv"
        )
        only_second_path = args.out_prefix.with_suffix(
            args.out_prefix.suffix + ".only_second.tsv"
        )

        # If out_prefix has no suffix, Path.with_suffix() is awkward. Normalize here.
        if args.out_prefix.suffix == "":
            summary_path = Path(str(args.out_prefix) + ".summary.tsv")
            matching_path = Path(str(args.out_prefix) + ".matching.tsv")
            only_first_path = Path(str(args.out_prefix) + ".only_first.tsv")
            only_second_path = Path(str(args.out_prefix) + ".only_second.tsv")

        write_summary(
            path=summary_path,
            first_name=args.first_name,
            second_name=args.second_name,
            mode=args.mode,
            first_n=sum(first.values()),
            second_n=sum(second.values()),
            matching_n=matching_n,
            only_first_n=only_first_n,
            only_second_n=only_second_n,
        )

        write_detail(
            matching_path,
            sorted_counter_items(matching, args.mode),
            args.mode,
            first,
            second,
        )
        write_detail(
            only_first_path,
            sorted_counter_items(only_first, args.mode),
            args.mode,
            first,
            second,
        )
        write_detail(
            only_second_path,
            sorted_counter_items(only_second, args.mode),
            args.mode,
            first,
            second,
        )

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.fail_on_difference and (only_first_n or only_second_n):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
