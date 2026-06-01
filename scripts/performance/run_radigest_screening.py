#!/usr/bin/env python3
"""Benchmark native radigest candidate-pair screening cases."""

from __future__ import annotations

import argparse
import csv
import json
import math
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
    "screening_output",
    "json_output",
    "stdout_log",
    "stderr_log",
    "status",
    "command",
]

TEMPLATE_FIELDS = {
    "radigest",
    "reference",
    "candidate_enzymes",
    "min_size",
    "max_size",
    "score_min",
    "score_max",
    "size_model",
    "jobs",
    "radigest_threads",
    "screening_output",
    "out_tsv",
    "json_output",
    "stdout_log",
    "stderr_log",
}

AUTO_TEMPLATES = [
    (
        "{radigest} -screen -fasta {reference} -candidate-enzymes "
        "{candidate_enzymes} -min {min_size} -max {max_size} "
        "-score-min {score_min} -score-max {score_max} -size-model "
        "{size_model} -jobs {jobs} -threads {radigest_threads} "
        "-out-tsv {screening_output} -json {json_output}"
    ),
    (
        "{radigest} -screen -fasta {reference} -candidates {candidate_enzymes} "
        "-min {min_size} -max {max_size} -score-min {score_min} "
        "-score-max {score_max} -size-model {size_model} -jobs {jobs} "
        "-threads {radigest_threads} -out-tsv {screening_output} "
        "-json {json_output}"
    ),
    (
        "{radigest} screen -fasta {reference} -candidate-enzymes "
        "{candidate_enzymes} -min {min_size} -max {max_size} "
        "-score-min {score_min} -score-max {score_max} -size-model "
        "{size_model} -jobs {jobs} -threads {radigest_threads} "
        "-out-tsv {screening_output} -json {json_output}"
    ),
    (
        "{radigest} screen --fasta {reference} --candidate-enzymes "
        "{candidate_enzymes} --min {min_size} --max {max_size} "
        "--score-min {score_min} --score-max {score_max} --size-model "
        "{size_model} --jobs {jobs} --threads {radigest_threads} "
        "--out-tsv {screening_output} --json {json_output}"
    ),
    (
        "{radigest} -screen -fasta {reference} -candidate-enzymes "
        "{candidate_enzymes} -min {min_size} -max {max_size} "
        "-score-min {score_min} -score-max {score_max} -size-model "
        "{size_model} -jobs {jobs} -threads {radigest_threads}"
    ),
    (
        "{radigest} screen -fasta {reference} -candidate-enzymes "
        "{candidate_enzymes} -min {min_size} -max {max_size} "
        "-score-min {score_min} -score-max {score_max} -size-model "
        "{size_model} -jobs {jobs} -threads {radigest_threads}"
    ),
]


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def resolve_executable(executable: str) -> str:
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


def format_template(template: str, values: dict[str, str]) -> list[str]:
    try:
        rendered = template.format(**values)
    except KeyError as exc:
        field = str(exc).strip("'")
        allowed = ", ".join(sorted(TEMPLATE_FIELDS))
        fail(f"unknown command_template field {{{field}}}; allowed fields: {allowed}")
    return shlex.split(rendered)


def count_tsv_like_rows(path: Path) -> int | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    raw_lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not raw_lines:
        return None

    data_lines = raw_lines
    first = raw_lines[0].lower()
    header_tokens = {
        "enzyme",
        "enzyme1",
        "enzyme_1",
        "enzyme2",
        "enzyme_2",
        "pair",
        "score",
        "fragments",
        "count",
    }
    first_tokens = {
        token.strip().lower()
        for token in first.replace(",", "\t").split("\t")
        if token.strip()
    }
    if first_tokens & header_tokens:
        data_lines = raw_lines[1:]
    return len(data_lines)


def json_candidate_count(value: object) -> int | None:
    if isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            return len(value)
        nested = [json_candidate_count(item) for item in value]
        nested_counts = [item for item in nested if item is not None]
        return max(nested_counts) if nested_counts else None
    if isinstance(value, dict):
        direct_count_keys = [
            "candidate_pairs",
            "pairs_evaluated",
            "pairs_scored",
            "retained_pairs",
            "pair_count",
            "count",
        ]
        for key in direct_count_keys:
            raw = value.get(key)
            if isinstance(raw, int) and raw >= 0:
                return raw
            if isinstance(raw, float) and raw >= 0 and math.isfinite(raw):
                return int(raw)
        list_keys = [
            "results",
            "pairs",
            "candidate_pairs",
            "screening_results",
            "enzyme_pairs",
            "records",
        ]
        for key in list_keys:
            raw = value.get(key)
            if isinstance(raw, list):
                return len(raw)
        nested = [json_candidate_count(item) for item in value.values()]
        nested_counts = [item for item in nested if item is not None]
        return max(nested_counts) if nested_counts else None
    return None


def count_json_rows(path: Path) -> int | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return json_candidate_count(value)


def detected_candidate_count(
    *, screening_output: Path, json_output: Path, stdout_log: Path
) -> int | None:
    for path in [screening_output, stdout_log]:
        count = count_tsv_like_rows(path)
        if count is not None:
            return count
    return count_json_rows(json_output)


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=RUN_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def command_values(
    *,
    radigest: str,
    reference: Path,
    candidate_enzymes: Path,
    min_size: int,
    max_size: int,
    score_min: int,
    score_max: int,
    size_model: str,
    jobs: int,
    radigest_threads: int,
    screening_output: Path,
    json_output: Path,
    stdout_log: Path,
    stderr_log: Path,
) -> dict[str, str]:
    return {
        "radigest": radigest,
        "reference": str(reference),
        "candidate_enzymes": str(candidate_enzymes),
        "min_size": str(min_size),
        "max_size": str(max_size),
        "score_min": str(score_min),
        "score_max": str(score_max),
        "size_model": size_model,
        "jobs": str(jobs),
        "radigest_threads": str(radigest_threads),
        "screening_output": str(screening_output),
        "out_tsv": str(screening_output),
        "json_output": str(json_output),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
    }


def clean_paths(paths: list[Path]) -> None:
    for path in paths:
        if path.exists():
            path.unlink()


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


def run_once(
    *,
    radigest: str,
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
    command_template: str,
    selected_template: str | None,
) -> tuple[dict[str, str], str | None]:
    prefix = raw_dir / f"{case_id}.run_{run_index:02d}"
    screening_output = raw_dir / f"{prefix.name}.screening.tsv"
    json_output = raw_dir / f"{prefix.name}.json"
    stdout_log = raw_dir / f"{prefix.name}.stdout.log"
    stderr_log = raw_dir / f"{prefix.name}.stderr.log"
    clean_paths([screening_output, json_output, stdout_log, stderr_log])

    values = command_values(
        radigest=radigest,
        reference=reference,
        candidate_enzymes=candidate_enzymes,
        min_size=min_size,
        max_size=max_size,
        score_min=score_min,
        score_max=score_max,
        size_model=size_model,
        jobs=jobs,
        radigest_threads=radigest_threads,
        screening_output=screening_output,
        json_output=json_output,
        stdout_log=stdout_log,
        stderr_log=stderr_log,
    )

    templates = AUTO_TEMPLATES if command_template == "auto" else [command_template]
    if selected_template is not None:
        templates = [selected_template]

    last_cmd: list[str] = []
    last_exit_code = 1
    last_elapsed = 0.0
    last_count: int | None = None
    successful_template = selected_template

    for template_index, template in enumerate(templates, start=1):
        if template_index > 1:
            clean_paths([screening_output, json_output, stdout_log, stderr_log])
        cmd = format_template(template, values)
        exit_code, elapsed = execute_command(
            cmd=cmd, stdout_log=stdout_log, stderr_log=stderr_log
        )
        count = detected_candidate_count(
            screening_output=screening_output,
            json_output=json_output,
            stdout_log=stdout_log,
        )
        last_cmd = cmd
        last_exit_code = exit_code
        last_elapsed = elapsed
        last_count = count
        if exit_code == 0 and count is not None:
            successful_template = template
            break

    status = "PASS" if last_exit_code == 0 and last_count is not None else "FAIL"
    row = {
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
        "wall_seconds": f"{last_elapsed:.6f}",
        "exit_code": str(last_exit_code),
        "candidate_pairs_reported": "NA" if last_count is None else str(last_count),
        "screening_output": str(screening_output),
        "json_output": str(json_output),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "status": status,
        "command": shlex.join(last_cmd),
    }
    return row, successful_template


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radigest", default="radigest")
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
    if not args.reference.exists():
        fail(f"reference does not exist: {args.reference}")
    if not args.candidate_enzymes.exists():
        fail(f"candidate enzyme file does not exist: {args.candidate_enzymes}")

    radigest = resolve_executable(args.radigest)
    candidate_names = read_candidate_enzymes(args.candidate_enzymes)
    candidate_pairs_evaluated = len(candidate_names) * (len(candidate_names) - 1) // 2
    args.raw_dir.mkdir(parents=True, exist_ok=True)

    selected_template: str | None = None
    rows: list[dict[str, str]] = []
    for run_index in range(1, args.runs + 1):
        row, selected_template = run_once(
            radigest=radigest,
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
            command_template=args.command_template,
            selected_template=selected_template,
        )
        rows.append(row)

    write_rows(args.out, rows)
    failed = [row for row in rows if row["status"] != "PASS"]
    if failed:
        print(
            f"{len(failed)} of {len(rows)} radigest screening runs failed; "
            f"see {args.out}",
            file=sys.stderr,
        )
        return 1

    print(f"Wrote {len(rows)} screening timing rows to {args.out}")
    if args.command_template == "auto" and selected_template is not None:
        print("Selected radigest screening template:")
        print(selected_template)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
