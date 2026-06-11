#!/usr/bin/env python3
"""Build the manuscript empirical depth-validation table."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

TABLE_COLUMNS = [
    "library",
    "enzyme_pair",
    "target_genome_pct",
    "predicted_genome_pct",
    "target_depth",
    "predicted_depth_at_modeled_budget",
    "modeled_read_pairs_per_sample",
    "observed_samples",
    "observed_loci",
    "mean_observed_read_pairs_at_loci",
    "median_observed_read_pairs_at_loci",
    "mean_observed_depth",
    "median_observed_depth",
    "mean_on_target_read_pair_fraction",
    "median_on_target_read_pair_fraction",
    "read_normalized_prediction_mean_budget",
    "read_normalized_prediction_median_budget",
    "mean_observed_over_normalized_prediction",
    "per_locus_median_depth",
    "per_locus_p25_depth",
    "per_locus_p75_depth",
    "fraction_predicted_loci_ge_1x",
    "fraction_predicted_loci_ge_3x",
    "fraction_predicted_loci_ge_5x",
    "fraction_predicted_loci_ge_10x",
    "mean_sample_fraction_loci_ge_1x",
    "mean_sample_fraction_loci_ge_3x",
    "mean_sample_fraction_loci_ge_5x",
    "mean_sample_fraction_loci_ge_10x",
    "interpretation",
]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return [
            {key: (value or "").strip() for key, value in row.items() if key}
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]


def value(row: dict[str, str], key: str) -> str:
    return row.get(key, "NA")


def to_table_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "library": row["display_name"],
        "enzyme_pair": row["enzyme_pair"],
        "target_genome_pct": row["target_genome_pct"],
        "predicted_genome_pct": row["predicted_weighted_genome_pct"],
        "target_depth": row["target_mean_locus_depth"],
        "predicted_depth_at_modeled_budget": row[
            "predicted_mean_locus_depth_at_budget"
        ],
        "modeled_read_pairs_per_sample": row["modeled_read_pairs_per_sample"],
        "observed_samples": row["observed_samples"],
        "observed_loci": row["observed_loci"],
        "mean_observed_read_pairs_at_loci": row["mean_observed_read_pairs_at_loci"],
        "median_observed_read_pairs_at_loci": row["median_observed_read_pairs_at_loci"],
        "mean_observed_depth": row["mean_observed_pairs_per_locus"],
        "median_observed_depth": row["median_observed_pairs_per_locus"],
        "mean_on_target_read_pair_fraction": value(
            row, "mean_assigned_read_pair_fraction"
        ),
        "median_on_target_read_pair_fraction": value(
            row, "median_assigned_read_pair_fraction"
        ),
        "read_normalized_prediction_mean_budget": row[
            "read_normalized_predicted_depth_mean_budget"
        ],
        "read_normalized_prediction_median_budget": row[
            "read_normalized_predicted_depth_median_budget"
        ],
        "mean_observed_over_normalized_prediction": row[
            "observed_mean_over_normalized_prediction"
        ],
        "per_locus_median_depth": value(row, "per_locus_mean_depth_median"),
        "per_locus_p25_depth": value(row, "per_locus_mean_depth_p25"),
        "per_locus_p75_depth": value(row, "per_locus_mean_depth_p75"),
        "fraction_predicted_loci_ge_1x": value(row, "per_locus_fraction_ge_1x"),
        "fraction_predicted_loci_ge_3x": value(row, "per_locus_fraction_ge_3x"),
        "fraction_predicted_loci_ge_5x": value(row, "per_locus_fraction_ge_5x"),
        "fraction_predicted_loci_ge_10x": value(row, "per_locus_fraction_ge_10x"),
        "mean_sample_fraction_loci_ge_1x": value(
            row, "mean_sample_fraction_loci_ge_1x"
        ),
        "mean_sample_fraction_loci_ge_3x": value(
            row, "mean_sample_fraction_loci_ge_3x"
        ),
        "mean_sample_fraction_loci_ge_5x": value(
            row, "mean_sample_fraction_loci_ge_5x"
        ),
        "mean_sample_fraction_loci_ge_10x": value(
            row, "mean_sample_fraction_loci_ge_10x"
        ),
        "interpretation": row["depth_model_interpretation"],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summaries", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        rows: list[dict[str, str]] = []
        for path in args.summaries:
            rows.extend(to_table_row(row) for row in read_tsv(path))
        if not rows:
            raise ValueError("no empirical depth-validation summary rows")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle, delimiter="\t", fieldnames=TABLE_COLUMNS, lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
