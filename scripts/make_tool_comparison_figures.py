#!/usr/bin/env python3
"""Generate matched-tool timing comparison figures.

Input:
  results/tables/tool_timing_interpretation.tsv

Outputs:
  results/figures/tool_wall_time_comparison.png
  results/figures/tool_memory_comparison.png

The table intentionally separates timing scopes:
  - cold_command
  - warm_package_reload_reference
  - warm_package_reuse_reference

Do not collapse those scopes into a single SimRAD value.
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
        raise FileNotFoundError(f"missing timing table: {path}")

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


def short_label(row: dict[str, str]) -> str:
    tool = row.get("tool", "")
    task = row.get("task", "")
    scope = row.get("timing_scope", "")

    if task == "radigest_count":
        return "radigest\nJSON\ncold"
    if task == "radigest_interval":
        return "radigest\ninterval\ncold"
    if task == "digital_rads_interval":
        return "Digital_RADs\ninterval\ncold"
    if task == "simrad_count":
        return "SimRAD\ncount\ncold"
    if task == "simrad_warm_reload_reference":
        return "SimRAD\ncount\nwarm\nreload ref"
    if task == "simrad_warm_reuse_reference":
        return "SimRAD\ncount\nwarm\nreuse ref"

    return f"{tool}\n{task}\n{scope}"


def ordered_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    order = {
        "radigest_count": 0,
        "radigest_interval": 1,
        "digital_rads_interval": 2,
        "simrad_count": 3,
        "simrad_warm_reload_reference": 4,
        "simrad_warm_reuse_reference": 5,
    }
    return sorted(rows, key=lambda row: order.get(row.get("task", ""), 999))


def save_figure(path: Path, manuscript_dir: Path | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()

    if manuscript_dir is not None:
        manuscript_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, manuscript_dir / path.name)


def runtime_values(row: dict[str, str]) -> tuple[float | None, float, float]:
    median = to_float(row.get("median_elapsed_wall_seconds"))
    if median is None:
        return None, 0.0, 0.0

    q1 = to_float(row.get("q1_elapsed_wall_seconds"))
    q3 = to_float(row.get("q3_elapsed_wall_seconds"))

    if q1 is not None and q3 is not None:
        return median, max(0.0, median - q1), max(0.0, q3 - median)

    return median, 0.0, 0.0


def memory_values(row: dict[str, str]) -> tuple[float | None, float, float]:
    """Return memory in MiB.

    Cold-command rows use median_max_rss_kb and Q1/Q3 when available.
    Warm SimRAD rows may only have process_max_rss_kb from /usr/bin/time -v
    for the whole R session.
    """
    median_kb = to_float(row.get("median_max_rss_kb"))

    if median_kb is not None:
        q1_kb = to_float(row.get("q1_max_rss_kb"))
        q3_kb = to_float(row.get("q3_max_rss_kb"))

        median = median_kb / 1024.0
        if q1_kb is not None and q3_kb is not None:
            lower = max(0.0, (median_kb - q1_kb) / 1024.0)
            upper = max(0.0, (q3_kb - median_kb) / 1024.0)
            return median, lower, upper

        return median, 0.0, 0.0

    process_kb = to_float(row.get("process_max_rss_kb"))
    if process_kb is not None:
        return process_kb / 1024.0, 0.0, 0.0

    return None, 0.0, 0.0


def plot_bars(
    rows: list[dict[str, str]],
    value_getter,
    ylabel: str,
    title: str,
    out: Path,
    manuscript_dir: Path | None,
    log_y: bool,
) -> None:
    labels: list[str] = []
    values: list[float] = []
    lower: list[float] = []
    upper: list[float] = []

    for row in ordered_rows(rows):
        value, lo, hi = value_getter(row)
        if value is None:
            continue
        labels.append(short_label(row))
        values.append(value)
        lower.append(lo)
        upper.append(hi)

    if not values:
        raise ValueError(f"no plottable values for {out}")

    x = list(range(len(values)))

    width = max(7.0, 1.0 * len(values) + 2.5)
    plt.figure(figsize=(width, 5.5))
    plt.bar(x, values, yerr=[lower, upper], capsize=4)
    plt.xticks(x, labels, rotation=0)
    plt.ylabel(ylabel)
    plt.title(title)

    if log_y:
        plt.yscale("log")

    save_figure(out, manuscript_dir)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timing-table",
        type=Path,
        default=Path("results/tables/tool_timing_interpretation.tsv"),
    )
    parser.add_argument("--out-dir", type=Path, default=Path("results/figures"))
    parser.add_argument(
        "--manuscript-dir",
        type=Path,
        default=Path("manuscript_figures"),
    )
    parser.add_argument("--no-manuscript-copy", action="store_true")
    parser.add_argument(
        "--linear",
        action="store_true",
        help="Use linear y-axis instead of log scale.",
    )
    args = parser.parse_args(argv)

    try:
        rows = read_rows(args.timing_table)
        manuscript_dir = None if args.no_manuscript_copy else args.manuscript_dir

        plot_bars(
            rows=rows,
            value_getter=runtime_values,
            ylabel="Wall time (s), median with Q1-Q3",
            title="Matched digest-task timing by tool and timing scope",
            out=args.out_dir / "tool_wall_time_comparison.png",
            manuscript_dir=manuscript_dir,
            log_y=not args.linear,
        )

        plot_bars(
            rows=rows,
            value_getter=memory_values,
            ylabel="Peak RSS (MiB)",
            title="Matched digest-task memory by tool and timing scope",
            out=args.out_dir / "tool_memory_comparison.png",
            manuscript_dir=manuscript_dir,
            log_y=not args.linear,
        )

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
