#!/usr/bin/env python3
"""Benchmark radigest-screen-pairs-cached candidate-pair screening cases."""

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
    "reference_path",
    "candidate_enzymes",
    "candidate_enzyme_count",
    "candidate_pairs_evaluated",
    "min_size",
    "max_size",
    "score_min",
    "score_max",
    "size_model",
    "jobs",
    "radigest_threads",
    "run_index",
    "wall_seconds",
    "exit_code",
    "candidate_pairs_reported",
    "screening_binary",
    "screening_output",
    "json_output",
    "stdout_log",
    "stderr_log",
    "status",
    "command",
]

ALLOWED_BACKENDS = {"radigest-screen-pairs-cached", "cached"}


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def resolve_executable(executable: str, *, label: str) -> str:
    env_name = label.upper().replace("-", "_")
    candidate = Path(executable)
    if candidate.parent != Path(".") or candidate.is_absolute():
        if candidate.exists() and candidate.is_file():
            return str(candidate)
        fail(
            f"{label} executable does not exist: {executable}. "
            f"Set {env_name}=/path/to/{label} or install it on PATH."
        )

    resolved = shutil.which(executable)
    if resolved is None:
        fail(
            f"{label} executable not found on PATH: {executable}. "
            f"Set {env_name}=/path/to/{label} or install it on PATH."
        )
    return resolved


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


def read_candidate_enzymes(path: Path) -> list[str]:
    names = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if len(names) < 2:
        fail(f"candidate enzyme file needs at least two names: {path}")
    if len(set(names)) != len(names):
        fail(f"candidate enzyme file has duplicate names: {path}")
    return names


def count_valid_json_files(json_dir: Path) -> int | None:
    if not json_dir.exists() or not json_dir.is_dir():
        return None
    json_files = sorted(json_dir.glob("*.json"))
    if not json_files:
        return None
    count = 0
    for json_file in json_files:
        try:
            value = json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        if not isinstance(value, dict):
            return None
        count += 1
    return count


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=RUN_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def clean_run_dir(run_dir: Path) -> None:
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)


def execute_command(
    *,
    cmd: list[str],
    stdout_log: Path,
    stderr_log: Path,
) -> tuple[int, float]:
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
    return proc.returncode, elapsed


def build_cached_command(
    *,
    screen_binary: str,
    reference: Path,
    candidate_enzymes: Path,
    min_size: int,
    max_size: int,
    score_min: int,
    score_max: int,
    size_model: str,
    jobs: int,
    radigest_threads: int,
    run_dir: Path,
) -> list[str]:
    return [
        screen_binary,
        "--fasta",
        str(reference),
        "--enzymes",
        str(candidate_enzymes),
        "--min",
        str(min_size),
        "--max",
        str(max_size),
        "--score-min",
        str(score_min),
        "--score-max",
        str(score_max),
        "--size-model",
        size_model,
        "--jobs",
        str(jobs),
        "--threads",
        str(radigest_threads),
        "--out-dir",
        str(run_dir),
        "--force",
    ]


def run_once(
    *,
    screen_binary: str,
    reference: Path,
    candidate_enzymes: Path,
    candidate_enzyme_count: int,
    candidate_pairs_evaluated: int,
    min_size: int,
    max_size: int,
    score_min: int,
    score_max: int,
    size_model: str,
    jobs: int,
    radigest_threads: int,
    case_id: str,
    dataset_id: str,
    condition_id: str,
    run_index: int,
    raw_dir: Path,
) -> dict[str, str]:
    run_label = f"{case_id}.run_{run_index:02d}"
    run_dir = raw_dir / run_label
    clean_run_dir(run_dir)
    json_dir = run_dir / "json"
    stdout_log = run_dir / f"{run_label}.stdout.log"
    stderr_log = run_dir / f"{run_label}.stderr.log"

    cmd = build_cached_command(
        screen_binary=screen_binary,
        reference=reference,
        candidate_enzymes=candidate_enzymes,
        min_size=min_size,
        max_size=max_size,
        score_min=score_min,
        score_max=score_max,
        size_model=size_model,
        jobs=jobs,
        radigest_threads=radigest_threads,
        run_dir=run_dir,
    )
    exit_code, elapsed = execute_command(
        cmd=cmd, stdout_log=stdout_log, stderr_log=stderr_log
    )
    reported_count = count_valid_json_files(json_dir)
    status = (
        "PASS"
        if exit_code == 0 and reported_count == candidate_pairs_evaluated
        else "FAIL"
    )

    return {
        "case_id": case_id,
        "dataset_id": dataset_id,
        "condition_id": condition_id,
        "reference_path": str(reference),
        "candidate_enzymes": str(candidate_enzymes),
        "candidate_enzyme_count": str(candidate_enzyme_count),
        "candidate_pairs_evaluated": str(candidate_pairs_evaluated),
        "min_size": str(min_size),
        "max_size": str(max_size),
        "score_min": str(score_min),
        "score_max": str(score_max),
        "size_model": size_model,
        "jobs": str(jobs),
        "radigest_threads": str(radigest_threads),
        "run_index": str(run_index),
        "wall_seconds": f"{elapsed:.6f}",
        "exit_code": str(exit_code),
        "candidate_pairs_reported": (
            "NA" if reported_count is None else str(reported_count)
        ),
        "screening_binary": screen_binary,
        "screening_output": str(run_dir),
        "json_output": str(json_dir),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "status": status,
        "command": shlex.join(cmd),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen-binary", default="radigest-screen-pairs-cached")
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--condition-id", required=True)
    parser.add_argument("--candidate-enzymes", required=True, type=Path)
    parser.add_argument("--min", required=True, dest="min_size", type=nonnegative_int)
    parser.add_argument("--max", required=True, dest="max_size", type=positive_int)
    parser.add_argument("--score-min", required=True, type=nonnegative_int)
    parser.add_argument("--score-max", required=True, type=positive_int)
    parser.add_argument("--size-model", required=True)
    parser.add_argument("--jobs", required=True, type=positive_int)
    parser.add_argument("--radigest-threads", required=True, type=positive_int)
    parser.add_argument("--runs", required=True, type=positive_int)
    parser.add_argument("--command-template", required=True)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_size <= args.min_size:
        fail("--max must be greater than --min")
    if args.score_max <= args.score_min:
        fail("--score-max must be greater than --score-min")
    if args.command_template not in ALLOWED_BACKENDS:
        fail(
            "Stage 5b uses radigest-screen-pairs-cached; "
            "set command_template=radigest-screen-pairs-cached in "
            "config/screening_speed_cases.tsv"
        )
    if not args.reference.exists():
        fail(f"reference does not exist: {args.reference}")
    if not args.candidate_enzymes.exists():
        fail(f"candidate enzyme file does not exist: {args.candidate_enzymes}")

    screen_binary = resolve_executable(
        args.screen_binary, label="radigest-screen-pairs-cached"
    )
    candidate_names = read_candidate_enzymes(args.candidate_enzymes)
    candidate_pairs_evaluated = len(candidate_names) * (len(candidate_names) - 1) // 2
    args.raw_dir.mkdir(parents=True, exist_ok=True)

    rows = [
        run_once(
            screen_binary=screen_binary,
            reference=args.reference,
            candidate_enzymes=args.candidate_enzymes,
            candidate_enzyme_count=len(candidate_names),
            candidate_pairs_evaluated=candidate_pairs_evaluated,
            min_size=args.min_size,
            max_size=args.max_size,
            score_min=args.score_min,
            score_max=args.score_max,
            size_model=args.size_model,
            jobs=args.jobs,
            radigest_threads=args.radigest_threads,
            case_id=args.case_id,
            dataset_id=args.dataset_id,
            condition_id=args.condition_id,
            run_index=run_index,
            raw_dir=args.raw_dir,
        )
        for run_index in range(1, args.runs + 1)
    ]

    write_rows(args.out, rows)
    failed = [row for row in rows if row["status"] != "PASS"]
    if failed:
        print(
            f"Wrote {len(rows)} screening timing rows to {args.out}; "
            f"{len(failed)} failed and will be rejected by the summary rule.",
            file=sys.stderr,
        )
        return 0

    print(f"Wrote {len(rows)} screening timing rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
