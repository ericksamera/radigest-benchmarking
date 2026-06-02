#!/usr/bin/env python3
"""Run one matched-tool timing case repeatedly.

This runner intentionally records tool-specific primary-output counts without
claiming those counts have a shared coordinate interpretation.
"""

from __future__ import annotations

import argparse
import csv
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import NoReturn

RUN_COLUMNS = [
    "case_id",
    "tool_id",
    "dataset_id",
    "condition_id",
    "reference_path",
    "enzyme_1",
    "enzyme_2",
    "min_size",
    "max_size",
    "timing_scope",
    "run_index",
    "wall_seconds",
    "exit_code",
    "primary_output_type",
    "primary_count",
    "primary_output",
    "stdout_log",
    "stderr_log",
    "status",
    "command",
    "notes",
]

VALID_TOOLS = {"radigest", "digital_rads", "ddradseqtools", "simrad", "ddgrader"}


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


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


def resolve_executable(executable: str) -> str:
    candidate = Path(executable)
    if candidate.parent != Path(".") or candidate.is_absolute():
        if candidate.exists() and candidate.is_file():
            return str(candidate)
        fail(f"executable does not exist: {executable}")
    resolved = shutil.which(executable)
    if resolved is None:
        fail(f"executable not found on PATH: {executable}")
    return resolved


def count_data_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for row in reader if any(value.strip() for value in row))


def count_fasta_records(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith(">"):
                count += 1
    return count


def first_tsv_value(path: Path, column: str) -> str:
    if not path.exists():
        return "NA"
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            return row.get(column, "NA") or "NA"
    return "NA"


def shell_command(parts: list[str]) -> str:
    return shlex.join(parts)


def execute(cmd: list[str], stdout_log: Path, stderr_log: Path) -> tuple[int, float]:
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
    return proc.returncode, time.perf_counter() - start


def build_radigest_command(args: argparse.Namespace, run_dir: Path) -> tuple[list[str], Path, str]:
    output = run_dir / "radigest.fragments.tsv"
    json_output = run_dir / "radigest.json"
    cmd = [
        resolve_executable(args.radigest),
        "-fasta",
        str(args.reference),
        "-enzymes",
        f"{args.enzyme_1},{args.enzyme_2}",
        "-min",
        str(args.min_size),
        "-max",
        str(args.max_size),
        "-threads",
        "1",
        "-fragments-tsv",
        str(output),
        "-json",
        str(json_output),
    ]
    return cmd, output, "interval_set"


def build_digital_rads_command(
    args: argparse.Namespace, run_dir: Path
) -> tuple[list[str], Path, str]:
    output = run_dir / "digital_rads.raw.tsv"
    cmd = [
        "bash",
        "scripts/comparators/run_digital_rads.sh",
        "--digital-rads",
        "external/Digital_RADs/Digital_RADs.py",
        "--reference",
        str(args.reference),
        "--enzyme1",
        args.enzyme_1,
        "--enzyme2",
        args.enzyme_2,
        "--min",
        str(args.min_size),
        "--max",
        str(args.max_size),
        "--enzymes-tsv",
        "config/enzymes.tsv",
        "--work-dir",
        str(run_dir / "digital_rads.work"),
        "--raw-out",
        str(output),
        "--summary-out",
        str(run_dir / "digital_rads.summary.tsv"),
        "--version-out",
        str(run_dir / "digital_rads.version.txt"),
        "--stdout-log",
        str(run_dir / "digital_rads.wrapper.stdout.log"),
        "--stderr-log",
        str(run_dir / "digital_rads.wrapper.stderr.log"),
    ]
    return cmd, output, "interval_set"


def build_ddradseqtools_command(
    args: argparse.Namespace, run_dir: Path
) -> tuple[list[str], Path, str]:
    output = run_dir / "ddradseqtools.frags.fasta"
    cmd = [
        "bash",
        "scripts/comparators/run_ddradseqtools_rsitesearch.sh",
        "--repo",
        "external/ddRADseqTools",
        "--reference",
        str(args.reference),
        "--enzyme1",
        args.enzyme_1,
        "--enzyme2",
        args.enzyme_2,
        "--min",
        str(args.min_size),
        "--max",
        str(args.max_size),
        "--work-dir",
        str(run_dir / "ddradseqtools.work"),
        "--frags-out",
        str(output),
        "--stats-out",
        str(run_dir / "ddradseqtools.fragment_stats.txt"),
        "--summary-out",
        str(run_dir / "ddradseqtools.summary.tsv"),
        "--version-out",
        str(run_dir / "ddradseqtools.version.txt"),
        "--stdout-log",
        str(run_dir / "ddradseqtools.stdout.log"),
        "--stderr-log",
        str(run_dir / "ddradseqtools.stderr.log"),
    ]
    return cmd, output, "interval_set"


def build_simrad_command(args: argparse.Namespace, run_dir: Path) -> tuple[list[str], Path, str]:
    output = run_dir / "simrad.tsv"
    cmd = [
        "Rscript",
        "scripts/comparators/run_simrad_ddrad.R",
        "--reference",
        str(args.reference),
        "--enzyme1",
        args.enzyme_1,
        "--enzyme2",
        args.enzyme_2,
        "--min",
        str(args.min_size),
        "--max",
        str(args.max_size),
        "--enzymes-tsv",
        "config/enzymes.tsv",
        "--out",
        str(output),
        "--version-log",
        str(run_dir / "simrad.version.txt"),
    ]
    return cmd, output, "aggregate_count"


def build_ddgrader_command(args: argparse.Namespace, run_dir: Path) -> tuple[list[str], Path, str]:
    output = run_dir / "ddgrader.summary.tsv"
    cmd = [
        "python3",
        "scripts/comparators/run_ddgrader_backend.py",
        "--repo",
        args.ddgrader_repo,
        "--reference",
        str(args.reference),
        "--enzyme-pairs",
        f"{args.enzyme_1},{args.enzyme_2}",
        "--min",
        str(args.min_size),
        "--max",
        str(args.max_size),
        "--out-raw-csv",
        str(run_dir / "ddgrader.raw.csv"),
        "--out-bins",
        str(run_dir / "ddgrader.bins.tsv"),
        "--out-summary",
        str(output),
        "--version-log",
        str(run_dir / "ddgrader.version.txt"),
    ]
    return cmd, output, "binned_counts"


def primary_count(tool_id: str, output: Path) -> str:
    if tool_id in {"radigest", "digital_rads"}:
        return str(count_data_rows(output))
    if tool_id == "ddradseqtools":
        return str(count_fasta_records(output))
    if tool_id == "simrad":
        return first_tsv_value(output, "size_selected_fragments")
    if tool_id == "ddgrader":
        return first_tsv_value(output, "binned_fragments_in_window")
    return "NA"


def build_command(args: argparse.Namespace, run_dir: Path) -> tuple[list[str], Path, str]:
    builders = {
        "radigest": build_radigest_command,
        "digital_rads": build_digital_rads_command,
        "ddradseqtools": build_ddradseqtools_command,
        "simrad": build_simrad_command,
        "ddgrader": build_ddgrader_command,
    }
    return builders[args.tool_id](args, run_dir)


def run_once(args: argparse.Namespace, run_index: int) -> dict[str, str]:
    run_dir = args.raw_dir / f"run_{run_index:02d}"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = run_dir / "stdout.log"
    stderr_log = run_dir / "stderr.log"
    cmd, primary_output, primary_output_type = build_command(args, run_dir)
    exit_code, elapsed = execute(cmd, stdout_log, stderr_log)
    count = primary_count(args.tool_id, primary_output) if exit_code == 0 else "NA"
    status = "PASS" if exit_code == 0 and primary_output.exists() else "FAIL"
    return {
        "case_id": args.case_id,
        "tool_id": args.tool_id,
        "dataset_id": args.dataset_id,
        "condition_id": args.condition_id,
        "reference_path": str(args.reference),
        "enzyme_1": args.enzyme_1,
        "enzyme_2": args.enzyme_2,
        "min_size": str(args.min_size),
        "max_size": str(args.max_size),
        "timing_scope": args.timing_scope,
        "run_index": str(run_index),
        "wall_seconds": f"{elapsed:.6f}",
        "exit_code": str(exit_code),
        "primary_output_type": primary_output_type,
        "primary_count": count,
        "primary_output": str(primary_output),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "status": status,
        "command": shell_command(cmd),
        "notes": args.notes,
    }


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=RUN_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--tool-id", required=True, choices=sorted(VALID_TOOLS))
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--condition-id", required=True)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--enzyme-1", required=True)
    parser.add_argument("--enzyme-2", required=True)
    parser.add_argument("--min", dest="min_size", required=True, type=nonnegative_int)
    parser.add_argument("--max", dest="max_size", required=True, type=positive_int)
    parser.add_argument("--runs", required=True, type=positive_int)
    parser.add_argument("--timing-scope", required=True)
    parser.add_argument("--notes", default="")
    parser.add_argument("--radigest", default="radigest")
    parser.add_argument("--ddgrader-repo", default="external/ddRadSeqWebTool")
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_size <= args.min_size:
        fail("--max must be greater than --min")
    if not args.reference.exists():
        fail(f"reference does not exist: {args.reference}")
    rows = [run_once(args, run_index) for run_index in range(1, args.runs + 1)]
    write_rows(args.out, rows)
    failed = [row for row in rows if row["status"] != "PASS"]
    if failed:
        print(f"{len(failed)} of {len(rows)} matched-tool timing runs failed", file=sys.stderr)
        print(f"see {args.out}", file=sys.stderr)
        return 1
    print(f"Wrote {len(rows)} matched-tool timing rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
