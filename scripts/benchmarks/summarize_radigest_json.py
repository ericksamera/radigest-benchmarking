#!/usr/bin/env python3
"""Summarize radigest JSON files into a manuscript-friendly TSV."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HEADER = [
    "file",
    "dataset",
    "condition",
    "radigest_version",
    "enzymes",
    "min",
    "max",
    "score_min",
    "score_max",
    "size_model",
    "total_fragments",
    "total_bases",
    "raw_fragments_scored",
    "raw_bases_scored",
    "raw_fragments_in_window",
    "raw_bases_in_window",
    "weighted_fragments",
    "weighted_bases",
    "mean_weighted_length",
    "warnings",
]


def infer_dataset_condition(path: Path) -> tuple[str, str]:
    stem = path.stem
    parts = stem.split("__")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return "", stem


def fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ";".join(map(str, value))
    return str(value)


def summarize(path: Path) -> dict[str, str]:
    with path.open() as handle:
        doc = json.load(handle)

    params = doc.get("parameters", {})
    size = doc.get("size_selection", {})
    dataset, condition = infer_dataset_condition(path)

    row = {
        "file": str(path),
        "dataset": dataset,
        "condition": condition,
        "radigest_version": doc.get("radigest_version", ""),
        "enzymes": ",".join(doc.get("enzymes", [])),
        "min": doc.get("min_length", params.get("min_length", "")),
        "max": doc.get("max_length", params.get("max_length", "")),
        "score_min": params.get("score_min", size.get("score_min", "")),
        "score_max": params.get("score_max", size.get("score_max", "")),
        "size_model": params.get("size_model", size.get("model", "")),
        "total_fragments": doc.get("total_fragments", ""),
        "total_bases": doc.get("total_bases", ""),
        "raw_fragments_scored": size.get("raw_fragments_scored", ""),
        "raw_bases_scored": size.get("raw_bases_scored", ""),
        "raw_fragments_in_window": size.get("raw_fragments_in_window", ""),
        "raw_bases_in_window": size.get("raw_bases_in_window", ""),
        "weighted_fragments": size.get("weighted_fragments", ""),
        "weighted_bases": size.get("weighted_bases", ""),
        "mean_weighted_length": size.get("mean_weighted_length", ""),
        "warnings": ";".join(doc.get("warnings", [])),
    }
    return {key: fmt(value) for key, value in row.items()}


def main(argv: list[str]) -> int:
    print("\t".join(HEADER))

    for item in argv:
        path = Path(item)
        if not path.exists():
            print(f"warning: missing JSON file: {path}", file=sys.stderr)
            continue
        try:
            row = summarize(path)
        except Exception as exc:
            print(f"warning: failed to parse {path}: {exc}", file=sys.stderr)
            continue
        print("\t".join(row.get(col, "") for col in HEADER))

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
