#!/usr/bin/env python3
"""Parse GNU /usr/bin/time -v output files into TSV."""

from __future__ import annotations

import re
import sys
from pathlib import Path

PATTERNS = {
    "elapsed_wall_time": re.compile(r"Elapsed \(wall clock\) time.*: (.+)"),
    "user_seconds": re.compile(r"User time \(seconds\): (.+)"),
    "system_seconds": re.compile(r"System time \(seconds\): (.+)"),
    "percent_cpu": re.compile(r"Percent of CPU this job got: (.+)"),
    "max_rss_kb": re.compile(r"Maximum resident set size \(kbytes\): (.+)"),
    "exit_status": re.compile(r"Exit status: (.+)"),
}

HEADER = [
    "file",
    "command",
    "elapsed_wall_time",
    "user_seconds",
    "system_seconds",
    "percent_cpu",
    "max_rss_kb",
    "exit_status",
]


def parse_time_file(path: Path) -> dict[str, str]:
    text = path.read_text(errors="replace")
    values = {key: "" for key in PATTERNS}
    for key, pattern in PATTERNS.items():
        match = pattern.search(text)
        if match:
            values[key] = match.group(1).strip()
    return values


def main(argv: list[str]) -> int:
    print("\t".join(HEADER))

    for item in argv:
        path = Path(item)
        if not path.exists():
            print(f"warning: missing time file: {path}", file=sys.stderr)
            continue

        values = parse_time_file(path)
        row = {
            "file": str(path),
            "command": "",
            **values,
        }
        print("\t".join(row.get(col, "") for col in HEADER))

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
