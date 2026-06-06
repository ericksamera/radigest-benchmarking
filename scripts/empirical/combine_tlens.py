#!/usr/bin/env python3
"""Combine per-BAM empirical TLEN outputs for one empirical library."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

HISTOGRAM_COLUMNS = ["library_id", "bam_id", "tlen", "count", "fraction"]
QC_COLUMNS = [
    "library_id",
    "bam_id",
    "bam_path",
    "reference_id",
    "reference_path",
    "enzyme_1",
    "enzyme_2",
    "min_size",
    "max_size",
    "score_min",
    "score_max",
    "size_model",
    "total_records",
    "used_pairs",
    "in_window_count",
    "in_window_fraction",
    "skipped_secondary",
    "skipped_supplementary",
    "skipped_qcfail",
    "skipped_duplicate",
    "skipped_unpaired",
    "skipped_unmapped",
    "skipped_mate_unmapped",
    "skipped_not_proper_pair",
    "skipped_low_mapq",
    "skipped_nonpositive_tlen",
    "skipped_above_max_tlen",
    "min_mapq",
    "exclude_duplicates",
    "max_tlen",
    "mean_tlen",
    "median_tlen",
    "min_observed_tlen",
    "max_observed_tlen",
]
SKIP_COLUMNS = [column for column in QC_COLUMNS if column.startswith("skipped_")]
INT_COLUMNS = ["total_records", "used_pairs", "in_window_count", *SKIP_COLUMNS]


def read_tsv(path: Path, required_columns: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        missing = [
            column for column in required_columns if column not in reader.fieldnames
        ]
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(missing)}")
        return [
            {key: (row.get(key) or "").strip() for key in required_columns}
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]


def median_from_histogram(histogram: Counter[int]) -> str:
    total = sum(histogram.values())
    if total == 0:
        return "NA"
    left_index = (total - 1) // 2
    right_index = total // 2
    left_value: int | None = None
    right_value: int | None = None
    cumulative = 0
    for tlen, count in sorted(histogram.items()):
        cumulative += count
        if left_value is None and cumulative > left_index:
            left_value = tlen
        if cumulative > right_index:
            right_value = tlen
            break
    if left_value is None or right_value is None:
        raise AssertionError("median calculation failed for non-empty histogram")
    return f"{((left_value + right_value) / 2):.6g}"


def write_combined_tlens(input_paths: list[Path], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as out_handle:
        for path in input_paths:
            with path.open("r", encoding="utf-8") as in_handle:
                for line in in_handle:
                    if line.strip():
                        out_handle.write(line)


def write_combined_histograms(
    input_paths: list[Path], output: Path, library_id: str
) -> Counter[int]:
    pooled: Counter[int] = Counter()
    rows: list[dict[str, str]] = []
    for path in input_paths:
        for row in read_tsv(path, HISTOGRAM_COLUMNS):
            rows.append(row)
            pooled[int(row["tlen"])] += int(row["count"])
    pooled_total = sum(pooled.values())
    for tlen, count in sorted(pooled.items()):
        fraction = 0.0 if pooled_total == 0 else count / pooled_total
        rows.append(
            {
                "library_id": library_id,
                "bam_id": "pooled",
                "tlen": str(tlen),
                "count": str(count),
                "fraction": f"{fraction:.12g}",
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, delimiter="\t", fieldnames=HISTOGRAM_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    return pooled


def write_combined_qc(
    input_paths: list[Path], output: Path, library_id: str, pooled_hist: Counter[int]
) -> None:
    rows: list[dict[str, str]] = []
    for path in input_paths:
        rows.extend(read_tsv(path, QC_COLUMNS))
    if not rows:
        raise ValueError("cannot combine zero QC rows")
    template = rows[0]
    pooled_row = dict(template)
    pooled_row["library_id"] = library_id
    pooled_row["bam_id"] = "pooled"
    pooled_row["bam_path"] = "NA"
    for column in INT_COLUMNS:
        pooled_row[column] = str(sum(int(row[column]) for row in rows))
    used_pairs = int(pooled_row["used_pairs"])
    in_window_count = int(pooled_row["in_window_count"])
    tlen_sum = sum(tlen * count for tlen, count in pooled_hist.items())
    pooled_row["in_window_fraction"] = (
        "NA" if used_pairs == 0 else f"{in_window_count / used_pairs:.12g}"
    )
    pooled_row["mean_tlen"] = (
        "NA" if used_pairs == 0 else f"{tlen_sum / used_pairs:.6g}"
    )
    pooled_row["median_tlen"] = median_from_histogram(pooled_hist)
    pooled_row["min_observed_tlen"] = "NA" if not pooled_hist else str(min(pooled_hist))
    pooled_row["max_observed_tlen"] = "NA" if not pooled_hist else str(max(pooled_hist))
    rows.append(pooled_row)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, delimiter="\t", fieldnames=QC_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-id", required=True)
    parser.add_argument("--tlens", type=Path, nargs="+", required=True)
    parser.add_argument("--histograms", type=Path, nargs="+", required=True)
    parser.add_argument("--qc-tables", type=Path, nargs="+", required=True)
    parser.add_argument("--tlens-out", type=Path, required=True)
    parser.add_argument("--hist-out", type=Path, required=True)
    parser.add_argument("--qc-out", type=Path, required=True)
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        write_combined_tlens(args.tlens, args.tlens_out)
        pooled_hist = write_combined_histograms(
            args.histograms, args.hist_out, args.library_id
        )
        write_combined_qc(args.qc_tables, args.qc_out, args.library_id, pooled_hist)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
