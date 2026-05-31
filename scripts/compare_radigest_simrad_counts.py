#!/usr/bin/env python3
"""Compatibility wrapper for ``scripts/comparators/compare_radigest_simrad_counts.py``.

The implementation was moved during repository layout cleanup. This wrapper is
kept so existing Makefile, Snakemake, and documentation paths continue to work.
"""

from __future__ import annotations

import runpy
from pathlib import Path

TARGET = (
    Path(__file__).resolve().parent
    / "comparators"
    / "compare_radigest_simrad_counts.py"
)


if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
