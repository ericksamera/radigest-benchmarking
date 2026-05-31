#!/usr/bin/env python3
"""Audit reproducibility state for the radigest comparison repository."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from collections import Counter
from pathlib import Path

TARGET_RE = re.compile(r"^([A-Za-z0-9_.-]+)\s*:")

REQUIRED_FILES = [
    "README.md",
    "CITATION.cff",
    "LICENSE",
    "Makefile",
    "config/enzymes.tsv",
    "config/benchmark_conditions.tsv",
    "config/datasets.tsv",
    "config/empirical_recovery.tsv",
    "config/synthetic_expected.tsv",
    "data/synthetic/synthetic_validation.fa",
    "workflow/Snakefile",
    "workflow/empirical_recovery.smk",
    "docs/reproduce_results.md",
    "docs/transparency_checklist.md",
    "scripts/ensure_radigest.sh",
    "scripts/validate_synthetic.py",
    "scripts/extract_bam_recovery_inputs.sh",
    "scripts/summarize_empirical_recovery.py",
    "scripts/downsample_tlens_per_sample.py",
    "scripts/make_manuscript_tables.py",
]

MANUSCRIPT_TABLES = [
    "manuscript_tables/claim_audit.tsv",
    "manuscript_tables/table_02_synthetic_validation.tsv",
    "manuscript_tables/table_03_interval_comparisons.tsv",
    "manuscript_tables/table_04_matched_timing.tsv",
    "manuscript_tables/table_05_screening_speed.tsv",
    "manuscript_tables/table_06_input_format.tsv",
    "manuscript_tables/table_07_mismatch_explanations.tsv",
    "manuscript_tables/table_08_empirical_recovery.tsv",
    "manuscript_tables/table_s01_environment.tsv",
    "manuscript_tables/table_s02_radigest_thread_scaling.tsv",
    "manuscript_tables/table_s03_pair_screen_job_scaling.tsv",
    "manuscript_tables/table_s04_empirical_recovery_sensitivity.tsv",
]


def is_target_line(line: str) -> bool:
    if line.startswith((" ", "\t", "#")):
        return False
    if ":=" in line or "?=" in line or "+=" in line:
        return False
    before = line.split(":", 1)[0]
    if "=" in before:
        return False
    return bool(TARGET_RE.match(line))


def audit_makefile(path: Path) -> list[str]:
    if not path.exists():
        return [f"FAIL\tmakefile_missing\t{path}"]

    targets: list[str] = []
    for line in path.read_text().splitlines():
        if is_target_line(line):
            match = TARGET_RE.match(line)
            if match:
                targets.append(match.group(1))

    out: list[str] = []
    for target, count in sorted(Counter(targets).items()):
        if count > 1:
            out.append(f"FAIL\tduplicate_make_target\t{target}\tcount={count}")

    required_targets = [
        "check",
        "validate-radigest",
        "radigest-local",
        "empirical-recovery-dry-run",
        "empirical-recovery",
        "manuscript-tables",
    ]

    target_set = set(targets)
    for target in required_targets:
        status = "PASS" if target in target_set else "WARN"
        out.append(f"{status}\tmake_target\t{target}")

    return out


def audit_required_files() -> list[str]:
    out = []
    for filename in REQUIRED_FILES:
        status = "PASS" if Path(filename).exists() else "FAIL"
        out.append(f"{status}\trequired_file\t{filename}")
    return out


def audit_manuscript_tables() -> list[str]:
    out = []
    for filename in MANUSCRIPT_TABLES:
        status = "PASS" if Path(filename).exists() else "WARN"
        out.append(f"{status}\tmanuscript_table\t{filename}")
    return out


def audit_to_be_filled(paths: list[Path]) -> list[str]:
    out = []
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(errors="replace")
        count = text.count("TO_BE_FILLED")
        status = "PASS" if count == 0 else "WARN"
        out.append(f"{status}\tto_be_filled\t{path}\tcount={count}")
    return out


def audit_empirical_config(path: Path) -> list[str]:
    out: list[str] = []
    if not path.exists():
        return [f"FAIL\tempirical_config_missing\t{path}"]

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)

    expected = {
        "sockeye_ddrad": ("200", "400"),
        "trichoderma_ddrad": ("200", "500"),
    }

    seen = {row.get("dataset_id", ""): row for row in rows}

    for dataset, (min_expected, max_expected) in expected.items():
        row = seen.get(dataset)
        if row is None:
            out.append(f"FAIL\tempirical_dataset_missing\t{dataset}")
            continue

        observed = (row.get("nominal_min", ""), row.get("nominal_max", ""))
        status = "PASS" if observed == (min_expected, max_expected) else "FAIL"
        out.append(
            f"{status}\tempirical_window\t{dataset}\t"
            f"observed={observed[0]}-{observed[1]}\t"
            f"expected={min_expected}-{max_expected}"
        )

    return out


def audit_git_staged_generated() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            check=False,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        return ["WARN\tgit_not_found"]

    if result.returncode != 0:
        return ["WARN\tgit_diff_cached_failed"]

    generated_prefixes = (
        "results/",
        "benchmark/",
        "data/reference/",
        "data/empirical/",
        "external/",
        ".local/",
        "codebase.json",
    )

    out: list[str] = []
    for line in result.stdout.splitlines():
        if line.startswith(generated_prefixes):
            out.append(f"WARN\tstaged_generated_path\t{line}")

    if not out:
        out.append("PASS\tstaged_generated_path\tnone")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fail-on-warn", action="store_true")
    args = parser.parse_args()

    checks: list[str] = []
    checks.extend(audit_required_files())
    checks.extend(audit_makefile(Path("Makefile")))
    checks.extend(audit_empirical_config(Path("config/empirical_recovery.tsv")))
    checks.extend(
        audit_to_be_filled(
            [
                Path("CITATION.cff"),
                Path("config/datasets.tsv"),
                Path("config/empirical_recovery.tsv"),
                Path("README.md"),
            ]
        )
    )
    checks.extend(audit_manuscript_tables())
    checks.extend(audit_git_staged_generated())

    print("status\tcheck\titem\tdetails")
    failed = False
    warned = False

    for check in checks:
        print(check)
        if check.startswith("FAIL\t"):
            failed = True
        elif check.startswith("WARN\t"):
            warned = True

    if failed:
        return 2
    if warned and args.fail_on_warn:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
