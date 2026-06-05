#!/usr/bin/env python3
"""Validate matched-tool timing manifests without running benchmarks."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]
MATCHED_CASES = ROOT / "config" / "matched_tool_timing_cases.tsv"
DATASETS = ROOT / "config" / "datasets.tsv"
CONDITIONS = ROOT / "config" / "conditions.tsv"
COMPARATORS = ROOT / "config" / "comparators.tsv"

REQUIRED_COLUMNS = [
    "case_id",
    "tool_id",
    "dataset_id",
    "condition_id",
    "reference_path",
    "enzyme_1",
    "enzyme_2",
    "min_size",
    "max_size",
    "runs",
    "timing_scope",
    "required_for_nonempirical",
    "notes",
]

VALID_TOOLS = {"radigest", "digital_rads", "ddradseqtools", "simrad", "ddgrader"}
VALID_TIMING_SCOPES = {
    "native_digest",
    "raw_tool_wrapper",
    "count_only_wrapper",
    "binned_screening_wrapper",
}
REQUIRED_MATCHED_GROUP_TOOLS = {
    ("small_yeast_s288c_plain", "B1"): VALID_TOOLS,
    ("moderate_cannabis_pink-pepper_plain", "B2"): VALID_TOOLS,
    ("large_wheat_chinese-spring_plain", "B2"): {
        "radigest",
        "digital_rads",
        "ddradseqtools",
        "ddgrader",
    },
}
EXPECTEDLY_EXCLUDED_TOOLS = {
    ("large_wheat_chinese-spring_plain", "B2"): {"simrad"},
}


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_tsv(path: Path, required_columns: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames
        if fieldnames is None:
            fail(f"{path.relative_to(ROOT)}: missing header")
        missing = [
            column for column in required_columns if column not in set(fieldnames)
        ]
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


def index_values(path: Path, key: str) -> set[str]:
    return {row[key] for row in read_tsv(path, [key])}


def valid_tools() -> set[str]:
    comparator_tools = index_values(COMPARATORS, "tool_id")
    return comparator_tools | {"radigest"}


def main() -> int:
    rows = read_tsv(MATCHED_CASES, REQUIRED_COLUMNS)
    dataset_ids = index_values(DATASETS, "dataset_id")
    condition_ids = index_values(CONDITIONS, "condition_id")
    valid_tool_ids = valid_tools()

    seen: set[str] = set()
    grouped_tools: dict[tuple[str, str], set[str]] = defaultdict(set)
    grouped_required_tools: dict[tuple[str, str], set[str]] = defaultdict(set)
    for line_number, row in enumerate(rows, start=2):
        case_id = row["case_id"]
        if case_id in seen:
            fail(
                f"config/matched_tool_timing_cases.tsv:{line_number} "
                f"duplicate case_id={case_id}"
            )
        seen.add(case_id)

        tool_id = row["tool_id"]
        if tool_id not in valid_tool_ids or tool_id not in VALID_TOOLS:
            fail(
                f"config/matched_tool_timing_cases.tsv:{line_number} "
                f"unknown tool_id={tool_id!r}"
            )
        if row["dataset_id"] not in dataset_ids:
            fail(
                f"config/matched_tool_timing_cases.tsv:{line_number} "
                f"unknown dataset_id={row['dataset_id']!r}"
            )
        if row["condition_id"] not in condition_ids:
            fail(
                f"config/matched_tool_timing_cases.tsv:{line_number} "
                f"unknown condition_id={row['condition_id']!r}"
            )
        if row["timing_scope"] not in VALID_TIMING_SCOPES:
            fail(
                f"config/matched_tool_timing_cases.tsv:{line_number} "
                f"invalid timing_scope={row['timing_scope']!r}"
            )
        if row["required_for_nonempirical"].lower() not in {"true", "false"}:
            fail(
                f"config/matched_tool_timing_cases.tsv:{line_number} "
                "required_for_nonempirical must be true or false"
            )
        reference = row["reference_path"]
        if reference.startswith("/") or reference == "NA":
            fail(
                f"config/matched_tool_timing_cases.tsv:{line_number} "
                "reference_path must be a relative repository path"
            )
        min_size = parse_int(row["min_size"], f"case {case_id} min_size")
        max_size = parse_int(row["max_size"], f"case {case_id} max_size")
        runs = parse_int(row["runs"], f"case {case_id} runs")
        if min_size < 0 or max_size <= min_size:
            fail(
                f"config/matched_tool_timing_cases.tsv:{line_number} "
                "invalid size interval"
            )
        if runs < 1:
            fail(
                f"config/matched_tool_timing_cases.tsv:{line_number} runs must be >= 1"
            )
        group_key = (row["dataset_id"], row["condition_id"])
        grouped_tools[group_key].add(tool_id)
        if row["required_for_nonempirical"].lower() == "true":
            grouped_required_tools[group_key].add(tool_id)

    for group_key, observed_tools in sorted(grouped_tools.items()):
        expected_tools = REQUIRED_MATCHED_GROUP_TOOLS.get(group_key, VALID_TOOLS)
        missing = sorted(expected_tools - observed_tools)
        if missing:
            dataset_id, condition_id = group_key
            fail(
                "config/matched_tool_timing_cases.tsv: dataset/condition group "
                f"{dataset_id}/{condition_id} missing tools: {', '.join(missing)}"
            )
        unexpected = sorted(
            EXPECTEDLY_EXCLUDED_TOOLS.get(group_key, set()) & observed_tools
        )
        if unexpected:
            dataset_id, condition_id = group_key
            fail(
                "config/matched_tool_timing_cases.tsv: dataset/condition group "
                f"{dataset_id}/{condition_id} includes excluded tools: "
                f"{', '.join(unexpected)}"
            )

    for group_key, expected_tools in sorted(REQUIRED_MATCHED_GROUP_TOOLS.items()):
        dataset_id, condition_id = group_key
        observed_required_tools = grouped_required_tools.get(group_key, set())
        missing = sorted(expected_tools - observed_required_tools)
        if missing:
            fail(
                "config/matched_tool_timing_cases.tsv: required matched-tool "
                f"group {dataset_id}/{condition_id} missing required tools: "
                f"{', '.join(missing)}"
            )

    print("Matched-tool timing case checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
