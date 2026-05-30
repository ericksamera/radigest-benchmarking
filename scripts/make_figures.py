#!/usr/bin/env python3
"""Generate benchmark figures with matplotlib.

Runtime and peak-RSS plots use median values with Q1-Q3 error bars when
available. If Q1/Q3 are absent but IQR is present, symmetric IQR/2 bars are
used as a fallback.

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


def save_figure(path: Path, manuscript_dir: Path | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()

    if manuscript_dir is not None:
        manuscript_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, manuscript_dir / path.name)


def value_and_error(
    row: dict[str, str],
    median_col: str,
    q1_col: str,
    q3_col: str,
    iqr_col: str,
    scale: float = 1.0,
) -> tuple[float | None, float, float]:
    """Return median and asymmetric lower/upper errors.

    Values are multiplied by scale after computing the error.
    """
    median = to_float(row.get(median_col, ""))
    if median is None:
        return None, 0.0, 0.0

    q1 = to_float(row.get(q1_col, ""))
    q3 = to_float(row.get(q3_col, ""))

    if q1 is not None and q3 is not None:
        lower = max(0.0, median - q1)
        upper = max(0.0, q3 - median)
        return median * scale, lower * scale, upper * scale

    iqr = to_float(row.get(iqr_col, ""))
    if iqr is not None:
        half = iqr / 2.0
        return median * scale, half * scale, half * scale

    return median * scale, 0.0, 0.0


def labels_for_rows(rows: list[dict[str, str]]) -> list[str]:
    labels: list[str] = []

    for row in rows:
        condition = row.get("condition", "")
        mode = row.get("output_mode", "")

        if condition:
            labels.append(f"{condition}\n{mode}")
        else:
            labels.append(mode)

    return labels


def bar_with_errors(
    rows: list[dict[str, str]],
    out_path: Path,
    manuscript_dir: Path | None,
    median_col: str,
    q1_col: str,
    q3_col: str,
    iqr_col: str,
    ylabel: str,
    title: str,
    scale: float = 1.0,
) -> None:
    labels: list[str] = []
    values: list[float] = []
    lower_errors: list[float] = []
    upper_errors: list[float] = []

    for row in rows:
        median, lower, upper = value_and_error(
            row=row,
            median_col=median_col,
            q1_col=q1_col,
            q3_col=q3_col,
            iqr_col=iqr_col,
            scale=scale,
        )

        if median is None:
            continue

        condition = row.get("condition", "")
        mode = row.get("output_mode", "")
        label = f"{condition}\n{mode}" if condition else mode

        labels.append(label)
        values.append(median)
        lower_errors.append(lower)
        upper_errors.append(upper)

    if not values:
        print(f"skip {out_path.name}: no plottable data", file=sys.stderr)
        return

    x = list(range(len(values)))
    yerr = [lower_errors, upper_errors]

    plt.figure()
    plt.bar(x, values, yerr=yerr, capsize=4)
    plt.xticks(x, labels, rotation=45, ha="right")
    plt.ylabel(ylabel)
    plt.title(title)
    save_figure(out_path, manuscript_dir)


def runtime_by_output_mode(
    rows: list[dict[str, str]],
    out_dir: Path,
    manuscript_dir: Path | None,
) -> None:
    bar_with_errors(
        rows=rows,
        out_path=out_dir / "runtime_by_output_mode.png",
        manuscript_dir=manuscript_dir,
        median_col="median_elapsed_wall_seconds",
        q1_col="q1_elapsed_wall_seconds",
        q3_col="q3_elapsed_wall_seconds",
        iqr_col="iqr_elapsed_wall_seconds",
        ylabel="Wall time (s), median with Q1-Q3",
        title="radigest runtime by condition and output mode",
    )


def rss_by_output_mode(
    rows: list[dict[str, str]],
    out_dir: Path,
    manuscript_dir: Path | None,
) -> None:
    bar_with_errors(
        rows=rows,
        out_path=out_dir / "peak_rss_by_output_mode.png",
        manuscript_dir=manuscript_dir,
        median_col="median_max_rss_kb",
        q1_col="q1_max_rss_kb",
        q3_col="q3_max_rss_kb",
        iqr_col="iqr_max_rss_kb",
        ylabel="Peak RSS (MiB), median with Q1-Q3",
        title="radigest peak memory by condition and output mode",
        scale=1.0 / 1024.0,
    )


def output_size_by_mode(
    rows: list[dict[str, str]],
    out_dir: Path,
    manuscript_dir: Path | None,
) -> None:
    bar_with_errors(
        rows=rows,
        out_path=out_dir / "output_size_by_mode.png",
        manuscript_dir=manuscript_dir,
        median_col="median_primary_output_size_bytes",
        q1_col="q1_primary_output_size_bytes",
        q3_col="q3_primary_output_size_bytes",
        iqr_col="iqr_primary_output_size_bytes",
        ylabel="Primary output size (bytes), median with Q1-Q3",
        title="radigest output size by condition and output mode",
    )


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
