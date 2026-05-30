#!/usr/bin/env python3
"""Check benchmark run-table completeness.

This script validates that results/tables/radigest_benchmark_runs.tsv contains
the expected dataset × condition × output_mode × replicate matrix.

It does not judge biological validity. It only checks that the benchmark
workflow produced complete, parseable run records with exit_status = 0.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

FIELDNAMES = [
    "dataset",
    "condition",
    "output_mode",
    "replicate",
    "status",
    "reason",
    "json_file",
    "time_file",
    "primary_output_file",
    "total_fragments",
    "total_bases",
    "elapsed_wall_seconds",
    "max_rss_kb",
    "warnings",
]


def split_csv(value: str) -> list[str]:
    """Split comma-separated CLI arguments into a clean string list."""
    return [x.strip() for x in value.split(",") if x.strip()]


def expected_replicates(n: int) -> list[str]:
    """Return expected replicate labels used by the Snakemake benchmark rules."""
    return [f"run{i}" for i in range(1, n + 1)]


def read_run_table(path: Path) -> list[dict[str, str]]:
    """Read the run-level benchmark table."""
    if not path.exists():
        raise FileNotFoundError(f"missing run table: {path}")

    rows: list[dict[str, str]] = []

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")

        for raw_row in reader:
            row = {
                key: "" if value is None else value
                for key, value in raw_row.items()
                if key is not None
            }
            rows.append(row)

    return rows


def path_exists(path_text: str) -> bool:
    """Return true when a nonempty path exists."""
    if path_text == "":
        return False
    return Path(path_text).exists()


def check_row(row: dict[str, str]) -> tuple[str, str]:
    """Check one benchmark run-table row."""
    if row.get("exit_status", "") != "0":
        return "FAIL", f"exit_status={row.get('exit_status', '')!r}"

    if not path_exists(row.get("json_file", "")):
        return "FAIL", "missing json_file"

    if not path_exists(row.get("time_file", "")):
        return "FAIL", "missing time_file"

    primary = row.get("primary_output_file", "")
    if primary and not Path(primary).exists():
        return "FAIL", "missing primary_output_file"

    if row.get("elapsed_wall_seconds", "") == "":
        return "FAIL", "missing elapsed_wall_seconds"

    if row.get("max_rss_kb", "") == "":
        return "FAIL", "missing max_rss_kb"

    if row.get("total_fragments", "") == "":
        return "FAIL", "missing total_fragments"

    if row.get("total_bases", "") == "":
        return "FAIL", "missing total_bases"

    return "PASS", ""


def missing_qc_row(
    dataset: str,
    condition: str,
    mode: str,
    replicate: str,
) -> dict[str, str]:
    """Return a QC row for an expected run that is absent."""
    return {
        "dataset": dataset,
        "condition": condition,
        "output_mode": mode,
        "replicate": replicate,
        "status": "FAIL",
        "reason": "missing run row",
        "json_file": "",
        "time_file": "",
        "primary_output_file": "",
        "total_fragments": "",
        "total_bases": "",
        "elapsed_wall_seconds": "",
        "max_rss_kb": "",
        "warnings": "",
    }


def checked_qc_row(
    dataset: str,
    condition: str,
    mode: str,
    replicate: str,
    row: dict[str, str],
    status: str,
    reason: str,
) -> dict[str, str]:
    """Return a QC row for an observed benchmark run."""
    return {
        "dataset": dataset,
        "condition": condition,
        "output_mode": mode,
        "replicate": replicate,
        "status": status,
        "reason": reason,
        "json_file": row.get("json_file", ""),
        "time_file": row.get("time_file", ""),
        "primary_output_file": row.get("primary_output_file", ""),
        "total_fragments": row.get("total_fragments", ""),
        "total_bases": row.get("total_bases", ""),
        "elapsed_wall_seconds": row.get("elapsed_wall_seconds", ""),
        "max_rss_kb": row.get("max_rss_kb", ""),
        "warnings": row.get("warnings", ""),
    }


def write_qc_table(path: Path, rows: list[dict[str, str]]) -> None:
    """Write the benchmark QC table."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs-tsv",
        type=Path,
        default=Path("results/tables/radigest_benchmark_runs.tsv"),
    )
    parser.add_argument("--expected-datasets", required=True)
    parser.add_argument("--expected-conditions", required=True)
    parser.add_argument("--expected-output-modes", required=True)
    parser.add_argument("--replicates", required=True, type=int)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("results/tables/radigest_benchmark_qc.tsv"),
    )
    args = parser.parse_args(argv)

    datasets = split_csv(args.expected_datasets)
    conditions = split_csv(args.expected_conditions)
    modes = split_csv(args.expected_output_modes)
    reps = expected_replicates(args.replicates)

    try:
        run_rows = read_run_table(args.runs_tsv)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    by_key: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for run_row in run_rows:
        key = (
            run_row.get("dataset", ""),
            run_row.get("condition", ""),
            run_row.get("output_mode", ""),
            run_row.get("replicate", ""),
        )
        by_key[key] = run_row

    qc_rows: list[dict[str, str]] = []
    failures = 0

    for dataset in datasets:
        for condition in conditions:
            for mode in modes:
                for replicate in reps:
                    key = (dataset, condition, mode, replicate)
                    observed_row = by_key.get(key)

                    if observed_row is None:
                        failures += 1
                        qc_rows.append(
                            missing_qc_row(
                                dataset=dataset,
                                condition=condition,
                                mode=mode,
                                replicate=replicate,
                            )
                        )
                        continue

                    status, reason = check_row(observed_row)
                    if status != "PASS":
                        failures += 1

                    qc_rows.append(
                        checked_qc_row(
                            dataset=dataset,
                            condition=condition,
                            mode=mode,
                            replicate=replicate,
                            row=observed_row,
                            status=status,
                            reason=reason,
                        )
                    )

    write_qc_table(args.out, qc_rows)

    print(f"wrote {args.out}", file=sys.stderr)

    if failures:
        print(f"benchmark QC failed: {failures} failing row(s)", file=sys.stderr)
        return 1

    print(f"benchmark QC passed: {len(qc_rows)} expected run row(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
