#!/usr/bin/env python3
"""Lightweight Stage 0 manifest checks.

This checker intentionally uses only the Python standard library. It validates
that scaffold manifests exist, are tab-delimited where expected, have required
columns, have unique primary identifiers, and that scenario files have the
expected top-level sections. It does not require reference data, radigest,
external comparator repositories, Snakemake, or PyYAML.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]

TSV_SPECS = {
    "config/datasets.tsv": [
        "dataset_id",
        "display_name",
        "reference_path",
        "format",
        "scope",
        "required_for_smoke",
        "notes",
    ],
    "config/enzymes.tsv": [
        "enzyme_id",
        "display_name",
        "recognition_sequence",
        "cut_offset",
        "source",
        "notes",
    ],
    "config/conditions.tsv": [
        "condition_id",
        "display_name",
        "enzyme_1",
        "enzyme_2",
        "min_size",
        "max_size",
        "size_model",
        "notes",
    ],
    "config/comparators.tsv": [
        "tool_id",
        "display_name",
        "comparison_level",
        "workflow",
        "normalizer",
        "primary_output_type",
        "allowed_claim",
        "required_paths",
    ],
    "config/artifacts.tsv": [
        "claim_id",
        "category",
        "required_output",
        "manuscript_artifact",
        "producer_rule",
        "required_for_release",
        "notes",
    ],
}

SCENARIO_SPECS = {
    "config/scenarios/smoke.yml": {"synthetic_validation", "manifest_check"},
    "config/scenarios/reviewer_nonempirical.yml": {
        "references",
        "matched_digest",
        "screening_speed",
        "thread_scaling",
        "pair_screen_scaling",
    },
    "config/scenarios/reviewer_empirical.yml": {"empirical"},
    "config/scenarios/reviewer_all.yml": {"include_scenarios", "release_contract"},
}

EXTRA_REQUIRED_FILES = [
    "config/candidate_enzymes.txt",
    "workflow/Snakefile",
    "workflow/rules/validation.smk",
    "workflow/rules/references.smk",
    "workflow/rules/comparators.smk",
    "workflow/rules/performance.smk",
    "workflow/rules/empirical.smk",
    "workflow/rules/manuscript.smk",
    "workflow/rules/audit.smk",
]

BOOL_COLUMNS = {
    "config/datasets.tsv": ["required_for_smoke"],
    "config/artifacts.tsv": ["required_for_release"],
}

DNA_RE = re.compile(r"^[ACGTRYSWKMBDHVN]+$", re.IGNORECASE)
TOP_LEVEL_RE = re.compile(r"^([A-Za-z0-9_\-]+):\s*(?:#.*)?$")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def rel(path: str) -> Path:
    return ROOT / path


def require_files(paths: Iterable[str]) -> None:
    missing = [path for path in paths if not rel(path).is_file()]
    if missing:
        fail("missing required files:\n  " + "\n  ".join(missing))


def read_tsv(path: str, required_columns: list[str]) -> list[dict[str, str]]:
    file_path = rel(path)
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            fail(f"{path} has no header")
        missing = [column for column in required_columns if column not in reader.fieldnames]
        if missing:
            fail(f"{path} missing columns: {', '.join(missing)}")
        rows = [row for row in reader if any((value or "").strip() for value in row.values())]
    if not rows:
        fail(f"{path} has no data rows")
    primary_key = required_columns[0]
    seen: set[str] = set()
    for line_number, row in enumerate(rows, start=2):
        key = (row.get(primary_key) or "").strip()
        if not key:
            fail(f"{path}:{line_number} has empty {primary_key}")
        if key in seen:
            fail(f"{path}:{line_number} duplicates {primary_key}={key}")
        seen.add(key)
        for column in required_columns:
            if (row.get(column) or "").strip() == "":
                fail(f"{path}:{line_number} has empty {column}")
        for column in BOOL_COLUMNS.get(path, []):
            value = (row.get(column) or "").strip().lower()
            if value not in {"true", "false"}:
                fail(f"{path}:{line_number} column {column} must be true or false")
    return rows


def check_tsv_semantics(path: str, rows: list[dict[str, str]]) -> None:
    if path == "config/enzymes.tsv":
        for row in rows:
            enzyme = row["enzyme_id"]
            sequence = row["recognition_sequence"]
            if not DNA_RE.fullmatch(sequence):
                fail(f"{path}: enzyme {enzyme} has non-IUPAC recognition sequence {sequence!r}")
            try:
                cut_offset = int(row["cut_offset"])
            except ValueError:
                fail(f"{path}: enzyme {enzyme} cut_offset is not an integer")
            if cut_offset < 0 or cut_offset > len(sequence):
                fail(f"{path}: enzyme {enzyme} cut_offset outside recognition sequence")
    if path == "config/conditions.tsv":
        for row in rows:
            condition = row["condition_id"]
            try:
                min_size = int(row["min_size"])
                max_size = int(row["max_size"])
            except ValueError:
                fail(f"{path}: condition {condition} min_size/max_size must be integers")
            if min_size < 0 or max_size <= min_size:
                fail(f"{path}: condition {condition} has invalid size interval")
    if path == "config/artifacts.tsv":
        for row in rows:
            claim = row["claim_id"]
            for column in ["required_output", "manuscript_artifact"]:
                value = row[column]
                if value == "NA" or value.startswith("/"):
                    fail(f"{path}: claim {claim} column {column} must be a relative repository path")


def read_top_level_yaml_keys(path: str) -> set[str]:
    keys: set[str] = set()
    for line in rel(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace():
            continue
        match = TOP_LEVEL_RE.match(line)
        if match:
            keys.add(match.group(1))
    return keys


def check_scenarios() -> None:
    require_files(SCENARIO_SPECS.keys())
    for path, expected_keys in SCENARIO_SPECS.items():
        observed = read_top_level_yaml_keys(path)
        missing = sorted(expected_keys - observed)
        if missing:
            fail(f"{path} missing top-level sections: {', '.join(missing)}")


def check_candidate_enzymes() -> None:
    path = "config/candidate_enzymes.txt"
    candidates = [
        line.strip()
        for line in rel(path).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not candidates:
        fail(f"{path} has no enzyme IDs")


def main() -> int:
    require_files([*TSV_SPECS.keys(), *SCENARIO_SPECS.keys(), *EXTRA_REQUIRED_FILES])
    for path, columns in TSV_SPECS.items():
        rows = read_tsv(path, columns)
        check_tsv_semantics(path, rows)
    check_candidate_enzymes()
    check_scenarios()
    print("Manifest scaffold checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
