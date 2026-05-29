#!/usr/bin/env python3
"""Summarize plain or gzipped FASTA files.

Output columns:
  file
  records
  total_bases
  non_n_bases
  n_bases
  n_fraction
  min_record_length
  max_record_length

Definition:
  n_bases counts only reference N/n characters.
  non_n_bases is total_bases - n_bases, so other IUPAC symbols are counted
  as non-N bases for denominator purposes.
"""

from __future__ import annotations

import argparse
import gzip
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO


@dataclass
class FastaStats:
    file: str
    records: int = 0
    total_bases: int = 0
    n_bases: int = 0
    min_record_length: int | None = None
    max_record_length: int = 0

    def add_record(self, length: int, n_count: int) -> None:
        self.records += 1
        self.total_bases += length
        self.n_bases += n_count
        if self.min_record_length is None or length < self.min_record_length:
            self.min_record_length = length
        if length > self.max_record_length:
            self.max_record_length = length

    @property
    def non_n_bases(self) -> int:
        return self.total_bases - self.n_bases

    @property
    def n_fraction(self) -> float:
        if self.total_bases == 0:
            return 0.0
        return self.n_bases / self.total_bases

    def as_row(self) -> list[str]:
        return [
            self.file,
            str(self.records),
            str(self.total_bases),
            str(self.non_n_bases),
            str(self.n_bases),
            f"{self.n_fraction:.8f}",
            str(self.min_record_length if self.min_record_length is not None else 0),
            str(self.max_record_length),
        ]


HEADER = [
    "file",
    "records",
    "total_bases",
    "non_n_bases",
    "n_bases",
    "n_fraction",
    "min_record_length",
    "max_record_length",
]


def open_fasta(path: str) -> TextIO:
    if path == "-":
        return sys.stdin
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"FASTA file does not exist: {p}")
    if str(p).endswith(".gz"):
        return gzip.open(p, "rt", encoding="utf-8", errors="replace")
    return p.open("rt", encoding="utf-8", errors="replace")


def summarize_one(path: str) -> FastaStats:
    stats = FastaStats(file=path)

    current_len = 0
    current_n = 0
    seen_header = False

    with open_fasta(path) as handle:
        for line_number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue

            if line.startswith(">"):
                if seen_header:
                    stats.add_record(current_len, current_n)
                seen_header = True
                current_len = 0
                current_n = 0
                continue

            if not seen_header:
                raise ValueError(
                    f"{path}: sequence data encountered before first FASTA header "
                    f"at line {line_number}"
                )

            seq = line.upper()
            current_len += len(seq)
            current_n += seq.count("N")

    if seen_header:
        stats.add_record(current_len, current_n)

    if stats.records == 0:
        raise ValueError(f"{path}: no FASTA records found")

    return stats


def write_rows(rows: list[FastaStats], output: Path | None) -> None:
    if output is None:
        out = sys.stdout
        close = False
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        out = output.open("w", encoding="utf-8")
        close = True

    try:
        print("\t".join(HEADER), file=out)
        for row in rows:
            print("\t".join(row.as_row()), file=out)
    finally:
        if close:
            out.close()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize one or more plain/gzipped FASTA files."
    )
    parser.add_argument(
        "fasta", nargs="+", help="Input FASTA path(s), or '-' for stdin"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output TSV path. Defaults to stdout.",
    )
    args = parser.parse_args(argv)

    rows: list[FastaStats] = []
    had_error = False

    for fasta in args.fasta:
        try:
            rows.append(summarize_one(fasta))
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            had_error = True

    if rows:
        write_rows(rows, args.output)

    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
