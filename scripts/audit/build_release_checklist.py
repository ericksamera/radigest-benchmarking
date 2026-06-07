#!/usr/bin/env python3
"""Build a release checklist from audit outputs."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import NoReturn

CHECK_COLUMNS = [
    "check_id",
    "category",
    "description",
    "status",
    "blocking",
    "evidence",
    "notes",
]
CLAIM_COLUMNS = ["claim_id", "required_for_release", "release_status"]
ARTIFACT_COLUMNS = [
    "claim_id",
    "required_for_release",
    "status",
    "output_exists",
    "output_bytes",
    "manuscript_artifact_exists",
    "manuscript_artifact_bytes",
]
INDEX_COLUMNS = ["path", "roles", "required_for_release", "status"]
ENV_COLUMNS = ["key", "value", "source"]

REQUIRED_ENV_KEYS = {
    "timestamp_utc",
    "git_commit",
    "git_branch",
    "git_dirty",
    "python_version",
    "snakemake_version",
    "radigest_path",
    "radigest_version",
    "radigest_screen_pairs_cached_version",
    "radigest_screen_pairs_cached_path",
    "radigest_design_path",
    "radigest_design_version",
}


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_tsv(path: Path, required_columns: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames
        if fieldnames is None:
            fail(f"{path}: missing header")
        fieldname_set = set(fieldnames)
        missing = [column for column in required_columns if column not in fieldname_set]
        if missing:
            fail(f"{path}: missing columns: {', '.join(missing)}")
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
        fail(f"{path}: no rows")
    return rows


def checklist_row(
    *,
    check_id: str,
    category: str,
    description: str,
    status: str,
    blocking: bool,
    evidence: str,
    notes: str,
) -> dict[str, str]:
    return {
        "check_id": check_id,
        "category": category,
        "description": description,
        "status": status,
        "blocking": "true" if blocking else "false",
        "evidence": evidence,
        "notes": notes,
    }


def build_checks(
    *,
    claim_rows: list[dict[str, str]],
    artifact_rows: list[dict[str, str]],
    output_rows: list[dict[str, str]],
    env_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []

    required_claims = [
        item for item in claim_rows if item["required_for_release"].lower() == "true"
    ]
    failed_claims = [
        item for item in required_claims if item["release_status"] != "PASS"
    ]
    checks.append(
        checklist_row(
            check_id="required_claims_pass",
            category="claims",
            description="All release-required claims pass the claim audit.",
            status="PASS" if not failed_claims else "FAIL",
            blocking=True,
            evidence=f"{len(required_claims)} required claims checked",
            notes=";".join(item["claim_id"] for item in failed_claims),
        )
    )

    required_artifacts = [
        item for item in artifact_rows if item["required_for_release"].lower() == "true"
    ]
    failed_artifacts = [item for item in required_artifacts if item["status"] != "PASS"]
    checks.append(
        checklist_row(
            check_id="required_artifacts_present",
            category="artifacts",
            description="All release-required outputs and manuscript artifacts are present and non-empty.",
            status="PASS" if not failed_artifacts else "FAIL",
            blocking=True,
            evidence=f"{len(required_artifacts)} required artifact rows checked",
            notes=";".join(item["claim_id"] for item in failed_artifacts),
        )
    )

    required_output_failures = [
        item
        for item in output_rows
        if item["required_for_release"].lower() == "true" and item["status"] != "PASS"
    ]
    checks.append(
        checklist_row(
            check_id="required_paths_indexed",
            category="outputs",
            description="Output index reports PASS for all release-required paths.",
            status="PASS" if not required_output_failures else "FAIL",
            blocking=True,
            evidence=f"{len(output_rows)} output-index rows checked",
            notes=";".join(item["path"] for item in required_output_failures[:20]),
        )
    )

    optional_blockers = [
        item
        for item in claim_rows
        if item["required_for_release"].lower() == "false"
        and item["release_status"] == "FAIL"
    ]
    checks.append(
        checklist_row(
            check_id="optional_claims_nonblocking",
            category="claims",
            description="Optional claims do not block the nonempirical release.",
            status="PASS" if not optional_blockers else "FAIL",
            blocking=True,
            evidence=f"{len(optional_blockers)} optional blocking failures observed",
            notes=";".join(item["claim_id"] for item in optional_blockers),
        )
    )

    env_by_key = {item["key"]: item["value"] for item in env_rows}
    missing_env = sorted(REQUIRED_ENV_KEYS - set(env_by_key))
    checks.append(
        checklist_row(
            check_id="environment_core_keys_present",
            category="environment",
            description="Environment table includes required reproducibility keys.",
            status="PASS" if not missing_env else "FAIL",
            blocking=True,
            evidence=f"{len(env_rows)} environment rows checked",
            notes=";".join(missing_env),
        )
    )

    git_dirty = env_by_key.get("git_dirty", "NA")
    checks.append(
        checklist_row(
            check_id="git_dirty_recorded",
            category="environment",
            description="Git dirty state is recorded for release provenance.",
            status="WARN" if git_dirty == "true" else "PASS",
            blocking=False,
            evidence=f"git_dirty={git_dirty}",
            notes=(
                "Dirty tree should be cleaned before final release."
                if git_dirty == "true"
                else ""
            ),
        )
    )

    empirical = [item for item in claim_rows if item["claim_id"] == "C11"]
    empirical_optional = (
        bool(empirical) and empirical[0]["required_for_release"].lower() == "false"
    )
    checks.append(
        checklist_row(
            check_id="empirical_optional_for_nonempirical_release",
            category="scope",
            description="Empirical recovery remains optional for the nonempirical release.",
            status="PASS" if empirical_optional else "FAIL",
            blocking=True,
            evidence=(
                "C11 required_for_release=false"
                if empirical_optional
                else "C11 not optional"
            ),
            notes="",
        )
    )

    return checks


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=CHECK_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim-audit", required=True, type=Path)
    parser.add_argument("--artifact-status", required=True, type=Path)
    parser.add_argument("--environment", required=True, type=Path)
    parser.add_argument("--output-index", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checks = build_checks(
        claim_rows=read_tsv(args.claim_audit, CLAIM_COLUMNS),
        artifact_rows=read_tsv(args.artifact_status, ARTIFACT_COLUMNS),
        env_rows=read_tsv(args.environment, ENV_COLUMNS),
        output_rows=read_tsv(args.output_index, INDEX_COLUMNS),
    )
    write_tsv(args.out, checks)
    print(f"Wrote {len(checks)} release-checklist rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
