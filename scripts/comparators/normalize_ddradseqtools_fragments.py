#!/usr/bin/env python3
"""Normalize DDRADSEQTOOLS rsitesearch.py fragment FASTA to BED-like intervals.

DDRADSEQTOOLS rsitesearch.py emits fragment FASTA records with headers like:

  >fragment: 1 | length: 8 | GC: 0.12 | strand: + | start: 6 | end: 13 | locus: contig

The emitted sequence includes restriction-site residual sequence relative to
radigest's cut-to-cut interval convention. This script converts the FASTA header
coordinates to zero-based half-open cut-coordinate intervals using enzyme motif
lengths and cut offsets on both ends of each fragment.

By default, seqids are canonicalized to the first FASTA defline token, matching
radigest's FASTA record identifier convention.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

OUT_FIELDS = [
    "seqid",
    "start0",
    "end0",
    "length",
    "source_tool",
    "raw_id",
    "strand",
    "raw_start",
    "raw_end",
    "raw_length",
    "sequence_length",
    "left_enzyme",
    "left_trim",
    "right_enzyme",
    "right_trim",
    "raw_locus",
    "seqid_mode",
]

SUMMARY_FIELDS = [
    "tool",
    "input",
    "enzyme1",
    "enzyme2",
    "min_size",
    "max_size",
    "seqid_mode",
    "raw_records",
    "normalized_records",
    "filtered_records",
    "total_cut_bases",
    "notes",
]

# DDRADSEQTOOLS reports FASTA header intervals after applying its own
# enzyme-specific residual convention. For most enzymes in the validation
# matrix, the generic cut-offset model below reproduces radigest's cut-to-cut
# intervals after trimming. SbfI is the exception in the DDRADSEQTOOLS enzyme
# database used by rsitesearch.py: its emitted headers are one base closer to
# the cut coordinate on both sides than predicted by the full recognition motif
# CCTGCAGG with cut_offset=6. The adjustment is deliberately scoped to the
# DDRADSEQTOOLS normalizer and does not alter radigest enzyme definitions.
DDRADSEQTOOLS_TRIM_ADJUSTMENTS = {
    "SbfI": -1,
}


def canonical_seqid(seqid: str, mode: str) -> str:
    seqid = seqid.strip()

    if mode == "unchanged":
        return seqid

    if mode == "first-token":
        return seqid.split()[0]

    if mode == "strip-pipe-description":
        return seqid.split()[0].split("|")[-1]

    raise ValueError(f"unknown seqid mode: {mode}")


def read_enzyme_table(path: Path) -> dict[str, dict[str, int | str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")

        rows: dict[str, dict[str, int | str]] = {}

        for row in reader:
            enzyme = (row.get("enzyme_id") or row.get("enzyme") or "").strip()
            if enzyme == "":
                continue

            motif = (
                row.get("recognition_sequence")
                or row.get("recognition_motif")
                or row.get("motif")
                or row.get("caret_form_motif")
                or row.get("caret_form")
                or ""
            ).strip()

            cut_raw = (row.get("cut_offset") or "").strip()

            if "^" in motif and cut_raw == "":
                cut_offset = motif.index("^")
            elif cut_raw != "":
                cut_offset = int(cut_raw)
            else:
                raise ValueError(
                    f"{path}: enzyme {enzyme} lacks cut_offset and caret motif"
                )

            motif = motif.replace("^", "").upper()
            if motif == "":
                raise ValueError(f"{path}: enzyme {enzyme} has empty motif")

            rows[enzyme] = {
                "motif": motif,
                "motif_len": len(motif),
                "cut_offset": cut_offset,
            }

    return rows


def parse_header(header: str) -> dict[str, str]:
    header = header.strip()
    if header.startswith(">"):
        header = header[1:]

    parts = [part.strip() for part in header.split("|")]
    out: dict[str, str] = {}

    for part in parts:
        if ":" not in part:
            continue

        key, value = part.split(":", 1)
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()
        out[key] = value

    if "fragment" not in out:
        match = re.match(r"fragment:\s*([^|]+)", header)
        if match:
            out["fragment"] = match.group(1).strip()

    for required in ["fragment", "strand", "start", "end", "locus", "length"]:
        if required not in out:
            raise ValueError(f"could not parse {required!r} from header: {header}")

    return out


def read_fasta_records(path: Path) -> list[tuple[dict[str, str], str]]:
    records: list[tuple[dict[str, str], str]] = []
    current_header: dict[str, str] | None = None
    sequence_parts: list[str] = []

    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "":
                continue

            if line.startswith(">"):
                if current_header is not None:
                    records.append((current_header, "".join(sequence_parts)))
                current_header = parse_header(line)
                sequence_parts = []
            else:
                sequence_parts.append(line)

    if current_header is not None:
        records.append((current_header, "".join(sequence_parts)))

    return records


def ddradseqtools_trim_adjustment(enzyme: str) -> int:
    return DDRADSEQTOOLS_TRIM_ADJUSTMENTS.get(enzyme, 0)


def left_trim_for_enzyme(
    enzyme: str,
    enzyme_defs: dict[str, dict[str, int | str]],
) -> int:
    if enzyme not in enzyme_defs:
        raise ValueError(f"enzyme not found in config table: {enzyme}")

    cut_offset = int(enzyme_defs[enzyme]["cut_offset"])

    # DDRADSEQTOOLS header intervals start at the motif-boundary coordinate,
    # expressed as a one-based inclusive coordinate in the FASTA header. Moving
    # from that coordinate to the cut-coordinate interval requires cut_offset -
    # 1 bases on the left side. This is zero for EcoRI/MseI/MspI but non-zero
    # for enzymes such as PstI and SbfI.
    return max(0, cut_offset - 1 + ddradseqtools_trim_adjustment(enzyme))


def right_trim_for_enzyme(
    enzyme: str,
    enzyme_defs: dict[str, dict[str, int | str]],
) -> int:
    if enzyme not in enzyme_defs:
        raise ValueError(f"enzyme not found in config table: {enzyme}")

    motif_len = int(enzyme_defs[enzyme]["motif_len"])
    cut_offset = int(enzyme_defs[enzyme]["cut_offset"])

    # DDRADSEQTOOLS header intervals include right-side recognition-site
    # residuals relative to radigest's cut-to-cut interval. The -1 adjustment
    # accounts for the one-based inclusive header coordinate convention.
    return max(0, motif_len - cut_offset - 1 + ddradseqtools_trim_adjustment(enzyme))


def normalize_record(
    header: dict[str, str],
    sequence: str,
    enzyme1: str,
    enzyme2: str,
    enzyme_defs: dict[str, dict[str, int | str]],
    seqid_mode: str,
) -> dict[str, str]:
    strand = header["strand"]
    raw_start = int(header["start"])
    raw_end = int(header["end"])
    raw_length = int(header["length"])
    raw_locus = header["locus"]
    seqid = canonical_seqid(raw_locus, seqid_mode)

    raw_left0 = min(raw_start, raw_end) - 1
    raw_right0 = max(raw_start, raw_end)

    if strand == "+":
        left_enzyme = enzyme1
        right_enzyme = enzyme2
    elif strand == "-":
        left_enzyme = enzyme2
        right_enzyme = enzyme1
    else:
        raise ValueError(f"unexpected strand value: {strand!r}")

    left_trim = left_trim_for_enzyme(left_enzyme, enzyme_defs)
    right_trim = right_trim_for_enzyme(right_enzyme, enzyme_defs)

    start0 = raw_left0 + left_trim
    end0 = raw_right0 - right_trim
    length = end0 - start0

    if length < 0:
        raise ValueError(
            f"negative normalized length for {raw_locus}: "
            f"start0={start0}, end0={end0}, header={header}"
        )

    raw_id = f"{seqid}:{raw_start}-{raw_end}:fragment{header['fragment']}"

    return {
        "seqid": seqid,
        "start0": str(start0),
        "end0": str(end0),
        "length": str(length),
        "source_tool": "DDRADSEQTOOLS_rsitesearch",
        "raw_id": raw_id,
        "strand": strand,
        "raw_start": str(raw_start),
        "raw_end": str(raw_end),
        "raw_length": str(raw_length),
        "sequence_length": str(len(sequence)),
        "left_enzyme": left_enzyme,
        "left_trim": str(left_trim),
        "right_enzyme": right_enzyme,
        "right_trim": str(right_trim),
        "raw_locus": raw_locus,
        "seqid_mode": seqid_mode,
    }


def write_tsv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(
    path: Path,
    input_path: Path,
    enzyme1: str,
    enzyme2: str,
    min_size: int,
    max_size: int,
    seqid_mode: str,
    raw_records: int,
    normalized_records: int,
    filtered_records: int,
    total_cut_bases: int,
) -> None:
    rows = [
        {
            "tool": "DDRADSEQTOOLS_rsitesearch",
            "input": str(input_path),
            "enzyme1": enzyme1,
            "enzyme2": enzyme2,
            "min_size": str(min_size),
            "max_size": str(max_size),
            "seqid_mode": seqid_mode,
            "raw_records": str(raw_records),
            "normalized_records": str(normalized_records),
            "filtered_records": str(filtered_records),
            "total_cut_bases": str(total_cut_bases),
            "notes": (
                "rsitesearch.py FASTA header coordinates normalized to "
                "zero-based half-open cut intervals using enzyme motif lengths, "
                "cut offsets, and DDRADSEQTOOLS-specific residual adjustments "
                "on fragment ends; seqids canonicalized according to seqid_mode"
            ),
        }
    ]
    write_tsv(path, rows, SUMMARY_FIELDS)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frags", required=True, type=Path)
    parser.add_argument("--enzymes-tsv", required=True, type=Path)
    parser.add_argument("--enzyme1", required=True)
    parser.add_argument("--enzyme2", required=True)
    parser.add_argument("--min", dest="min_size", required=True, type=int)
    parser.add_argument("--max", dest="max_size", required=True, type=int)
    parser.add_argument(
        "--seqid-mode",
        choices=["unchanged", "first-token", "strip-pipe-description"],
        default="first-token",
    )
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        enzyme_defs = read_enzyme_table(args.enzymes_tsv)
        records = read_fasta_records(args.frags)

        normalized: list[dict[str, str]] = []
        filtered: list[dict[str, str]] = []

        for header, sequence in records:
            row = normalize_record(
                header=header,
                sequence=sequence,
                enzyme1=args.enzyme1,
                enzyme2=args.enzyme2,
                enzyme_defs=enzyme_defs,
                seqid_mode=args.seqid_mode,
            )
            normalized.append(row)

            length = int(row["length"])
            if args.min_size <= length <= args.max_size:
                filtered.append(row)

        total_cut_bases = sum(int(row["length"]) for row in filtered)

        write_tsv(args.out, filtered, OUT_FIELDS)
        write_summary(
            path=args.summary,
            input_path=args.frags,
            enzyme1=args.enzyme1,
            enzyme2=args.enzyme2,
            min_size=args.min_size,
            max_size=args.max_size,
            seqid_mode=args.seqid_mode,
            raw_records=len(records),
            normalized_records=len(normalized),
            filtered_records=len(filtered),
            total_cut_bases=total_cut_bases,
        )

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out}", file=sys.stderr)
    print(f"wrote {args.summary}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
