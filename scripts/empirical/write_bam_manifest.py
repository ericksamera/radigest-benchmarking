#!/usr/bin/env python3
"""Write the per-BAM inventory for one empirical library directory."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

REQUIRED_COLUMNS = [
    "library_id",
    "display_name",
    "enabled",
    "include_for_manuscript",
    "source_type",
    "bam_dir",
    "bam_glob",
    "bam_index_suffix",
    "reference_id",
    "reference_path",
    "enzyme_1",
    "enzyme_2",
    "min_size",
    "max_size",
    "score_min",
    "score_max",
    "size_model",
    "size_edge_sd",
    "min_mapq",
    "exclude_duplicates",
    "max_tlen",
    "notes",
]

OUTPUT_COLUMNS = [
    "library_id",
    "bam_id",
    "bam_path",
    "bam_index_path",
    "bam_index_exists",
    "reference_id",
    "reference_path",
    "enzyme_1",
    "enzyme_2",
    "min_size",
    "max_size",
    "score_min",
    "score_max",
    "size_model",
    "size_edge_sd",
    "min_mapq",
    "exclude_duplicates",
    "max_tlen",
]


def read_manifest(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        missing = [
            column for column in REQUIRED_COLUMNS if column not in reader.fieldnames
        ]
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(missing)}")
        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            if not any((value or "").strip() for value in row.values()):
                continue
            cleaned = {key: (row.get(key) or "").strip() for key in REQUIRED_COLUMNS}
            library_id = cleaned["library_id"]
            if library_id in rows:
                raise ValueError(f"{path}: duplicate library_id={library_id!r}")
            rows[library_id] = cleaned
    if not rows:
        raise ValueError(f"{path}: no empirical-library rows")
    return rows


def safe_bam_id(path: Path) -> str:
    name = path.name
    if name.endswith(".bam"):
        name = name[:-4]
    elif name.endswith(".cram"):
        name = name[:-5]
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._")
    if not name:
        raise ValueError(f"could not derive bam_id from {path}")
    return name


def relative_to_cwd(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def index_is_na(value: str) -> bool:
    return value.strip().upper() in {"", "NA", "N/A", "NONE", "NULL"}


def write_bam_manifest(row: dict[str, str], output: Path) -> None:
    if row["source_type"] != "local_bam_dir":
        raise ValueError(
            f"{row['library_id']}: write_bam_manifest currently supports "
            "source_type=local_bam_dir only"
        )
    bam_dir = Path(row["bam_dir"])
    if not bam_dir.is_dir():
        raise FileNotFoundError(f"{row['library_id']}: missing BAM directory {bam_dir}")
    bam_paths = sorted(
        path
        for path in bam_dir.glob(row["bam_glob"])
        if path.is_file() or path.is_symlink()
    )
    if not bam_paths:
        raise FileNotFoundError(
            f"{row['library_id']}: no BAMs matched {bam_dir / row['bam_glob']}"
        )

    index_suffix = row["bam_index_suffix"]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, delimiter="\t", fieldnames=OUTPUT_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        for bam_path in bam_paths:
            index_path = "NA"
            index_exists = "false"
            if not index_is_na(index_suffix):
                candidate_index = Path(str(bam_path) + index_suffix)
                index_path = relative_to_cwd(candidate_index)
                index_exists = "true" if candidate_index.exists() else "false"
            writer.writerow(
                {
                    "library_id": row["library_id"],
                    "bam_id": safe_bam_id(bam_path),
                    "bam_path": relative_to_cwd(bam_path),
                    "bam_index_path": index_path,
                    "bam_index_exists": index_exists,
                    "reference_id": row["reference_id"],
                    "reference_path": row["reference_path"],
                    "enzyme_1": row["enzyme_1"],
                    "enzyme_2": row["enzyme_2"],
                    "min_size": row["min_size"],
                    "max_size": row["max_size"],
                    "score_min": row["score_min"],
                    "score_max": row["score_max"],
                    "size_model": row["size_model"],
                    "size_edge_sd": row["size_edge_sd"],
                    "min_mapq": row["min_mapq"],
                    "exclude_duplicates": row["exclude_duplicates"],
                    "max_tlen": row["max_tlen"],
                }
            )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--library-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        rows = read_manifest(args.manifest)
        if args.library_id not in rows:
            raise ValueError(
                f"unknown library_id={args.library_id!r} in {args.manifest}"
            )
        write_bam_manifest(rows[args.library_id], args.out)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
