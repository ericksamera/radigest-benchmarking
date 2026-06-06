#!/usr/bin/env python3
"""Build empirical size-selection model curves from TLEN and radigest histograms."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

CURVE_COLUMNS = [
    "library_id",
    "display_name",
    "model",
    "model_label",
    "model_params",
    "length",
    "empirical_count",
    "empirical_density",
    "pred_raw_count",
    "pred_raw_density",
    "pred_hard_count",
    "pred_hard_density",
    "weight",
    "pred_weighted_count",
    "pred_weighted_density",
    "min_size",
    "max_size",
    "score_min",
    "score_max",
    "size_edge_sd",
    "in_size_window",
    "in_score_window",
]

VALID_MODELS = ["none", "hard", "soft-window", "normal", "triangular"]


@dataclass(frozen=True)
class LibraryConfig:
    library_id: str
    display_name: str
    min_size: int
    max_size: int
    score_min: int
    score_max: int
    size_edge_sd: float

    @property
    def center(self) -> float:
        return (self.min_size + self.max_size) / 2.0

    @property
    def half_width(self) -> float:
        return (self.max_size - self.min_size) / 2.0


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


def read_manifest_row(path: Path, library_id: str) -> LibraryConfig:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        for row_number, row in enumerate(reader, start=2):
            row = {key: (value or "").strip() for key, value in row.items() if key}
            if row.get("library_id") != library_id:
                continue
            min_size = parse_int(row["min_size"], f"{path}: row {row_number} min_size")
            max_size = parse_int(row["max_size"], f"{path}: row {row_number} max_size")
            score_min = parse_int(
                row["score_min"], f"{path}: row {row_number} score_min"
            )
            score_max = parse_int(
                row["score_max"], f"{path}: row {row_number} score_max"
            )
            size_edge_sd = parse_float(
                row["size_edge_sd"], f"{path}: row {row_number} size_edge_sd"
            )
            if max_size <= min_size:
                raise ValueError(f"{path}: row {row_number}: max_size <= min_size")
            if score_max <= score_min:
                raise ValueError(f"{path}: row {row_number}: score_max <= score_min")
            if size_edge_sd <= 0:
                raise ValueError(f"{path}: row {row_number}: size_edge_sd must be > 0")
            return LibraryConfig(
                library_id=library_id,
                display_name=row.get("display_name") or library_id,
                min_size=min_size,
                max_size=max_size,
                score_min=score_min,
                score_max=score_max,
                size_edge_sd=size_edge_sd,
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
        saw_pooled = False
        buffered_rows: list[dict[str, str]] = []
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
        # Fall back to summing all rows if the histogram has not yet been pooled.
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


def model_weight(model: str, length: int, cfg: LibraryConfig) -> float:
    if model == "none":
        return 1.0
    if model == "hard":
        return 1.0 if cfg.min_size <= length <= cfg.max_size else 0.0
    if model == "soft-window":
        lower = sigmoid((length - cfg.min_size) / cfg.size_edge_sd)
        upper = sigmoid((cfg.max_size - length) / cfg.size_edge_sd)
        return lower * upper
    if model == "normal":
        z = (length - cfg.center) / cfg.size_edge_sd
        return math.exp(-0.5 * z * z)
    if model == "triangular":
        if cfg.half_width <= 0:
            return 0.0
        return max(0.0, 1.0 - abs(length - cfg.center) / cfg.half_width)
    raise ValueError(f"unknown model {model!r}")


def model_label(model: str, cfg: LibraryConfig) -> str:
    labels = {
        "none": "No size selection",
        "hard": f"Hard {cfg.min_size}-{cfg.max_size} bp",
        "soft-window": f"Soft-window {cfg.min_size}-{cfg.max_size} bp, edge {cfg.size_edge_sd:g}",
        "normal": f"Normal mean {cfg.center:g}, SD {cfg.size_edge_sd:g}",
        "triangular": f"Triangular peak {cfg.center:g}",
    }
    return labels[model]


def model_params(model: str, cfg: LibraryConfig) -> str:
    if model == "none":
        return "weight=1"
    if model == "hard":
        return f"min={cfg.min_size};max={cfg.max_size}"
    if model == "soft-window":
        return f"min={cfg.min_size};max={cfg.max_size};edge_sd={cfg.size_edge_sd:g}"
    if model == "normal":
        return f"mean={cfg.center:g};sd={cfg.size_edge_sd:g}"
    if model == "triangular":
        return f"min={cfg.min_size};max={cfg.max_size};peak={cfg.center:g}"
    raise ValueError(f"unknown model {model!r}")


def write_curves(
    *,
    output: Path,
    cfg: LibraryConfig,
    empirical: Counter[int],
    raw: Counter[int],
    hard: Counter[int],
) -> None:
    empirical_total = sum(empirical.values())
    raw_total = sum(raw.values())
    hard_total = sum(hard.values())
    if empirical_total == 0:
        raise ValueError("empirical histogram is empty")
    if raw_total == 0:
        raise ValueError("raw prediction histogram is empty")

    min_length = min([*empirical.keys(), *raw.keys(), *hard.keys(), cfg.score_min])
    max_length = max([*empirical.keys(), *raw.keys(), *hard.keys(), cfg.score_max])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, delimiter="\t", fieldnames=CURVE_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        for model in VALID_MODELS:
            weighted_counts = {
                length: raw.get(length, 0) * model_weight(model, length, cfg)
                for length in range(min_length, max_length + 1)
            }
            weighted_total = sum(weighted_counts.values())
            for length in range(min_length, max_length + 1):
                empirical_count = empirical.get(length, 0)
                raw_count = raw.get(length, 0)
                hard_count = hard.get(length, 0)
                weight = model_weight(model, length, cfg)
                weighted_count = weighted_counts[length]
                writer.writerow(
                    {
                        "library_id": cfg.library_id,
                        "display_name": cfg.display_name,
                        "model": model,
                        "model_label": model_label(model, cfg),
                        "model_params": model_params(model, cfg),
                        "length": length,
                        "empirical_count": empirical_count,
                        "empirical_density": empirical_count / empirical_total,
                        "pred_raw_count": raw_count,
                        "pred_raw_density": raw_count / raw_total,
                        "pred_hard_count": hard_count,
                        "pred_hard_density": (
                            0.0 if hard_total == 0 else hard_count / hard_total
                        ),
                        "weight": weight,
                        "pred_weighted_count": f"{weighted_count:.12g}",
                        "pred_weighted_density": (
                            0.0
                            if weighted_total == 0
                            else weighted_count / weighted_total
                        ),
                        "min_size": cfg.min_size,
                        "max_size": cfg.max_size,
                        "score_min": cfg.score_min,
                        "score_max": cfg.score_max,
                        "size_edge_sd": f"{cfg.size_edge_sd:g}",
                        "in_size_window": str(
                            cfg.min_size <= length <= cfg.max_size
                        ).lower(),
                        "in_score_window": str(
                            cfg.score_min <= length <= cfg.score_max
                        ).lower(),
                    }
                )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--library-id", required=True)
    parser.add_argument("--empirical-hist", type=Path, required=True)
    parser.add_argument("--raw-hist", type=Path, required=True)
    parser.add_argument("--hard-hist", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        cfg = read_manifest_row(args.manifest, args.library_id)
        empirical = read_empirical_histogram(args.empirical_hist, args.library_id)
        raw = read_prediction_histogram(args.raw_hist, args.library_id, "raw")
        hard = read_prediction_histogram(args.hard_hist, args.library_id, "hard")
        write_curves(output=args.out, cfg=cfg, empirical=empirical, raw=raw, hard=hard)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
