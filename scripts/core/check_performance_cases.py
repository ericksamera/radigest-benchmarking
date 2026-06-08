#!/usr/bin/env python3
"""Validate performance-case manifests without running benchmarks."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]
PERFORMANCE_CASES = ROOT / "config" / "performance_cases.tsv"
DATASETS = ROOT / "config" / "datasets.tsv"
CONDITIONS = ROOT / "config" / "conditions.tsv"

REQUIRED_COLUMNS = [
    "case_id",
    "category",
    "dataset_id",
    "reference_path",
    "condition_id",
    "enzyme_1",
    "enzyme_2",
    "min_size",
    "max_size",
    "threads",
    "runs",
    "comparison_group",
    "input_format",
    "required_for_nonempirical",
    "notes",
]

VALID_CATEGORIES = {"input_format"}
VALID_INPUT_FORMATS = {"plain", "gzip"}


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_tsv(path: Path, required_columns: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames
        if fieldnames is None:
            fail(f"{path.relative_to(ROOT)}: missing header")
        fieldname_set = set(fieldnames)
        missing = [column for column in required_columns if column not in fieldname_set]
        if missing:
            fail(f"{path.relative_to(ROOT)}: missing columns: " + ", ".join(missing))
        rows: list[dict[str, str]] = []
        for raw_row in reader:
            if not any((value or "").strip() for value in raw_row.values()):
                continue
            row: dict[str, str] = {}
            for key, value in raw_row.items():
                if key is not None:
                    row[key] = "" if value is None else value
            rows.append(row)
    if not rows:
        fail(f"{path.relative_to(ROOT)}: no data rows")
    return rows


def parse_int(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError:
        fail(f"{label} must be an integer")


def main() -> int:
    rows = read_tsv(PERFORMANCE_CASES, REQUIRED_COLUMNS)
    dataset_ids = {
        row["dataset_id"] for row in read_tsv(DATASETS, ["dataset_id", "display_name"])
    }
    condition_ids = {
        row["condition_id"]
        for row in read_tsv(CONDITIONS, ["condition_id", "display_name"])
    }

    seen: set[str] = set()
    group_formats: dict[str, set[str]] = {}
    for line_number, row in enumerate(rows, start=2):
        case_id = row["case_id"]
        if case_id in seen:
            fail(
                f"config/performance_cases.tsv:{line_number} "
                f"duplicate case_id={case_id}"
            )
        seen.add(case_id)

        category = row["category"]
        if category not in VALID_CATEGORIES:
            fail(
                f"config/performance_cases.tsv:{line_number} "
                f"invalid category={category!r}"
            )
        if row["dataset_id"] not in dataset_ids:
            fail(
                f"config/performance_cases.tsv:{line_number} unknown dataset_id="
                f"{row['dataset_id']!r}"
            )
        if row["condition_id"] not in condition_ids:
            fail(
                f"config/performance_cases.tsv:{line_number} unknown condition_id="
                f"{row['condition_id']!r}"
            )
        reference_path = row["reference_path"]
        if reference_path.startswith("/") or reference_path == "NA":
            fail(
                f"config/performance_cases.tsv:{line_number} reference_path must be "
                "a relative repository path"
            )
        input_format = row["input_format"]
        if input_format not in VALID_INPUT_FORMATS:
            fail(
                f"config/performance_cases.tsv:{line_number} invalid input_format="
                f"{input_format!r}"
            )
        if row["required_for_nonempirical"].lower() not in {"true", "false"}:
            fail(
                f"config/performance_cases.tsv:{line_number} "
                "required_for_nonempirical must be true or false"
            )
        min_size = parse_int(row["min_size"], f"case {case_id} min_size")
        max_size = parse_int(row["max_size"], f"case {case_id} max_size")
        threads = parse_int(row["threads"], f"case {case_id} threads")
        runs = parse_int(row["runs"], f"case {case_id} runs")
        if min_size < 0 or max_size <= min_size:
            fail(f"config/performance_cases.tsv:{line_number} invalid size interval")
        if threads < 1 or runs < 1:
            fail(
                f"config/performance_cases.tsv:{line_number} "
                "threads/runs must be >= 1"
            )
        group_formats.setdefault(row["comparison_group"], set()).add(input_format)

    for group, formats in sorted(group_formats.items()):
        if not {"plain", "gzip"}.issubset(formats):
            fail(
                f"config/performance_cases.tsv: comparison_group {group!r} must "
                "include both plain and gzip input_format rows"
            )

    print("Performance case checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
