#!/usr/bin/env python3
"""Benchmark cached radigest candidate-pair screening cases.

Two backends are supported:

* radigest-screen-pairs-cached: end-to-end cached screening with JSON output.
* radigest-bench-screen-cached: phase-timed benchmark output; pair-screen scaling
  uses --reuse-index and --output-mode none so speedups measure score_pairs_seconds.
"""

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
    "build_workers",
    "run_index",
    "wall_seconds",
    "timing_backend",
    "timed_phase",
    "build_cut_index_seconds",
    "score_pairs_seconds",
    "json_marshal_seconds",
    "write_json_seconds",
    "total_seconds",
    "pairs_per_second_score_phase",
    "pairs_per_second_end_to_end",
    "exit_code",
    "candidate_pairs_reported",
    "screening_binary",
    "screening_output",
    "json_output",
    "benchmark_tsv",
    "stdout_log",
    "stderr_log",
    "status",
    "command",
]

CACHED_BACKENDS = {"radigest-screen-pairs-cached", "cached"}
BENCH_BACKENDS = {"radigest-bench-screen-cached", "bench-cached", "bench"}
ALLOWED_BACKENDS = CACHED_BACKENDS | BENCH_BACKENDS
BENCH_REQUIRED_COLUMNS = {
    "run",
    "candidate_enzymes",
    "candidate_pairs",
    "jobs",
    "build_workers",
    "build_cut_index_seconds",
    "score_pairs_seconds",
    "json_marshal_seconds",
    "write_json_seconds",
    "total_seconds",
    "pairs_per_second_score_phase",
    "pairs_per_second_end_to_end",
    "summaries",
}


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def normalize_backend(value: str) -> str:
    if value in CACHED_BACKENDS:
        return "cached"
    if value in BENCH_BACKENDS:
        return "bench"
    fail(
        "Unsupported screening command_template "
        f"{value!r}; expected radigest-screen-pairs-cached or radigest-bench-screen-cached"
    )


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
    build_workers: int,
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
        "--build-workers",
        str(build_workers),
        "--out-dir",
        str(run_dir),
        "--force",
    ]


def build_bench_command(
    *,
    bench_binary: str,
    reference: Path,
    candidate_enzymes: Path,
    min_size: int,
    max_size: int,
    score_min: int,
    score_max: int,
    size_model: str,
    jobs: int,
    radigest_threads: int,
    build_workers: int,
    runs: int,
) -> list[str]:
    return [
        bench_binary,
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
        "--build-workers",
        str(build_workers),
        "--runs",
        str(runs),
        "--reuse-index",
        "--output-mode",
        "none",
    ]


def base_row(
    *,
    case_id: str,
    dataset_id: str,
    condition_id: str,
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
    build_workers: int,
    run_index: int,
) -> dict[str, str]:
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
        "build_workers": str(build_workers),
        "run_index": str(run_index),
    }


def run_cached_once(
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
    build_workers: int,
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
        build_workers=build_workers,
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

    row = base_row(
        case_id=case_id,
        dataset_id=dataset_id,
        condition_id=condition_id,
        reference=reference,
        candidate_enzymes=candidate_enzymes,
        candidate_enzyme_count=candidate_enzyme_count,
        candidate_pairs_evaluated=candidate_pairs_evaluated,
        min_size=min_size,
        max_size=max_size,
        score_min=score_min,
        score_max=score_max,
        size_model=size_model,
        jobs=jobs,
        radigest_threads=radigest_threads,
        build_workers=build_workers,
        run_index=run_index,
    )
    row.update(
        {
            "wall_seconds": f"{elapsed:.6f}",
            "timing_backend": "radigest-screen-pairs-cached",
            "timed_phase": "end_to_end_wall",
            "build_cut_index_seconds": "NA",
            "score_pairs_seconds": "NA",
            "json_marshal_seconds": "NA",
            "write_json_seconds": "NA",
            "total_seconds": f"{elapsed:.6f}",
            "pairs_per_second_score_phase": "NA",
            "pairs_per_second_end_to_end": (
                f"{candidate_pairs_evaluated / elapsed:.6f}" if elapsed > 0 else "NA"
            ),
            "exit_code": str(exit_code),
            "candidate_pairs_reported": (
                "NA" if reported_count is None else str(reported_count)
            ),
            "screening_binary": screen_binary,
            "screening_output": str(run_dir),
            "json_output": str(json_dir),
            "benchmark_tsv": "NA",
            "stdout_log": str(stdout_log),
            "stderr_log": str(stderr_log),
            "status": status,
            "command": shlex.join(cmd),
        }
    )
    return row


def read_bench_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames or []
        missing = sorted(BENCH_REQUIRED_COLUMNS - set(fieldnames))
        if missing:
            fail(
                f"{path}: radigest-bench-screen-cached output missing columns: {', '.join(missing)}"
            )
        return [
            {
                key: "" if value is None else value
                for key, value in row.items()
                if key is not None
            }
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]


def run_bench_case(
    *,
    bench_binary: str,
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
    build_workers: int,
    runs: int,
    case_id: str,
    dataset_id: str,
    condition_id: str,
    raw_dir: Path,
) -> list[dict[str, str]]:
    run_dir = raw_dir / f"{case_id}.bench"
    clean_run_dir(run_dir)
    stdout_log = run_dir / f"{case_id}.bench.tsv"
    stderr_log = run_dir / f"{case_id}.bench.stderr.log"
    cmd = build_bench_command(
        bench_binary=bench_binary,
        reference=reference,
        candidate_enzymes=candidate_enzymes,
        min_size=min_size,
        max_size=max_size,
        score_min=score_min,
        score_max=score_max,
        size_model=size_model,
        jobs=jobs,
        radigest_threads=radigest_threads,
        build_workers=build_workers,
        runs=runs,
    )
    exit_code, elapsed = execute_command(
        cmd=cmd, stdout_log=stdout_log, stderr_log=stderr_log
    )

    parsed_rows: list[dict[str, str]] = []
    if exit_code == 0:
        parsed_rows = read_bench_rows(stdout_log)

    if exit_code != 0 or not parsed_rows:
        rows: list[dict[str, str]] = []
        for run_index in range(1, runs + 1):
            row = base_row(
                case_id=case_id,
                dataset_id=dataset_id,
                condition_id=condition_id,
                reference=reference,
                candidate_enzymes=candidate_enzymes,
                candidate_enzyme_count=candidate_enzyme_count,
                candidate_pairs_evaluated=candidate_pairs_evaluated,
                min_size=min_size,
                max_size=max_size,
                score_min=score_min,
                score_max=score_max,
                size_model=size_model,
                jobs=jobs,
                radigest_threads=radigest_threads,
                build_workers=build_workers,
                run_index=run_index,
            )
            row.update(
                {
                    "wall_seconds": "NA",
                    "timing_backend": "radigest-bench-screen-cached",
                    "timed_phase": "score_pairs_seconds",
                    "build_cut_index_seconds": "NA",
                    "score_pairs_seconds": "NA",
                    "json_marshal_seconds": "NA",
                    "write_json_seconds": "NA",
                    "total_seconds": f"{elapsed:.6f}",
                    "pairs_per_second_score_phase": "NA",
                    "pairs_per_second_end_to_end": "NA",
                    "exit_code": str(exit_code),
                    "candidate_pairs_reported": "NA",
                    "screening_binary": bench_binary,
                    "screening_output": str(run_dir),
                    "json_output": "NA",
                    "benchmark_tsv": str(stdout_log),
                    "stdout_log": str(stdout_log),
                    "stderr_log": str(stderr_log),
                    "status": "FAIL",
                    "command": shlex.join(cmd),
                }
            )
            rows.append(row)
        return rows

    rows = []
    for bench_row in parsed_rows:
        run_index = int(bench_row["run"])
        candidate_pairs_reported = int(bench_row["candidate_pairs"])
        summaries = int(bench_row["summaries"])
        status = (
            "PASS"
            if exit_code == 0
            and candidate_pairs_reported == candidate_pairs_evaluated
            and summaries == candidate_pairs_evaluated
            else "FAIL"
        )
        row = base_row(
            case_id=case_id,
            dataset_id=dataset_id,
            condition_id=condition_id,
            reference=reference,
            candidate_enzymes=candidate_enzymes,
            candidate_enzyme_count=candidate_enzyme_count,
            candidate_pairs_evaluated=candidate_pairs_evaluated,
            min_size=min_size,
            max_size=max_size,
            score_min=score_min,
            score_max=score_max,
            size_model=size_model,
            jobs=jobs,
            radigest_threads=radigest_threads,
            build_workers=build_workers,
            run_index=run_index,
        )
        row.update(
            {
                "wall_seconds": bench_row["score_pairs_seconds"],
                "timing_backend": "radigest-bench-screen-cached",
                "timed_phase": "score_pairs_seconds",
                "build_cut_index_seconds": bench_row["build_cut_index_seconds"],
                "score_pairs_seconds": bench_row["score_pairs_seconds"],
                "json_marshal_seconds": bench_row["json_marshal_seconds"],
                "write_json_seconds": bench_row["write_json_seconds"],
                "total_seconds": bench_row["total_seconds"],
                "pairs_per_second_score_phase": bench_row[
                    "pairs_per_second_score_phase"
                ],
                "pairs_per_second_end_to_end": bench_row["pairs_per_second_end_to_end"],
                "exit_code": str(exit_code),
                "candidate_pairs_reported": str(candidate_pairs_reported),
                "screening_binary": bench_binary,
                "screening_output": str(run_dir),
                "json_output": "NA",
                "benchmark_tsv": str(stdout_log),
                "stdout_log": str(stdout_log),
                "stderr_log": str(stderr_log),
                "status": status,
                "command": shlex.join(cmd),
            }
        )
        rows.append(row)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen-binary", default="radigest-screen-pairs-cached")
    parser.add_argument("--bench-screen-binary", default="radigest-bench-screen-cached")
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
    parser.add_argument(
        "--build-workers",
        type=positive_int,
        default=None,
        help=(
            "Parallel cut-index build workers. Defaults to --radigest-threads so "
            "job-scaling benchmarks only vary pair-scoring jobs."
        ),
    )
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
    backend = normalize_backend(args.command_template)
    if not args.reference.exists():
        fail(f"reference does not exist: {args.reference}")
    if not args.candidate_enzymes.exists():
        fail(f"candidate enzyme file does not exist: {args.candidate_enzymes}")

    candidate_names = read_candidate_enzymes(args.candidate_enzymes)
    candidate_pairs_evaluated = len(candidate_names) * (len(candidate_names) - 1) // 2
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    build_workers = args.build_workers or args.radigest_threads

    if backend == "cached":
        screen_binary = resolve_executable(
            args.screen_binary, label="radigest-screen-pairs-cached"
        )
        rows = [
            run_cached_once(
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
                build_workers=build_workers,
                case_id=args.case_id,
                dataset_id=args.dataset_id,
                condition_id=args.condition_id,
                run_index=run_index,
                raw_dir=args.raw_dir,
            )
            for run_index in range(1, args.runs + 1)
        ]
    else:
        bench_binary = resolve_executable(
            args.bench_screen_binary, label="radigest-bench-screen-cached"
        )
        rows = run_bench_case(
            bench_binary=bench_binary,
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
            build_workers=build_workers,
            runs=args.runs,
            case_id=args.case_id,
            dataset_id=args.dataset_id,
            condition_id=args.condition_id,
            raw_dir=args.raw_dir,
        )

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
