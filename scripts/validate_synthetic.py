#!/usr/bin/env python3
"""Run radigest synthetic validation cases and compare expected intervals."""

from __future__ import annotations

import argparse
import csv
import shlex
import subprocess
import sys
from pathlib import Path


FLAG_MAP = {
    "include_ends": "-include-ends",
    "allow_same": "-allow-same",
}


def parse_expected(value: str) -> list[tuple[int, int]]:
    value = value.strip()
    if value in {"", "NONE"}:
        return []

    intervals: list[tuple[int, int]] = []
    for part in value.split(";"):
        part = part.strip()
        if not (part.startswith("[") and part.endswith(")")):
            raise ValueError(f"invalid interval syntax: {part}")
        body = part[1:-1]
        start, end = body.split(",", 1)
        intervals.append((int(start), int(end)))
    return intervals


def read_observed_tsv(path: Path, record_id: str) -> list[tuple[int, int]]:
    if not path.exists():
        return []

    observed: list[tuple[int, int]] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            chrom = row.get("chrom") or row.get("seqid") or row.get("record_id")
            if chrom != record_id:
                continue
            observed.append((int(row["start0"]), int(row["end0"])))
    return observed


def build_command(radigest: str, fasta: Path, row: dict[str, str], out_tsv: Path, out_json: Path) -> list[str]:
    cmd = [
        radigest,
        "-fasta",
        str(fasta),
        "-enzymes",
        row["enzymes"],
        "-min",
        row["min"],
        "-max",
        row["max"],
        "-threads",
        "1",
        "-fragments-tsv",
        str(out_tsv),
        "-json",
        str(out_json),
    ]

    options = row.get("options", "none").strip()
    if options and options != "none":
        for opt in options.split(","):
            opt = opt.strip()
            if not opt:
                continue
            if opt not in FLAG_MAP:
                raise ValueError(f"unknown synthetic option {opt!r} in case {row['case_id']}")
            cmd.append(FLAG_MAP[opt])

    return cmd


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--radigest", default="radigest")
    parser.add_argument("--fasta", type=Path, default=Path("data/synthetic/synthetic_validation.fa"))
    parser.add_argument("--expected", type=Path, default=Path("config/synthetic_expected.tsv"))
    parser.add_argument("--out-dir", type=Path, default=Path("results/raw/synthetic"))
    parser.add_argument("--summary", type=Path, default=Path("results/processed/synthetic_validation_results.tsv"))
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]]
    with args.expected.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    failures = 0

    with args.summary.open("w", newline="") as out_handle:
        writer = csv.DictWriter(
            out_handle,
            delimiter="\t",
            fieldnames=[
                "case_id",
                "record_id",
                "enzymes",
                "min",
                "max",
                "options",
                "expected",
                "observed",
                "status",
                "command",
            ],
        )
        writer.writeheader()

        for row in rows:
            case_id = row["case_id"]
            record_id = row["record_id"]
            out_tsv = args.out_dir / f"{case_id}.fragments.tsv"
            out_json = args.out_dir / f"{case_id}.json"
            log = args.out_dir / f"{case_id}.log"

            cmd = build_command(args.radigest, args.fasta, row, out_tsv, out_json)

            with log.open("w") as log_handle:
                proc = subprocess.run(
                    cmd,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )

            expected = parse_expected(row["expected_intervals_0based_halfopen"])
            observed = read_observed_tsv(out_tsv, record_id)

            status = "PASS" if proc.returncode == 0 and observed == expected else "FAIL"
            if status == "FAIL":
                failures += 1

            writer.writerow(
                {
                    "case_id": case_id,
                    "record_id": record_id,
                    "enzymes": row["enzymes"],
                    "min": row["min"],
                    "max": row["max"],
                    "options": row.get("options", ""),
                    "expected": ";".join(f"[{s},{e})" for s, e in expected) or "NONE",
                    "observed": ";".join(f"[{s},{e})" for s, e in observed) or "NONE",
                    "status": status,
                    "command": shlex.join(cmd),
                }
            )

    if failures:
        print(f"synthetic validation failed: {failures} case(s)", file=sys.stderr)
        return 1

    print(f"synthetic validation passed: {len(rows)} case(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
