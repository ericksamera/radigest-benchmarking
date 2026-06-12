#!/usr/bin/env python3
"""Convert the public Illumina BovineHD annotation CSV into BED.

The BovineHD support package is distributed as a zip file containing an
Illumina annotation/manifest table. This script extracts SNP name, chromosome
and 1-based coordinate columns, maps chromosome labels to the sequence IDs used
by the supplied reference FASTA when possible, and writes BED3+1 intervals for
use as a radigest target panel.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

NA_CHROM = {"", "0", "NA", "N/A", "NONE", "NULL", ".", "UN", "UNKNOWN"}
CHR_ALIASES = {
    "M": "MT",
    "MITO": "MT",
    "MITOCHONDRIA": "MT",
    "MITOCHONDRION": "MT",
    "CHRM": "MT",
    "CHRMT": "MT",
    "CHRMITO": "MT",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(2)


def normalize_chrom(value: str) -> str:
    text = (value or "").strip().strip('"')
    text = re.sub(r"^chr", "", text, flags=re.IGNORECASE)
    text = text.upper() if text.upper() in {"X", "Y", "MT", "M"} else text
    return CHR_ALIASES.get(text.upper(), text)


def first_token(header_line: str) -> str:
    return header_line[1:].split()[0]


def fasta_chrom_map(path: Path) -> dict[str, str]:
    """Map simple chromosome labels to FASTA record IDs.

    NCBI FASTA records usually have accession IDs as the first token but include
    text such as "chromosome 1" in the description. Illumina annotation files
    usually use simple chromosome labels. This mapper makes BED seqids match the
    exact IDs emitted by radigest from the FASTA.
    """
    mapping: dict[str, str] = {}
    seen_labels: Counter[str] = Counter()
    with path.open("rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.startswith(">"):
                continue
            seqid = first_token(line)
            text = line.strip()
            mapping.setdefault(seqid, seqid)
            mapping.setdefault(normalize_chrom(seqid), seqid)

            match = re.search(r"\bchromosome\s+([^,\s]+)", text, flags=re.IGNORECASE)
            if match:
                label = normalize_chrom(match.group(1))
                seen_labels[label] += 1
                mapping.setdefault(label, seqid)
                continue
            if re.search(r"\bmitochondr", text, flags=re.IGNORECASE):
                label = "MT"
                seen_labels[label] += 1
                mapping.setdefault(label, seqid)

    ambiguous = [label for label, count in seen_labels.items() if count > 1]
    if ambiguous:
        print(
            "warning: ambiguous chromosome labels in FASTA descriptions: "
            + ", ".join(sorted(ambiguous)),
            file=sys.stderr,
        )
    return mapping


def choose_member(zf: zipfile.ZipFile, requested: str | None) -> str:
    names = [name for name in zf.namelist() if not name.endswith("/")]
    if requested:
        matches = [
            name for name in names if Path(name).name == requested or name == requested
        ]
        if not matches:
            fail(f"requested zip member not found: {requested}")
        return matches[0]
    csv_like = [
        name
        for name in names
        if Path(name).suffix.lower() in {".csv", ".txt"}
        and "annotation" in name.lower()
    ]
    if not csv_like:
        csv_like = [
            name for name in names if Path(name).suffix.lower() in {".csv", ".txt"}
        ]
    if not csv_like:
        fail("zip contains no CSV/TXT member")
    return max(csv_like, key=lambda name: zf.getinfo(name).file_size)


def iter_candidate_rows(zf: zipfile.ZipFile, member: str):
    """Yield rows from an Illumina annotation/manifest CSV.

    Handles both sectioned Infinium CSVs with an [Assay] block and regular CSV
    files where the header appears directly.
    """
    with zf.open(member) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
        lines = text.readlines()

    assay_start = None
    for i, line in enumerate(lines):
        if line.strip().lower() == "[assay]":
            assay_start = i + 1
            break
    if assay_start is not None:
        payload = "".join(lines[assay_start:])
        kept = []
        for line in payload.splitlines(True):
            if line.strip().startswith("[") and line.strip().endswith("]"):
                break
            kept.append(line)
        payload = "".join(kept)
    else:
        header_idx = None
        for i, line in enumerate(lines):
            lowered = line.lower()
            if ("mapinfo" in lowered or "position" in lowered) and (
                "chr" in lowered or "chrom" in lowered
            ):
                header_idx = i
                break
        if header_idx is None:
            fail(
                "could not locate an assay/annotation header with Chr and "
                "MapInfo/Position columns"
            )
        payload = "".join(lines[header_idx:])

    reader = csv.DictReader(io.StringIO(payload))
    if reader.fieldnames is None:
        fail(f"could not parse CSV header in {member}")
    for row in reader:
        if not row or not any((value or "").strip() for value in row.values()):
            continue
        yield row


def get_column(row: dict[str, str], aliases: list[str]) -> str | None:
    by_norm = {re.sub(r"[^a-z0-9]", "", key.lower()): key for key in row}
    for alias in aliases:
        key = by_norm.get(re.sub(r"[^a-z0-9]", "", alias.lower()))
        if key is not None:
            return row.get(key)
    return None


def evenly_spaced_subset(
    rows: list[tuple[str, int, int, str]], max_targets: int
) -> list[tuple[str, int, int, str]]:
    if max_targets <= 0 or len(rows) <= max_targets:
        return rows
    if max_targets == 1:
        return [rows[len(rows) // 2]]
    n = len(rows)
    selected = []
    used: set[int] = set()
    for i in range(max_targets):
        idx = round(i * (n - 1) / (max_targets - 1))
        if idx in used:
            continue
        used.add(idx)
        selected.append(rows[idx])
    return selected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--zip", required=True, type=Path, help="Illumina BovineHD annotation zip"
    )
    parser.add_argument(
        "--member", default=None, help="optional CSV member name inside the zip"
    )
    parser.add_argument(
        "--reference", required=True, type=Path, help="reference FASTA used by radigest"
    )
    parser.add_argument("--bed", required=True, type=Path, help="output BED file")
    parser.add_argument(
        "--summary", required=True, type=Path, help="output conversion summary TSV"
    )
    parser.add_argument(
        "--max-targets",
        type=int,
        default=0,
        help=(
            "optional deterministic cap on emitted targets after filtering; "
            "0 keeps all. Capped output is sampled evenly across sorted genomic "
            "coordinates rather than taking the first chromosome only."
        ),
    )
    args = parser.parse_args(argv)

    if not args.zip.is_file():
        fail(f"missing annotation zip: {args.zip}")
    if not args.reference.is_file():
        fail(f"missing reference FASTA: {args.reference}")
    if args.max_targets < 0:
        fail("--max-targets must be >= 0")

    chrom_map = fasta_chrom_map(args.reference)
    skipped = Counter()
    builds = Counter()
    raw_chroms = Counter()
    unmapped_chroms = Counter()
    rows_out: list[tuple[str, int, int, str]] = []
    selected_member = "NA"

    with zipfile.ZipFile(args.zip) as zf:
        selected_member = choose_member(zf, args.member)
        for row_index, row in enumerate(
            iter_candidate_rows(zf, selected_member), start=1
        ):
            name = (
                get_column(row, ["Name", "IlmnID", "SNP Name", "SNP", "ID"])
                or f"BovineHD_{row_index}"
            )
            chrom_raw = get_column(row, ["Chr", "Chromosome", "Chrom", "CHROM"])
            pos_raw = get_column(
                row, ["MapInfo", "Position", "Pos", "Coordinate", "Physical Position"]
            )
            build = get_column(row, ["GenomeBuild", "Genome Build", "Build"])
            if build:
                builds[build.strip()] += 1
            chrom = normalize_chrom(chrom_raw or "")
            if chrom.upper() in NA_CHROM:
                skipped["missing_chrom"] += 1
                continue
            raw_chroms[chrom] += 1
            try:
                pos = int(float((pos_raw or "").strip()))
            except ValueError:
                skipped["missing_or_bad_position"] += 1
                continue
            if pos <= 0:
                skipped["nonpositive_position"] += 1
                continue
            seqid = chrom_map.get(chrom) or chrom_map.get(normalize_chrom(chrom))
            if seqid is None:
                unmapped_chroms[chrom] += 1
                skipped["unmapped_chrom"] += 1
                continue
            rows_out.append(
                (seqid, pos - 1, pos, str(name).strip() or f"BovineHD_{row_index}")
            )

    rows_out.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    targets_after_filtering = len(rows_out)
    rows_out = evenly_spaced_subset(rows_out, args.max_targets)
    emitted = len(rows_out)
    if emitted == 0:
        fail("no BED intervals were emitted; check genome build and chromosome naming")

    args.bed.parent.mkdir(parents=True, exist_ok=True)
    with args.bed.open("w", encoding="utf-8") as out:
        for seqid, start, end, name in rows_out:
            out.write(f"{seqid}\t{start}\t{end}\t{name}\n")

    args.summary.parent.mkdir(parents=True, exist_ok=True)
    with args.summary.open("w", encoding="utf-8") as out:
        out.write("metric\tvalue\n")
        out.write(f"annotation_zip\t{args.zip}\n")
        out.write(f"annotation_member\t{selected_member}\n")
        out.write(f"reference\t{args.reference}\n")
        out.write(f"output_bed\t{args.bed}\n")
        out.write(f"targets_after_filtering\t{targets_after_filtering}\n")
        out.write(f"targets_emitted\t{emitted}\n")
        out.write(f"max_targets\t{args.max_targets}\n")
        out.write(
            "genome_builds_observed\t"
            + ";".join(f"{k}:{v}" for k, v in builds.most_common())
            + "\n"
        )
        out.write(
            "raw_chromosomes_observed\t"
            + ";".join(f"{k}:{v}" for k, v in raw_chroms.most_common(20))
            + "\n"
        )
        out.write(
            "unmapped_chromosomes\t"
            + ";".join(f"{k}:{v}" for k, v in unmapped_chroms.most_common())
            + "\n"
        )
        for key, value in sorted(skipped.items()):
            out.write(f"skipped_{key}\t{value}\n")

    print(f"wrote {emitted} BovineHD SNP intervals to {args.bed}")
    print(f"wrote conversion summary to {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
