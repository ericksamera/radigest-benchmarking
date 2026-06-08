#!/usr/bin/env python3
"""Build the manuscript-facing Stage 5b screening-speed table."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import NoReturn

OUTPUT_COLUMNS = [
    "case_id",
    "dataset_id",
    "condition_id",
    "candidate_enzyme_count",
    "candidate_pairs_evaluated",
    "screening_binary",
    "jobs",
    "radigest_threads",
    "build_workers",
    "runs",
    "median_wall_seconds",
    "wall_seconds_stdev",
    "candidate_pairs_per_second_median",
    "candidate_pairs_per_second_stdev",
    "reported_pair_consistency",
    "reported_pair_coverage",
    "status",
    "claim_boundary",
]

REQUIRED_SUMMARY_COLUMNS = [
    "case_id",
    "dataset_id",
    "condition_id",
    "candidate_enzyme_count",
    "candidate_pairs_evaluated",
    "screening_binary",
    "jobs",
    "radigest_threads",
    "build_workers",
    "configured_runs",
    "wall_seconds_median",
    "candidate_pairs_per_second_median",
    "reported_pair_consistency",
    "reported_pair_coverage",
    "status",
]


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


def make_rows(summary_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in summary_rows:
        rows.append(
            {
                "case_id": row["case_id"],
                "dataset_id": row["dataset_id"],
                "condition_id": row["condition_id"],
                "candidate_enzyme_count": row["candidate_enzyme_count"],
                "candidate_pairs_evaluated": row["candidate_pairs_evaluated"],
                "screening_binary": row["screening_binary"],
                "jobs": row["jobs"],
                "radigest_threads": row["radigest_threads"],
                "build_workers": row["build_workers"],
                "runs": row["configured_runs"],
                "median_wall_seconds": row["wall_seconds_median"],
                "wall_seconds_stdev": row.get("wall_seconds_stdev", "NA"),
                "candidate_pairs_per_second_median": row[
                    "candidate_pairs_per_second_median"
                ],
                "candidate_pairs_per_second_stdev": row.get(
                    "candidate_pairs_per_second_stdev", "NA"
                ),
                "reported_pair_consistency": row["reported_pair_consistency"],
                "reported_pair_coverage": row["reported_pair_coverage"],
                "status": row["status"],
                "claim_boundary": (
                    "Cached radigest-screen-pairs-cached throughput timing only; "
                    "not a cross-tool coordinate-equivalence claim."
                ),
            }
        )
    return rows


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = make_rows(read_tsv(args.summary, REQUIRED_SUMMARY_COLUMNS))
    write_rows(args.out, rows)
    failed = [row for row in rows if row["status"] != "PASS"]
    if args.require_pass and failed:
        print(
            f"{len(failed)} of {len(rows)} screening-speed table rows failed; "
            f"see {args.out}",
            file=sys.stderr,
        )
        return 1
    print(f"Wrote {len(rows)} screening-speed table rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
