#!/usr/bin/env python3
"""Run radigest synthetic validation cases and compare expected intervals.

The synthetic manifest is intentionally small and tracked in Git. Each row in
``config/synthetic_expected.tsv`` is executed against the same synthetic FASTA,
then the radigest fragment TSV is filtered to the requested record and compared
with the expected zero-based, half-open intervals.
"""

from __future__ import annotations

import argparse
import csv
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

FLAG_MAP = {
    "include_ends": "-include-ends",
    "allow_same": "-allow-same",
}

SUMMARY_COLUMNS = [
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
]


def parse_expected(value: str) -> list[tuple[int, int]]:
    """Parse a semicolon-delimited interval field such as ``[5,11);[11,16)``."""
    value = value.strip()
    if value in {"", "NONE"}:
        return []

    intervals: list[tuple[int, int]] = []
    for part in value.split(";"):
        part = part.strip()
        if not (part.startswith("[") and part.endswith(")")):
            raise ValueError(f"invalid interval syntax: {part!r}")
        body = part[1:-1]
        start, end = body.split(",", 1)
        intervals.append((int(start), int(end)))
    return intervals


def format_intervals(intervals: list[tuple[int, int]]) -> str:
    """Serialize intervals in the manifest's compact notation."""
    return ";".join(f"[{start},{end})" for start, end in intervals) or "NONE"


def read_expected_rows(path: Path) -> list[dict[str, str]]:
    """Read the synthetic validation manifest."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        rows: list[dict[str, str]] = []
        for row in reader:
            if not any((value or "").strip() for value in row.values()):
                continue
            clean_row: dict[str, str] = {}
            for key, value in row.items():
                if key is not None:
                    clean_row[key] = "" if value is None else value
            rows.append(clean_row)
    if not rows:
        raise ValueError(f"{path}: no validation rows")
    return rows


def resolve_executable(executable: str) -> str:
    """Return an executable path or fail with a reviewer-actionable message."""
    candidate = Path(executable)
    if candidate.parent != Path(".") or candidate.is_absolute():
        if candidate.exists() and candidate.is_file():
            return str(candidate)
        raise FileNotFoundError(
            f"radigest executable does not exist: {executable}. "
            "Set RADIGEST=/path/to/radigest or install radigest on PATH."
        )

    resolved = shutil.which(executable)
    if resolved is None:
        raise FileNotFoundError(
            f"radigest executable not found on PATH: {executable}. "
            "Set RADIGEST=/path/to/radigest or install radigest on PATH."
        )
    return resolved


def read_observed_tsv(path: Path, record_id: str) -> list[tuple[int, int]]:
    """Read observed intervals from a radigest fragment TSV for one record."""
    if not path.exists():
        return []

    observed: list[tuple[int, int]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        for row in reader:
            chrom = row.get("chrom") or row.get("seqid") or row.get("record_id")
            if chrom != record_id:
                continue
            try:
                observed.append((int(row["start0"]), int(row["end0"])))
            except KeyError as exc:
                raise ValueError(
                    f"{path}: missing required column {exc.args[0]}"
                ) from exc
            except ValueError as exc:
                raise ValueError(
                    f"{path}: non-integer start0/end0 for {record_id}"
                ) from exc
    return observed


def build_command(
    radigest: str,
    fasta: Path,
    row: dict[str, str],
    out_tsv: Path,
    out_json: Path,
) -> list[str]:
    """Build the radigest command for one synthetic validation row."""
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
        for option in options.split(","):
            option = option.strip()
            if not option:
                continue
            if option not in FLAG_MAP:
                raise ValueError(
                    f"unknown synthetic option {option!r} in case {row['case_id']}"
                )
            cmd.append(FLAG_MAP[option])

    return cmd


def validate_row(
    *,
    row: dict[str, str],
    radigest: str,
    fasta: Path,
    out_dir: Path,
) -> dict[str, str]:
    """Execute and validate one synthetic case."""
    case_id = row["case_id"]
    record_id = row["record_id"]
    out_tsv = out_dir / f"{case_id}.fragments.tsv"
    out_json = out_dir / f"{case_id}.json"
    log = out_dir / f"{case_id}.log"

    for path in [out_tsv, out_json, log]:
        if path.exists():
            path.unlink()

    expected = parse_expected(row["expected_intervals_0based_halfopen"])
    cmd = build_command(radigest, fasta, row, out_tsv, out_json)

    with log.open("w", encoding="utf-8") as log_handle:
        proc = subprocess.run(
            cmd,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )

    observed = read_observed_tsv(out_tsv, record_id)
    status = "PASS" if proc.returncode == 0 and observed == expected else "FAIL"

    return {
        "case_id": case_id,
        "record_id": record_id,
        "enzymes": row["enzymes"],
        "min": row["min"],
        "max": row["max"],
        "options": row.get("options", ""),
        "expected": format_intervals(expected),
        "observed": format_intervals(observed),
        "status": status,
        "command": shlex.join(cmd),
    }


def write_summary(path: Path, rows: list[dict[str, str]]) -> None:
    """Write the synthetic validation summary TSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radigest", default="radigest")
    parser.add_argument(
        "--fasta",
        type=Path,
        default=Path("data/synthetic/synthetic_validation.fa"),
        help="Synthetic validation FASTA.",
    )
    parser.add_argument(
        "--expected",
        type=Path,
        default=Path("config/synthetic_expected.tsv"),
        help="Expected synthetic validation intervals.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("results/validation/raw/synthetic"),
        help="Directory for per-case radigest output and logs.",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/validation/synthetic_validation_results.tsv"),
        help="Output summary TSV.",
    )
    args = parser.parse_args(argv)
    summary_rows: list[dict[str, str]] = []

    try:
        radigest = resolve_executable(args.radigest)
        if not args.fasta.is_file():
            raise FileNotFoundError(f"synthetic FASTA does not exist: {args.fasta}")
        rows = read_expected_rows(args.expected)
        args.out_dir.mkdir(parents=True, exist_ok=True)

        summary_rows = [
            validate_row(
                row=row,
                radigest=radigest,
                fasta=args.fasta,
                out_dir=args.out_dir,
            )
            for row in rows
        ]
        write_summary(args.summary, summary_rows)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    failures = sum(1 for row in summary_rows if row["status"] != "PASS")
    if failures:
        print(f"synthetic validation failed: {failures} case(s)", file=sys.stderr)
        print(f"summary: {args.summary}", file=sys.stderr)
        return 1

    print(f"synthetic validation passed: {len(summary_rows)} case(s)")
    print(f"summary: {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
