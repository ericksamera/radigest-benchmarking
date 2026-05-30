#!/usr/bin/env python3
"""Generate radigest input-format benchmark figures.

Input:
  results/tables/radigest_input_format_comparison.tsv

Outputs:
  results/figures/input_format_runtime.png
  results/figures/input_format_runtime_ratio.png
  results/figures/input_format_memory.png
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

import matplotlib.pyplot as plt


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing input-format comparison table: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return [
            {
                key: "" if value is None else value
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]


def to_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = str(value).strip()
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def save_figure(path: Path, manuscript_dir: Path | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()

    if manuscript_dir is not None:
        manuscript_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, manuscript_dir / path.name)


def mode_order(mode: str) -> int:
    order = {
        "json": 0,
        "gff": 1,
        "fragments_tsv": 2,
        "fragments_fasta": 3,
    }
    return order.get(mode, 999)


def sorted_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(rows, key=lambda row: mode_order(row.get("output_mode", "")))


def plot_runtime(rows: list[dict[str, str]], out_dir: Path, manuscript_dir: Path | None) -> None:
    labels: list[str] = []
    gzip_values: list[float] = []
    plain_values: list[float] = []

    for row in sorted_rows(rows):
        mode = row.get("output_mode", "")
        gzip_value = to_float(row.get("gzip_median_elapsed_wall_seconds"))
        plain_value = to_float(row.get("plain_median_elapsed_wall_seconds"))
        if gzip_value is None or plain_value is None:
            continue
        labels.append(mode)
        gzip_values.append(gzip_value)
        plain_values.append(plain_value)

    if not labels:
        raise ValueError("no plottable runtime rows")

    x = list(range(len(labels)))
    offset = 0.18

    plt.figure(figsize=(7.5, 5.0))
    plt.bar([v - offset for v in x], gzip_values, width=0.35, label="gzipped FASTA")
    plt.bar([v + offset for v in x], plain_values, width=0.35, label="plain FASTA")
    plt.xticks(x, labels, rotation=30, ha="right")
    plt.ylabel("Wall time (s), median")
    plt.title("radigest input-format benchmark")
    plt.legend()
    save_figure(out_dir / "input_format_runtime.png", manuscript_dir)


def plot_runtime_ratio(
    rows: list[dict[str, str]],
    out_dir: Path,
    manuscript_dir: Path | None,
) -> None:
    labels: list[str] = []
    ratios: list[float] = []

    for row in sorted_rows(rows):
        mode = row.get("output_mode", "")
        ratio = to_float(row.get("elapsed_ratio_gzip_over_plain"))
        if ratio is None:
            continue
        labels.append(mode)
        ratios.append(ratio)

    if not labels:
        raise ValueError("no plottable runtime-ratio rows")

    x = list(range(len(labels)))

    plt.figure(figsize=(7.5, 5.0))
    plt.bar(x, ratios)
    plt.axhline(1.0, linestyle="--", linewidth=1)
    plt.xticks(x, labels, rotation=30, ha="right")
    plt.ylabel("Median time ratio: gzipped / plain")
    plt.title("radigest gzip input overhead by output mode")
    save_figure(out_dir / "input_format_runtime_ratio.png", manuscript_dir)


def plot_memory(rows: list[dict[str, str]], out_dir: Path, manuscript_dir: Path | None) -> None:
    labels: list[str] = []
    gzip_values: list[float] = []
    plain_values: list[float] = []

    for row in sorted_rows(rows):
        mode = row.get("output_mode", "")
        gzip_value = to_float(row.get("gzip_median_max_rss_kb"))
        plain_value = to_float(row.get("plain_median_max_rss_kb"))
        if gzip_value is None or plain_value is None:
            continue
        labels.append(mode)
        gzip_values.append(gzip_value / 1024.0)
        plain_values.append(plain_value / 1024.0)

    if not labels:
        raise ValueError("no plottable memory rows")

    x = list(range(len(labels)))
    offset = 0.18

    plt.figure(figsize=(7.5, 5.0))
    plt.bar([v - offset for v in x], gzip_values, width=0.35, label="gzipped FASTA")
    plt.bar([v + offset for v in x], plain_values, width=0.35, label="plain FASTA")
    plt.xticks(x, labels, rotation=30, ha="right")
    plt.ylabel("Peak RSS (MiB), median")
    plt.title("radigest input-format memory benchmark")
    plt.legend()
    save_figure(out_dir / "input_format_memory.png", manuscript_dir)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--comparison",
        type=Path,
        default=Path("results/tables/radigest_input_format_comparison.tsv"),
    )
    parser.add_argument("--out-dir", type=Path, default=Path("results/figures"))
    parser.add_argument(
        "--manuscript-dir",
        type=Path,
        default=Path("manuscript_figures"),
    )
    parser.add_argument("--no-manuscript-copy", action="store_true")
    args = parser.parse_args(argv)

    try:
        rows = read_rows(args.comparison)
        manuscript_dir = None if args.no_manuscript_copy else args.manuscript_dir
        plot_runtime(rows, args.out_dir, manuscript_dir)
        plot_runtime_ratio(rows, args.out_dir, manuscript_dir)
        plot_memory(rows, args.out_dir, manuscript_dir)

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
