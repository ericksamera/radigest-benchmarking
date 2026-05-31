#!/usr/bin/env python3
"""Summarize empirical insert-length recovery modelling.

This script summarizes:
  - observed TLEN distribution;
  - best model from radigest-fit-size-model;
  - hard-window radigest JSON;
  - empirical-weighted radigest JSON.

It intentionally reads weighted metrics from JSON size_selection fields, not
top-level total_fragments/total_bases, because the top-level values are the
hard-kept fragment totals.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path


FIELDS = [
    "dataset",
    "species",
    "enzyme_pair",
    "nominal_min",
    "nominal_max",
    "score_min",
    "score_max",
    "observed_pairs",
    "observed_tlen_min",
    "observed_tlen_q01",
    "observed_tlen_q05",
    "observed_tlen_q25",
    "observed_tlen_median",
    "observed_tlen_q75",
    "observed_tlen_q95",
    "observed_tlen_q99",
    "observed_tlen_max",
    "observed_tlen_mean",
    "observed_fraction_below_min",
    "observed_fraction_in_window",
    "observed_fraction_above_max",
    "best_model",
    "best_model_params",
    "best_model_delta_aic",
    "best_model_kl",
    "best_model_obs_mean",
    "best_model_pred_mean",
    "best_model_obs_pairs",
    "best_model_pred_weight_sum",
    "hard_model",
    "hard_raw_fragments_scored",
    "hard_raw_bases_scored",
    "hard_raw_fragments_in_window",
    "hard_raw_bases_in_window",
    "hard_weighted_fragments",
    "hard_weighted_bases",
    "hard_mean_weighted_length",
    "weighted_model",
    "weighted_raw_fragments_scored",
    "weighted_raw_bases_scored",
    "weighted_raw_fragments_in_window",
    "weighted_raw_bases_in_window",
    "weighted_fragments",
    "weighted_bases",
    "weighted_mean_weighted_length",
    "weighted_minus_hard_fragments",
    "weighted_minus_hard_bases",
    "weighted_fragment_ratio_vs_hard",
    "weighted_base_ratio_vs_hard",
    "sample_count",
    "sample_pairs_min",
    "sample_pairs_median",
    "sample_pairs_max",
    "sample_mean_tlen_min",
    "sample_mean_tlen_median",
    "sample_mean_tlen_max",
    "tlens",
    "fit_table",
    "hard_json",
    "weighted_json",
    "sample_summary",
    "notes",
]


def to_float(value: str | int | float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).strip()
    if value == "":
        return None

    try:
        return float(value)
    except ValueError:
        return None


def fmt(value: float | None, digits: int = 6) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}"


def read_tlen_stats(
    path: Path,
    nominal_min: int,
    nominal_max: int,
) -> dict[str, str]:
    counts: Counter[int] = Counter()
    total = 0
    total_sum = 0
    below = 0
    inside = 0
    above = 0
    min_tlen: int | None = None
    max_tlen: int | None = None

    with path.open() as handle:
        for raw in handle:
            raw = raw.strip()
            if raw == "":
                continue

            value = int(raw)
            counts[value] += 1
            total += 1
            total_sum += value

            if min_tlen is None or value < min_tlen:
                min_tlen = value
            if max_tlen is None or value > max_tlen:
                max_tlen = value

            if value < nominal_min:
                below += 1
            elif value <= nominal_max:
                inside += 1
            else:
                above += 1

    if total == 0:
        raise ValueError(f"no TLEN values found in {path}")

    def q(prob: float) -> int:
        target = int(round((total - 1) * prob)) + 1
        seen = 0
        for length in sorted(counts):
            seen += counts[length]
            if seen >= target:
                return length
        return max_tlen if max_tlen is not None else 0

    return {
        "observed_pairs": str(total),
        "observed_tlen_min": str(min_tlen),
        "observed_tlen_q01": str(q(0.01)),
        "observed_tlen_q05": str(q(0.05)),
        "observed_tlen_q25": str(q(0.25)),
        "observed_tlen_median": str(q(0.50)),
        "observed_tlen_q75": str(q(0.75)),
        "observed_tlen_q95": str(q(0.95)),
        "observed_tlen_q99": str(q(0.99)),
        "observed_tlen_max": str(max_tlen),
        "observed_tlen_mean": fmt(total_sum / total, 3),
        "observed_fraction_below_min": fmt(below / total),
        "observed_fraction_in_window": fmt(inside / total),
        "observed_fraction_above_max": fmt(above / total),
    }


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            return []
        return [
            {
                key: "" if value is None else value
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]


def read_best_fit(path: Path) -> dict[str, str]:
    rows = read_tsv(path)
    if not rows:
        raise ValueError(f"empty fit table: {path}")

    best = rows[0]

    return {
        "best_model": best.get("model", ""),
        "best_model_params": best.get("params", ""),
        "best_model_delta_aic": best.get("delta_aic", ""),
        "best_model_kl": best.get("kl", ""),
        "best_model_obs_mean": best.get("obs_mean", ""),
        "best_model_pred_mean": best.get("pred_mean", ""),
        "best_model_obs_pairs": best.get("obs_pairs", ""),
        "best_model_pred_weight_sum": best.get("pred_weight_sum", ""),
    }


def read_size_selection_json(path: Path, prefix: str) -> dict[str, str]:
    with path.open() as handle:
        obj = json.load(handle)

    ss = obj.get("size_selection", {})

    def get(key: str) -> str:
        value = ss.get(key, "")
        if isinstance(value, float):
            return f"{value:.6f}"
        return str(value)

    return {
        f"{prefix}_model": get("model"),
        f"{prefix}_raw_fragments_scored": get("raw_fragments_scored"),
        f"{prefix}_raw_bases_scored": get("raw_bases_scored"),
        f"{prefix}_raw_fragments_in_window": get("raw_fragments_in_window"),
        f"{prefix}_raw_bases_in_window": get("raw_bases_in_window"),
        f"{prefix}_weighted_fragments": get("weighted_fragments"),
        f"{prefix}_weighted_bases": get("weighted_bases"),
        f"{prefix}_mean_weighted_length": get("mean_weighted_length"),
    }


def read_sample_summary(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {
            "sample_count": "",
            "sample_pairs_min": "",
            "sample_pairs_median": "",
            "sample_pairs_max": "",
            "sample_mean_tlen_min": "",
            "sample_mean_tlen_median": "",
            "sample_mean_tlen_max": "",
        }

    rows = read_tsv(path)
    pairs: list[float] = []
    means: list[float] = []

    for row in rows:
        pair_value = to_float(row.get("pairs"))
        mean_value = to_float(row.get("mean_tlen"))
        if pair_value is not None:
            pairs.append(pair_value)
        if mean_value is not None:
            means.append(mean_value)

    def summarize(values: list[float]) -> tuple[str, str, str]:
        if not values:
            return "", "", ""
        values = sorted(values)
        return (
            fmt(values[0], 3),
            fmt(float(statistics.median(values)), 3),
            fmt(values[-1], 3),
        )

    pairs_min, pairs_median, pairs_max = summarize(pairs)
    mean_min, mean_median, mean_max = summarize(means)

    return {
        "sample_count": str(len(rows)),
        "sample_pairs_min": pairs_min,
        "sample_pairs_median": pairs_median,
        "sample_pairs_max": pairs_max,
        "sample_mean_tlen_min": mean_min,
        "sample_mean_tlen_median": mean_median,
        "sample_mean_tlen_max": mean_max,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--species", default="")
    parser.add_argument("--enzyme-pair", required=True)
    parser.add_argument("--nominal-min", type=int, required=True)
    parser.add_argument("--nominal-max", type=int, required=True)
    parser.add_argument("--score-min", type=int, required=True)
    parser.add_argument("--score-max", type=int, required=True)
    parser.add_argument("--tlens", required=True, type=Path)
    parser.add_argument("--fit-table", required=True, type=Path)
    parser.add_argument("--hard-json", required=True, type=Path)
    parser.add_argument("--weighted-json", required=True, type=Path)
    parser.add_argument("--sample-summary", type=Path, default=None)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        row: dict[str, str] = {
            "dataset": args.dataset,
            "species": args.species,
            "enzyme_pair": args.enzyme_pair,
            "nominal_min": str(args.nominal_min),
            "nominal_max": str(args.nominal_max),
            "score_min": str(args.score_min),
            "score_max": str(args.score_max),
        }

        row.update(read_tlen_stats(args.tlens, args.nominal_min, args.nominal_max))
        row.update(read_best_fit(args.fit_table))
        row.update(read_size_selection_json(args.hard_json, "hard"))
        row.update(read_size_selection_json(args.weighted_json, "weighted"))
        row.update(read_sample_summary(args.sample_summary))

        hard_frag = to_float(row.get("hard_weighted_fragments"))
        hard_bases = to_float(row.get("hard_weighted_bases"))
        weighted_frag = to_float(row.get("weighted_weighted_fragments"))
        weighted_bases = to_float(row.get("weighted_weighted_bases"))

        row["weighted_fragments"] = row.pop("weighted_weighted_fragments", "")
        row["weighted_bases"] = row.pop("weighted_weighted_bases", "")
        row["weighted_mean_weighted_length"] = row.pop(
            "weighted_mean_weighted_length",
            "",
        )

        if hard_frag is not None and weighted_frag is not None:
            row["weighted_minus_hard_fragments"] = fmt(weighted_frag - hard_frag)
            row["weighted_fragment_ratio_vs_hard"] = fmt(weighted_frag / hard_frag)
        else:
            row["weighted_minus_hard_fragments"] = ""
            row["weighted_fragment_ratio_vs_hard"] = ""

        if hard_bases is not None and weighted_bases is not None:
            row["weighted_minus_hard_bases"] = fmt(weighted_bases - hard_bases)
            row["weighted_base_ratio_vs_hard"] = fmt(weighted_bases / hard_bases)
        else:
            row["weighted_minus_hard_bases"] = ""
            row["weighted_base_ratio_vs_hard"] = ""

        row["tlens"] = str(args.tlens)
        row["fit_table"] = str(args.fit_table)
        row["hard_json"] = str(args.hard_json)
        row["weighted_json"] = str(args.weighted_json)
        row["sample_summary"] = "" if args.sample_summary is None else str(
            args.sample_summary
        )
        row["notes"] = (
            "Empirical recovery model fit to pooled positive TLENs. "
            "This reflects size selection, short-fragment representation, PCR, "
            "sequencing, mapping, and filtering effects; it is not a pure "
            "wet-lab size-selection probability."
        )

        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=FIELDS)
            writer.writeheader()
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
