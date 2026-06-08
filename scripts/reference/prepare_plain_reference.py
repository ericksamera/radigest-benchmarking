#!/usr/bin/env python3
"""Create an uncompressed FASTA from a gzipped reference FASTA."""

from __future__ import annotations

import argparse
import gzip
import shutil
import sys
from pathlib import Path


def prepare_plain(source: Path, dest: Path, force: bool = False) -> None:
    if not source.is_file() or source.stat().st_size == 0:
        raise FileNotFoundError(f"source FASTA does not exist or is empty: {source}")
    if dest.exists() and not force:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    if source.name.endswith(".gz"):
        with gzip.open(source, "rb") as inp, tmp.open("wb") as out:
            shutil.copyfileobj(inp, out)
    else:
        shutil.copyfile(source, tmp)
    tmp.replace(dest)


def first_nonempty_line(path: Path) -> str:
    with path.open("rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.strip():
                return line.rstrip("\n")
    return ""


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--dest", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    try:
        prepare_plain(args.source, args.dest, force=args.force)
        first = first_nonempty_line(args.dest)
        if not first.startswith(">"):
            raise ValueError(f"destination is not FASTA: {args.dest}")
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
