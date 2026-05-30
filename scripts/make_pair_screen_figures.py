#!/usr/bin/env python3
"""Generate enzyme-pair screening heatmap with matplotlib only."""

from __future__ import annotations

import argparse
import csv
import math
import shutil
import sys
from pathlib import Path

import matplotlib.pyplot as plt


def read_matrix(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing matrix TSV: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return list(reader)


def to_float(value: str) -> float | None:
    value = str(value).strip()
    if value == "":
        return None

    try:
        return float(value)
    except ValueError:
        return None


def build_matrix(
    rows: list[dict[str, str]],
    log10: bool,
) -> tuple[list[str], list[list[float]], str]:
    enzymes = sorted(
        {row.get("enzyme1", "") for row in rows if row.get("enzyme1", "")}
        | {row.get("enzyme2", "") for row in rows if row.get("enzyme2", "")}
    )

    if not enzymes:
        raise ValueError("no enzymes found in pair-screen matrix table")

    index = {enzyme: i for i, enzyme in enumerate(enzymes)}
    matrix = [[math.nan for _ in enzymes] for _ in enzymes]

    metric_name = rows[0].get("metric_name", "metric") if rows else "metric"

    for row in rows:
        enzyme1 = row.get("enzyme1", "")
        enzyme2 = row.get("enzyme2", "")
        value = to_float(row.get("metric_value", ""))

        if enzyme1 not in index or enzyme2 not in index or value is None:
            continue

        if log10:
            if value <= 0:
                plotted_value = math.nan
            else:
                plotted_value = math.log10(value)
        else:
            plotted_value = value

        i = index[enzyme1]
        j = index[enzyme2]
        matrix[i][j] = plotted_value
        matrix[j][i] = plotted_value

    return enzymes, matrix, metric_name


def save_figure(path: Path, manuscript_dir: Path | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()

    if manuscript_dir is not None:
        manuscript_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, manuscript_dir / path.name)


def make_heatmap(
    enzymes: list[str],
    matrix: list[list[float]],
    metric_name: str,
    out: Path,
    manuscript_dir: Path | None,
    log10: bool,
) -> None:
    width = max(6.0, 0.55 * len(enzymes) + 2.5)
    height = max(5.0, 0.50 * len(enzymes) + 2.0)

    label = f"log10({metric_name})" if log10 else metric_name

    plt.figure(figsize=(width, height))
    image = plt.imshow(matrix, aspect="auto")
    plt.colorbar(image, label=label)
    plt.xticks(range(len(enzymes)), enzymes, rotation=90)
    plt.yticks(range(len(enzymes)), enzymes)
    plt.xlabel("Enzyme 2")
    plt.ylabel("Enzyme 1")
    plt.title("radigest enzyme-pair screening")
    save_figure(out, manuscript_dir)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--manuscript-dir",
        type=Path,
        default=Path("manuscript_figures"),
    )
    parser.add_argument(
        "--no-manuscript-copy",
        action="store_true",
        help="Do not copy figure to manuscript_figures/.",
    )
    parser.add_argument(
        "--log10",
        action="store_true",
        help="Plot log10(metric_value); nonpositive values are shown as missing.",
    )
    args = parser.parse_args(argv)

    try:
        rows = read_matrix(args.matrix)
        enzymes, matrix, metric_name = build_matrix(rows, log10=args.log10)
        manuscript_dir = None if args.no_manuscript_copy else args.manuscript_dir

        make_heatmap(
            enzymes=enzymes,
            matrix=matrix,
            metric_name=metric_name,
            out=args.out,
            manuscript_dir=manuscript_dir,
            log10=args.log10,
        )

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
