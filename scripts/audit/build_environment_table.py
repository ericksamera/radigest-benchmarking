#!/usr/bin/env python3
"""Build a reproducibility/environment table for the benchmark run."""

from __future__ import annotations

import argparse
import csv
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NoReturn

COLUMNS = ["key", "value", "source"]


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def run_command(command: list[str], *, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "NA"
    output = result.stdout.strip()
    if result.returncode != 0 or not output:
        return "NA"
    return output.splitlines()[0]


def resolve_executable(value: str) -> str:
    if value in {"", "NA", "auto"}:
        return value or "NA"
    path = Path(value)
    if path.is_absolute() or path.parent != Path("."):
        return str(path)
    resolved = shutil.which(value)
    return resolved if resolved is not None else value


def executable_version(value: str) -> str:
    resolved = resolve_executable(value)
    if resolved in {"", "NA", "auto"}:
        return "NA"
    for args in [[resolved, "--version"], [resolved, "version"]]:
        version = run_command(args)
        if version != "NA":
            return version
    return "NA"


def git_dirty(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "NA"
    if result.returncode != 0:
        return "NA"
    return "false" if result.stdout.strip() == "" else "true"


def rows_for(args: argparse.Namespace) -> list[dict[str, str]]:
    root = args.root.resolve()
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    radigest_path = resolve_executable(args.radigest)
    screen_path = resolve_executable(args.radigest_screen_pairs_cached)
    snakemake_path = shutil.which("snakemake") or "NA"
    return [
        {"key": "timestamp_utc", "value": timestamp, "source": "runtime"},
        {"key": "cwd", "value": str(root), "source": "runtime"},
        {"key": "platform", "value": platform.platform(), "source": "python.platform"},
        {
            "key": "python_version",
            "value": sys.version.replace("\n", " "),
            "source": "sys.version",
        },
        {
            "key": "python_executable",
            "value": sys.executable,
            "source": "sys.executable",
        },
        {
            "key": "conda_prefix",
            "value": os.environ.get("CONDA_PREFIX", "NA"),
            "source": "CONDA_PREFIX",
        },
        {
            "key": "git_commit",
            "value": run_command(["git", "rev-parse", "HEAD"], cwd=root),
            "source": "git",
        },
        {
            "key": "git_branch",
            "value": run_command(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root
            ),
            "source": "git",
        },
        {"key": "git_dirty", "value": git_dirty(root), "source": "git"},
        {"key": "snakemake_path", "value": snakemake_path, "source": "PATH"},
        {
            "key": "snakemake_version",
            "value": run_command(["snakemake", "--version"]),
            "source": "snakemake --version",
        },
        {
            "key": "radigest_path",
            "value": radigest_path,
            "source": "workflow config radigest",
        },
        {
            "key": "radigest_version",
            "value": executable_version(args.radigest),
            "source": "radigest --version",
        },
        {
            "key": "radigest_screen_pairs_cached_path",
            "value": screen_path,
            "source": "workflow config radigest_screen_pairs_cached",
        },
        {
            "key": "radigest_screen_pairs_cached_version",
            "value": executable_version(args.radigest_screen_pairs_cached),
            "source": "radigest-screen-pairs-cached --version",
        },
    ]


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--root", default=Path("."), type=Path)
    parser.add_argument("--radigest", default="radigest")
    parser.add_argument("--radigest-screen-pairs-cached", default="auto")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    write_rows(args.out, rows_for(args))
    print(f"Wrote environment table to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
