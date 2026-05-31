#!/usr/bin/env python3
"""Compatibility wrapper for ``scripts/benchmarks/compare_input_format_benchmark.py``.

The implementation was moved during repository layout cleanup. This wrapper is
kept so existing Makefile, Snakemake, and documentation paths continue to work.
"""

from __future__ import annotations

import runpy
from pathlib import Path

TARGET = (
    Path(__file__).resolve().parent / "benchmarks" / "compare_input_format_benchmark.py"
)


if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
