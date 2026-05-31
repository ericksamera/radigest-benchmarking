#!/usr/bin/env python3
"""Compatibility wrapper for scripts/core/audit_reproducibility.py."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

target = Path(__file__).resolve().parent / "core" / "audit_reproducibility.py"
sys.argv[0] = str(target)
runpy.run_path(str(target), run_name="__main__")
