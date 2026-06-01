#!/usr/bin/env python3
"""Validate large-reference performance-case manifests without running benchmarks."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]
LARGE_GENOME_CASES = ROOT / "config" / "large_genome_cases.tsv"
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
    "output_mode",
    "threads",
    "runs",
    "comparison_group",
    "input_format",
    "required_for_nonempirical",
    "notes",
]

VALID_OUTPUT_MODES = {"json", "fragments_tsv", "both"}
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
    rows = read_tsv(LARGE_GENOME_CASES, REQUIRED_COLUMNS)
    dataset_ids = {
        row["dataset_id"] for row in read_tsv(DATASETS, ["dataset_id", "display_name"])
    }
    condition_ids = {
        row["condition_id"]
        for row in read_tsv(CONDITIONS, ["condition_id", "display_name"])
    }

    seen: set[str] = set()
    for line_number, row in enumerate(rows, start=2):
        case_id = row["case_id"]
        if case_id in seen:
            fail(
                f"config/large_genome_cases.tsv:{line_number} duplicate "
                f"case_id={case_id}"
            )
        seen.add(case_id)
        if row["category"] != "large_genome":
            fail(
                f"config/large_genome_cases.tsv:{line_number} invalid category="
                f"{row['category']!r}"
            )
        if row["dataset_id"] not in dataset_ids:
            fail(
                f"config/large_genome_cases.tsv:{line_number} unknown dataset_id="
                f"{row['dataset_id']!r}"
            )
        if row["condition_id"] not in condition_ids:
            fail(
                f"config/large_genome_cases.tsv:{line_number} unknown condition_id="
                f"{row['condition_id']!r}"
            )
        if row["reference_path"].startswith("/") or row["reference_path"] == "NA":
            fail(
                f"config/large_genome_cases.tsv:{line_number} reference_path must "
                "be a relative repository path"
            )
        if row["output_mode"] not in VALID_OUTPUT_MODES:
            fail(
                f"config/large_genome_cases.tsv:{line_number} invalid "
                f"output_mode={row['output_mode']!r}"
            )
        if row["input_format"] not in VALID_INPUT_FORMATS:
            fail(
                f"config/large_genome_cases.tsv:{line_number} invalid "
                f"input_format={row['input_format']!r}"
            )
        if row["required_for_nonempirical"].lower() not in {"true", "false"}:
            fail(
                f"config/large_genome_cases.tsv:{line_number} "
                "required_for_nonempirical must be true or false"
            )
        min_size = parse_int(row["min_size"], f"case {case_id} min_size")
        max_size = parse_int(row["max_size"], f"case {case_id} max_size")
        threads = parse_int(row["threads"], f"case {case_id} threads")
        runs = parse_int(row["runs"], f"case {case_id} runs")
        if min_size < 0 or max_size <= min_size:
            fail(f"config/large_genome_cases.tsv:{line_number} invalid size interval")
        if threads < 1 or runs < 1:
            fail(
                f"config/large_genome_cases.tsv:{line_number} threads/runs "
                "must be >= 1"
            )

    print("Large-genome performance case checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
