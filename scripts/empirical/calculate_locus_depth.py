#!/usr/bin/env python3
"""Calculate empirical read-pair depth across predicted RAD loci."""

from __future__ import annotations

import argparse
import bisect
import csv
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

OUTPUT_COLUMNS = [
    "library_id",
    "sample",
    "bam_path",
    "loci",
    "observed_read_pairs_at_loci",
    "mean_pairs_per_locus",
    "filtered_read_pairs",
    "read_pairs_overlapping_loci",
    "read_pairs_outside_loci",
    "assigned_read_pair_fraction",
    "min_mapq",
    "exclude_duplicates",
    "loci_bed",
]


@dataclass(frozen=True)
class IntervalIndex:
    intervals_by_chrom: dict[str, list[tuple[int, int]]]
    starts_by_chrom: dict[str, list[int]]
    ends_by_chrom: dict[str, list[int]]

    @property
    def n_loci(self) -> int:
        return sum(len(items) for items in self.intervals_by_chrom.values())


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
    intervals_by_chrom: dict[str, list[tuple[int, int]]] = {}
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
            intervals_by_chrom.setdefault(chrom, []).append((start, end))

    starts_by_chrom: dict[str, list[int]] = {}
    ends_by_chrom: dict[str, list[int]] = {}
    for chrom, intervals in intervals_by_chrom.items():
        intervals.sort()
        starts_by_chrom[chrom] = [start for start, _end in intervals]
        ends_by_chrom[chrom] = [end for _start, end in intervals]
    return IntervalIndex(
        intervals_by_chrom=intervals_by_chrom,
        starts_by_chrom=starts_by_chrom,
        ends_by_chrom=ends_by_chrom,
    )


def count_overlaps(index: IntervalIndex, chrom: str, start: int, end: int) -> int:
    intervals = index.intervals_by_chrom.get(chrom)
    if not intervals:
        return 0
    starts = index.starts_by_chrom[chrom]
    ends = index.ends_by_chrom[chrom]
    i = bisect.bisect_right(ends, start)
    count = 0
    while i < len(intervals) and starts[i] < end:
        interval_start, interval_end = intervals[i]
        if interval_end > start and interval_start < end:
            count += 1
        i += 1
    return count


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
) -> dict[str, int | float]:
    assert pysam is not None
    filtered_read_pairs = 0
    overlapping_read_pairs = 0
    outside_loci = 0
    locus_overlaps = 0
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
            overlaps = count_overlaps(index, chrom, start, end)
            if overlaps > 0:
                overlapping_read_pairs += 1
                locus_overlaps += overlaps
            else:
                outside_loci += 1
    return {
        "filtered_read_pairs": filtered_read_pairs,
        "read_pairs_overlapping_loci": overlapping_read_pairs,
        "read_pairs_outside_loci": outside_loci,
        "observed_read_pairs_at_loci": locus_overlaps,
    }


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, delimiter="\t", fieldnames=OUTPUT_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bam-manifest", type=Path, required=True)
    parser.add_argument("--loci-bed", type=Path, required=True)
    parser.add_argument("--library-id", required=True)
    parser.add_argument("--min-mapq", type=int, default=0)
    parser.add_argument("--exclude-duplicates", default="true")
    parser.add_argument("--out", type=Path, required=True)
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
        for bam_row in read_bam_manifest(args.bam_manifest):
            if bam_row["library_id"] != args.library_id:
                continue
            bam_path = Path(bam_row["bam_path"])
            stats = summarize_bam(
                bam_path=bam_path,
                index=loci,
                min_mapq=args.min_mapq,
                exclude_duplicates=exclude_duplicates,
            )
            observed = int(stats["observed_read_pairs_at_loci"])
            filtered = int(stats["filtered_read_pairs"])
            rows.append(
                {
                    "library_id": args.library_id,
                    "sample": bam_row["bam_id"],
                    "bam_path": str(bam_path),
                    "loci": str(loci.n_loci),
                    "observed_read_pairs_at_loci": str(observed),
                    "mean_pairs_per_locus": f"{observed / loci.n_loci:.12g}",
                    "filtered_read_pairs": str(filtered),
                    "read_pairs_overlapping_loci": str(
                        stats["read_pairs_overlapping_loci"]
                    ),
                    "read_pairs_outside_loci": str(stats["read_pairs_outside_loci"]),
                    "assigned_read_pair_fraction": (
                        "NA"
                        if filtered == 0
                        else f"{int(stats['read_pairs_overlapping_loci']) / filtered:.12g}"
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
        write_rows(args.out, rows)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
