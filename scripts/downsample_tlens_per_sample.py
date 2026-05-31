#!/usr/bin/env python3
"""Compatibility wrapper for ``scripts/empirical/downsample_tlens_per_sample.py``.

The implementation was moved during repository layout cleanup. This wrapper is
kept so existing Makefile, Snakemake, and documentation paths continue to work.
"""

from __future__ import annotations

import runpy
from pathlib import Path

TARGET = (
    Path(__file__).resolve().parent / "empirical" / "downsample_tlens_per_sample.py"
)


if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
