#!/usr/bin/env python3
"""Summarize DDRADSEQTOOLS rsitesearch.py fragment FASTA output."""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

FIELDS = [
    "tool",
    "reference",
    "enzyme1",
    "enzyme2",
    "min_size",
    "max_size",
    "fragments",
    "total_bases",
    "min_fragment_length",
    "max_fragment_length",
    "mean_fragment_length",
    "median_fragment_length",
    "frags_file",
    "stats_file",
    "version_log",
    "notes",
]


def fasta_lengths(path: Path) -> list[int]:
    if not path.exists():
        raise FileNotFoundError(f"missing fragment FASTA: {path}")

    lengths: list[int] = []
    current = 0
    seen = False

    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if seen:
                    lengths.append(current)
                seen = True
                current = 0
            else:
                current += len(line)

    if seen:
        lengths.append(current)

    return lengths


def fmt_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"


def write_summary(
    out: Path,
    lengths: list[int],
    args: argparse.Namespace,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)

    if lengths:
        min_len = str(min(lengths))
        max_len = str(max(lengths))
        mean_len = fmt_float(float(statistics.mean(lengths)))
        median_len = fmt_float(float(statistics.median(lengths)))
    else:
        min_len = ""
        max_len = ""
        mean_len = ""
        median_len = ""

    row = {
        "tool": "DDRADSEQTOOLS_rsitesearch",
        "reference": str(args.reference),
        "enzyme1": args.enzyme1,
        "enzyme2": args.enzyme2,
        "min_size": str(args.min_size),
        "max_size": str(args.max_size),
        "fragments": str(len(lengths)),
        "total_bases": str(sum(lengths)),
        "min_fragment_length": min_len,
        "max_fragment_length": max_len,
        "mean_fragment_length": mean_len,
        "median_fragment_length": median_len,
        "frags_file": str(args.frags),
        "stats_file": str(args.stats),
        "version_log": str(args.version_log),
        "notes": (
            "DDRADSEQTOOLS rsitesearch.py fragment FASTA summary. "
            "Compare as digest-level fragment/locus output; not a read-simulation task."
        ),
    }

    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(row)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frags", required=True, type=Path)
    parser.add_argument("--stats", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--enzyme1", required=True)
    parser.add_argument("--enzyme2", required=True)
    parser.add_argument("--min", dest="min_size", required=True, type=int)
    parser.add_argument("--max", dest="max_size", required=True, type=int)
    parser.add_argument("--version-log", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        lengths = fasta_lengths(args.frags)
        write_summary(args.out, lengths, args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
