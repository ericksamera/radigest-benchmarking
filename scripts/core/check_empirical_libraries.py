#!/usr/bin/env python3
"""Validate the empirical-library manifest without running empirical analyses."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]
EMPIRICAL_LIBRARIES = ROOT / "config" / "empirical_libraries.tsv"
ENZYMES = ROOT / "config" / "enzymes.tsv"

REQUIRED_COLUMNS = [
    "library_id",
    "display_name",
    "enabled",
    "include_for_manuscript",
    "source_type",
    "bam_path",
    "bam_index_path",
    "reference_id",
    "reference_path",
    "enzyme_1",
    "enzyme_2",
    "min_size",
    "max_size",
    "score_min",
    "score_max",
    "size_model",
    "min_mapq",
    "exclude_duplicates",
    "max_tlen",
    "notes",
]

BOOLEAN_COLUMNS = ["enabled", "include_for_manuscript", "exclude_duplicates"]
VALID_SOURCE_TYPES = {"local_bam", "local_cram", "local_fastq_pe", "sra_fastq"}
VALID_SIZE_MODELS = {"hard", "normal", "triangular", "soft-window"}
NA_VALUES = {"NA", "N/A", "NONE", "NULL", ""}


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def read_tsv(path: Path, required_columns: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames
        if fieldnames is None:
            fail(f"{rel(path)}: missing header")
        fieldname_set = set(fieldnames)
        missing = [column for column in required_columns if column not in fieldname_set]
        if missing:
            fail(f"{rel(path)}: missing columns: " + ", ".join(missing))
        rows: list[dict[str, str]] = []
        for raw_row in reader:
            if not any((value or "").strip() for value in raw_row.values()):
                continue
            row: dict[str, str] = {}
            for key, value in raw_row.items():
                if key is not None:
                    row[key] = "" if value is None else value.strip()
            rows.append(row)
    if not rows:
        fail(f"{rel(path)}: no data rows")
    return rows


def parse_bool(value: str, label: str) -> bool:
    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        fail(f"{label} must be true or false")
    return normalized == "true"


def parse_int(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError:
        fail(f"{label} must be an integer")


def is_na(value: str) -> bool:
    return value.strip().upper() in NA_VALUES


def require_relative_path(value: str, label: str) -> None:
    if is_na(value):
        fail(f"{label} must not be NA")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        fail(f"{label} must be a repository-relative path without '..'")


def validate_local_path_shape(
    value: str, label: str, *, allow_na: bool = False
) -> None:
    if is_na(value):
        if allow_na:
            return
        fail(f"{label} must not be NA")
    require_relative_path(value, label)
    if not value.startswith("data/empirical/"):
        fail(f"{label} should live under data/empirical/ for private local inputs")


def validate_reference_path_shape(value: str, label: str) -> None:
    require_relative_path(value, label)
    if not (value.startswith("data/empirical/") or value.startswith("data/reference/")):
        fail(
            f"{label} should live under data/empirical/ for private references "
            "or data/reference/ for downloaded public references"
        )


def read_enzyme_ids() -> set[str]:
    rows = read_tsv(ENZYMES, ["enzyme_id"])
    return {row["enzyme_id"] for row in rows}


def main() -> int:
    rows = read_tsv(EMPIRICAL_LIBRARIES, REQUIRED_COLUMNS)
    enzymes = read_enzyme_ids()
    seen: set[str] = set()
    enabled_count = 0
    manuscript_count = 0

    for line_number, row in enumerate(rows, start=2):
        library_id = row["library_id"]
        if library_id in seen:
            fail(
                f"config/empirical_libraries.tsv:{line_number} "
                f"duplicate library_id={library_id}"
            )
        seen.add(library_id)

        for column in REQUIRED_COLUMNS:
            if row.get(column, "") == "":
                fail(f"config/empirical_libraries.tsv:{line_number} empty {column}")
        for column in BOOLEAN_COLUMNS:
            parse_bool(
                row[column],
                f"config/empirical_libraries.tsv:{line_number} {column}",
            )

        enabled = parse_bool(row["enabled"], f"library {library_id} enabled")
        include_for_manuscript = parse_bool(
            row["include_for_manuscript"],
            f"library {library_id} include_for_manuscript",
        )
        if include_for_manuscript and not enabled:
            fail(
                f"config/empirical_libraries.tsv:{line_number} library {library_id} "
                "sets include_for_manuscript=true but enabled=false"
            )
        if enabled:
            enabled_count += 1
        if include_for_manuscript:
            manuscript_count += 1

        source_type = row["source_type"]
        if source_type not in VALID_SOURCE_TYPES:
            fail(
                f"config/empirical_libraries.tsv:{line_number} invalid "
                f"source_type={source_type!r}"
            )
        size_model = row["size_model"]
        if size_model not in VALID_SIZE_MODELS:
            fail(
                f"config/empirical_libraries.tsv:{line_number} invalid "
                f"size_model={size_model!r}"
            )
        for column in ["enzyme_1", "enzyme_2"]:
            if row[column] not in enzymes:
                fail(
                    f"config/empirical_libraries.tsv:{line_number} unknown "
                    f"{column}={row[column]!r}"
                )

        min_size = parse_int(row["min_size"], f"library {library_id} min_size")
        max_size = parse_int(row["max_size"], f"library {library_id} max_size")
        score_min = parse_int(row["score_min"], f"library {library_id} score_min")
        score_max = parse_int(row["score_max"], f"library {library_id} score_max")
        min_mapq = parse_int(row["min_mapq"], f"library {library_id} min_mapq")
        max_tlen = parse_int(row["max_tlen"], f"library {library_id} max_tlen")
        if min_size < 0 or max_size <= min_size:
            fail(f"config/empirical_libraries.tsv:{line_number} invalid size interval")
        if score_min < 0 or score_max <= score_min:
            fail(f"config/empirical_libraries.tsv:{line_number} invalid score interval")
        if score_min > min_size or score_max < max_size:
            fail(
                f"config/empirical_libraries.tsv:{line_number} score_min/score_max "
                "must cover min_size/max_size"
            )
        if min_mapq < 0:
            fail(f"config/empirical_libraries.tsv:{line_number} min_mapq must be >= 0")
        if max_tlen <= 0:
            fail(f"config/empirical_libraries.tsv:{line_number} max_tlen must be > 0")

        validate_reference_path_shape(
            row["reference_path"], f"library {library_id} reference_path"
        )
        if is_na(row["reference_id"]):
            fail(
                f"config/empirical_libraries.tsv:{line_number} "
                "reference_id must not be NA"
            )

        if source_type == "local_bam":
            validate_local_path_shape(row["bam_path"], f"library {library_id} bam_path")
            validate_local_path_shape(
                row["bam_index_path"],
                f"library {library_id} bam_index_path",
                allow_na=True,
            )
            if not row["bam_path"].endswith(".bam"):
                fail(
                    f"config/empirical_libraries.tsv:{line_number} local_bam "
                    "bam_path should end with .bam"
                )
        elif source_type == "local_cram":
            validate_local_path_shape(row["bam_path"], f"library {library_id} bam_path")
            validate_local_path_shape(
                row["bam_index_path"],
                f"library {library_id} bam_index_path",
                allow_na=True,
            )
            if not row["bam_path"].endswith(".cram"):
                fail(
                    f"config/empirical_libraries.tsv:{line_number} local_cram "
                    "bam_path should end with .cram"
                )
        else:
            # FASTQ/SRA ingestion is planned later. For now these rows can exist as
            # disabled metadata placeholders but should not be enabled.
            if enabled:
                fail(
                    f"config/empirical_libraries.tsv:{line_number} source_type "
                    f"{source_type!r} is not wired into the empirical workflow yet"
                )

        if enabled:
            for column in ["bam_path", "reference_path"]:
                candidate = ROOT / row[column]
                if not candidate.exists():
                    fail(
                        f"config/empirical_libraries.tsv:{line_number} enabled "
                        f"library {library_id} missing {column}: {row[column]}"
                    )
            if not is_na(row["bam_index_path"]):
                index_path = ROOT / row["bam_index_path"]
                if not index_path.exists():
                    fail(
                        f"config/empirical_libraries.tsv:{line_number} enabled "
                        f"library {library_id} missing bam_index_path: "
                        f"{row['bam_index_path']}"
                    )

    print(
        "Empirical library manifest checks passed "
        f"({enabled_count} enabled, {manuscript_count} manuscript)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
