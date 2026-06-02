#!/usr/bin/env python3
"""Build artifact-status rows from config/artifacts.tsv."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NoReturn

STATUS_COLUMNS = [
    "claim_id",
    "category",
    "required_output",
    "manuscript_artifact",
    "producer_rule",
    "required_for_release",
    "output_exists",
    "output_bytes",
    "output_mtime_utc",
    "manuscript_artifact_exists",
    "manuscript_artifact_bytes",
    "manuscript_artifact_mtime_utc",
    "status",
    "notes",
]
ARTIFACT_COLUMNS = [
    "claim_id",
    "category",
    "required_output",
    "manuscript_artifact",
    "producer_rule",
    "required_for_release",
    "notes",
]
TRUE_VALUES = {"true", "1", "yes", "y"}


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
    return rows


def utc_mtime(path: Path) -> str:
    stat = path.stat()
    return (
        datetime.fromtimestamp(stat.st_mtime, timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def path_info(path: Path) -> tuple[str, str, str]:
    if not path.exists():
        return "false", "0", "NA"
    if not path.is_file():
        return "false", "0", "NA"
    return "true", str(path.stat().st_size), utc_mtime(path)


def is_true(value: str) -> bool:
    return value.strip().lower() in TRUE_VALUES


def status_for(
    *,
    required: bool,
    output_exists: str,
    output_bytes: str,
    artifact_exists: str,
    artifact_bytes: str,
) -> tuple[str, str]:
    problems: list[str] = []
    output_present = output_exists == "true" and int(output_bytes) > 0
    artifact_present = artifact_exists == "true" and int(artifact_bytes) > 0

    if not output_present:
        problems.append("required_output missing or zero bytes")
    if not artifact_present:
        problems.append("manuscript_artifact missing or zero bytes")

    if not problems:
        return "PASS", ""
    if required:
        return "FAIL", "; ".join(problems)
    return "WARN", "; ".join(problems)


def build_row(row: dict[str, str], *, root: Path) -> dict[str, str]:
    required_output = Path(row["required_output"])
    manuscript_artifact = Path(row["manuscript_artifact"])
    output_exists, output_bytes, output_mtime = path_info(root / required_output)
    artifact_exists, artifact_bytes, artifact_mtime = path_info(
        root / manuscript_artifact
    )
    status, status_notes = status_for(
        required=is_true(row["required_for_release"]),
        output_exists=output_exists,
        output_bytes=output_bytes,
        artifact_exists=artifact_exists,
        artifact_bytes=artifact_bytes,
    )
    notes = row.get("notes", "")
    if status_notes:
        notes = f"{notes} {status_notes}".strip()
    return {
        "claim_id": row["claim_id"],
        "category": row["category"],
        "required_output": row["required_output"],
        "manuscript_artifact": row["manuscript_artifact"],
        "producer_rule": row["producer_rule"],
        "required_for_release": row["required_for_release"],
        "output_exists": output_exists,
        "output_bytes": output_bytes,
        "output_mtime_utc": output_mtime,
        "manuscript_artifact_exists": artifact_exists,
        "manuscript_artifact_bytes": artifact_bytes,
        "manuscript_artifact_mtime_utc": artifact_mtime,
        "status": status,
        "notes": notes,
    }


def write_tsv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--root", default=Path("."), type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    artifact_rows = read_tsv(args.artifacts, ARTIFACT_COLUMNS)
    rows = [build_row(row, root=root) for row in artifact_rows]
    write_tsv(args.out, rows, STATUS_COLUMNS)
    print(f"Wrote {len(rows)} artifact-status rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
