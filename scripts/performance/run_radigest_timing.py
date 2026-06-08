#!/usr/bin/env python3
"""Run one radigest performance case repeatedly and write per-run timing rows."""

from __future__ import annotations

import argparse
import csv
import json
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import NoReturn

RUN_COLUMNS = [
    "case_id",
    "dataset_id",
    "condition_id",
    "input_format",
    "output_mode",
    "reference_path",
    "enzymes",
    "min_size",
    "max_size",
    "threads",
    "run_index",
    "wall_seconds",
    "exit_code",
    "retained_fragments",
    "fragments_tsv",
    "json_output",
    "stdout_log",
    "stderr_log",
    "status",
    "command",
]


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def resolve_executable(executable: str) -> str:
    """Resolve an executable path or PATH entry with a clear error."""
    candidate = Path(executable)
    if candidate.parent != Path(".") or candidate.is_absolute():
        if candidate.exists() and candidate.is_file():
            return str(candidate)
        fail(
            f"radigest executable does not exist: {executable}. "
            "Set RADIGEST=/path/to/radigest or install radigest on PATH."
        )

    resolved = shutil.which(executable)
    if resolved is None:
        fail(
            f"radigest executable not found on PATH: {executable}. "
            "Set RADIGEST=/path/to/radigest or install radigest on PATH."
        )
    return resolved


def count_fragments_tsv(path: Path) -> int:
    """Count rows in a radigest fragment TSV."""
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            return 0
        return sum(
            1 for row in reader if any((value or "").strip() for value in row.values())
        )


def count_fragments_json(path: Path) -> int:
    """Read retained-fragment count from a radigest JSON summary."""
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError:
        return 0

    candidates = [
        payload.get("total_fragments"),
        (
            payload.get("size_selection", {}).get("raw_fragments_in_window")
            if isinstance(payload.get("size_selection"), dict)
            else None
        ),
    ]
    for value in candidates:
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                continue
    return 0


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=RUN_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def run_once(
    *,
    radigest: str,
    reference: Path,
    enzymes: str,
    min_size: int,
    max_size: int,
    threads: int,
    case_id: str,
    dataset_id: str,
    condition_id: str,
    input_format: str,
    output_mode: str,
    run_index: int,
    raw_dir: Path,
) -> dict[str, str]:
    """Run radigest once and return a timing row."""
    prefix = raw_dir / f"{case_id}.run_{run_index:02d}"
    fragments_tsv = raw_dir / f"{prefix.name}.fragments.tsv"
    json_output = raw_dir / f"{prefix.name}.json"
    stdout_log = raw_dir / f"{prefix.name}.stdout.log"
    stderr_log = raw_dir / f"{prefix.name}.stderr.log"

    for path in [fragments_tsv, json_output, stdout_log, stderr_log]:
        if path.exists():
            path.unlink()

    cmd = [
        radigest,
        "-fasta",
        str(reference),
        "-enzymes",
        enzymes,
        "-min",
        str(min_size),
        "-max",
        str(max_size),
        "-threads",
        str(threads),
    ]
    if output_mode in {"fragments_tsv", "both"}:
        cmd.extend(["-fragments-tsv", str(fragments_tsv)])
    if output_mode in {"json", "both"}:
        cmd.extend(["-json", str(json_output)])

    start = time.perf_counter()
    with stdout_log.open("w", encoding="utf-8") as stdout_handle, stderr_log.open(
        "w", encoding="utf-8"
    ) as stderr_handle:
        proc = subprocess.run(
            cmd,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            check=False,
        )
    elapsed = time.perf_counter() - start

    expected_outputs = []
    if output_mode in {"fragments_tsv", "both"}:
        expected_outputs.append(fragments_tsv)
    if output_mode in {"json", "both"}:
        expected_outputs.append(json_output)

    if fragments_tsv.exists():
        retained = count_fragments_tsv(fragments_tsv)
    elif json_output.exists():
        retained = count_fragments_json(json_output)
    else:
        retained = 0

    status = "PASS"
    if proc.returncode != 0 or not all(path.exists() for path in expected_outputs):
        status = "FAIL"

    return {
        "case_id": case_id,
        "dataset_id": dataset_id,
        "condition_id": condition_id,
        "input_format": input_format,
        "output_mode": output_mode,
        "reference_path": str(reference),
        "enzymes": enzymes,
        "min_size": str(min_size),
        "max_size": str(max_size),
        "threads": str(threads),
        "run_index": str(run_index),
        "wall_seconds": f"{elapsed:.6f}",
        "exit_code": str(proc.returncode),
        "retained_fragments": str(retained),
        "fragments_tsv": str(fragments_tsv) if fragments_tsv.exists() else "NA",
        "json_output": str(json_output) if json_output.exists() else "NA",
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "status": status,
        "command": shlex.join(cmd),
    }


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an integer: {value!r}") from None
    if parsed < 1:
        raise argparse.ArgumentTypeError(f"must be >= 1: {value!r}")
    return parsed


def nonnegative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an integer: {value!r}") from None
    if parsed < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0: {value!r}")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radigest", default="radigest")
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--condition-id", required=True)
    parser.add_argument("--input-format", required=True)
    parser.add_argument(
        "--output-mode",
        choices=["json", "fragments_tsv", "both"],
        default="both",
        help="radigest output artifact mode to time; input-format cases use both by default",
    )
    parser.add_argument("--enzymes", required=True)
    parser.add_argument("--min", required=True, dest="min_size", type=nonnegative_int)
    parser.add_argument("--max", required=True, dest="max_size", type=positive_int)
    parser.add_argument("--threads", required=True, type=positive_int)
    parser.add_argument("--runs", required=True, type=positive_int)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_size <= args.min_size:
        fail("--max must be greater than --min")
    if not args.reference.exists():
        fail(f"reference does not exist: {args.reference}")

    radigest = resolve_executable(args.radigest)
    args.raw_dir.mkdir(parents=True, exist_ok=True)

    rows = [
        run_once(
            radigest=radigest,
            reference=args.reference,
            enzymes=args.enzymes,
            min_size=args.min_size,
            max_size=args.max_size,
            threads=args.threads,
            case_id=args.case_id,
            dataset_id=args.dataset_id,
            condition_id=args.condition_id,
            input_format=args.input_format,
            output_mode=args.output_mode,
            run_index=run_index,
            raw_dir=args.raw_dir,
        )
        for run_index in range(1, args.runs + 1)
    ]
    write_rows(args.out, rows)

    failed = [row for row in rows if row["status"] != "PASS"]
    if failed:
        print(
            f"{len(failed)} of {len(rows)} radigest timing runs failed; "
            f"see {args.out}",
            file=sys.stderr,
        )
        return 1

    print(f"Wrote {len(rows)} timing rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
