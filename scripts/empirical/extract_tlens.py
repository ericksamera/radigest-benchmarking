#!/usr/bin/env python3
"""Extract positive TLEN values from one empirical BAM."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import pysam  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - exercised only outside the conda env.
    pysam = None  # type: ignore[assignment]

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
TRUE_VALUES = {"1", "true", "t", "yes", "y"}
FALSE_VALUES = {"0", "false", "f", "no", "n"}


@dataclass
class TlenSummary:
    library_id: str
    bam_id: str
    bam_path: str
    reference_id: str
    reference_path: str
    enzyme_1: str
    enzyme_2: str
    min_size: int
    max_size: int
    score_min: int
    score_max: int
    size_model: str
    min_mapq: int
    exclude_duplicates: bool
    max_tlen: int
    total_records: int = 0
    skips: dict[str, int] = field(
        default_factory=lambda: {column: 0 for column in SKIP_COLUMNS}
    )
    histogram: Counter[int] = field(default_factory=Counter)

    @property
    def used_pairs(self) -> int:
        return sum(self.histogram.values())

    @property
    def tlen_sum(self) -> int:
        return sum(tlen * count for tlen, count in self.histogram.items())

    @property
    def in_window_count(self) -> int:
        return sum(
            count
            for tlen, count in self.histogram.items()
            if self.min_size <= tlen <= self.max_size
        )

    def mean_tlen(self) -> str:
        if self.used_pairs == 0:
            return "NA"
        return f"{self.tlen_sum / self.used_pairs:.6g}"

    def median_tlen(self) -> str:
        if self.used_pairs == 0:
            return "NA"
        return f"{median_from_histogram(self.histogram):.6g}"

    def min_observed_tlen(self) -> str:
        if self.used_pairs == 0:
            return "NA"
        return str(min(self.histogram))

    def max_observed_tlen(self) -> str:
        if self.used_pairs == 0:
            return "NA"
        return str(max(self.histogram))

    def in_window_fraction(self) -> str:
        if self.used_pairs == 0:
            return "NA"
        return f"{self.in_window_count / self.used_pairs:.12g}"

    def qc_row(self) -> dict[str, str | int]:
        row: dict[str, str | int] = {
            "library_id": self.library_id,
            "bam_id": self.bam_id,
            "bam_path": self.bam_path,
            "reference_id": self.reference_id,
            "reference_path": self.reference_path,
            "enzyme_1": self.enzyme_1,
            "enzyme_2": self.enzyme_2,
            "min_size": self.min_size,
            "max_size": self.max_size,
            "score_min": self.score_min,
            "score_max": self.score_max,
            "size_model": self.size_model,
            "total_records": self.total_records,
            "used_pairs": self.used_pairs,
            "in_window_count": self.in_window_count,
            "in_window_fraction": self.in_window_fraction(),
            "min_mapq": self.min_mapq,
            "exclude_duplicates": str(self.exclude_duplicates).lower(),
            "max_tlen": self.max_tlen,
            "mean_tlen": self.mean_tlen(),
            "median_tlen": self.median_tlen(),
            "min_observed_tlen": self.min_observed_tlen(),
            "max_observed_tlen": self.max_observed_tlen(),
        }
        row.update(self.skips)
        return row


def median_from_histogram(histogram: Counter[int]) -> float:
    total = sum(histogram.values())
    if total == 0:
        raise ValueError("cannot compute median of an empty histogram")
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
    return (left_value + right_value) / 2


def parse_bool(value: str, label: str) -> bool:
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"{label} must be true or false, got {value!r}")


def parse_int(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an integer, got {value!r}") from exc


def should_use_record(record: Any, summary: TlenSummary) -> int | None:
    summary.total_records += 1
    if record.is_secondary:
        summary.skips["skipped_secondary"] += 1
        return None
    if record.is_supplementary:
        summary.skips["skipped_supplementary"] += 1
        return None
    if record.is_qcfail:
        summary.skips["skipped_qcfail"] += 1
        return None
    if summary.exclude_duplicates and record.is_duplicate:
        summary.skips["skipped_duplicate"] += 1
        return None
    if not record.is_paired:
        summary.skips["skipped_unpaired"] += 1
        return None
    if record.is_unmapped:
        summary.skips["skipped_unmapped"] += 1
        return None
    if record.mate_is_unmapped:
        summary.skips["skipped_mate_unmapped"] += 1
        return None
    if not record.is_proper_pair:
        summary.skips["skipped_not_proper_pair"] += 1
        return None
    if record.mapping_quality < summary.min_mapq:
        summary.skips["skipped_low_mapq"] += 1
        return None
    tlen = int(record.template_length)
    if tlen <= 0:
        summary.skips["skipped_nonpositive_tlen"] += 1
        return None
    if tlen > summary.max_tlen:
        summary.skips["skipped_above_max_tlen"] += 1
        return None
    return tlen


def iter_histogram_rows(summary: TlenSummary) -> list[dict[str, str | int]]:
    denominator = summary.used_pairs
    rows: list[dict[str, str | int]] = []
    for tlen, count in sorted(summary.histogram.items()):
        fraction = 0.0 if denominator == 0 else count / denominator
        rows.append(
            {
                "library_id": summary.library_id,
                "bam_id": summary.bam_id,
                "tlen": tlen,
                "count": count,
                "fraction": f"{fraction:.12g}",
            }
        )
    return rows


def write_histogram(path: Path, summary: TlenSummary) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, delimiter="\t", fieldnames=HISTOGRAM_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(iter_histogram_rows(summary))


def write_qc(path: Path, summary: TlenSummary) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, delimiter="\t", fieldnames=QC_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerow(summary.qc_row())


def extract_tlens(*, bam: Path, tlens_out: Path, summary: TlenSummary) -> None:
    if not bam.exists():
        raise FileNotFoundError(f"missing BAM: {bam}")
    tlens_out.parent.mkdir(parents=True, exist_ok=True)
    assert pysam is not None
    with tlens_out.open("w", encoding="utf-8") as tlens_handle:
        with pysam.AlignmentFile(str(bam), "rb") as bam_file:
            for record in bam_file.fetch(until_eof=True):
                tlen = should_use_record(record, summary)
                if tlen is None:
                    continue
                summary.histogram[tlen] += 1
                tlens_handle.write(f"{tlen}\n")


def build_summary(args: argparse.Namespace) -> TlenSummary:
    return TlenSummary(
        library_id=args.library_id,
        bam_id=args.bam_id,
        bam_path=str(args.bam),
        reference_id=args.reference_id,
        reference_path=args.reference_path,
        enzyme_1=args.enzyme_1,
        enzyme_2=args.enzyme_2,
        min_size=parse_int(args.min_size, "min_size"),
        max_size=parse_int(args.max_size, "max_size"),
        score_min=parse_int(args.score_min, "score_min"),
        score_max=parse_int(args.score_max, "score_max"),
        size_model=args.size_model,
        min_mapq=parse_int(args.min_mapq, "min_mapq"),
        exclude_duplicates=parse_bool(args.exclude_duplicates, "exclude_duplicates"),
        max_tlen=parse_int(args.max_tlen, "max_tlen"),
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bam", type=Path, required=True)
    parser.add_argument("--library-id", required=True)
    parser.add_argument("--bam-id", required=True)
    parser.add_argument("--reference-id", required=True)
    parser.add_argument("--reference-path", required=True)
    parser.add_argument("--enzyme-1", required=True)
    parser.add_argument("--enzyme-2", required=True)
    parser.add_argument("--min-size", required=True)
    parser.add_argument("--max-size", required=True)
    parser.add_argument("--score-min", required=True)
    parser.add_argument("--score-max", required=True)
    parser.add_argument("--size-model", required=True)
    parser.add_argument("--min-mapq", required=True)
    parser.add_argument("--exclude-duplicates", required=True)
    parser.add_argument("--max-tlen", required=True)
    parser.add_argument("--tlens-out", type=Path, required=True)
    parser.add_argument("--hist-out", type=Path, required=True)
    parser.add_argument("--qc-out", type=Path, required=True)
    args = parser.parse_args(argv)

    if pysam is None:
        print(
            "error: pysam is required for TLEN extraction; use empirical conda env",
            file=sys.stderr,
        )
        return 2
    try:
        summary = build_summary(args)
        extract_tlens(bam=args.bam, tlens_out=args.tlens_out, summary=summary)
        write_histogram(args.hist_out, summary)
        write_qc(args.qc_out, summary)
        if summary.used_pairs == 0:
            raise ValueError("no usable positive TLEN values after filtering")
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
