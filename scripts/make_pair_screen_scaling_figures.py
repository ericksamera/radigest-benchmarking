#!/usr/bin/env python3
"""Generate radigest-screen-pairs job-scaling figures."""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

import matplotlib.pyplot as plt


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing summary table: {path}")

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

    value = value.strip()
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


def sorted_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(rows, key=lambda row: int(float(row["jobs"])))


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
    log_y: bool = False,
) -> None:
    x_values: list[float] = []
    y_values: list[float] = []
    lower_errors: list[float] = []
    upper_errors: list[float] = []

    for row in sorted_rows(rows):
        jobs = to_float(row.get("jobs"))
        value = to_float(row.get(value_col))

        if jobs is None or value is None:
            continue

        q1 = to_float(row.get(q1_col)) if q1_col else None
        q3 = to_float(row.get(q3_col)) if q3_col else None

        x_values.append(jobs)
        y_values.append(value * scale)

        if q1 is not None and q3 is not None:
            lower_errors.append(max(0.0, (value - q1) * scale))
            upper_errors.append(max(0.0, (q3 - value) * scale))
        else:
            lower_errors.append(0.0)
            upper_errors.append(0.0)

    if not x_values:
        raise ValueError(f"no plottable rows for {value_col}")

    plt.figure(figsize=(6.8, 4.8))
    plt.errorbar(
        x_values,
        y_values,
        yerr=[lower_errors, upper_errors],
        marker="o",
        capsize=4,
    )
    plt.xticks(x_values, [str(int(x)) for x in x_values])
    plt.xlabel("radigest-screen-pairs --jobs")
    plt.ylabel(ylabel)
    plt.title(title)

    if log_y:
        plt.yscale("log")

    save_figure(out, manuscript_dir)


def plot_speedup(
    rows: list[dict[str, str]],
    out: Path,
    manuscript_dir: Path | None,
) -> None:
    x_values: list[float] = []
    y_values: list[float] = []

    for row in sorted_rows(rows):
        jobs = to_float(row.get("jobs"))
        speedup = to_float(row.get("speedup_vs_jobs1"))

        if jobs is None or speedup is None:
            continue

        x_values.append(jobs)
        y_values.append(speedup)

    if not x_values:
        raise ValueError("no plottable speedup rows")

    plt.figure(figsize=(6.8, 4.8))
    plt.plot(x_values, y_values, marker="o", label="observed")
    plt.plot(x_values, x_values, linestyle="--", label="ideal")
    plt.xticks(x_values, [str(int(x)) for x in x_values])
    plt.xlabel("radigest-screen-pairs --jobs")
    plt.ylabel("Speedup relative to jobs=1")
    plt.title("Pair-screening job-level speedup")
    plt.legend()

    save_figure(out, manuscript_dir)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/tables/pair_screen_scaling_summary.tsv"),
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
            out=args.out_dir / "pair_screen_job_scaling_wall_time.png",
            manuscript_dir=manuscript_dir,
            value_col="median_elapsed_wall_seconds",
            q1_col="q1_elapsed_wall_seconds",
            q3_col="q3_elapsed_wall_seconds",
            ylabel="Wall time (s), median with Q1-Q3",
            title="Pair-screening runtime by job count",
        )

        plot_metric(
            rows=rows,
            out=args.out_dir / "pair_screen_job_scaling_throughput.png",
            manuscript_dir=manuscript_dir,
            value_col="median_pairs_per_second",
            q1_col=None,
            q3_col=None,
            ylabel="Completed enzyme pairs per second",
            title="Pair-screening throughput by job count",
        )

        plot_metric(
            rows=rows,
            out=args.out_dir / "pair_screen_job_scaling_peak_rss.png",
            manuscript_dir=manuscript_dir,
            value_col="median_max_rss_kb",
            q1_col="q1_max_rss_kb",
            q3_col="q3_max_rss_kb",
            ylabel="Peak RSS (MiB), median with Q1-Q3",
            title="Pair-screening memory by job count",
            scale=1.0 / 1024.0,
        )

        plot_speedup(
            rows=rows,
            out=args.out_dir / "pair_screen_job_scaling_speedup.png",
            manuscript_dir=manuscript_dir,
        )

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
