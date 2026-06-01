#!/usr/bin/env python3
"""Write SHA256 and basic FASTA statistics for Stage 3 references."""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

REQUIRED_COLUMNS = [
    "reference_id",
    "display_name",
    "accession",
    "source_type",
    "output_gzip",
    "output_plain",
    "required_for_nonempirical",
    "notes",
]

OUTPUT_COLUMNS = [
    "reference_id",
    "display_name",
    "accession",
    "source_type",
    "artifact_kind",
    "path",
    "sha256",
    "size_bytes",
    "records",
    "total_bases",
    "status",
]


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames
        if fieldnames is None:
            raise ValueError(f"{path}: missing header")
        missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(missing)}")
        rows = []
        for row in reader:
            if not any((value or "").strip() for value in row.values()):
                continue
            rows.append({key: (row.get(key) or "").strip() for key in REQUIRED_COLUMNS})
        if not rows:
            raise ValueError(f"{path}: no reference rows")
        return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fasta_stats(path: Path) -> tuple[int, int]:
    records = 0
    total_bases = 0
    with path.open("rt", encoding="utf-8", errors="replace") as handle:
        seen_header = False
        for line_number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                records += 1
                seen_header = True
                continue
            if not seen_header:
                raise ValueError(
                    f"{path}: sequence before first FASTA header at line {line_number}"
                )
            total_bases += len(line)
    if records == 0:
        raise ValueError(f"{path}: no FASTA records")
    return records, total_bases


def artifact_row(row: dict[str, str], kind: str, path_raw: str) -> dict[str, str]:
    path = Path(path_raw)
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(
            f"missing or empty {kind} artifact for {row['reference_id']}: {path}"
        )

    records = "NA"
    total_bases = "NA"
    if kind == "plain_fasta":
        rec_count, base_count = fasta_stats(path)
        records = str(rec_count)
        total_bases = str(base_count)

    return {
        "reference_id": row["reference_id"],
        "display_name": row["display_name"],
        "accession": row["accession"],
        "source_type": row["source_type"],
        "artifact_kind": kind,
        "path": str(path),
        "sha256": sha256_file(path),
        "size_bytes": str(path.stat().st_size),
        "records": records,
        "total_bases": total_bases,
        "status": "ok",
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("config/references.tsv"))
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        rows = read_manifest(args.manifest)
        out_rows: list[dict[str, str]] = []
        for row in rows:
            out_rows.append(artifact_row(row, "gzip_fasta", row["output_gzip"]))
            out_rows.append(artifact_row(row, "plain_fasta", row["output_plain"]))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            writer.writerows(out_rows)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
