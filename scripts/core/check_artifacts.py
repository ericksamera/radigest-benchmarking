#!/usr/bin/env python3
"""Validate manuscript artifact contracts.

The artifact manifest maps manuscript claims and curated outputs to the
upstream files that must already exist before manuscript tables are exported.
This script checks those contracts without regenerating analyses.
"""

from __future__ import annotations

import argparse
import csv
import glob
import sys
from pathlib import Path

REQUIRED_COLUMNS = [
    "artifact_id",
    "category_id",
    "required_input",
    "generated_artifact",
    "producer_target",
    "required_for_release",
]

OUTPUT_COLUMNS = [
    "artifact_id",
    "category_id",
    "claim_id",
    "contract_type",
    "path",
    "status",
    "required_for_release",
    "producer_target",
    "producer_workflow",
    "manuscript_artifact",
    "notes",
]

TRUE_VALUES = {"1", "true", "yes", "y"}


def split_paths(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def is_true(value: str) -> bool:
    return value.strip().lower() in TRUE_VALUES


def read_manifest(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing artifact manifest: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")

        missing = [name for name in REQUIRED_COLUMNS if name not in reader.fieldnames]
        if missing:
            missing_text = ", ".join(missing)
            raise ValueError(f"{path}: missing required column(s): {missing_text}")

        rows: list[dict[str, str]] = []
        for row in reader:
            rows.append(
                {
                    key: "" if value is None else value
                    for key, value in row.items()
                    if key is not None
                }
            )
        return rows


def path_status(path_text: str) -> str:
    if path_text == "":
        return "not_applicable"
    if any(ch in path_text for ch in "*?["):
        return "present" if glob.glob(path_text) else "missing"
    return "present" if Path(path_text).exists() else "missing"


def check_rows(
    manifest_rows: list[dict[str, str]],
    check_generated: bool,
    release_only: bool,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in manifest_rows:
        release_required = is_true(row.get("required_for_release", ""))
        if release_only and not release_required:
            continue

        common = {
            "artifact_id": row.get("artifact_id", ""),
            "category_id": row.get("category_id", ""),
            "claim_id": row.get("claim_id", ""),
            "required_for_release": "true" if release_required else "false",
            "producer_target": row.get("producer_target", ""),
            "producer_workflow": row.get("producer_workflow", ""),
            "manuscript_artifact": row.get("manuscript_artifact", ""),
            "notes": row.get("notes", ""),
        }

        required_inputs = split_paths(row.get("required_input", ""))
        if not required_inputs:
            out.append(
                {
                    **common,
                    "contract_type": "required_input",
                    "path": "",
                    "status": "not_applicable",
                }
            )
        for path_text in required_inputs:
            out.append(
                {
                    **common,
                    "contract_type": "required_input",
                    "path": path_text,
                    "status": path_status(path_text),
                }
            )

        if check_generated:
            for path_text in split_paths(row.get("generated_artifact", "")):
                out.append(
                    {
                        **common,
                        "contract_type": "generated_artifact",
                        "path": path_text,
                        "status": path_status(path_text),
                    }
                )
    return out


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, str]]) -> tuple[int, int]:
    missing = sum(1 for row in rows if row["status"] == "missing")
    release_missing = sum(
        1
        for row in rows
        if row["status"] == "missing" and row["required_for_release"] == "true"
    )
    return missing, release_missing


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("config/artifacts.tsv"))
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("results/processed/artifact_contracts.tsv"),
    )
    parser.add_argument(
        "--check-generated",
        action="store_true",
        help="Also check curated/generated manuscript artifact paths.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero exit code when checked paths are missing.",
    )
    parser.add_argument(
        "--release-only",
        action="store_true",
        help="Only check rows marked required_for_release=true.",
    )
    args = parser.parse_args(argv)

    try:
        rows = check_rows(
            read_manifest(args.manifest),
            args.check_generated,
            args.release_only,
        )
        write_tsv(args.out, rows)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    missing, release_missing = summarize(rows)
    print(
        f"wrote {args.out}; checked={len(rows)} missing={missing} "
        f"release_missing={release_missing}",
        file=sys.stderr,
    )
    if args.strict and missing:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
