#!/usr/bin/env python3
"""Update config/datasets.tsv SHA256 values from reference_checksums.tsv."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read a tab-delimited table and return field names plus rows."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")

        fieldnames = list(reader.fieldnames)
        rows: list[dict[str, str]] = []

        for raw_row in reader:
            row = {
                key: "" if value is None else value
                for key, value in raw_row.items()
                if key is not None
            }
            rows.append(row)

    return fieldnames, rows


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    """Write rows to a tab-delimited table."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def choose_dataset_column(fieldnames: list[str]) -> str:
    if "dataset" in fieldnames:
        return "dataset"
    if "dataset_id" in fieldnames:
        return "dataset_id"
    raise ValueError("datasets file lacks dataset/dataset_id column")


def choose_sha_column(fieldnames: list[str]) -> str:
    if "sha256" in fieldnames:
        return "sha256"
    if "expected_sha256" in fieldnames:
        return "expected_sha256"
    raise ValueError("datasets file lacks sha256/expected_sha256 column")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", type=Path, default=Path("config/datasets.tsv"))
    parser.add_argument(
        "--checksums",
        type=Path,
        default=Path("results/processed/reference_checksums.tsv"),
    )
    parser.add_argument("--dataset", required=True, help="Dataset ID to update")
    args = parser.parse_args(argv)

    try:
        dataset_fields, dataset_rows = read_rows(args.datasets)
        _, checksum_rows = read_rows(args.checksums)

        dataset_col = choose_dataset_column(dataset_fields)
        sha_col = choose_sha_column(dataset_fields)

        checksum_by_dataset = {
            row.get("dataset", row.get("dataset_id", "")): row for row in checksum_rows
        }

        if args.dataset not in checksum_by_dataset:
            print(
                f"error: {args.dataset} not found in {args.checksums}",
                file=sys.stderr,
            )
            return 2

        checksum_row = checksum_by_dataset[args.dataset]
        observed = checksum_row.get("observed_sha256", "").strip()
        status = checksum_row.get("status", "")

        if not observed:
            print(
                f"error: {args.dataset} has no observed_sha256 in {args.checksums}",
                file=sys.stderr,
            )
            return 2

        if status not in {"exists", "downloaded", "downloaded_force"}:
            print(
                f"error: {args.dataset} status is {status!r}, "
                "not a usable downloaded/existing file",
                file=sys.stderr,
            )
            return 2

        updated = False
        for row in dataset_rows:
            if row.get(dataset_col) == args.dataset:
                row[sha_col] = observed
                updated = True

        if not updated:
            print(
                f"error: {args.dataset} not found in {args.datasets}", file=sys.stderr
            )
            return 2

        write_rows(args.datasets, dataset_fields, dataset_rows)

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"updated {args.datasets}: {args.dataset} {sha_col}={observed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
