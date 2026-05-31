#!/usr/bin/env python3
"""Generate screening-speed comparison figures.

Input:
  results/tables/screening_speed_summary.tsv

Outputs:
  results/figures/screening_speed_wall_time.png
  results/figures/screening_speed_pairs_per_second.png
  results/figures/screening_speed_peak_rss.png

This figure compares screening workflow throughput, not coordinate equivalence.
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
        raise FileNotFoundError(f"missing screening summary: {path}")

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


def label(row: dict[str, str]) -> str:
    tool = row.get("tool", "")
    if tool == "radigest":
        return "radigest\nscreen-pairs"
    if tool == "ddgRADer_backend":
        return "ddgRADer\nbackend"
    return tool or row.get("task", "")


def sorted_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    order = {"radigest": 0, "ddgRADer_backend": 1}
    return sorted(rows, key=lambda row: order.get(row.get("tool", ""), 99))


def plot_metric(
    rows: list[dict[str, str]],
    out: Path,
    manuscript_dir: Path | None,
    value_col: str,
    q1_col: str | None,
    q3_col: str | None,
    ylabel: str,
    title: str,
    scale: float = 1.0,
    log_y: bool = True,
) -> None:
    labels: list[str] = []
    values: list[float] = []
    lower: list[float] = []
    upper: list[float] = []

    for row in sorted_rows(rows):
        value = to_float(row.get(value_col))
        if value is None:
            continue

        q1 = to_float(row.get(q1_col)) if q1_col else None
        q3 = to_float(row.get(q3_col)) if q3_col else None

        labels.append(label(row))
        values.append(value * scale)

        if q1 is not None and q3 is not None:
            lower.append(max(0.0, (value - q1) * scale))
            upper.append(max(0.0, (q3 - value) * scale))
        else:
            lower.append(0.0)
            upper.append(0.0)

    if not values:
        raise ValueError(f"no plottable values for {value_col}")

    x = list(range(len(values)))

    plt.figure(figsize=(6.5, 4.8))
    plt.bar(x, values, yerr=[lower, upper], capsize=4)
    plt.xticks(x, labels)
    plt.ylabel(ylabel)
    plt.title(title)

    if log_y:
        plt.yscale("log")

    save_figure(out, manuscript_dir)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/tables/screening_speed_summary.tsv"),
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
        rows = read_rows(args.summary)
        manuscript_dir = None if args.no_manuscript_copy else args.manuscript_dir

        plot_metric(
            rows=rows,
            out=args.out_dir / "screening_speed_wall_time.png",
            manuscript_dir=manuscript_dir,
            value_col="median_elapsed_wall_seconds",
            q1_col="q1_elapsed_wall_seconds",
            q3_col="q3_elapsed_wall_seconds",
            ylabel="Wall time (s), median with Q1-Q3",
            title="Enzyme-pair screening runtime",
            log_y=True,
        )

        plot_metric(
            rows=rows,
            out=args.out_dir / "screening_speed_pairs_per_second.png",
            manuscript_dir=manuscript_dir,
            value_col="median_pairs_per_second",
            q1_col=None,
            q3_col=None,
            ylabel="Completed pairs per second",
            title="Enzyme-pair screening throughput",
            log_y=True,
        )

        plot_metric(
            rows=rows,
            out=args.out_dir / "screening_speed_peak_rss.png",
            manuscript_dir=manuscript_dir,
            value_col="median_max_rss_kb",
            q1_col="q1_max_rss_kb",
            q3_col="q3_max_rss_kb",
            ylabel="Peak RSS (MiB), median with Q1-Q3",
            title="Enzyme-pair screening memory",
            scale=1.0 / 1024.0,
            log_y=False,
        )

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
