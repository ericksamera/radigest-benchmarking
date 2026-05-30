#!/usr/bin/env python3
"""Compare radigest benchmark results for gzipped vs plain FASTA inputs."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

FIELDNAMES = [
    "condition",
    "output_mode",
    "gzip_dataset",
    "plain_dataset",
    "gzip_n_runs",
    "plain_n_runs",
    "gzip_median_elapsed_wall_seconds",
    "plain_median_elapsed_wall_seconds",
    "elapsed_delta_plain_minus_gzip",
    "elapsed_ratio_gzip_over_plain",
    "gzip_median_max_rss_kb",
    "plain_median_max_rss_kb",
    "rss_delta_plain_minus_gzip",
    "gzip_median_fragments",
    "plain_median_fragments",
    "gzip_median_bases",
    "plain_median_bases",
    "fragments_match",
    "bases_match",
    "notes",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing benchmark summary: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        rows: list[dict[str, str]] = []
        for raw_row in reader:
            row = {
                key: "" if value is None else value
                for key, value in raw_row.items()
                if key is not None
            }
            rows.append(row)

    return rows


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


def fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"


def same_numeric(left: str, right: str) -> str:
    a = to_float(left)
    b = to_float(right)
    if a is None or b is None:
        return ""
    return "true" if abs(a - b) < 1e-9 else "false"


def build_comparison(
    rows: list[dict[str, str]],
    gzip_dataset: str,
    plain_dataset: str,
) -> list[dict[str, str]]:
    by_key: dict[tuple[str, str, str], dict[str, str]] = {}

    for row in rows:
        key = (
            row.get("dataset", ""),
            row.get("condition", ""),
            row.get("output_mode", ""),
        )
        by_key[key] = row

    conditions = sorted({row.get("condition", "") for row in rows if row.get("condition", "")})
    modes = sorted({row.get("output_mode", "") for row in rows if row.get("output_mode", "")})

    out: list[dict[str, str]] = []

    for condition in conditions:
        for mode in modes:
            gzip_row = by_key.get((gzip_dataset, condition, mode))
            plain_row = by_key.get((plain_dataset, condition, mode))

            if gzip_row is None and plain_row is None:
                continue

            notes: list[str] = []
            if gzip_row is None:
                notes.append("missing gzip dataset row")
            if plain_row is None:
                notes.append("missing plain dataset row")

            gzip_elapsed = to_float(
                None if gzip_row is None else gzip_row.get("median_elapsed_wall_seconds", "")
            )
            plain_elapsed = to_float(
                None if plain_row is None else plain_row.get("median_elapsed_wall_seconds", "")
            )

            gzip_rss = to_float(None if gzip_row is None else gzip_row.get("median_max_rss_kb", ""))
            plain_rss = to_float(None if plain_row is None else plain_row.get("median_max_rss_kb", ""))

            elapsed_delta = None
            elapsed_ratio = None
            if gzip_elapsed is not None and plain_elapsed is not None:
                elapsed_delta = plain_elapsed - gzip_elapsed
                if plain_elapsed != 0:
                    elapsed_ratio = gzip_elapsed / plain_elapsed

            rss_delta = None
            if gzip_rss is not None and plain_rss is not None:
                rss_delta = plain_rss - gzip_rss

            gzip_fragments = "" if gzip_row is None else gzip_row.get("median_total_fragments", "")
            plain_fragments = "" if plain_row is None else plain_row.get("median_total_fragments", "")
            gzip_bases = "" if gzip_row is None else gzip_row.get("median_total_bases", "")
            plain_bases = "" if plain_row is None else plain_row.get("median_total_bases", "")

            out.append(
                {
                    "condition": condition,
                    "output_mode": mode,
                    "gzip_dataset": gzip_dataset,
                    "plain_dataset": plain_dataset,
                    "gzip_n_runs": "" if gzip_row is None else gzip_row.get("n_runs", ""),
                    "plain_n_runs": "" if plain_row is None else plain_row.get("n_runs", ""),
                    "gzip_median_elapsed_wall_seconds": fmt(gzip_elapsed),
                    "plain_median_elapsed_wall_seconds": fmt(plain_elapsed),
                    "elapsed_delta_plain_minus_gzip": fmt(elapsed_delta),
                    "elapsed_ratio_gzip_over_plain": fmt(elapsed_ratio),
                    "gzip_median_max_rss_kb": fmt(gzip_rss),
                    "plain_median_max_rss_kb": fmt(plain_rss),
                    "rss_delta_plain_minus_gzip": fmt(rss_delta),
                    "gzip_median_fragments": gzip_fragments,
                    "plain_median_fragments": plain_fragments,
                    "gzip_median_bases": gzip_bases,
                    "plain_median_bases": plain_bases,
                    "fragments_match": same_numeric(gzip_fragments, plain_fragments),
                    "bases_match": same_numeric(gzip_bases, plain_bases),
                    "notes": "; ".join(notes),
                }
            )

    return out


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/tables/radigest_benchmark_summary.tsv"),
    )
    parser.add_argument("--gzip-dataset", default="yeast_small")
    parser.add_argument("--plain-dataset", default="yeast_small_plain")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("results/tables/radigest_input_format_comparison.tsv"),
    )
    args = parser.parse_args(argv)

    try:
        rows = read_rows(args.summary)
        comparison = build_comparison(
            rows=rows,
            gzip_dataset=args.gzip_dataset,
            plain_dataset=args.plain_dataset,
        )
        write_rows(args.out, comparison)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
