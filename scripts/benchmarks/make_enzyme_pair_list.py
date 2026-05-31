#!/usr/bin/env python3
"""Create unordered enzyme-pair lists for screening benchmarks."""

from __future__ import annotations

import argparse
import csv
import itertools
import sys
from pathlib import Path

TSV_FIELDS = ["pair_id", "enzyme1", "enzyme2", "pair_label"]


def read_enzymes(path: Path) -> list[str]:
    enzymes: list[str] = []

    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            enzymes.append(line.split()[0])

    if len(enzymes) < 2:
        raise ValueError(f"{path}: at least two enzymes are required")

    return enzymes


def write_tsv(path: Path, pairs: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=TSV_FIELDS)
        writer.writeheader()

        for i, (enzyme1, enzyme2) in enumerate(pairs, start=1):
            writer.writerow(
                {
                    "pair_id": f"pair{i:04d}",
                    "enzyme1": enzyme1,
                    "enzyme2": enzyme2,
                    "pair_label": f"{enzyme1}+{enzyme2}",
                }
            )


def write_ddgrader(path: Path, pairs: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = ";".join(f"{enzyme1},{enzyme2}" for enzyme1, enzyme2 in pairs)
    path.write_text(text + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enzymes", required=True, type=Path)
    parser.add_argument("--out-tsv", required=True, type=Path)
    parser.add_argument("--out-ddgrader", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        enzymes = read_enzymes(args.enzymes)
        pairs = list(itertools.combinations(enzymes, 2))
        write_tsv(args.out_tsv, pairs)
        write_ddgrader(args.out_ddgrader, pairs)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out_tsv}", file=sys.stderr)
    print(f"wrote {args.out_ddgrader}", file=sys.stderr)
    print(f"enzyme_count={len(enzymes)} pair_count={len(pairs)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
