#!/usr/bin/env python3
"""Validate the artifact release-contract manifest."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "config" / "artifacts.tsv"
REQUIRED_COLUMNS = [
    "claim_id",
    "category",
    "required_output",
    "manuscript_artifact",
    "producer_rule",
    "required_for_release",
    "notes",
]
VALID_CATEGORIES = {"validation", "comparators", "performance", "empirical"}
VALID_PRODUCER_RULES = {
    "validation_all",
    "comparators_all",
    "performance_all",
    "empirical_all",
}
BOOL_VALUES = {"true", "false"}


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_artifacts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames
        if fieldnames is None:
            fail(f"{path.relative_to(ROOT)}: missing header")
        fieldname_set = set(fieldnames)
        missing = [column for column in REQUIRED_COLUMNS if column not in fieldname_set]
        if missing:
            fail(f"{path.relative_to(ROOT)}: missing columns: {', '.join(missing)}")
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


def check_relative_output(value: str, *, claim_id: str, column: str) -> None:
    if value.startswith("/") or value in {"", "NA"}:
        fail(
            f"config/artifacts.tsv: claim {claim_id} column {column} must be a "
            "relative non-NA path"
        )
    if ".." in Path(value).parts:
        fail(
            f"config/artifacts.tsv: claim {claim_id} column {column} may not "
            "contain '..' path components"
        )


def main() -> int:
    rows = read_artifacts(ARTIFACTS)
    seen_claims: set[str] = set()
    outputs_by_path: dict[str, list[str]] = defaultdict(list)

    for line_number, row in enumerate(rows, start=2):
        claim_id = row["claim_id"]
        if not claim_id:
            fail(f"config/artifacts.tsv:{line_number} empty claim_id")
        if claim_id in seen_claims:
            fail(f"config/artifacts.tsv:{line_number} duplicate claim_id={claim_id}")
        seen_claims.add(claim_id)

        category = row["category"]
        if category not in VALID_CATEGORIES:
            fail(
                f"config/artifacts.tsv:{line_number} claim {claim_id} has invalid "
                f"category={category!r}"
            )
        producer_rule = row["producer_rule"]
        if producer_rule not in VALID_PRODUCER_RULES:
            fail(
                f"config/artifacts.tsv:{line_number} claim {claim_id} has invalid "
                f"producer_rule={producer_rule!r}"
            )
        required = row["required_for_release"].lower()
        if required not in BOOL_VALUES:
            fail(
                f"config/artifacts.tsv:{line_number} claim {claim_id} "
                "required_for_release must be true or false"
            )

        for column in ["required_output", "manuscript_artifact"]:
            check_relative_output(row[column], claim_id=claim_id, column=column)
        outputs_by_path[row["required_output"]].append(claim_id)

    duplicated_outputs = {
        path: claim_ids
        for path, claim_ids in outputs_by_path.items()
        if len(claim_ids) > 1
    }
    if duplicated_outputs:
        details = "; ".join(
            f"{path}: {','.join(claim_ids)}"
            for path, claim_ids in sorted(duplicated_outputs.items())
        )
        fail(f"config/artifacts.tsv: required_output paths must be unique: {details}")

    print("Artifact manifest checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
