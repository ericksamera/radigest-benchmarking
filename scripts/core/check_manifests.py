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
from typing import Iterable, NoReturn

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
    "config/synthetic_expected.tsv": [
        "case_id",
        "record_id",
        "enzymes",
        "min",
        "max",
        "options",
        "expected_intervals_0based_halfopen",
        "expected_gff_1based_closed",
        "note",
    ],
    "config/references.tsv": [
        "reference_id",
        "display_name",
        "accession",
        "source_type",
        "output_gzip",
        "output_plain",
        "required_for_nonempirical",
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
    "config/comparator_cases.tsv": [
        "case_id",
        "tool_id",
        "dataset_id",
        "condition_id",
        "reference_path",
        "comparison_mode",
        "required_for_nonempirical",
        "notes",
    ],
    "config/screening_speed_cases.tsv": [
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
        "required_for_nonempirical",
        "command_template",
        "notes",
    ],
    "config/thread_scaling_cases.tsv": [
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
    ],
    "config/matched_tool_timing_cases.tsv": [
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
    ],
    "config/empirical_libraries.tsv": [
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
        "min_mapq",
        "exclude_duplicates",
        "max_tlen",
        "notes",
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
        "matched_tool_timing",
    },
    "config/scenarios/reviewer_empirical.yml": {"empirical"},
    "config/scenarios/reviewer_all.yml": {"include_scenarios", "release_contract"},
}

EXTRA_REQUIRED_FILES = [
    "config/candidate_enzymes.txt",
    "data/synthetic/synthetic_validation.fa",
    "data/synthetic/comparator_ecori_msei_smoke.fa",
    "scripts/validation/validate_synthetic.py",
    "scripts/manuscript/make_synthetic_validation_table.py",
    "scripts/reference/fetch_ncbi_reference.py",
    "scripts/reference/prepare_plain_reference.py",
    "scripts/reference/write_reference_checksums.py",
    "scripts/validation/normalize_radigest_tsv.py",
    "scripts/validation/compare_interval_sets.py",
    "scripts/comparators/run_digital_rads.sh",
    "scripts/comparators/normalize_digital_rads.py",
    "scripts/comparators/run_ddradseqtools_rsitesearch.sh",
    "scripts/comparators/normalize_ddradseqtools_fragments.py",
    "scripts/comparators/summarize_ddradseqtools_fragments.py",
    "scripts/comparators/build_cut_equivalence_table.py",
    "scripts/comparators/build_comparator_case_matrix.py",
    "scripts/performance/run_radigest_timing.py",
    "scripts/performance/summarize_radigest_timing.py",
    "scripts/performance/run_radigest_screening.py",
    "scripts/performance/summarize_screening_speed.py",
    "scripts/performance/summarize_thread_scaling.py",
    "scripts/performance/run_matched_tool_timing.py",
    "scripts/performance/summarize_matched_tool_timing.py",
    "scripts/manuscript/make_input_format_table.py",
    "scripts/manuscript/make_screening_speed_table.py",
    "scripts/manuscript/make_thread_scaling_table.py",
    "scripts/manuscript/make_performance_figures.R",
    "scripts/manuscript/make_matched_tool_timing_table.py",
    "scripts/core/check_empirical_libraries.py",
    "scripts/empirical/write_bam_manifest.py",
    "scripts/core/check_artifacts.py",
    "scripts/audit/build_artifact_status.py",
    "scripts/audit/build_claim_audit.py",
    "scripts/audit/build_environment_table.py",
    "scripts/audit/build_release_checklist.py",
    "scripts/audit/build_output_index.py",
    "scripts/audit/check_audit_release.py",
    "scripts/audit/check_release_checklist.py",
    "workflow/Snakefile",
    "workflow/rules/radigest.smk",
    "workflow/rules/validation.smk",
    "workflow/rules/references.smk",
    "workflow/rules/comparators.smk",
    "workflow/rules/performance.smk",
    "workflow/rules/empirical.smk",
    "workflow/rules/manuscript.smk",
    "workflow/rules/audit.smk",
    "workflow/envs/comparators.yml",
    "workflow/envs/figures.yml",
    "workflow/envs/empirical.yml",
    "workflow/envs/radigest-build.yml",
]

BOOL_COLUMNS = {
    "config/datasets.tsv": ["required_for_smoke"],
    "config/artifacts.tsv": ["required_for_release"],
    "config/references.tsv": ["required_for_nonempirical"],
    "config/comparator_cases.tsv": ["required_for_nonempirical"],
    "config/screening_speed_cases.tsv": ["required_for_nonempirical"],
    "config/thread_scaling_cases.tsv": ["required_for_nonempirical"],
    "config/matched_tool_timing_cases.tsv": ["required_for_nonempirical"],
    "config/empirical_libraries.tsv": [
        "enabled",
        "include_for_manuscript",
        "exclude_duplicates",
    ],
}

DNA_RE = re.compile(r"^[ACGTRYSWKMBDHVN]+$", re.IGNORECASE)
TOP_LEVEL_RE = re.compile(r"^([A-Za-z0-9_\-]+):\s*(?:#.*)?$")


def fail(message: str) -> NoReturn:
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
        fieldnames = reader.fieldnames
        if fieldnames is None:
            fail(f"{path} has no header")
        fieldname_set = set(fieldnames)
        missing = [column for column in required_columns if column not in fieldname_set]
        if missing:
            fail(f"{path} missing columns: {', '.join(missing)}")
        rows = [
            row
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]
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


def parse_expected_intervals(value: str) -> list[tuple[int, int]]:
    value = value.strip()
    if value in {"", "NONE"}:
        return []
    intervals: list[tuple[int, int]] = []
    for part in value.split(";"):
        part = part.strip()
        if not (part.startswith("[") and part.endswith(")")):
            fail(f"invalid expected interval syntax: {part!r}")
        start, end = part[1:-1].split(",", 1)
        try:
            start_i = int(start)
            end_i = int(end)
        except ValueError:
            fail(f"invalid expected interval coordinates: {part!r}")
        if end_i < start_i:
            fail(f"expected interval end before start: {part!r}")
        intervals.append((start_i, end_i))
    return intervals


def check_tsv_semantics(path: str, rows: list[dict[str, str]]) -> None:
    if path == "config/enzymes.tsv":
        for row in rows:
            enzyme = row["enzyme_id"]
            sequence = row["recognition_sequence"]
            if not DNA_RE.fullmatch(sequence):
                fail(
                    f"{path}: enzyme {enzyme} has non-IUPAC recognition sequence {sequence!r}"
                )
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
                fail(
                    f"{path}: condition {condition} min_size/max_size must be integers"
                )
            if min_size < 0 or max_size <= min_size:
                fail(f"{path}: condition {condition} has invalid size interval")
    if path == "config/synthetic_expected.tsv":
        for row in rows:
            case = row["case_id"]
            try:
                min_size = int(row["min"])
                max_size = int(row["max"])
            except ValueError:
                fail(f"{path}: case {case} min/max must be integers")
            if min_size < 0 or max_size < min_size:
                fail(f"{path}: case {case} has invalid size interval")
            parse_expected_intervals(row["expected_intervals_0based_halfopen"])
            options = [
                option.strip()
                for option in row["options"].split(",")
                if option.strip() and option.strip() != "none"
            ]
            allowed_options = {"include_ends", "allow_same"}
            invalid_options = sorted(set(options) - allowed_options)
            if invalid_options:
                fail(
                    f"{path}: case {case} has invalid options: "
                    + ", ".join(invalid_options)
                )
    if path == "config/references.tsv":
        for row in rows:
            reference = row["reference_id"]
            source_type = row["source_type"]
            if source_type not in {"ncbi_datasets", "url"}:
                fail(
                    f"{path}: reference {reference} has invalid source_type {source_type!r}"
                )
            accession = row["accession"]
            if not accession or accession.upper() in {
                "NA",
                "N/A",
                "NONE",
                "NULL",
                "TO_BE_FILLED",
                "TBD",
            }:
                fail(f"{path}: reference {reference} has missing accession")
            gzip_path = row["output_gzip"]
            plain_path = row["output_plain"]
            expected_gzip = f"data/reference/{reference}.fa.gz"
            expected_plain = f"data/reference/{reference}.fa"
            if gzip_path != expected_gzip:
                fail(
                    f"{path}: reference {reference} output_gzip must be {expected_gzip}"
                )
            if plain_path != expected_plain:
                fail(
                    f"{path}: reference {reference} output_plain must be {expected_plain}"
                )

    if path == "config/comparator_cases.tsv":
        valid_modes = {"exact", "length-only"}
        valid_tools = {"digital_rads", "ddradseqtools", "simrad", "ddgrader"}
        for row in rows:
            case = row["case_id"]
            tool = row["tool_id"]
            if tool not in valid_tools:
                fail(f"{path}: case {case} has unknown tool_id {tool!r}")
            mode = row["comparison_mode"]
            if mode not in valid_modes:
                fail(f"{path}: case {case} has invalid comparison_mode {mode!r}")
            ref_path = row["reference_path"]
            if ref_path == "NA" or ref_path.startswith("/"):
                fail(
                    f"{path}: case {case} reference_path must be a relative repository path"
                )

    if path == "config/thread_scaling_cases.tsv":
        valid_categories = {"thread_scaling"}
        valid_output_modes = {"json", "fragments_tsv", "both"}
        valid_input_formats = {"plain", "gzip"}
        for row in rows:
            case = row["case_id"]
            if row["category"] not in valid_categories:
                fail(f"{path}: case {case} has invalid category {row['category']!r}")
            if row["output_mode"] not in valid_output_modes:
                fail(
                    f"{path}: case {case} has invalid output_mode {row['output_mode']!r}"
                )
            if row["input_format"] not in valid_input_formats:
                fail(
                    f"{path}: case {case} has invalid input_format {row['input_format']!r}"
                )
            ref_path = row["reference_path"]
            if ref_path == "NA" or ref_path.startswith("/"):
                fail(
                    f"{path}: case {case} reference_path must be a relative repository path"
                )
            try:
                min_size = int(row["min_size"])
                max_size = int(row["max_size"])
                threads = int(row["threads"])
                runs = int(row["runs"])
            except ValueError:
                fail(f"{path}: case {case} min/max/threads/runs must be integers")
            if min_size < 0 or max_size <= min_size:
                fail(f"{path}: case {case} has invalid size interval")
            if threads < 1 or runs < 1:
                fail(f"{path}: case {case} threads/runs must be >= 1")

    if path == "config/matched_tool_timing_cases.tsv":
        valid_tools = {
            "radigest",
            "digital_rads",
            "ddradseqtools",
            "simrad",
            "ddgrader",
        }
        valid_scopes = {
            "native_digest",
            "raw_tool_wrapper",
            "count_only_wrapper",
            "binned_screening_wrapper",
        }
        for row in rows:
            case = row["case_id"]
            if row["tool_id"] not in valid_tools:
                fail(f"{path}: case {case} has invalid tool_id {row['tool_id']!r}")
            if row["timing_scope"] not in valid_scopes:
                fail(
                    f"{path}: case {case} has invalid timing_scope "
                    f"{row['timing_scope']!r}"
                )
            ref_path = row["reference_path"]
            if ref_path == "NA" or ref_path.startswith("/"):
                fail(
                    f"{path}: case {case} reference_path must be a relative "
                    "repository path"
                )
            try:
                min_size = int(row["min_size"])
                max_size = int(row["max_size"])
                runs = int(row["runs"])
            except ValueError:
                fail(f"{path}: case {case} min/max/runs must be integers")
            if min_size < 0 or max_size <= min_size:
                fail(f"{path}: case {case} has invalid size interval")
            if runs < 1:
                fail(f"{path}: case {case} runs must be >= 1")

    if path == "config/artifacts.tsv":
        for row in rows:
            claim = row["claim_id"]
            for column in ["required_output", "manuscript_artifact"]:
                value = row[column]
                if value == "NA" or value.startswith("/"):
                    fail(
                        f"{path}: claim {claim} column {column} must be a relative repository path"
                    )


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
