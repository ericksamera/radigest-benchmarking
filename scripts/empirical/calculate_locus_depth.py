#!/usr/bin/env python3
"""Calculate empirical read-pair depth across predicted RAD loci.

The primary per-sample table is retained for backward compatibility.  When
``--per-locus-out`` is supplied, the script also writes an aggregate per-locus
coverage table that can be used to diagnose locus-level depth dispersion and
coverage-threshold recovery.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import pysam  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - exercised only outside the conda env.
    pysam = None  # type: ignore[assignment]

TRUE_VALUES = {"1", "true", "t", "yes", "y"}
FALSE_VALUES = {"0", "false", "f", "no", "n"}
DEPTH_THRESHOLDS = (1, 3, 5, 10)

OUTPUT_COLUMNS = [
    "library_id",
    "sample",
    "bam_path",
    "loci",
    "observed_read_pairs_at_loci",
    "mean_pairs_per_locus",
    "median_pairs_per_locus",
    "p25_pairs_per_locus",
    "p75_pairs_per_locus",
    "max_pairs_per_locus",
    "loci_ge_1x",
    "fraction_loci_ge_1x",
    "loci_ge_3x",
    "fraction_loci_ge_3x",
    "loci_ge_5x",
    "fraction_loci_ge_5x",
    "loci_ge_10x",
    "fraction_loci_ge_10x",
    "filtered_read_pairs",
    "read_pairs_overlapping_loci",
    "read_pairs_outside_loci",
    "assigned_read_pair_fraction",
    "min_mapq",
    "exclude_duplicates",
    "loci_bed",
]

PER_LOCUS_COLUMNS = [
    "library_id",
    "locus_index",
    "locus_id",
    "seqid",
    "start0",
    "end0",
    "length",
    "observed_samples",
    "total_read_pairs_at_locus",
    "mean_pairs_per_sample",
]


@dataclass(frozen=True)
class Locus:
    locus_id: str
    seqid: str
    start0: int
    end0: int

    @property
    def length(self) -> int:
        return self.end0 - self.start0


@dataclass(frozen=True)
class IntervalIndex:
    loci: list[Locus]
    intervals_by_chrom: dict[str, list[tuple[int, int, int]]]
    starts_by_chrom: dict[str, list[int]]
    ends_by_chrom: dict[str, list[int]]

    @property
    def n_loci(self) -> int:
        return len(self.loci)


def parse_bool(value: str, label: str) -> bool:
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"{label} must be true or false, got {value!r}")


def read_bam_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        required = {"library_id", "bam_id", "bam_path"}
        missing = sorted(required - set(reader.fieldnames))
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(missing)}")
        return [
            {key: (value or "").strip() for key, value in row.items() if key}
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]


def read_loci_bed(path: Path) -> IntervalIndex:
    loci: list[Locus] = []
    intervals_by_chrom: dict[str, list[tuple[int, int, int]]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) < 3:
                raise ValueError(
                    f"{path}: row {row_number}: BED requires at least 3 columns"
                )
            chrom = fields[0]
            start = int(fields[1])
            end = int(fields[2])
            if end < start:
                raise ValueError(f"{path}: row {row_number}: end before start")
            if end == start:
                continue
            locus_index = len(loci)
            locus_id = (
                fields[3]
                if len(fields) > 3 and fields[3]
                else f"locus_{locus_index + 1}"
            )
            loci.append(Locus(locus_id=locus_id, seqid=chrom, start0=start, end0=end))
            intervals_by_chrom.setdefault(chrom, []).append((start, end, locus_index))

    starts_by_chrom: dict[str, list[int]] = {}
    ends_by_chrom: dict[str, list[int]] = {}
    for chrom, intervals in intervals_by_chrom.items():
        intervals.sort(key=lambda item: (item[0], item[1], item[2]))
        starts_by_chrom[chrom] = [start for start, _end, _idx in intervals]
        ends_by_chrom[chrom] = [end for _start, end, _idx in intervals]
    return IntervalIndex(
        loci=loci,
        intervals_by_chrom=intervals_by_chrom,
        starts_by_chrom=starts_by_chrom,
        ends_by_chrom=ends_by_chrom,
    )


def overlapping_locus_indices(
    index: IntervalIndex, chrom: str, start: int, end: int
) -> list[int]:
    intervals = index.intervals_by_chrom.get(chrom)
    if not intervals:
        return []
    starts = index.starts_by_chrom[chrom]
    ends = index.ends_by_chrom[chrom]

    # Predicted restriction-fragment loci are non-overlapping in normal radigest
    # output.  In that setting, starts and ends are both monotonic after sorting
    # by start, so this skips intervals ending before the query.  The explicit
    # overlap check below preserves correctness if a future BED contains adjacent
    # intervals or rare overlaps.
    i = bisect.bisect_right(ends, start)
    hits: list[int] = []
    while i < len(intervals) and starts[i] < end:
        interval_start, interval_end, locus_index = intervals[i]
        if interval_end > start and interval_start < end:
            hits.append(locus_index)
        i += 1
    return hits


def usable_positive_template(
    record: Any, *, min_mapq: int, exclude_duplicates: bool
) -> bool:
    if record.is_secondary or record.is_supplementary or record.is_qcfail:
        return False
    if exclude_duplicates and record.is_duplicate:
        return False
    if not record.is_paired or not record.is_proper_pair:
        return False
    if record.is_unmapped or record.mate_is_unmapped:
        return False
    if record.reference_id < 0 or record.next_reference_id < 0:
        return False
    if record.reference_id != record.next_reference_id:
        return False
    if record.mapping_quality < min_mapq:
        return False
    return int(record.template_length) > 0


def summarize_bam(
    *,
    bam_path: Path,
    index: IntervalIndex,
    min_mapq: int,
    exclude_duplicates: bool,
) -> tuple[dict[str, int | float], list[int]]:
    assert pysam is not None
    filtered_read_pairs = 0
    overlapping_read_pairs = 0
    outside_loci = 0
    locus_overlaps = 0
    locus_counts = [0] * index.n_loci
    with pysam.AlignmentFile(str(bam_path), "rb") as bam_file:
        for record in bam_file.fetch(until_eof=True):
            if not usable_positive_template(
                record, min_mapq=min_mapq, exclude_duplicates=exclude_duplicates
            ):
                continue
            filtered_read_pairs += 1
            chrom = bam_file.get_reference_name(record.reference_id)
            start = int(record.reference_start)
            end = start + int(record.template_length)
            hits = overlapping_locus_indices(index, chrom, start, end)
            if hits:
                overlapping_read_pairs += 1
                locus_overlaps += len(hits)
                for locus_index in hits:
                    locus_counts[locus_index] += 1
            else:
                outside_loci += 1
    return (
        {
            "filtered_read_pairs": filtered_read_pairs,
            "read_pairs_overlapping_loci": overlapping_read_pairs,
            "read_pairs_outside_loci": outside_loci,
            "observed_read_pairs_at_loci": locus_overlaps,
        },
        locus_counts,
    )


def percentile(sorted_values: list[int], q: float) -> float:
    if not sorted_values:
        return 0.0
    if q <= 0:
        return float(sorted_values[0])
    if q >= 1:
        return float(sorted_values[-1])
    pos = q * (len(sorted_values) - 1)
    lower = int(pos)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = pos - lower
    return (
        float(sorted_values[lower]) * (1.0 - fraction)
        + float(sorted_values[upper]) * fraction
    )


def fmt_float(value: float) -> str:
    return f"{value:.12g}"


def locus_count_stats(locus_counts: list[int]) -> dict[str, str]:
    sorted_counts = sorted(locus_counts)
    n_loci = len(sorted_counts)
    if n_loci == 0:
        raise ValueError("locus count vector is empty")
    out = {
        "median_pairs_per_locus": fmt_float(float(statistics.median(sorted_counts))),
        "p25_pairs_per_locus": fmt_float(percentile(sorted_counts, 0.25)),
        "p75_pairs_per_locus": fmt_float(percentile(sorted_counts, 0.75)),
        "max_pairs_per_locus": str(sorted_counts[-1]),
    }
    for threshold in DEPTH_THRESHOLDS:
        count = sum(1 for value in sorted_counts if value >= threshold)
        out[f"loci_ge_{threshold}x"] = str(count)
        out[f"fraction_loci_ge_{threshold}x"] = fmt_float(count / n_loci)
    return out


def write_rows(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, delimiter="\t", fieldnames=columns, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def build_per_locus_rows(
    *,
    library_id: str,
    index: IntervalIndex,
    aggregate_counts: list[int],
    observed_samples: int,
) -> list[dict[str, str]]:
    if observed_samples <= 0:
        raise ValueError("observed_samples must be positive for per-locus output")
    rows: list[dict[str, str]] = []
    for i, locus in enumerate(index.loci):
        total = aggregate_counts[i]
        rows.append(
            {
                "library_id": library_id,
                "locus_index": str(i + 1),
                "locus_id": locus.locus_id,
                "seqid": locus.seqid,
                "start0": str(locus.start0),
                "end0": str(locus.end0),
                "length": str(locus.length),
                "observed_samples": str(observed_samples),
                "total_read_pairs_at_locus": str(total),
                "mean_pairs_per_sample": fmt_float(total / observed_samples),
            }
        )
    return rows


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bam-manifest", type=Path, required=True)
    parser.add_argument("--loci-bed", type=Path, required=True)
    parser.add_argument("--library-id", required=True)
    parser.add_argument("--min-mapq", type=int, default=0)
    parser.add_argument("--exclude-duplicates", default="true")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--per-locus-out", type=Path)
    args = parser.parse_args(argv)

    if pysam is None:
        print("error: pysam is required; use empirical conda env", file=sys.stderr)
        return 2
    try:
        exclude_duplicates = parse_bool(args.exclude_duplicates, "exclude_duplicates")
        loci = read_loci_bed(args.loci_bed)
        if loci.n_loci == 0:
            raise ValueError(f"{args.loci_bed}: no loci after filtering")
        rows: list[dict[str, str]] = []
        aggregate_locus_counts = [0] * loci.n_loci
        observed_samples = 0
        for bam_row in read_bam_manifest(args.bam_manifest):
            if bam_row["library_id"] != args.library_id:
                continue
            bam_path = Path(bam_row["bam_path"])
            stats, locus_counts = summarize_bam(
                bam_path=bam_path,
                index=loci,
                min_mapq=args.min_mapq,
                exclude_duplicates=exclude_duplicates,
            )
            observed_samples += 1
            for locus_index, count in enumerate(locus_counts):
                aggregate_locus_counts[locus_index] += count
            observed = int(stats["observed_read_pairs_at_loci"])
            filtered = int(stats["filtered_read_pairs"])
            per_locus_stats = locus_count_stats(locus_counts)
            rows.append(
                {
                    "library_id": args.library_id,
                    "sample": bam_row["bam_id"],
                    "bam_path": str(bam_path),
                    "loci": str(loci.n_loci),
                    "observed_read_pairs_at_loci": str(observed),
                    "mean_pairs_per_locus": fmt_float(observed / loci.n_loci),
                    **per_locus_stats,
                    "filtered_read_pairs": str(filtered),
                    "read_pairs_overlapping_loci": str(
                        stats["read_pairs_overlapping_loci"]
                    ),
                    "read_pairs_outside_loci": str(stats["read_pairs_outside_loci"]),
                    "assigned_read_pair_fraction": (
                        "NA"
                        if filtered == 0
                        else fmt_float(
                            int(stats["read_pairs_overlapping_loci"]) / filtered
                        )
                    ),
                    "min_mapq": str(args.min_mapq),
                    "exclude_duplicates": str(exclude_duplicates).lower(),
                    "loci_bed": str(args.loci_bed),
                }
            )
        if not rows:
            raise ValueError(
                f"{args.bam_manifest}: no BAM rows for library_id={args.library_id!r}"
            )
        write_rows(args.out, rows, OUTPUT_COLUMNS)
        if args.per_locus_out is not None:
            write_rows(
                args.per_locus_out,
                build_per_locus_rows(
                    library_id=args.library_id,
                    index=loci,
                    aggregate_counts=aggregate_locus_counts,
                    observed_samples=observed_samples,
                ),
                PER_LOCUS_COLUMNS,
            )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
