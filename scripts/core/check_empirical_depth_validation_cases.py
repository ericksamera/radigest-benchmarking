#!/usr/bin/env python3
"""Validate empirical depth-validation case manifest against enabled libraries."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]
DEPTH_COLUMNS = [
    "library_id",
    "display_name",
    "enabled",
    "enzyme_1",
    "enzyme_2",
    "min_size",
    "max_size",
    "score_min",
    "score_max",
    "size_model",
    "size_mean",
    "size_sd",
    "size_edge_sd",
    "target_genome_pct",
    "coverage_tolerance_pct",
    "desired_depth",
    "samples",
    "read_layout",
    "read_length",
    "flowcell_read_pairs",
    "lane_read_pairs",
    "lanes",
    "usable_read_fraction",
    "min_mapq",
    "exclude_duplicates",
    "notes",
]
LIBRARY_COLUMNS = [
    "library_id",
    "enabled",
    "include_for_manuscript",
    "source_type",
    "bam_dir",
    "bam_glob",
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
]
VALID_SIZE_MODELS = {"hard", "normal", "triangular", "soft-window"}
BOOL_VALUES = {"true", "false"}


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_tsv(path: Path, required_columns: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            fail(f"{rel(path)}: missing header")
        missing = [c for c in required_columns if c not in set(reader.fieldnames)]
        if missing:
            fail(f"{rel(path)}: missing columns: {', '.join(missing)}")
        rows = [
            {key: (value or "").strip() for key, value in row.items() if key}
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]
    if not rows:
        fail(f"{rel(path)}: no rows")
    return rows


def parse_bool(value: str, label: str) -> bool:
    value_l = value.strip().lower()
    if value_l not in BOOL_VALUES:
        fail(f"{label} must be true or false")
    return value_l == "true"


def parse_int(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError:
        fail(f"{label} must be an integer")


def parse_float(value: str, label: str) -> float:
    try:
        return float(value)
    except ValueError:
        fail(f"{label} must be numeric")


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        default=Path("config/empirical_depth_validation_cases.tsv"),
        type=Path,
    )
    parser.add_argument(
        "--library-manifest", default=Path("config/empirical_libraries.tsv"), type=Path
    )
    parser.add_argument(
        "--require-effective-enabled",
        action="store_true",
        help="Fail unless at least one enabled depth-validation row has an enabled parent library.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    depth_path = resolve(args.manifest)
    library_path = resolve(args.library_manifest)
    depth_rows = read_tsv(depth_path, DEPTH_COLUMNS)
    library_rows = read_tsv(library_path, LIBRARY_COLUMNS)
    libraries = {row["library_id"]: row for row in library_rows}
    effective_enabled: list[str] = []

    seen: set[str] = set()
    for line_number, row in enumerate(depth_rows, start=2):
        label = f"{rel(depth_path)}:{line_number} library {row['library_id']}"
        library_id = row["library_id"]
        if library_id in seen:
            fail(f"{rel(depth_path)}:{line_number} duplicate library_id={library_id!r}")
        seen.add(library_id)
        enabled = parse_bool(row["enabled"], f"{label} enabled")
        if library_id not in libraries:
            fail(f"{label} is absent from {rel(library_path)}")
        parent = libraries[library_id]
        parent_enabled = parse_bool(parent["enabled"], f"library {library_id} enabled")
        if row["size_model"] not in VALID_SIZE_MODELS:
            fail(f"{label} invalid size_model={row['size_model']!r}")
        min_size = parse_int(row["min_size"], f"{label} min_size")
        max_size = parse_int(row["max_size"], f"{label} max_size")
        score_min = parse_int(row["score_min"], f"{label} score_min")
        score_max = parse_int(row["score_max"], f"{label} score_max")
        if min_size < 0 or max_size <= min_size:
            fail(f"{label} has invalid size interval")
        if (
            score_min < 0
            or score_max <= score_min
            or score_min > min_size
            or score_max < max_size
        ):
            fail(f"{label} score_min/score_max must cover min_size/max_size")
        for column in [
            "size_mean",
            "size_sd",
            "size_edge_sd",
            "target_genome_pct",
            "coverage_tolerance_pct",
            "desired_depth",
            "usable_read_fraction",
        ]:
            parse_float(row[column], f"{label} {column}")
        for column in ["samples", "read_length", "lanes", "min_mapq"]:
            if parse_int(row[column], f"{label} {column}") < 0:
                fail(f"{label} {column} must be >= 0")
        parse_bool(row["exclude_duplicates"], f"{label} exclude_duplicates")
        if row["read_layout"] not in {"pe", "se"}:
            fail(f"{label} read_layout must be pe or se")
        has_flowcell = row.get("flowcell_read_pairs", "NA") not in {"", "NA"}
        has_lane = row.get("lane_read_pairs", "NA") not in {"", "NA"}
        if has_flowcell == has_lane:
            fail(
                f"{label} must set exactly one of flowcell_read_pairs or lane_read_pairs"
            )
        if enabled and parent_enabled:
            effective_enabled.append(library_id)

    if args.require_effective_enabled and not effective_enabled:
        fail(
            "no effective empirical depth-validation cases are enabled; enable a "
            "parent library row, then rerun after adding BAMs to the configured "
            "data/empirical drop-off directory"
        )
    suffix = f" ({len(effective_enabled)} effective enabled)"
    print(f"Empirical depth-validation case checks passed{suffix}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
