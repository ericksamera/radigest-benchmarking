#!/usr/bin/env python3
"""Summarize empirical-library radigest prediction fragment lengths."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

HISTOGRAM_COLUMNS = [
    "library_id",
    "prediction_mode",
    "length",
    "count",
    "fraction",
    "in_size_window",
    "in_score_window",
]
SUMMARY_COLUMNS = [
    "library_id",
    "prediction_mode",
    "reference_id",
    "reference_path",
    "enzyme_1",
    "enzyme_2",
    "min_size",
    "max_size",
    "score_min",
    "score_max",
    "size_model",
    "size_edge_sd",
    "total_fragments",
    "size_window_fragments",
    "size_window_fraction",
    "score_window_fragments",
    "score_window_fraction",
    "mean_length",
    "median_length",
    "min_observed_length",
    "max_observed_length",
    "fragments_tsv",
]


def get_first(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = row.get(name, "")
        if value != "":
            return value
    return ""


def parse_int(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an integer, got {value!r}") from exc


def read_lengths(path: Path) -> Counter[int]:
    histogram: Counter[int] = Counter()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        for row_number, row in enumerate(reader, start=2):
            length_raw = get_first(row, ["length", "len", "fragment_length"])
            if length_raw == "":
                start_raw = get_first(row, ["start0", "start", "start_zero_based"])
                end_raw = get_first(row, ["end0", "end", "end_zero_based"])
                if start_raw == "" or end_raw == "":
                    raise ValueError(
                        f"{path}: row {row_number}: missing length or start/end"
                    )
                length = parse_int(
                    end_raw, f"{path}: row {row_number} end"
                ) - parse_int(start_raw, f"{path}: row {row_number} start")
            else:
                length = parse_int(length_raw, f"{path}: row {row_number} length")
            if length < 0:
                raise ValueError(f"{path}: row {row_number}: negative length={length}")
            histogram[length] += 1
    return histogram


def median_from_histogram(histogram: Counter[int]) -> str:
    total = sum(histogram.values())
    if total == 0:
        return "NA"
    left_index = (total - 1) // 2
    right_index = total // 2
    left_value: int | None = None
    right_value: int | None = None
    cumulative = 0
    for length, count in sorted(histogram.items()):
        cumulative += count
        if left_value is None and cumulative > left_index:
            left_value = length
        if cumulative > right_index:
            right_value = length
            break
    if left_value is None or right_value is None:
        raise AssertionError("median calculation failed for non-empty histogram")
    return f"{((left_value + right_value) / 2):.6g}"


def write_histogram(
    *,
    histogram: Counter[int],
    output: Path,
    library_id: str,
    prediction_mode: str,
    min_size: int,
    max_size: int,
    score_min: int,
    score_max: int,
) -> None:
    total = sum(histogram.values())
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, delimiter="\t", fieldnames=HISTOGRAM_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        for length, count in sorted(histogram.items()):
            fraction = "NA" if total == 0 else f"{count / total:.12g}"
            writer.writerow(
                {
                    "library_id": library_id,
                    "prediction_mode": prediction_mode,
                    "length": length,
                    "count": count,
                    "fraction": fraction,
                    "in_size_window": str(min_size <= length <= max_size).lower(),
                    "in_score_window": str(score_min <= length <= score_max).lower(),
                }
            )


def write_summary(
    *,
    histogram: Counter[int],
    output: Path,
    args: argparse.Namespace,
) -> None:
    total = sum(histogram.values())
    min_size = parse_int(args.min_size, "min_size")
    max_size = parse_int(args.max_size, "max_size")
    score_min = parse_int(args.score_min, "score_min")
    score_max = parse_int(args.score_max, "score_max")
    size_window = sum(
        count for length, count in histogram.items() if min_size <= length <= max_size
    )
    score_window = sum(
        count for length, count in histogram.items() if score_min <= length <= score_max
    )
    length_sum = sum(length * count for length, count in histogram.items())
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, delimiter="\t", fieldnames=SUMMARY_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerow(
            {
                "library_id": args.library_id,
                "prediction_mode": args.prediction_mode,
                "reference_id": args.reference_id,
                "reference_path": args.reference_path,
                "enzyme_1": args.enzyme_1,
                "enzyme_2": args.enzyme_2,
                "min_size": args.min_size,
                "max_size": args.max_size,
                "score_min": args.score_min,
                "score_max": args.score_max,
                "size_model": args.size_model,
                "size_edge_sd": args.size_edge_sd,
                "total_fragments": total,
                "size_window_fragments": size_window,
                "size_window_fraction": (
                    "NA" if total == 0 else f"{size_window / total:.12g}"
                ),
                "score_window_fragments": score_window,
                "score_window_fraction": (
                    "NA" if total == 0 else f"{score_window / total:.12g}"
                ),
                "mean_length": "NA" if total == 0 else f"{length_sum / total:.6g}",
                "median_length": median_from_histogram(histogram),
                "min_observed_length": "NA" if total == 0 else min(histogram),
                "max_observed_length": "NA" if total == 0 else max(histogram),
                "fragments_tsv": str(args.fragments),
            }
        )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fragments", type=Path, required=True)
    parser.add_argument("--library-id", required=True)
    parser.add_argument("--prediction-mode", required=True, choices=["raw", "hard"])
    parser.add_argument("--reference-id", required=True)
    parser.add_argument("--reference-path", required=True)
    parser.add_argument("--enzyme-1", required=True)
    parser.add_argument("--enzyme-2", required=True)
    parser.add_argument("--min-size", required=True)
    parser.add_argument("--max-size", required=True)
    parser.add_argument("--score-min", required=True)
    parser.add_argument("--score-max", required=True)
    parser.add_argument("--size-model", required=True)
    parser.add_argument("--size-edge-sd", required=True)
    parser.add_argument("--hist-out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        histogram = read_lengths(args.fragments)
        write_histogram(
            histogram=histogram,
            output=args.hist_out,
            library_id=args.library_id,
            prediction_mode=args.prediction_mode,
            min_size=parse_int(args.min_size, "min_size"),
            max_size=parse_int(args.max_size, "max_size"),
            score_min=parse_int(args.score_min, "score_min"),
            score_max=parse_int(args.score_max, "score_max"),
        )
        write_summary(histogram=histogram, output=args.summary_out, args=args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
