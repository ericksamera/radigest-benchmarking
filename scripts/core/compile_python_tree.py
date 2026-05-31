#!/usr/bin/env python3
"""Recursively compile Python scripts under one or more directories."""

from __future__ import annotations

import py_compile
import sys
from pathlib import Path


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    return bool(
        parts.intersection(
            {
                ".git",
                ".snakemake",
                ".mypy_cache",
                ".pytest_cache",
                ".ruff_cache",
                "__pycache__",
                ".phase1_backups",
                ".phase2_backups",
            }
        )
    )


def main(argv: list[str]) -> int:
    roots = [Path(arg) for arg in argv] if argv else [Path("scripts")]
    files: list[Path] = []

    for root in roots:
        if root.is_file() and root.suffix == ".py":
            files.append(root)
        elif root.exists():
            files.extend(sorted(root.rglob("*.py")))

    files = [path for path in files if not should_skip(path)]

    failed = False
    for path in files:
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            print(exc.msg, file=sys.stderr)
            failed = True

    if failed:
        return 1

    print(f"compiled {len(files)} Python file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
