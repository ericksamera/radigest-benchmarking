#!/usr/bin/env python3
"""Plot empirical TLEN recovery against radigest hard and weighted predictions.

The script is streaming-friendly for large TLEN files. It bins:
  - observed TLENs;
  - hard-window fragment weights from a radigest fragments TSV;
  - empirical recovery weights from a radigest fragments TSV.

Expected radigest TSV columns include:
  length
  hard_kept
  size_weight
"""

from __future__ import annotations

import argparse
import csv
import math
import shutil
import sys
from pathlib import Path

import matplotlib.pyplot as plt


def bin_index(value: float, bin_width: int, max_length: int) -> int | None:
    if value < 1:
        return None
    if value > max_length:
        return None
    return int(value // bin_width)


def empty_bins(max_length: int, bin_width: int) -> list[float]:
    return [0.0 for _ in range(max_length // bin_width + 1)]


def bin_centers(max_length: int, bin_width: int) -> list[float]:
    return [i * bin_width + bin_width / 2.0 for i in range(max_length // bin_width + 1)]


def normalize(values: list[float]) -> list[float]:
    total = sum(values)
    if total <= 0:
        return values
    return [value / total for value in values]


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "t", "yes", "y"}


def read_tlen_histogram(path: Path, max_length: int, bin_width: int) -> list[float]:
    bins = empty_bins(max_length, bin_width)

    with path.open() as handle:
        for line in handle:
            value = line.strip()
            if value == "":
                continue

            try:
                length = int(value)
            except ValueError:
                continue

            idx = bin_index(length, bin_width, max_length)
            if idx is not None:
                bins[idx] += 1.0

    return bins


def read_fragment_histogram(
    path: Path,
    max_length: int,
    bin_width: int,
    mode: str,
) -> list[float]:
    bins = empty_bins(max_length, bin_width)

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")

        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")

        if "length" not in reader.fieldnames:
            raise ValueError(f"{path}: missing required column 'length'")

        for row in reader:
            try:
                length = float(row["length"])
            except ValueError:
                continue

            idx = bin_index(length, bin_width, max_length)
            if idx is None:
                continue

            if mode == "hard":
                hard_kept = row.get("hard_kept", "")
                weight = 1.0 if parse_bool(hard_kept) else 0.0
            elif mode == "weighted":
                raw_weight = row.get("size_weight", "")
                try:
                    weight = float(raw_weight)
                except ValueError:
                    weight = 0.0
            else:
                raise ValueError(f"unsupported mode: {mode}")

            bins[idx] += weight

    return bins


def save_figure(path: Path, manuscript_dir: Path | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()

    if manuscript_dir is not None:
        manuscript_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, manuscript_dir / path.name)


def plot_distribution(
    centers: list[float],
    observed: list[float],
    hard: list[float],
    weighted: list[float],
    nominal_min: int,
    nominal_max: int,
    label: str,
    out: Path,
    manuscript_dir: Path | None,
) -> None:
    plt.figure(figsize=(7.5, 4.8))

    plt.plot(centers, observed, label="Observed TLEN")
    plt.plot(centers, hard, label="Hard-window prediction")
    plt.plot(centers, weighted, label="Empirical-weighted prediction")

    plt.axvline(nominal_min, linestyle="--", linewidth=1)
    plt.axvline(nominal_max, linestyle="--", linewidth=1)

    plt.xlabel("Insert or fragment length (bp)")
    plt.ylabel("Relative frequency / weight")
    plt.title(label)
    plt.legend()

    save_figure(out, manuscript_dir)


def plot_ratio(
    centers: list[float],
    observed: list[float],
    hard: list[float],
    weighted: list[float],
    out: Path,
    manuscript_dir: Path | None,
) -> None:
    ratio_weighted_to_hard: list[float] = []
    ratio_obs_to_hard: list[float] = []

    for obs, hrd, wgt in zip(observed, hard, weighted, strict=True):
        if hrd > 0:
            ratio_weighted_to_hard.append(wgt / hrd)
            ratio_obs_to_hard.append(obs / hrd)
        else:
            ratio_weighted_to_hard.append(math.nan)
            ratio_obs_to_hard.append(math.nan)

    plt.figure(figsize=(7.5, 4.8))
    plt.plot(centers, ratio_obs_to_hard, label="Observed / hard")
    plt.plot(centers, ratio_weighted_to_hard, label="Weighted / hard")

    plt.xlabel("Length (bp)")
    plt.ylabel("Ratio to hard-window prediction")
    plt.title("Recovery-weighted length enrichment")
    plt.legend()

    save_figure(out, manuscript_dir)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tlens", required=True, type=Path)
    parser.add_argument("--hard-fragments", required=True, type=Path)
    parser.add_argument("--weighted-fragments", required=True, type=Path)
    parser.add_argument("--nominal-min", required=True, type=int)
    parser.add_argument("--nominal-max", required=True, type=int)
    parser.add_argument("--max-length", type=int, default=1000)
    parser.add_argument("--bin-width", type=int, default=10)
    parser.add_argument(
        "--label",
        default="Empirical recovery",
        help="Dataset label used in figure titles.",
    )
    parser.add_argument(
        "--prefix",
        default="empirical_recovery",
        help="Output filename prefix.",
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
        centers = bin_centers(args.max_length, args.bin_width)

        observed = normalize(
            read_tlen_histogram(args.tlens, args.max_length, args.bin_width)
        )
        hard = normalize(
            read_fragment_histogram(
                args.hard_fragments,
                args.max_length,
                args.bin_width,
                mode="hard",
            )
        )
        weighted = normalize(
            read_fragment_histogram(
                args.weighted_fragments,
                args.max_length,
                args.bin_width,
                mode="weighted",
            )
        )

        manuscript_dir = None if args.no_manuscript_copy else args.manuscript_dir

        plot_distribution(
            centers=centers,
            observed=observed,
            hard=hard,
            weighted=weighted,
            nominal_min=args.nominal_min,
            nominal_max=args.nominal_max,
            label=args.label,
            out=args.out_dir / f"{args.prefix}_distribution.png",
            manuscript_dir=manuscript_dir,
        )

        plot_ratio(
            centers=centers,
            observed=observed,
            hard=hard,
            weighted=weighted,
            out=args.out_dir / f"{args.prefix}_ratio.png",
            manuscript_dir=manuscript_dir,
        )

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
