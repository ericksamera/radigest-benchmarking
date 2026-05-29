#!/usr/bin/env python3
"""Generate benchmark figures with matplotlib.

Figures are generated only from existing summary tables. This script does not
invent or impute missing benchmark data.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

import matplotlib.pyplot as plt


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def to_float(value: str) -> float | None:
    value = str(value).strip()
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def save_figure(path: Path, manuscript_dir: Path | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()

    if manuscript_dir is not None:
        manuscript_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, manuscript_dir / path.name)


def runtime_by_output_mode(
    rows: list[dict[str, str]],
    out_dir: Path,
    manuscript_dir: Path | None,
) -> None:
    points: list[tuple[str, float]] = []

    for row in rows:
        mode = row.get("output_mode", "")
        elapsed = to_float(row.get("median_elapsed_wall_seconds", ""))
        if mode and elapsed is not None:
            points.append((mode, elapsed))

    if not points:
        print("skip runtime figure: no elapsed-time data", file=sys.stderr)
        return

    labels = [x[0] for x in points]
    values = [x[1] for x in points]

    plt.figure()
    plt.bar(labels, values)
    plt.xlabel("Output mode")
    plt.ylabel("Median wall time (s)")
    plt.title("radigest runtime by output mode")
    plt.xticks(rotation=45, ha="right")
    save_figure(out_dir / "runtime_by_output_mode.png", manuscript_dir)


def rss_by_output_mode(
    rows: list[dict[str, str]],
    out_dir: Path,
    manuscript_dir: Path | None,
) -> None:
    points: list[tuple[str, float]] = []

    for row in rows:
        mode = row.get("output_mode", "")
        rss = to_float(row.get("median_max_rss_kb", ""))
        if mode and rss is not None:
            points.append((mode, rss / 1024.0))

    if not points:
        print("skip RSS figure: no max-RSS data", file=sys.stderr)
        return

    labels = [x[0] for x in points]
    values = [x[1] for x in points]

    plt.figure()
    plt.bar(labels, values)
    plt.xlabel("Output mode")
    plt.ylabel("Median peak RSS (MiB)")
    plt.title("radigest peak memory by output mode")
    plt.xticks(rotation=45, ha="right")
    save_figure(out_dir / "peak_rss_by_output_mode.png", manuscript_dir)


def output_size_by_mode(
    rows: list[dict[str, str]],
    out_dir: Path,
    manuscript_dir: Path | None,
) -> None:
    points: list[tuple[str, float]] = []

    for row in rows:
        mode = row.get("output_mode", "")
        size = to_float(row.get("median_primary_output_size_bytes", ""))
        if mode and size is not None:
            points.append((mode, size))

    if not points:
        print("skip output-size figure: no output-size data", file=sys.stderr)
        return

    labels = [x[0] for x in points]
    values = [x[1] for x in points]

    plt.figure()
    plt.bar(labels, values)
    plt.xlabel("Output mode")
    plt.ylabel("Median primary output size (bytes)")
    plt.title("radigest output size by mode")
    plt.xticks(rotation=45, ha="right")
    save_figure(out_dir / "output_size_by_mode.png", manuscript_dir)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark-summary",
        type=Path,
        default=Path("results/tables/radigest_benchmark_summary.tsv"),
    )
    parser.add_argument("--out-dir", type=Path, default=Path("results/figures"))
    parser.add_argument(
        "--manuscript-dir",
        type=Path,
        default=Path("manuscript_figures"),
    )
    parser.add_argument(
        "--no-manuscript-copy",
        action="store_true",
        help="Do not copy figures to manuscript_figures/.",
    )
    args = parser.parse_args(argv)

    rows = read_tsv(args.benchmark_summary)
    if not rows:
        print(f"error: no rows found in {args.benchmark_summary}", file=sys.stderr)
        return 2

    manuscript_dir = None if args.no_manuscript_copy else args.manuscript_dir

    runtime_by_output_mode(rows, args.out_dir, manuscript_dir)
    rss_by_output_mode(rows, args.out_dir, manuscript_dir)
    output_size_by_mode(rows, args.out_dir, manuscript_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
