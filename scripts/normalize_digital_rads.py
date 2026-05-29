#!/usr/bin/env python3
"""Normalize Digital_RADs.py two-enzyme output to cut-coordinate intervals.

Digital_RADs.py reports motif-bounded RAD markers. This script converts those
rows to radigest-compatible zero-based half-open cut-coordinate intervals using
enzyme motifs and cut offsets from config/enzymes.tsv.

Digital_RADs.py two-enzyme output columns:
  contig  position  length  direction  sequence  GC

For direction 1:
  enzyme1 is upstream of enzyme2.
  position is 1-based motif start of enzyme1.
  length is motif1-start to motif2-end.

For direction -1:
  enzyme2 is upstream of enzyme1.
  position is the downstream enzyme1 motif end coordinate as printed by
  Digital_RADs.py.
  length is motif2-start to motif1-end.

Output:
  seqid start0 end0 length source_tool raw_id direction digital_position
  digital_length digital_sequence digital_gc motif_start0 motif_end0
  enzyme_left enzyme_right
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

OUTPUT_COLUMNS = [
    "seqid",
    "start0",
    "end0",
    "length",
    "source_tool",
    "raw_id",
    "direction",
    "digital_position",
    "digital_length",
    "digital_sequence",
    "digital_gc",
    "motif_start0",
    "motif_end0",
    "enzyme_left",
    "enzyme_right",
]


SUMMARY_COLUMNS = [
    "tool",
    "input",
    "enzyme1",
    "enzyme2",
    "min_size",
    "max_size",
    "raw_rows",
    "normalized_rows",
    "filtered_rows",
    "total_cut_bases",
    "notes",
]


@dataclass(frozen=True)
class Enzyme:
    name: str
    motif: str
    cut_offset: int

    @property
    def motif_len(self) -> int:
        return len(self.motif)


def read_enzymes(path: Path) -> dict[str, Enzyme]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        out: dict[str, Enzyme] = {}
        for row in reader:
            name = row.get("enzyme", "")
            motif = (
                (row.get("recognition_motif") or row.get("motif") or "")
                .replace("^", "")
                .upper()
            )
            cut_raw = row.get("cut_offset", "")
            if not name or not motif or cut_raw == "":
                continue
            if any(ch not in "ACGT" for ch in motif):
                # Digital_RADs itself does not implement IUPAC motif expansion.
                continue
            out[name] = Enzyme(name=name, motif=motif, cut_offset=int(cut_raw))
    return out


def normalize_row(
    row: dict[str, str],
    row_number: int,
    enzyme1: Enzyme,
    enzyme2: Enzyme,
) -> dict[str, str]:
    seqid = row.get("contig", "")
    if not seqid:
        raise ValueError(f"row {row_number}: missing contig")

    position = int(row["position"])
    digital_length = int(row["length"])
    direction = int(row["direction"])

    if digital_length < 0:
        raise ValueError(f"row {row_number}: negative digital length")

    if direction == 1:
        # motif interval: enzyme1 motif start -> enzyme2 motif end
        motif_start0 = position - 1
        motif_end0 = motif_start0 + digital_length

        enzyme1_motif_start0 = motif_start0
        enzyme2_motif_start0 = motif_end0 - enzyme2.motif_len

        start0 = enzyme1_motif_start0 + enzyme1.cut_offset
        end0 = enzyme2_motif_start0 + enzyme2.cut_offset
        enzyme_left = enzyme1.name
        enzyme_right = enzyme2.name

    elif direction == -1:
        # motif interval: enzyme2 motif start -> enzyme1 motif end
        motif_end0 = position
        motif_start0 = motif_end0 - digital_length

        enzyme2_motif_start0 = motif_start0
        enzyme1_motif_start0 = motif_end0 - enzyme1.motif_len

        start0 = enzyme2_motif_start0 + enzyme2.cut_offset
        end0 = enzyme1_motif_start0 + enzyme1.cut_offset
        enzyme_left = enzyme2.name
        enzyme_right = enzyme1.name

    else:
        raise ValueError(f"row {row_number}: unsupported direction {direction}")

    if start0 < 0:
        raise ValueError(f"row {row_number}: normalized start is negative")
    if end0 < start0:
        raise ValueError(f"row {row_number}: normalized end < start")

    length = end0 - start0
    raw_id = f"{seqid}:{start0}-{end0}:row{row_number}"

    return {
        "seqid": seqid,
        "start0": str(start0),
        "end0": str(end0),
        "length": str(length),
        "source_tool": "Digital_RADs.py",
        "raw_id": raw_id,
        "direction": str(direction),
        "digital_position": str(position),
        "digital_length": str(digital_length),
        "digital_sequence": row.get("sequence", ""),
        "digital_gc": row.get("GC", ""),
        "motif_start0": str(motif_start0),
        "motif_end0": str(motif_end0),
        "enzyme_left": enzyme_left,
        "enzyme_right": enzyme_right,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize Digital_RADs.py two-enzyme output "
            "to cut-coordinate intervals."
        )
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--enzymes-tsv", default="config/enzymes.tsv", type=Path)
    parser.add_argument("--enzyme1", required=True)
    parser.add_argument("--enzyme2", required=True)
    parser.add_argument("--min", dest="min_size", required=True, type=int)
    parser.add_argument("--max", dest="max_size", required=True, type=int)
    args = parser.parse_args(argv)

    if args.min_size > args.max_size:
        print("error: --min must be <= --max", file=sys.stderr)
        return 2

    enzymes = read_enzymes(args.enzymes_tsv)
    if args.enzyme1 not in enzymes:
        print(
            f"error: enzyme1 not available for Digital normalization: {args.enzyme1}",
            file=sys.stderr,
        )
        return 2
    if args.enzyme2 not in enzymes:
        print(
            f"error: enzyme2 not available for Digital normalization: {args.enzyme2}",
            file=sys.stderr,
        )
        return 2

    enzyme1 = enzymes[args.enzyme1]
    enzyme2 = enzymes[args.enzyme2]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)

    raw_rows = 0
    normalized_rows = 0
    filtered_rows = 0
    total_cut_bases = 0

    with (
        args.input.open(newline="", encoding="utf-8") as in_handle,
        args.output.open("w", newline="", encoding="utf-8") as out_handle,
    ):
        reader = csv.DictReader(in_handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{args.input}: missing header")

        writer = csv.DictWriter(out_handle, delimiter="\t", fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()

        for row_number, row in enumerate(reader, start=2):
            raw_rows += 1
            normalized = normalize_row(row, row_number, enzyme1, enzyme2)
            normalized_rows += 1

            length = int(normalized["length"])
            if length < args.min_size or length > args.max_size:
                filtered_rows += 1
                continue

            total_cut_bases += length
            writer.writerow(normalized)

    with args.summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerow(
            {
                "tool": "Digital_RADs.py",
                "input": str(args.input),
                "enzyme1": args.enzyme1,
                "enzyme2": args.enzyme2,
                "min_size": args.min_size,
                "max_size": args.max_size,
                "raw_rows": raw_rows,
                "normalized_rows": normalized_rows,
                "filtered_rows": filtered_rows,
                "total_cut_bases": total_cut_bases,
                "notes": (
                    "Digital motif-bounded intervals converted to cut-to-cut "
                    "intervals using config/enzymes.tsv"
                ),
            }
        )

    print(
        f"normalized {normalized_rows} Digital_RADs.py row(s); wrote "
        f"{normalized_rows - filtered_rows} filtered cut-coordinate interval(s)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
