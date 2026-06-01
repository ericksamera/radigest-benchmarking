#!/usr/bin/env python3
"""Validate pair-screen job-scaling manifests without running benchmarks."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]
PAIR_SCREEN_CASES = ROOT / "config" / "pair_screen_scaling_cases.tsv"
DATASETS = ROOT / "config" / "datasets.tsv"
CONDITIONS = ROOT / "config" / "conditions.tsv"
REQUIRED_COLUMNS = [
    "case_id",
    "dataset_id",
    "reference_path",
    "condition_id",
    "candidate_enzymes",
    "min_size",
    "max_size",
    "score_min",
    "score_max",
    "size_model",
    "jobs",
    "radigest_threads",
    "runs",
    "comparison_group",
    "required_for_nonempirical",
    "command_template",
    "notes",
]
VALID_SIZE_MODELS = {"hard"}
VALID_COMMAND_TEMPLATES = {"radigest-screen-pairs-cached", "cached"}


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def repo_label(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_tsv(path: Path, required_columns: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames
        if fieldnames is None:
            fail(f"{repo_label(path)}: missing header")
        fieldname_set = set(fieldnames)
        missing = [column for column in required_columns if column not in fieldname_set]
        if missing:
            fail(f"{repo_label(path)}: missing columns: " + ", ".join(missing))
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
        fail(f"{repo_label(path)}: no data rows")
    return rows


def parse_int(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError:
        fail(f"{label} must be an integer")


def validate_relative_path(value: str, *, line_number: int, column: str) -> Path:
    if not value or value == "NA" or value.startswith("/"):
        fail(
            f"config/pair_screen_scaling_cases.tsv:{line_number} {column} must be "
            "a relative repository path"
        )
    return ROOT / value


def read_candidate_names(path: Path) -> list[str]:
    if not path.exists():
        fail(f"{repo_label(path)}: candidate enzyme file does not exist")
    names = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if len(names) < 2:
        fail(f"{repo_label(path)}: at least two candidate enzymes are required")
    if len(set(names)) != len(names):
        fail(f"{repo_label(path)}: candidate enzyme names must be unique")
    return names


def main() -> int:
    rows = read_tsv(PAIR_SCREEN_CASES, REQUIRED_COLUMNS)
    dataset_ids = {
        row["dataset_id"] for row in read_tsv(DATASETS, ["dataset_id", "display_name"])
    }
    condition_ids = {
        row["condition_id"]
        for row in read_tsv(CONDITIONS, ["condition_id", "display_name"])
    }
    seen: set[str] = set()
    group_jobs: dict[str, set[int]] = {}
    group_threads: dict[str, set[int]] = {}
    group_conditions: dict[str, set[str]] = {}
    required_count = 0
    for line_number, row in enumerate(rows, start=2):
        case_id = row["case_id"]
        if case_id in seen:
            fail(
                f"config/pair_screen_scaling_cases.tsv:{line_number} "
                f"duplicate case_id={case_id}"
            )
        seen.add(case_id)

        if row["dataset_id"] not in dataset_ids:
            fail(
                f"config/pair_screen_scaling_cases.tsv:{line_number} "
                f"unknown dataset_id={row['dataset_id']!r}"
            )
        if row["condition_id"] not in condition_ids:
            fail(
                f"config/pair_screen_scaling_cases.tsv:{line_number} "
                f"unknown condition_id={row['condition_id']!r}"
            )
        validate_relative_path(
            row["reference_path"], line_number=line_number, column="reference_path"
        )
        candidate_path = validate_relative_path(
            row["candidate_enzymes"],
            line_number=line_number,
            column="candidate_enzymes",
        )
        read_candidate_names(candidate_path)

        min_size = parse_int(row["min_size"], f"case {case_id} min_size")
        max_size = parse_int(row["max_size"], f"case {case_id} max_size")
        score_min = parse_int(row["score_min"], f"case {case_id} score_min")
        score_max = parse_int(row["score_max"], f"case {case_id} score_max")
        jobs = parse_int(row["jobs"], f"case {case_id} jobs")
        radigest_threads = parse_int(
            row["radigest_threads"], f"case {case_id} radigest_threads"
        )
        runs = parse_int(row["runs"], f"case {case_id} runs")
        if min_size < 0 or max_size <= min_size:
            fail(
                f"config/pair_screen_scaling_cases.tsv:{line_number} "
                "invalid size interval"
            )
        if score_min < 0 or score_max <= score_min:
            fail(
                f"config/pair_screen_scaling_cases.tsv:{line_number} "
                "invalid score interval"
            )
        if jobs < 1 or radigest_threads < 1 or runs < 1:
            fail(
                f"config/pair_screen_scaling_cases.tsv:{line_number} "
                "jobs/radigest_threads/runs must be >= 1"
            )
        if row["size_model"] not in VALID_SIZE_MODELS:
            fail(
                f"config/pair_screen_scaling_cases.tsv:{line_number} "
                f"invalid size_model={row['size_model']!r}"
            )
        if row["required_for_nonempirical"].lower() not in {"true", "false"}:
            fail(
                f"config/pair_screen_scaling_cases.tsv:{line_number} "
                "required_for_nonempirical must be true or false"
            )
        if row["required_for_nonempirical"].lower() == "true":
            required_count += 1
        if row["command_template"] not in VALID_COMMAND_TEMPLATES:
            fail(
                f"config/pair_screen_scaling_cases.tsv:{line_number} command_template "
                "must be radigest-screen-pairs-cached"
            )
        group = row["comparison_group"]
        group_jobs.setdefault(group, set()).add(jobs)
        group_threads.setdefault(group, set()).add(radigest_threads)
        group_conditions.setdefault(group, set()).add(row["condition_id"])

    if required_count < 2:
        fail(
            "config/pair_screen_scaling_cases.tsv: at least two required cases are needed"
        )
    for group, job_counts in sorted(group_jobs.items()):
        if 1 not in job_counts:
            fail(
                f"config/pair_screen_scaling_cases.tsv: comparison_group {group!r} "
                "must include a jobs=1 baseline"
            )
        if len(job_counts) < 2:
            fail(
                f"config/pair_screen_scaling_cases.tsv: comparison_group {group!r} "
                "must include at least two job counts"
            )
    for group, thread_counts in sorted(group_threads.items()):
        if len(thread_counts) != 1 or 1 not in thread_counts:
            fail(
                f"config/pair_screen_scaling_cases.tsv: comparison_group {group!r} "
                "must keep radigest_threads fixed at 1"
            )
    for group, condition_ids_for_group in sorted(group_conditions.items()):
        if len(condition_ids_for_group) != 1:
            fail(
                f"config/pair_screen_scaling_cases.tsv: comparison_group {group!r} "
                "must not mix conditions"
            )

    print("Pair-screen scaling case checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
