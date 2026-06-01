#!/usr/bin/env python3
"""Validate Stage 4b non-coordinate comparator contracts.

This validator is intentionally separate from check_manifests.py so Stage 4b can
be applied to trees where that scaffold checker has local formatting or mode
changes. It uses only the Python standard library.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

NONCOORDINATE_CASES = Path("config/noncoordinate_comparator_cases.tsv")
COMPARATORS = Path("config/comparators.tsv")
DATASETS = Path("config/datasets.tsv")
CONDITIONS = Path("config/conditions.tsv")
ENZYMES = Path("config/enzymes.tsv")
ARTIFACTS = Path("config/artifacts.tsv")

REQUIRED_CASE_COLUMNS = [
    "case_id",
    "tool_id",
    "dataset_id",
    "condition_id",
    "reference_path",
    "enzyme_1",
    "enzyme_2",
    "min_size",
    "max_size",
    "radigest_min_size",
    "radigest_max_size",
    "output_path",
    "required_for_nonempirical",
    "notes",
]

EXPECTED_TOOL_CONTRACTS = {
    "simrad": {
        "comparison_level": "count_only",
        "allowed_claim": "count_level_digest",
        "primary_output_type": "aggregate_count",
    },
    "ddgrader": {
        "comparison_level": "binned_screening",
        "allowed_claim": "screening_throughput",
        "primary_output_type": "binned_counts",
    },
}

TRUE_VALUES = {"1", "true", "yes", "y"}


def rel(path: Path) -> Path:
    return ROOT / path


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def read_tsv(
    path: Path, required_columns: list[str] | None = None
) -> list[dict[str, str]]:
    full = rel(path)
    if not full.exists():
        fail(f"missing required file: {path}")
    with full.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            fail(f"{path}: missing header")
        fieldnames = list(reader.fieldnames)
        if required_columns is not None:
            missing = [
                column for column in required_columns if column not in fieldnames
            ]
            if missing:
                fail(f"{path}: missing columns: {', '.join(missing)}")
        rows = [
            {
                key: "" if value is None else value
                for key, value in row.items()
                if key is not None
            }
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]
    if not rows:
        fail(f"{path}: no data rows")
    return rows


def index_rows(
    path: Path, rows: list[dict[str, str]], key: str
) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        value = row.get(key, "")
        if not value:
            fail(f"{path}: row has empty {key}")
        if value in out:
            fail(f"{path}: duplicate {key}={value}")
        out[value] = row
    return out


def parse_int(path: Path, case_id: str, column: str, value: str) -> int:
    try:
        return int(value)
    except ValueError:
        fail(f"{path}: case {case_id} column {column} must be an integer")


def require_relative_path(path: Path, case_id: str, column: str, value: str) -> None:
    candidate = Path(value)
    if not value or candidate.is_absolute() or value.startswith(".."):
        fail(
            f"{path}: case {case_id} column {column} must be a relative repository path"
        )


def is_true(value: str) -> bool:
    return value.strip().lower() in TRUE_VALUES


def validate_tool_contracts(comparators: dict[str, dict[str, str]]) -> None:
    for tool_id, expected in EXPECTED_TOOL_CONTRACTS.items():
        if tool_id not in comparators:
            fail(f"{COMPARATORS}: missing tool_id={tool_id}")
        row = comparators[tool_id]
        for column, expected_value in expected.items():
            observed = row.get(column, "")
            if observed != expected_value:
                fail(
                    f"{COMPARATORS}: tool_id={tool_id} column {column} must be "
                    f"{expected_value!r}, got {observed!r}"
                )
        if row.get("allowed_claim") == "coordinate_equivalence":
            fail(
                f"{COMPARATORS}: tool_id={tool_id} must not allow coordinate_equivalence"
            )


def validate_cases(
    cases: list[dict[str, str]],
    comparators: dict[str, dict[str, str]],
    datasets: dict[str, dict[str, str]],
    conditions: dict[str, dict[str, str]],
    enzymes: dict[str, dict[str, str]],
) -> set[str]:
    output_paths: set[str] = set()
    seen_cases: set[str] = set()

    for row in cases:
        case_id = row["case_id"]
        if case_id in seen_cases:
            fail(f"{NONCOORDINATE_CASES}: duplicate case_id={case_id}")
        seen_cases.add(case_id)

        tool_id = row["tool_id"]
        if tool_id not in EXPECTED_TOOL_CONTRACTS:
            fail(
                f"{NONCOORDINATE_CASES}: case {case_id} has unsupported tool_id={tool_id!r}"
            )
        if tool_id not in comparators:
            fail(
                f"{NONCOORDINATE_CASES}: case {case_id} uses unknown tool_id={tool_id}"
            )

        dataset_id = row["dataset_id"]
        if dataset_id not in datasets:
            fail(
                f"{NONCOORDINATE_CASES}: case {case_id} uses unknown dataset_id={dataset_id}"
            )
        if row["reference_path"] != datasets[dataset_id].get("reference_path", ""):
            fail(
                f"{NONCOORDINATE_CASES}: case {case_id} reference_path does not match "
                f"config/datasets.tsv dataset_id={dataset_id}"
            )

        condition_id = row["condition_id"]
        if condition_id not in conditions:
            fail(
                f"{NONCOORDINATE_CASES}: case {case_id} uses unknown condition_id={condition_id}"
            )
        condition = conditions[condition_id]
        for column in ["enzyme_1", "enzyme_2"]:
            enzyme_id = row[column]
            if enzyme_id not in enzymes:
                fail(
                    f"{NONCOORDINATE_CASES}: case {case_id} uses unknown {column}={enzyme_id}"
                )
            if enzyme_id != condition.get(column, ""):
                fail(
                    f"{NONCOORDINATE_CASES}: case {case_id} {column} does not match condition {condition_id}"
                )

        min_size = parse_int(NONCOORDINATE_CASES, case_id, "min_size", row["min_size"])
        max_size = parse_int(NONCOORDINATE_CASES, case_id, "max_size", row["max_size"])
        radigest_min = parse_int(
            NONCOORDINATE_CASES, case_id, "radigest_min_size", row["radigest_min_size"]
        )
        radigest_max = parse_int(
            NONCOORDINATE_CASES, case_id, "radigest_max_size", row["radigest_max_size"]
        )
        if min_size < 0 or max_size < min_size:
            fail(
                f"{NONCOORDINATE_CASES}: case {case_id} has invalid comparator size interval"
            )
        if radigest_min < 0 or radigest_max < radigest_min:
            fail(
                f"{NONCOORDINATE_CASES}: case {case_id} has invalid radigest size interval"
            )
        if row["min_size"] != condition.get("min_size", "") or row[
            "max_size"
        ] != condition.get("max_size", ""):
            fail(
                f"{NONCOORDINATE_CASES}: case {case_id} min/max does not match condition {condition_id}"
            )

        require_relative_path(
            NONCOORDINATE_CASES, case_id, "reference_path", row["reference_path"]
        )
        require_relative_path(
            NONCOORDINATE_CASES, case_id, "output_path", row["output_path"]
        )
        if not row["output_path"].startswith("results/comparators/"):
            fail(
                f"{NONCOORDINATE_CASES}: case {case_id} output_path must be under results/comparators/"
            )
        if not is_true(row["required_for_nonempirical"]):
            fail(
                f"{NONCOORDINATE_CASES}: case {case_id} must be required_for_nonempirical=true"
            )
        output_paths.add(row["output_path"])

    return output_paths


def validate_artifacts(output_paths: set[str]) -> None:
    artifacts = read_tsv(ARTIFACTS)
    release_outputs = {
        row.get("required_output", "")
        for row in artifacts
        if row.get("category") == "comparators"
        and is_true(row.get("required_for_release", ""))
    }
    missing = sorted(output_paths - release_outputs)
    if missing:
        fail(
            f"{ARTIFACTS}: missing release artifact rows for Stage 4b outputs: "
            + ", ".join(missing)
        )


def main() -> int:
    comparators = index_rows(COMPARATORS, read_tsv(COMPARATORS), "tool_id")
    datasets = index_rows(DATASETS, read_tsv(DATASETS), "dataset_id")
    conditions = index_rows(CONDITIONS, read_tsv(CONDITIONS), "condition_id")
    enzymes = index_rows(ENZYMES, read_tsv(ENZYMES), "enzyme_id")
    cases = read_tsv(NONCOORDINATE_CASES, REQUIRED_CASE_COLUMNS)

    validate_tool_contracts(comparators)
    outputs = validate_cases(cases, comparators, datasets, conditions, enzymes)
    validate_artifacts(outputs)
    print("Non-coordinate comparator checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
