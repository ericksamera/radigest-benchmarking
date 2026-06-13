#!/usr/bin/env python3
"""Validate target SNP-panel / BED-overlap case manifest."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_COLUMNS = [
    "case_id",
    "display_name",
    "enabled",
    "include_for_manuscript",
    "library_id",
    "reference_id",
    "reference_path",
    "panel_bed",
    "candidate_enzymes",
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
    "top_n",
    "notes",
]

LIBRARY_COLUMNS = ["library_id", "enabled", "reference_id", "reference_path"]
BOOL_COLUMNS = ["enabled", "include_for_manuscript"]
BOOL_VALUES = {"true", "false"}
VALID_SIZE_MODELS = {"hard", "normal", "triangular", "soft-window"}
NA_VALUES = {"", "NA", "N/A", "NONE", "NULL"}


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def read_tsv(path: Path, required_columns: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            fail(f"{rel(path)}: missing header")
        missing = [
            column
            for column in required_columns
            if column not in set(reader.fieldnames)
        ]
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
    normalized = value.strip().lower()
    if normalized not in BOOL_VALUES:
        fail(f"{label} must be true or false")
    return normalized == "true"


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


def is_na(value: str) -> bool:
    return value.strip().upper() in NA_VALUES


def check_relative_path(value: str, label: str) -> None:
    if is_na(value):
        fail(f"{label} must not be NA")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        fail(f"{label} must be a repository-relative path without '..'")


def count_candidate_enzymes(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        text = raw.strip()
        if text and not text.startswith("#"):
            count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", default=Path("config/snp_panel_cases.tsv"), type=Path
    )
    parser.add_argument(
        "--library-manifest", default=Path("config/empirical_libraries.tsv"), type=Path
    )
    parser.add_argument("--require-enabled", action="append", default=[])
    parser.add_argument("--allow-missing-enabled-inputs", action="store_true")
    args = parser.parse_args(argv)

    manifest = resolve(args.manifest)
    library_manifest = resolve(args.library_manifest)
    rows = read_tsv(manifest, REQUIRED_COLUMNS)
    library_rows = read_tsv(library_manifest, LIBRARY_COLUMNS)
    libraries = {row["library_id"]: row for row in library_rows}

    seen: set[str] = set()
    enabled_cases: set[str] = set()
    for line_number, row in enumerate(rows, start=2):
        case_id = row["case_id"]
        label = f"{rel(manifest)}:{line_number} case {case_id}"
        if case_id in seen:
            fail(f"{label}: duplicate case_id")
        seen.add(case_id)
        for column in REQUIRED_COLUMNS:
            if row.get(column, "") == "":
                fail(f"{label}: empty {column}")
        enabled = parse_bool(row["enabled"], f"{label} enabled")
        include = parse_bool(
            row["include_for_manuscript"], f"{label} include_for_manuscript"
        )
        if include and not enabled:
            fail(f"{label}: include_for_manuscript=true but enabled=false")
        if row["library_id"] not in libraries:
            fail(
                f"{label}: library_id {row['library_id']!r} absent from {rel(library_manifest)}"
            )
        parent = libraries[row["library_id"]]
        parent_enabled = parse_bool(
            parent["enabled"], f"library {row['library_id']} enabled"
        )
        if enabled and parent_enabled:
            enabled_cases.add(case_id)
        if row["reference_id"] != parent["reference_id"]:
            fail(f"{label}: reference_id does not match parent empirical library")
        if row["reference_path"] != parent["reference_path"]:
            fail(f"{label}: reference_path does not match parent empirical library")
        for column in ["reference_path", "panel_bed", "candidate_enzymes"]:
            check_relative_path(row[column], f"{label} {column}")
        if not row["panel_bed"].startswith("data/empirical/"):
            fail(f"{label}: panel_bed should live under data/empirical/")
        if row["size_model"] not in VALID_SIZE_MODELS:
            fail(f"{label}: invalid size_model={row['size_model']!r}")
        min_size = parse_int(row["min_size"], f"{label} min_size")
        max_size = parse_int(row["max_size"], f"{label} max_size")
        score_min = parse_int(row["score_min"], f"{label} score_min")
        score_max = parse_int(row["score_max"], f"{label} score_max")
        if min_size < 0 or max_size <= min_size:
            fail(f"{label}: invalid size interval")
        if (
            score_min < 0
            or score_max <= score_min
            or score_min > min_size
            or score_max < max_size
        ):
            fail(f"{label}: score_min/score_max must cover min_size/max_size")
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
        for column in ["samples", "read_length", "lanes", "top_n"]:
            if parse_int(row[column], f"{label} {column}") < 1:
                fail(f"{label}: {column} must be >= 1")
        if row["read_layout"] not in {"pe", "se"}:
            fail(f"{label}: read_layout must be pe or se")
        has_flowcell = not is_na(row["flowcell_read_pairs"])
        has_lane = not is_na(row["lane_read_pairs"])
        if has_flowcell == has_lane:
            fail(f"{label}: set exactly one of flowcell_read_pairs or lane_read_pairs")
        candidate_path = resolve(Path(row["candidate_enzymes"]))
        if not candidate_path.exists():
            fail(f"{label}: missing candidate_enzymes file {row['candidate_enzymes']}")
        if count_candidate_enzymes(candidate_path) < 2:
            fail(f"{label}: candidate_enzymes must contain at least two enzyme names")
        panel_path = resolve(Path(row["panel_bed"]))
        if enabled and parent_enabled and not args.allow_missing_enabled_inputs:
            if not panel_path.exists():
                fail(f"{label}: missing panel_bed {row['panel_bed']}")

    missing_required = sorted(set(args.require_enabled) - enabled_cases)
    if missing_required:
        fail(
            "required SNP-panel case(s) not effectively enabled: "
            + ", ".join(missing_required)
        )
    print(f"SNP-panel case checks passed ({len(enabled_cases)} effective enabled).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
