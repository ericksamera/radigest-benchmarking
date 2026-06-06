#!/usr/bin/env python3
"""Fit a default empirical size-selection model grid."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MIN_SIZES = [100, 125, 150, 175, 200, 225]
DEFAULT_MAX_SIZES = [350, 400, 450, 500, 550, 600, 650, 700]
DEFAULT_EDGE_SDS = [25, 50, 75, 100, 125]
DEFAULT_BETAS = [
    0.0,
    0.0005,
    0.001,
    0.0015,
    0.002,
    0.0025,
    0.003,
    0.004,
    0.005,
    0.0075,
    0.01,
    0.0125,
    0.015,
]

GRID_COLUMNS = [
    "library_id",
    "display_name",
    "model",
    "model_family",
    "model_label",
    "model_params",
    "min_size",
    "max_size",
    "score_min",
    "score_max",
    "size_edge_sd",
    "length_bias_beta_per_bp",
    "length_bias_half_life_bp",
    "js_read",
    "pred_median",
    "obs_median",
    "pred_in_window_fraction",
    "obs_in_window_fraction",
    "selected",
]


@dataclass(frozen=True)
class LibraryConfig:
    library_id: str
    display_name: str
    score_min: int
    score_max: int


@dataclass(frozen=True)
class CandidateModel:
    model: str
    min_size: int
    max_size: int
    edge_sd: float | None = None
    beta: float = 0.0

    @property
    def center(self) -> float:
        return (self.min_size + self.max_size) / 2.0

    @property
    def half_width(self) -> float:
        return (self.max_size - self.min_size) / 2.0

    @property
    def model_family(self) -> str:
        labels = {
            "none": "Raw digest",
            "hard": "Hard window",
            "soft-window": "Soft window",
            "soft-window-short-bias": "Soft + short-bias",
        }
        return labels[self.model]

    @property
    def model_label(self) -> str:
        if self.model == "none":
            return "Raw digest"
        if self.model == "hard":
            return f"Hard {self.min_size}-{self.max_size} bp"
        if self.model == "soft-window":
            return (
                f"Soft-window {self.min_size}-{self.max_size} bp, edge {self.edge_sd:g}"
            )
        if self.model == "soft-window-short-bias":
            return (
                f"Soft-window {self.min_size}-{self.max_size} bp, "
                f"edge {self.edge_sd:g}, beta {self.beta:g}/bp"
            )
        raise ValueError(f"unknown model {self.model!r}")

    @property
    def model_params(self) -> str:
        if self.model == "none":
            return "weight=1"
        if self.model == "hard":
            return f"min={self.min_size};max={self.max_size}"
        if self.model == "soft-window":
            return f"min={self.min_size};max={self.max_size};edge_sd={self.edge_sd:g}"
        if self.model == "soft-window-short-bias":
            return (
                f"min={self.min_size};max={self.max_size};edge_sd={self.edge_sd:g};"
                f"length_bias_beta_per_bp={self.beta:g}"
            )
        raise ValueError(f"unknown model {self.model!r}")

    @property
    def half_life(self) -> str:
        if self.beta == 0:
            return "inf"
        return f"{math.log(2) / self.beta:.6g}"


def parse_int(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an integer, got {value!r}") from exc


def parse_float(value: str, label: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be numeric, got {value!r}") from exc


def parse_int_list(value: str) -> list[int]:
    values = [
        parse_int(part.strip(), "grid integer")
        for part in value.split(",")
        if part.strip()
    ]
    if not values:
        raise ValueError("integer grid cannot be empty")
    return values


def parse_float_list(value: str) -> list[float]:
    values = [
        parse_float(part.strip(), "grid value")
        for part in value.split(",")
        if part.strip()
    ]
    if not values:
        raise ValueError("numeric grid cannot be empty")
    return values


def read_manifest_row(path: Path, library_id: str) -> LibraryConfig:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        for row_number, row in enumerate(reader, start=2):
            clean = {key: (value or "").strip() for key, value in row.items() if key}
            if clean.get("library_id") != library_id:
                continue
            return LibraryConfig(
                library_id=library_id,
                display_name=clean.get("display_name") or library_id,
                score_min=parse_int(
                    clean["score_min"], f"{path}: row {row_number} score_min"
                ),
                score_max=parse_int(
                    clean["score_max"], f"{path}: row {row_number} score_max"
                ),
            )
    raise ValueError(f"{path}: library_id {library_id!r} not found")


def read_empirical_histogram(path: Path, library_id: str) -> Counter[int]:
    histogram: Counter[int] = Counter()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        required = {"library_id", "bam_id", "tlen", "count"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(sorted(missing))}")
        buffered_rows: list[dict[str, str]] = []
        saw_pooled = False
        for row in reader:
            clean = {key: (value or "").strip() for key, value in row.items() if key}
            if clean.get("library_id") != library_id:
                continue
            if clean.get("bam_id") == "pooled":
                saw_pooled = True
                histogram[parse_int(clean["tlen"], f"{path}: tlen")] += parse_int(
                    clean["count"], f"{path}: count"
                )
            else:
                buffered_rows.append(clean)
        if saw_pooled:
            return histogram
        for clean in buffered_rows:
            histogram[parse_int(clean["tlen"], f"{path}: tlen")] += parse_int(
                clean["count"], f"{path}: count"
            )
    return histogram


def read_prediction_histogram(
    path: Path, library_id: str, prediction_mode: str
) -> Counter[int]:
    histogram: Counter[int] = Counter()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        required = {"library_id", "prediction_mode", "length", "count"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(sorted(missing))}")
        for row in reader:
            clean = {key: (value or "").strip() for key, value in row.items() if key}
            if clean.get("library_id") != library_id:
                continue
            if clean.get("prediction_mode") != prediction_mode:
                continue
            histogram[parse_int(clean["length"], f"{path}: length")] += parse_int(
                clean["count"], f"{path}: count"
            )
    return histogram


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def soft_window_weight(length: int, model: CandidateModel) -> float:
    if model.edge_sd is None or model.edge_sd <= 0:
        raise ValueError("soft-window model requires edge_sd > 0")
    lower = sigmoid((length - model.min_size) / model.edge_sd)
    upper = sigmoid((model.max_size - length) / model.edge_sd)
    return lower * upper


def model_weight(length: int, model: CandidateModel) -> float:
    if model.model == "none":
        return 1.0
    if model.model == "hard":
        return 1.0 if model.min_size <= length <= model.max_size else 0.0
    if model.model == "soft-window":
        return soft_window_weight(length, model)
    if model.model == "soft-window-short-bias":
        return soft_window_weight(length, model) * math.exp(
            -model.beta * max(0, length - model.min_size)
        )
    raise ValueError(f"unknown model {model.model!r}")


def normalized(counts: dict[int, float], lengths: range) -> list[float]:
    values = [float(counts.get(length, 0.0)) for length in lengths]
    total = sum(values)
    if total <= 0:
        return [0.0 for _ in values]
    return [value / total for value in values]


def jensen_shannon_distance(p: list[float], q: list[float]) -> float:
    if len(p) != len(q):
        raise ValueError("p and q must have the same length")
    p_total = sum(p)
    q_total = sum(q)
    if p_total <= 0 or q_total <= 0:
        return float("nan")
    p = [value / p_total for value in p]
    q = [value / q_total for value in q]
    m = [(p_value + q_value) / 2.0 for p_value, q_value in zip(p, q)]

    def kl_div(a: list[float], b: list[float]) -> float:
        return sum(
            a_value * math.log2(a_value / b_value)
            for a_value, b_value in zip(a, b)
            if a_value > 0 and b_value > 0
        )

    return math.sqrt(0.5 * kl_div(p, m) + 0.5 * kl_div(q, m))


def weighted_median(lengths: range, density: list[float]) -> float:
    total = sum(density)
    if total <= 0:
        return float("nan")
    cumulative = 0.0
    for length, value in zip(lengths, density):
        cumulative += value / total
        if cumulative >= 0.5:
            return float(length)
    return float(lengths.stop - 1)


def in_window_fraction(
    lengths: range, density: list[float], model: CandidateModel
) -> float:
    total = sum(density)
    if total <= 0:
        return float("nan")
    return (
        sum(
            value
            for length, value in zip(lengths, density)
            if model.min_size <= length <= model.max_size
        )
        / total
    )


def candidate_models(
    *,
    min_sizes: list[int],
    max_sizes: list[int],
    edge_sds: list[float],
    betas: list[float],
) -> list[CandidateModel]:
    models = [
        CandidateModel(
            model="none",
            min_size=min(min_sizes),
            max_size=max(max_sizes),
        )
    ]
    for min_size in min_sizes:
        for max_size in max_sizes:
            if max_size <= min_size:
                continue
            models.append(
                CandidateModel(model="hard", min_size=min_size, max_size=max_size)
            )
            for edge_sd in edge_sds:
                models.append(
                    CandidateModel(
                        model="soft-window",
                        min_size=min_size,
                        max_size=max_size,
                        edge_sd=edge_sd,
                    )
                )
                for beta in betas:
                    models.append(
                        CandidateModel(
                            model="soft-window-short-bias",
                            min_size=min_size,
                            max_size=max_size,
                            edge_sd=edge_sd,
                            beta=beta,
                        )
                    )
    return models


def fit_grid(
    *,
    cfg: LibraryConfig,
    empirical: Counter[int],
    raw: Counter[int],
    min_sizes: list[int],
    max_sizes: list[int],
    edge_sds: list[float],
    betas: list[float],
) -> list[dict[str, str]]:
    if cfg.score_max <= cfg.score_min:
        raise ValueError("score_max must be greater than score_min")
    lengths = range(cfg.score_min, cfg.score_max + 1)
    empirical_density = normalized(
        {length: float(count) for length, count in empirical.items()}, lengths
    )
    if sum(empirical_density) <= 0:
        raise ValueError(
            "empirical histogram has no observations in score_min/score_max"
        )
    raw_counts = {length: float(count) for length, count in raw.items()}
    if sum(raw_counts.get(length, 0.0) for length in lengths) <= 0:
        raise ValueError(
            "raw prediction histogram has no observations in score_min/score_max"
        )
    obs_median = weighted_median(lengths, empirical_density)
    rows: list[dict[str, str]] = []
    best_index = -1
    best_js = float("inf")
    for index, model in enumerate(
        candidate_models(
            min_sizes=min_sizes,
            max_sizes=max_sizes,
            edge_sds=edge_sds,
            betas=betas,
        )
    ):
        weighted_counts = {
            length: raw_counts.get(length, 0.0) * model_weight(length, model)
            for length in lengths
        }
        pred_density = normalized(weighted_counts, lengths)
        js_read = jensen_shannon_distance(pred_density, empirical_density)
        if js_read < best_js:
            best_js = js_read
            best_index = index
        rows.append(
            {
                "library_id": cfg.library_id,
                "display_name": cfg.display_name,
                "model": model.model,
                "model_family": model.model_family,
                "model_label": model.model_label,
                "model_params": model.model_params,
                "min_size": str(model.min_size),
                "max_size": str(model.max_size),
                "score_min": str(cfg.score_min),
                "score_max": str(cfg.score_max),
                "size_edge_sd": "NA" if model.edge_sd is None else f"{model.edge_sd:g}",
                "length_bias_beta_per_bp": f"{model.beta:g}",
                "length_bias_half_life_bp": model.half_life,
                "js_read": f"{js_read:.12g}",
                "pred_median": f"{weighted_median(lengths, pred_density):.6g}",
                "obs_median": f"{obs_median:.6g}",
                "pred_in_window_fraction": f"{in_window_fraction(lengths, pred_density, model):.12g}",
                "obs_in_window_fraction": f"{in_window_fraction(lengths, empirical_density, model):.12g}",
                "selected": "false",
            }
        )
    if best_index < 0:
        raise ValueError("model grid produced no candidate models")
    rows[best_index]["selected"] = "true"
    return rows


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, delimiter="\t", fieldnames=GRID_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--library-id", required=True)
    parser.add_argument("--empirical-hist", type=Path, required=True)
    parser.add_argument("--raw-hist", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--best-out", type=Path, required=True)
    parser.add_argument(
        "--min-sizes",
        default=",".join(str(value) for value in DEFAULT_MIN_SIZES),
        help="Comma-separated lower-bound grid in bp.",
    )
    parser.add_argument(
        "--max-sizes",
        default=",".join(str(value) for value in DEFAULT_MAX_SIZES),
        help="Comma-separated upper-bound grid in bp.",
    )
    parser.add_argument(
        "--edge-sds",
        default=",".join(str(value) for value in DEFAULT_EDGE_SDS),
        help="Comma-separated soft-window edge-SD grid in bp.",
    )
    parser.add_argument(
        "--betas",
        default=",".join(str(value) for value in DEFAULT_BETAS),
        help="Comma-separated short-insert bias beta grid in per-bp units.",
    )
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        cfg = read_manifest_row(args.manifest, args.library_id)
        empirical = read_empirical_histogram(args.empirical_hist, args.library_id)
        raw = read_prediction_histogram(args.raw_hist, args.library_id, "raw")
        rows = fit_grid(
            cfg=cfg,
            empirical=empirical,
            raw=raw,
            min_sizes=parse_int_list(args.min_sizes),
            max_sizes=parse_int_list(args.max_sizes),
            edge_sds=parse_float_list(args.edge_sds),
            betas=parse_float_list(args.betas),
        )
        write_rows(args.out, rows)
        best_rows = [row for row in rows if row["selected"] == "true"]
        write_rows(args.best_out, best_rows)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
