#!/usr/bin/env python3
"""Summarize empirical depth validation against a radigest-design prediction."""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

DEPTH_THRESHOLDS = (1, 3, 5, 10)

SUMMARY_COLUMNS = [
    "library_id",
    "display_name",
    "enzyme_pair",
    "target_genome_pct",
    "predicted_weighted_genome_pct",
    "target_mean_locus_depth",
    "predicted_mean_locus_depth_at_budget",
    "modeled_read_pairs_per_sample",
    "weighted_fragments",
    "raw_loci_in_size_window",
    "observed_samples",
    "observed_loci",
    "mean_observed_read_pairs_at_loci",
    "median_observed_read_pairs_at_loci",
    "mean_observed_pairs_per_locus",
    "median_observed_pairs_per_locus",
    "min_observed_pairs_per_locus",
    "max_observed_pairs_per_locus",
    "mean_assigned_read_pair_fraction",
    "median_assigned_read_pair_fraction",
    "read_normalized_predicted_depth_mean_budget",
    "read_normalized_predicted_depth_median_budget",
    "observed_mean_over_normalized_prediction",
    "observed_median_over_normalized_prediction",
    "mean_sample_fraction_loci_ge_1x",
    "median_sample_fraction_loci_ge_1x",
    "mean_sample_fraction_loci_ge_3x",
    "median_sample_fraction_loci_ge_3x",
    "mean_sample_fraction_loci_ge_5x",
    "median_sample_fraction_loci_ge_5x",
    "mean_sample_fraction_loci_ge_10x",
    "median_sample_fraction_loci_ge_10x",
    "per_locus_mean_depth_mean",
    "per_locus_mean_depth_median",
    "per_locus_mean_depth_p25",
    "per_locus_mean_depth_p75",
    "per_locus_mean_depth_min",
    "per_locus_mean_depth_max",
    "per_locus_fraction_ge_1x",
    "per_locus_fraction_ge_3x",
    "per_locus_fraction_ge_5x",
    "per_locus_fraction_ge_10x",
    "depth_model_interpretation",
    "design_tsv",
    "per_sample_depth_tsv",
    "per_locus_depth_tsv",
]

MANUSCRIPT_COLUMNS = [
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


def parse_float(row: dict[str, str], names: list[str], label: str) -> float:
    for name in names:
        value = row.get(name, "")
        if value not in {"", "NA"}:
            return float(value)
    raise ValueError(f"missing numeric field for {label}: tried {', '.join(names)}")


def parse_optional_float(row: dict[str, str], names: list[str]) -> float | None:
    for name in names:
        value = row.get(name, "")
        if value not in {"", "NA"}:
            return float(value)
    return None


def parse_int(row: dict[str, str], names: list[str], label: str) -> int:
    for name in names:
        value = row.get(name, "")
        if value not in {"", "NA"}:
            return int(float(value))
    raise ValueError(f"missing integer field for {label}: tried {', '.join(names)}")


def fmt(value: float, digits: int = 6) -> str:
    return f"{value:.{digits}f}"


def fmt_count(value: float) -> str:
    return f"{value:.0f}"


def fmt_optional(value: float | None, digits: int = 6) -> str:
    return "NA" if value is None else fmt(value, digits)


def find_design_row(
    rows: list[dict[str, str]], *, enzyme_1: str, enzyme_2: str
) -> dict[str, str]:
    wanted = {enzyme_1, enzyme_2}
    for row in rows:
        observed = {row.get("enzyme_a", ""), row.get("enzyme_b", "")}
        if observed == wanted:
            return row
    raise ValueError(f"no design row found for {enzyme_1},{enzyme_2}")


def safe_ratio(numerator: float, denominator: float) -> str:
    if denominator == 0:
        return "NA"
    return fmt(numerator / denominator)


def finite_values(values: list[float | None]) -> list[float]:
    return [value for value in values if value is not None]


def mean_or_none(values: list[float]) -> float | None:
    return None if not values else statistics.mean(values)


def median_or_none(values: list[float]) -> float | None:
    return None if not values else statistics.median(values)


def percentile(sorted_values: list[float], q: float) -> float | None:
    if not sorted_values:
        return None
    if q <= 0:
        return sorted_values[0]
    if q >= 1:
        return sorted_values[-1]
    pos = q * (len(sorted_values) - 1)
    lower = int(pos)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = pos - lower
    return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction


def sample_threshold_summaries(depth_rows: list[dict[str, str]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for threshold in DEPTH_THRESHOLDS:
        values = finite_values(
            [
                parse_optional_float(row, [f"fraction_loci_ge_{threshold}x"])
                for row in depth_rows
            ]
        )
        out[f"mean_sample_fraction_loci_ge_{threshold}x"] = fmt_optional(
            mean_or_none(values)
        )
        out[f"median_sample_fraction_loci_ge_{threshold}x"] = fmt_optional(
            median_or_none(values)
        )
    return out


def per_locus_summaries(
    per_locus_depth: Path | None, observed_loci: int
) -> dict[str, str]:
    empty = {
        "per_locus_mean_depth_mean": "NA",
        "per_locus_mean_depth_median": "NA",
        "per_locus_mean_depth_p25": "NA",
        "per_locus_mean_depth_p75": "NA",
        "per_locus_mean_depth_min": "NA",
        "per_locus_mean_depth_max": "NA",
        **{
            f"per_locus_fraction_ge_{threshold}x": "NA"
            for threshold in DEPTH_THRESHOLDS
        },
        "per_locus_depth_tsv": "NA",
    }
    if per_locus_depth is None:
        return empty
    rows = read_tsv(per_locus_depth)
    if not rows:
        raise ValueError(f"{per_locus_depth}: no per-locus rows")
    if len(rows) != observed_loci:
        raise ValueError(
            f"{per_locus_depth}: per-locus row count {len(rows)} differs from observed_loci {observed_loci}"
        )
    values = sorted(
        parse_float(row, ["mean_pairs_per_sample"], "per-locus mean pairs per sample")
        for row in rows
    )
    out = {
        "per_locus_mean_depth_mean": fmt(statistics.mean(values)),
        "per_locus_mean_depth_median": fmt(statistics.median(values)),
        "per_locus_mean_depth_p25": fmt_optional(percentile(values, 0.25)),
        "per_locus_mean_depth_p75": fmt_optional(percentile(values, 0.75)),
        "per_locus_mean_depth_min": fmt(values[0]),
        "per_locus_mean_depth_max": fmt(values[-1]),
        "per_locus_depth_tsv": str(per_locus_depth),
    }
    n_loci = len(values)
    for threshold in DEPTH_THRESHOLDS:
        count = sum(1 for value in values if value >= threshold)
        out[f"per_locus_fraction_ge_{threshold}x"] = fmt(count / n_loci)
    return out


def build_summary_row(args: argparse.Namespace) -> dict[str, str]:
    design_rows = read_tsv(args.design_tsv)
    depth_rows = read_tsv(args.per_sample_depth)
    design = find_design_row(
        design_rows, enzyme_1=args.enzyme_1, enzyme_2=args.enzyme_2
    )
    if not depth_rows:
        raise ValueError(f"{args.per_sample_depth}: no sample rows")

    read_pairs = [
        parse_float(row, ["observed_read_pairs_at_loci", "read_pairs"], "read pairs")
        for row in depth_rows
    ]
    depths = [
        parse_float(row, ["mean_pairs_per_locus"], "mean pairs per locus")
        for row in depth_rows
    ]
    assigned_fractions = finite_values(
        [
            parse_optional_float(row, ["assigned_read_pair_fraction"])
            for row in depth_rows
        ]
    )
    loci_values = [parse_int(row, ["loci"], "loci") for row in depth_rows]
    observed_loci = loci_values[0]
    if any(value != observed_loci for value in loci_values):
        raise ValueError(f"{args.per_sample_depth}: loci count differs across samples")

    modeled_read_pairs = parse_float(
        design, ["read_pairs_per_sample"], "modeled read pairs per sample"
    )
    predicted_depth = parse_float(
        design,
        ["predicted_mean_locus_depth", "expected_mean_depth"],
        "predicted mean depth",
    )
    mean_read_pairs = statistics.mean(read_pairs)
    median_read_pairs = statistics.median(read_pairs)
    mean_depth = statistics.mean(depths)
    median_depth = statistics.median(depths)
    normalized_mean = predicted_depth * (mean_read_pairs / modeled_read_pairs)
    normalized_median = predicted_depth * (median_read_pairs / modeled_read_pairs)
    interpretation = (
        "Budget-level mean depth prediction with empirical diagnostics. Read-normalized "
        "values rescale the design prediction to observed read pairs assigned to predicted "
        "loci; per-sample threshold and per-locus distribution summaries quantify recovery "
        "heterogeneity. The model does not claim uniform sample allocation, locus-specific "
        "coverage prediction, PCR-duplicate behavior, or genotype-calling yield."
    )
    per_locus_path = args.per_locus_depth if args.per_locus_depth is not None else None

    return {
        "library_id": args.library_id,
        "display_name": args.display_name,
        "enzyme_pair": f"{args.enzyme_1}+{args.enzyme_2}",
        "target_genome_pct": fmt(
            parse_float(design, ["target_genome_pct"], "target genome pct")
        ),
        "predicted_weighted_genome_pct": fmt(
            parse_float(
                design,
                ["predicted_weighted_genome_pct", "generated_weighted_genome_pct"],
                "predicted weighted genome pct",
            )
        ),
        "target_mean_locus_depth": fmt(
            parse_float(
                design, ["target_mean_locus_depth", "desired_depth"], "target depth"
            )
        ),
        "predicted_mean_locus_depth_at_budget": fmt(predicted_depth),
        "modeled_read_pairs_per_sample": fmt(modeled_read_pairs),
        "weighted_fragments": fmt(
            parse_float(design, ["weighted_fragments"], "weighted fragments")
        ),
        "raw_loci_in_size_window": str(
            parse_int(design, ["raw_fragments_in_window"], "raw fragments in window")
        ),
        "observed_samples": str(len(depth_rows)),
        "observed_loci": str(observed_loci),
        "mean_observed_read_pairs_at_loci": fmt_count(mean_read_pairs),
        "median_observed_read_pairs_at_loci": fmt_count(median_read_pairs),
        "mean_observed_pairs_per_locus": fmt(mean_depth),
        "median_observed_pairs_per_locus": fmt(median_depth),
        "min_observed_pairs_per_locus": fmt(min(depths)),
        "max_observed_pairs_per_locus": fmt(max(depths)),
        "mean_assigned_read_pair_fraction": fmt_optional(
            mean_or_none(assigned_fractions)
        ),
        "median_assigned_read_pair_fraction": fmt_optional(
            median_or_none(assigned_fractions)
        ),
        "read_normalized_predicted_depth_mean_budget": fmt(normalized_mean),
        "read_normalized_predicted_depth_median_budget": fmt(normalized_median),
        "observed_mean_over_normalized_prediction": safe_ratio(
            mean_depth, normalized_mean
        ),
        "observed_median_over_normalized_prediction": safe_ratio(
            median_depth, normalized_median
        ),
        **sample_threshold_summaries(depth_rows),
        **per_locus_summaries(per_locus_path, observed_loci),
        "depth_model_interpretation": interpretation,
        "design_tsv": str(args.design_tsv),
        "per_sample_depth_tsv": str(args.per_sample_depth),
    }


def manuscript_row(row: dict[str, str]) -> dict[str, str]:
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
        "mean_on_target_read_pair_fraction": row["mean_assigned_read_pair_fraction"],
        "median_on_target_read_pair_fraction": row[
            "median_assigned_read_pair_fraction"
        ],
        "read_normalized_prediction_mean_budget": row[
            "read_normalized_predicted_depth_mean_budget"
        ],
        "read_normalized_prediction_median_budget": row[
            "read_normalized_predicted_depth_median_budget"
        ],
        "mean_observed_over_normalized_prediction": row[
            "observed_mean_over_normalized_prediction"
        ],
        "per_locus_median_depth": row["per_locus_mean_depth_median"],
        "per_locus_p25_depth": row["per_locus_mean_depth_p25"],
        "per_locus_p75_depth": row["per_locus_mean_depth_p75"],
        "fraction_predicted_loci_ge_1x": row["per_locus_fraction_ge_1x"],
        "fraction_predicted_loci_ge_3x": row["per_locus_fraction_ge_3x"],
        "fraction_predicted_loci_ge_5x": row["per_locus_fraction_ge_5x"],
        "fraction_predicted_loci_ge_10x": row["per_locus_fraction_ge_10x"],
        "mean_sample_fraction_loci_ge_1x": row["mean_sample_fraction_loci_ge_1x"],
        "mean_sample_fraction_loci_ge_3x": row["mean_sample_fraction_loci_ge_3x"],
        "mean_sample_fraction_loci_ge_5x": row["mean_sample_fraction_loci_ge_5x"],
        "mean_sample_fraction_loci_ge_10x": row["mean_sample_fraction_loci_ge_10x"],
        "interpretation": row["depth_model_interpretation"],
    }


def write_one_row(path: Path, row: dict[str, str], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, delimiter="\t", fieldnames=columns, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerow(row)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-id", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--enzyme-1", required=True)
    parser.add_argument("--enzyme-2", required=True)
    parser.add_argument("--design-tsv", type=Path, required=True)
    parser.add_argument("--per-sample-depth", type=Path, required=True)
    parser.add_argument("--per-locus-depth", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manuscript-out", type=Path)
    args = parser.parse_args(argv)

    try:
        row = build_summary_row(args)
        write_one_row(args.out, row, SUMMARY_COLUMNS)
        if args.manuscript_out is not None:
            write_one_row(args.manuscript_out, manuscript_row(row), MANUSCRIPT_COLUMNS)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
