#!/usr/bin/env python3
"""Summarize radigest enzyme-pair screening output.

Input:
  results/tables/ranked_pairs.tsv

Outputs:
  - top pair table;
  - pairwise matrix table for heatmaps;
  - QC/summary table.

The script is deliberately tolerant of minor column-name differences in
radigest-rank-pairs output.
"""

from __future__ import annotations

import argparse
import csv
import glob
import math
import re
import sys
from pathlib import Path

PAIR1_COLUMNS = [
    "enzyme1",
    "enzyme_1",
    "enzyme_a",
    "enzyme_A",
    "enzymeA",
    "left_enzyme",
    "enzyme_left",
]

PAIR2_COLUMNS = [
    "enzyme2",
    "enzyme_2",
    "enzyme_b",
    "enzyme_B",
    "enzymeB",
    "right_enzyme",
    "enzyme_right",
]

PAIR_COLUMNS = [
    "pair",
    "enzyme_pair",
    "enzymes",
    "enzyme_pair_label",
]

OBJECTIVE_COLUMNS = {
    "weighted-bases": [
        "weighted_bases",
        "weighted-bases",
        "weightedBases",
    ],
    "weighted-fragments": [
        "weighted_fragments",
        "weighted-fragments",
        "weightedFragments",
    ],
    "raw-bases": [
        "raw_bases_in_window",
        "raw-bases-in-window",
        "rawBasesInWindow",
        "total_bases",
    ],
    "raw-fragments": [
        "raw_fragments_in_window",
        "raw-fragments-in-window",
        "rawFragmentsInWindow",
        "total_fragments",
    ],
    "weighted-genome-pct": [
        "weighted_genome_pct",
        "weighted-genome-pct",
        "weighted_genome_percent",
    ],
    "closest-target": [
        "distance_to_target",
        "abs_distance_to_target",
        "target_distance",
    ],
}

TOP_COLUMNS = [
    "rank",
    "enzyme1",
    "enzyme2",
    "metric_name",
    "metric_value",
    "weighted_bases",
    "weighted_fragments",
    "raw_bases_in_window",
    "raw_fragments_in_window",
    "mean_weighted_length",
    "weighted_genome_pct",
    "source_ranked_tsv",
]

MATRIX_COLUMNS = [
    "enzyme1",
    "enzyme2",
    "metric_name",
    "metric_value",
]

SUMMARY_COLUMNS = [
    "ranked_tsv",
    "objective",
    "metric_column",
    "ranked_rows",
    "candidate_enzymes",
    "expected_unique_pairs",
    "json_files",
    "top_enzyme1",
    "top_enzyme2",
    "top_metric_value",
    "status",
    "notes",
]


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing TSV: {path}")

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


def write_tsv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def find_column(fieldnames: list[str], candidates: list[str]) -> str | None:
    lower_to_original = {name.lower(): name for name in fieldnames}

    for candidate in candidates:
        hit = lower_to_original.get(candidate.lower())
        if hit is not None:
            return hit

    return None


def parse_pair_from_string(value: str) -> tuple[str, str] | None:
    tokens = [x for x in re.split(r"[,;+|:/\s_-]+", value.strip()) if x]
    if len(tokens) >= 2:
        return tokens[0], tokens[1]
    return None


def infer_pair(row: dict[str, str], fieldnames: list[str]) -> tuple[str, str]:
    col1 = find_column(fieldnames, PAIR1_COLUMNS)
    col2 = find_column(fieldnames, PAIR2_COLUMNS)

    if col1 is not None and col2 is not None:
        enzyme1 = row.get(col1, "").strip()
        enzyme2 = row.get(col2, "").strip()
        if enzyme1 and enzyme2:
            return enzyme1, enzyme2

    pair_col = find_column(fieldnames, PAIR_COLUMNS)
    if pair_col is not None:
        parsed = parse_pair_from_string(row.get(pair_col, ""))
        if parsed is not None:
            return parsed

    raise ValueError(
        "could not infer enzyme pair columns from ranked-pairs table; "
        f"columns are: {', '.join(fieldnames)}"
    )


def float_or_none(value: str) -> float | None:
    value = str(value).strip()
    if value == "":
        return None

    try:
        return float(value)
    except ValueError:
        return None


def fmt_float(value: float | None) -> str:
    if value is None:
        return ""
    if math.isfinite(value) and abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.10g}"


def select_metric_column(fieldnames: list[str], objective: str) -> str:
    candidates = OBJECTIVE_COLUMNS.get(objective, [objective])
    hit = find_column(fieldnames, candidates)

    if hit is not None:
        return hit

    fallback_candidates = [
        "weighted_bases",
        "raw_bases_in_window",
        "weighted_fragments",
        "raw_fragments_in_window",
    ]
    fallback = find_column(fieldnames, fallback_candidates)

    if fallback is not None:
        print(
            f"warning: objective {objective!r} not found; using {fallback!r}",
            file=sys.stderr,
        )
        return fallback

    raise ValueError(
        "could not identify a numeric objective column in ranked-pairs table; "
        f"columns are: {', '.join(fieldnames)}"
    )


def get_value(row: dict[str, str], fieldnames: list[str], candidates: list[str]) -> str:
    col = find_column(fieldnames, candidates)
    if col is None:
        return ""
    return row.get(col, "")


def read_candidate_enzymes(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []

    enzymes: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            enzymes.append(line)

    return enzymes


def count_json_files(json_dir: Path | None) -> int:
    if json_dir is None:
        return 0
    return len(glob.glob(str(json_dir / "*.json")))


def build_tables(
    ranked_tsv: Path,
    rows: list[dict[str, str]],
    objective: str,
    top_n: int,
) -> tuple[list[dict[str, str]], list[dict[str, str]], str]:
    if not rows:
        raise ValueError(f"{ranked_tsv}: no rows")

    fieldnames = list(rows[0].keys())
    metric_col = select_metric_column(fieldnames, objective)

    parsed_rows: list[tuple[float, dict[str, str], str, str]] = []

    for row in rows:
        enzyme1, enzyme2 = infer_pair(row, fieldnames)
        metric = float_or_none(row.get(metric_col, ""))
        if metric is None:
            continue
        parsed_rows.append((metric, row, enzyme1, enzyme2))

    if not parsed_rows:
        raise ValueError(f"{ranked_tsv}: no numeric values in {metric_col}")

    reverse = objective != "closest-target"
    parsed_rows.sort(key=lambda item: item[0], reverse=reverse)

    top_rows: list[dict[str, str]] = []
    matrix_rows: list[dict[str, str]] = []

    for rank, (metric, row, enzyme1, enzyme2) in enumerate(parsed_rows, start=1):
        matrix_rows.append(
            {
                "enzyme1": enzyme1,
                "enzyme2": enzyme2,
                "metric_name": metric_col,
                "metric_value": fmt_float(metric),
            }
        )

        if rank <= top_n:
            top_rows.append(
                {
                    "rank": str(rank),
                    "enzyme1": enzyme1,
                    "enzyme2": enzyme2,
                    "metric_name": metric_col,
                    "metric_value": fmt_float(metric),
                    "weighted_bases": get_value(
                        row,
                        fieldnames,
                        ["weighted_bases", "weighted-bases"],
                    ),
                    "weighted_fragments": get_value(
                        row,
                        fieldnames,
                        ["weighted_fragments", "weighted-fragments"],
                    ),
                    "raw_bases_in_window": get_value(
                        row,
                        fieldnames,
                        ["raw_bases_in_window", "raw-bases-in-window"],
                    ),
                    "raw_fragments_in_window": get_value(
                        row,
                        fieldnames,
                        ["raw_fragments_in_window", "raw-fragments-in-window"],
                    ),
                    "mean_weighted_length": get_value(
                        row,
                        fieldnames,
                        ["mean_weighted_length", "mean-weighted-length"],
                    ),
                    "weighted_genome_pct": get_value(
                        row,
                        fieldnames,
                        ["weighted_genome_pct", "weighted-genome-pct"],
                    ),
                    "source_ranked_tsv": str(ranked_tsv),
                }
            )

    return top_rows, matrix_rows, metric_col


def build_summary(
    ranked_tsv: Path,
    ranked_rows: list[dict[str, str]],
    top_rows: list[dict[str, str]],
    objective: str,
    metric_col: str,
    candidate_enzymes: list[str],
    json_files: int,
) -> list[dict[str, str]]:
    expected_pairs = ""
    status = "PASS"
    notes: list[str] = []

    if candidate_enzymes:
        expected_n = len(candidate_enzymes) * (len(candidate_enzymes) - 1) // 2
        expected_pairs = str(expected_n)

        if len(ranked_rows) != expected_n:
            status = "WARN"
            notes.append(
                f"ranked rows ({len(ranked_rows)}) != expected pairs ({expected_n})"
            )

        if json_files and json_files < expected_n:
            status = "WARN"
            notes.append(f"json files ({json_files}) < expected pairs ({expected_n})")

    if not top_rows:
        status = "FAIL"
        notes.append("no top rows generated")

    top = top_rows[0] if top_rows else {}

    return [
        {
            "ranked_tsv": str(ranked_tsv),
            "objective": objective,
            "metric_column": metric_col,
            "ranked_rows": str(len(ranked_rows)),
            "candidate_enzymes": str(len(candidate_enzymes)),
            "expected_unique_pairs": expected_pairs,
            "json_files": str(json_files),
            "top_enzyme1": top.get("enzyme1", ""),
            "top_enzyme2": top.get("enzyme2", ""),
            "top_metric_value": top.get("metric_value", ""),
            "status": status,
            "notes": "; ".join(notes),
        }
    ]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ranked", required=True, type=Path)
    parser.add_argument("--out-top", required=True, type=Path)
    parser.add_argument("--out-matrix", required=True, type=Path)
    parser.add_argument("--out-summary", required=True, type=Path)
    parser.add_argument("--objective", default="weighted-bases")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--candidate-enzymes", type=Path, default=None)
    parser.add_argument("--json-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        ranked_rows = read_tsv(args.ranked)
        top_rows, matrix_rows, metric_col = build_tables(
            ranked_tsv=args.ranked,
            rows=ranked_rows,
            objective=args.objective,
            top_n=args.top_n,
        )

        candidate_enzymes = read_candidate_enzymes(args.candidate_enzymes)
        json_files = count_json_files(args.json_dir)

        summary_rows = build_summary(
            ranked_tsv=args.ranked,
            ranked_rows=ranked_rows,
            top_rows=top_rows,
            objective=args.objective,
            metric_col=metric_col,
            candidate_enzymes=candidate_enzymes,
            json_files=json_files,
        )

        write_tsv(args.out_top, top_rows, TOP_COLUMNS)
        write_tsv(args.out_matrix, matrix_rows, MATRIX_COLUMNS)
        write_tsv(args.out_summary, summary_rows, SUMMARY_COLUMNS)

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out_top}", file=sys.stderr)
    print(f"wrote {args.out_matrix}", file=sys.stderr)
    print(f"wrote {args.out_summary}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
