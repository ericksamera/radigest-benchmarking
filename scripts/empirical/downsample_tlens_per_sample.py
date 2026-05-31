#!/usr/bin/env python3
"""Deterministically downsample TLEN files per sample using reservoir sampling."""

from __future__ import annotations

import argparse
import csv
import glob
import random
import sys
from pathlib import Path


def reservoir_sample(path: Path, n: int, rng: random.Random) -> tuple[list[str], int]:
    reservoir: list[str] = []
    seen = 0

    with path.open() as handle:
        for line in handle:
            value = line.strip()
            if value == "":
                continue

            try:
                ivalue = int(value)
            except ValueError:
                continue

            if ivalue <= 0:
                continue

            seen += 1

            if len(reservoir) < n:
                reservoir.append(str(ivalue))
            else:
                j = rng.randint(1, seen)
                if j <= n:
                    reservoir[j - 1] = str(ivalue)

    return reservoir, seen


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-glob", required=True)
    parser.add_argument("--max-per-sample", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        files = sorted(Path(path) for path in glob.glob(args.input_glob))

        if not files:
            raise ValueError(f"no files matched {args.input_glob!r}")

        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.summary.parent.mkdir(parents=True, exist_ok=True)

        rows: list[dict[str, str]] = []

        with args.out.open("w") as out:
            for index, path in enumerate(files):
                rng = random.Random(args.seed + index)
                sample, seen = reservoir_sample(path, args.max_per_sample, rng)

                for value in sample:
                    out.write(value)
                    out.write("\n")

                rows.append(
                    {
                        "file": str(path),
                        "sample": path.stem.replace(".tlens", ""),
                        "input_tlens": str(seen),
                        "output_tlens": str(len(sample)),
                    }
                )

        with args.summary.open("w", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                delimiter="\t",
                fieldnames=["file", "sample", "input_tlens", "output_tlens"],
            )
            writer.writeheader()
            writer.writerows(rows)

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out}", file=sys.stderr)
    print(f"wrote {args.summary}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
