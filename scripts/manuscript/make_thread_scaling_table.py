#!/usr/bin/env python3
"""Build the manuscript-facing radigest thread-scaling table."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import NoReturn

TABLE_COLUMNS = [
    "dataset_id",
    "dataset_display_name",
    "condition_id",
    "condition_display_name",
    "output_mode",
    "reference_path",
    "threads",
    "runs",
    "successful_runs",
    "retained_fragments",
    "median_wall_seconds",
    "wall_seconds_stdev",
    "speedup_vs_1_thread_median",
    "speedup_vs_1_thread_stdev",
    "parallel_efficiency_vs_1_thread",
    "status",
    "claim_boundary",
]

CLAIM_BOUNDARY = (
    "Intra-tool radigest thread scaling only. Results are stratified by output "
    "mode, and each comparison group must retain the same fragment count across "
    "thread counts before speedup is interpreted."
)


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


def keyed(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        out[row[key]] = row
    return out


def build_table_rows(
    summary_rows: list[dict[str, str]],
    datasets: dict[str, dict[str, str]],
    conditions: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in sorted(
        summary_rows,
        key=lambda item: (
            item["dataset_id"],
            item["condition_id"],
            item["output_mode"],
            int(item["threads"]),
        ),
    ):
        dataset = datasets.get(row["dataset_id"], {})
        condition = conditions.get(row["condition_id"], {})
        rows.append(
            {
                "dataset_id": row["dataset_id"],
                "dataset_display_name": dataset.get("display_name", row["dataset_id"]),
                "condition_id": row["condition_id"],
                "condition_display_name": condition.get(
                    "display_name", row["condition_id"]
                ),
                "output_mode": row["output_mode"],
                "reference_path": row["reference_path"],
                "threads": row["threads"],
                "runs": row["configured_runs"],
                "successful_runs": row["successful_runs"],
                "retained_fragments": row["retained_fragments"],
                "median_wall_seconds": row["wall_seconds_median"],
                "wall_seconds_stdev": row.get("wall_seconds_stdev", "NA"),
                "speedup_vs_1_thread_median": row["speedup_vs_1_thread_median"],
                "speedup_vs_1_thread_stdev": row.get("speedup_vs_1_thread_stdev", "NA"),
                "parallel_efficiency_vs_1_thread": row[
                    "parallel_efficiency_vs_1_thread"
                ],
                "status": row["status"],
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return rows


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=TABLE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--datasets", required=True, type=Path)
    parser.add_argument("--conditions", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary_rows = read_tsv(
        args.summary,
        [
            "dataset_id",
            "condition_id",
            "output_mode",
            "reference_path",
            "threads",
            "configured_runs",
            "successful_runs",
            "retained_fragments",
            "wall_seconds_median",
            "speedup_vs_1_thread_median",
            "parallel_efficiency_vs_1_thread",
            "status",
        ],
    )
    datasets = keyed(
        read_tsv(args.datasets, ["dataset_id", "display_name"]),
        "dataset_id",
    )
    conditions = keyed(
        read_tsv(args.conditions, ["condition_id", "display_name"]), "condition_id"
    )

    table_rows = build_table_rows(summary_rows, datasets, conditions)
    write_rows(args.out, table_rows)

    failed = [row for row in table_rows if row["status"] != "PASS"]
    if args.require_pass and failed:
        print(
            f"{len(failed)} of {len(table_rows)} thread-scaling table rows failed; "
            f"see {args.out}",
            file=sys.stderr,
        )
        return 1

    print(f"Wrote {len(table_rows)} thread-scaling table rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
