#!/usr/bin/env python3
"""Compatibility wrapper for ``scripts/validation/normalize_radigest_tsv.py``.

The implementation was moved during repository layout cleanup. This wrapper is
kept so existing Makefile, Snakemake, and documentation paths continue to work.
"""

from __future__ import annotations

import runpy
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "validation" / "normalize_radigest_tsv.py"


if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
