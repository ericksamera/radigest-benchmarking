#!/usr/bin/env python3
"""Screen enzyme pairs for overlap with a user-defined target BED panel.

The script runs radigest once per unique enzyme pair in a candidate panel,
exports hard-window BED intervals, intersects those intervals with a target BED
panel, and merges the overlap metrics with a radigest-design table generated
for the same pair set.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import itertools
import json
import math
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

NA = "NA"

PAIR_COLUMNS = [
    "case_id",
    "display_name",
    "enzyme_a",
    "enzyme_b",
    "enzyme_pair",
    "panel_loci_total",
    "panel_loci_captured",
    "panel_fraction_captured",
    "panel_loci_read_accessible",
    "panel_fraction_read_accessible",
    "panel_containing_fragments",
    "panel_bp_overlap",
    "panel_containing_fragment_bp",
    "hard_loci",
    "hard_bp",
    "off_panel_fragment_loci",
    "off_panel_fragment_bp",
    "panel_loci_per_million_off_panel_bp",
    "target_genome_pct",
    "coverage_tolerance_pct",
    "target_mean_locus_depth",
    "predicted_weighted_genome_pct",
    "predicted_mean_locus_depth",
    "expected_mean_depth_panel_fragments",
    "weighted_fragments",
    "raw_fragments_in_window",
    "read_pairs_per_sample",
    "mean_weighted_insert_length",
    "feasible",
    "rank_by_panel_read_accessible",
    "rank_by_panel_captured",
    "rank_by_panel_specificity",
    "radigest_bed",
    "radigest_json",
]

TOP_COLUMNS = [
    "rank_by_panel_read_accessible",
    "enzyme_pair",
    "panel_loci_captured",
    "panel_loci_read_accessible",
    "panel_fraction_read_accessible",
    "panel_containing_fragments",
    "predicted_weighted_genome_pct",
    "predicted_mean_locus_depth",
    "expected_mean_depth_panel_fragments",
    "feasible",
    "hard_loci",
    "hard_bp",
    "off_panel_fragment_loci",
    "off_panel_fragment_bp",
    "panel_loci_per_million_off_panel_bp",
    "interpretation",
]

SUMMARY_COLUMNS = [
    "case_id",
    "display_name",
    "panel_bed",
    "reference",
    "candidate_enzymes",
    "pairs_screened",
    "panel_loci_total",
    "best_panel_pair",
    "best_panel_loci_captured",
    "best_panel_loci_read_accessible",
    "best_panel_fraction_read_accessible",
    "best_panel_predicted_mean_depth",
    "best_panel_predicted_weighted_genome_pct",
    "best_panel_off_panel_fragment_bp",
    "max_genome_recovery_pair",
    "max_genome_recovery_pct",
    "max_genome_recovery_panel_loci_read_accessible",
    "best_panel_pair_same_as_max_genome_recovery_pair",
    "interpretation",
]


@dataclass(frozen=True)
class Interval:
    seqid: str
    start: int
    end: int
    name: str

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass
class FragmentIndex:
    intervals_by_seqid: dict[str, list[Interval]]
    starts_by_seqid: dict[str, list[int]]
    ends_by_seqid: dict[str, list[int]]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_candidate_enzymes(path: Path) -> list[str]:
    enzymes: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        text = raw.strip()
        if text and not text.startswith("#"):
            enzymes.append(text)
    if len(enzymes) < 2:
        raise ValueError(f"{path}: expected at least two enzymes")
    duplicated = sorted({name for name in enzymes if enzymes.count(name) > 1})
    if duplicated:
        raise ValueError(f"{path}: duplicate enzyme names: {', '.join(duplicated)}")
    return enzymes


def split_bed_line(line: str) -> list[str]:
    if "\t" in line:
        return line.rstrip("\n").split("\t")
    return line.strip().split()


def read_bed(path: Path, *, label: str) -> list[Interval]:
    rows: list[Interval] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            text = raw.strip()
            if not text or text.startswith("#"):
                continue
            if text.startswith("track") or text.startswith("browser"):
                continue
            parts = split_bed_line(raw)
            if len(parts) < 3:
                raise ValueError(
                    f"{path}:{line_number}: BED row has fewer than 3 columns"
                )
            seqid = parts[0]
            try:
                start = int(parts[1])
                end = int(parts[2])
            except ValueError as exc:
                raise ValueError(
                    f"{path}:{line_number}: BED start/end must be integers"
                ) from exc
            if start < 0 or end <= start:
                raise ValueError(
                    f"{path}:{line_number}: expected 0-based half-open BED with end > start"
                )
            name = (
                parts[3] if len(parts) >= 4 and parts[3] else f"{label}_{len(rows) + 1}"
            )
            rows.append(Interval(seqid=seqid, start=start, end=end, name=name))
    if not rows:
        raise ValueError(f"{path}: no BED intervals found")
    return rows


def read_bed_or_empty(path: Path, *, label: str) -> list[Interval]:
    """Read BED intervals, treating absent or empty files as zero retained loci."""
    if not path.exists() or path.stat().st_size == 0:
        return []
    return read_bed(path, label=label)


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


def first_present(row: dict[str, str], names: Iterable[str]) -> str:
    for name in names:
        value = row.get(name, "")
        if value not in {"", NA}:
            return value
    return NA


def optional_float(value: str) -> float | None:
    if value in {"", NA}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fmt_float(value: float | None, digits: int = 6) -> str:
    if value is None:
        return NA
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if not math.isfinite(value):
        return NA
    return f"{value:.{digits}f}"


def fmt_int(value: int | float | None) -> str:
    if value is None:
        return NA
    return str(int(round(value)))


def truthy(value: str) -> str:
    text = str(value).strip().lower()
    if text in {"true", "t", "1", "yes", "y", "pass", "passed", "feasible"}:
        return "true"
    if text in {"false", "f", "0", "no", "n", "fail", "failed", "infeasible"}:
        return "false"
    return value if value not in {"", NA} else NA


def parse_pair_from_design_row(row: dict[str, str]) -> tuple[str, str] | None:
    e1 = first_present(
        row, ["enzyme_a", "enzyme_1", "enzyme1", "enzymeA", "enzyme_left"]
    )
    e2 = first_present(
        row, ["enzyme_b", "enzyme_2", "enzyme2", "enzymeB", "enzyme_right"]
    )
    if e1 != NA and e2 != NA:
        return e1, e2
    label = first_present(row, ["enzyme_pair", "pair", "pair_id", "enzyme_pair_id"])
    if label == NA:
        return None
    for sep in ["+", ",", "/", "–", "-"]:
        if sep in label:
            parts = [part.strip() for part in label.split(sep) if part.strip()]
            if len(parts) == 2:
                return parts[0], parts[1]
    return None


def read_design_by_pair(path: Path) -> dict[frozenset[str], dict[str, str]]:
    out: dict[frozenset[str], dict[str, str]] = {}
    for row in read_tsv(path):
        pair = parse_pair_from_design_row(row)
        if pair is None:
            continue
        out[frozenset(pair)] = row
    if not out:
        raise ValueError(f"{path}: no enzyme-pair rows could be parsed")
    return out


def design_metrics(row: dict[str, str] | None) -> dict[str, str]:
    if row is None:
        return {
            "target_genome_pct": NA,
            "coverage_tolerance_pct": NA,
            "target_mean_locus_depth": NA,
            "predicted_weighted_genome_pct": NA,
            "predicted_mean_locus_depth": NA,
            "weighted_fragments": NA,
            "raw_fragments_in_window": NA,
            "read_pairs_per_sample": NA,
            "mean_weighted_insert_length": NA,
            "feasible": NA,
        }
    feasible_value = first_present(
        row, ["feasible", "is_feasible", "passes", "meets_targets", "status"]
    )
    return {
        "target_genome_pct": first_present(
            row,
            ["target_genome_pct", "target_recovered_genome_pct", "target_recovery_pct"],
        ),
        "coverage_tolerance_pct": first_present(
            row,
            ["coverage_tolerance_pct", "genome_tolerance_pct", "target_tolerance_pct"],
        ),
        "target_mean_locus_depth": first_present(
            row, ["target_mean_locus_depth", "target_mean_depth", "desired_depth"]
        ),
        "predicted_weighted_genome_pct": first_present(
            row,
            [
                "predicted_weighted_genome_pct",
                "generated_weighted_genome_pct",
                "weighted_genome_pct",
                "recovered_genome_pct",
                "genome_pct",
                "weighted_recovered_genome_pct",
            ],
        ),
        "predicted_mean_locus_depth": first_present(
            row,
            [
                "predicted_mean_locus_depth",
                "expected_mean_depth",
                "mean_locus_depth",
                "predicted_depth",
                "expected_depth",
            ],
        ),
        "weighted_fragments": first_present(
            row, ["weighted_fragments", "effective_fragments"]
        ),
        "raw_fragments_in_window": first_present(
            row, ["raw_fragments_in_window", "fragments_in_window", "hard_fragments"]
        ),
        "read_pairs_per_sample": first_present(
            row, ["read_pairs_per_sample", "modeled_read_pairs_per_sample"]
        ),
        "mean_weighted_insert_length": first_present(
            row,
            [
                "mean_weighted_insert_length",
                "weighted_mean_insert_length",
                "mean_insert_length",
            ],
        ),
        "feasible": truthy(feasible_value),
    }


def build_fragment_index(fragments: list[Interval]) -> FragmentIndex:
    grouped: dict[str, list[Interval]] = {}
    for fragment in fragments:
        grouped.setdefault(fragment.seqid, []).append(fragment)
    starts: dict[str, list[int]] = {}
    ends: dict[str, list[int]] = {}
    for seqid, rows in grouped.items():
        rows.sort(key=lambda item: (item.start, item.end, item.name))
        starts[seqid] = [item.start for item in rows]
        ends[seqid] = [item.end for item in rows]
    return FragmentIndex(
        intervals_by_seqid=grouped, starts_by_seqid=starts, ends_by_seqid=ends
    )


def overlapping_fragments(index: FragmentIndex, target: Interval) -> list[Interval]:
    fragments = index.intervals_by_seqid.get(target.seqid)
    if not fragments:
        return []
    starts = index.starts_by_seqid[target.seqid]
    ends = index.ends_by_seqid[target.seqid]
    hit_index = bisect.bisect_left(starts, target.end)
    hits: list[Interval] = []
    i = hit_index - 1
    while i >= 0 and ends[i] > target.start:
        fragment = fragments[i]
        if fragment.start < target.end and fragment.end > target.start:
            hits.append(fragment)
        i -= 1
    return hits


def overlap_bp(a: Interval, b: Interval) -> int:
    return max(0, min(a.end, b.end) - max(a.start, b.start))


def interval_overlaps(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    return start_a < end_b and end_a > start_b


def read_accessible(
    fragment: Interval, target: Interval, *, read_layout: str, read_length: int
) -> bool:
    if read_length <= 0:
        return False
    left_start = fragment.start
    left_end = min(fragment.end, fragment.start + read_length)
    if interval_overlaps(target.start, target.end, left_start, left_end):
        return True
    if read_layout.lower() == "pe":
        right_start = max(fragment.start, fragment.end - read_length)
        right_end = fragment.end
        if interval_overlaps(target.start, target.end, right_start, right_end):
            return True
    return False


def run_command(command: list[str], *, log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log_handle:
        log_handle.write("command: " + " ".join(command) + "\n\n")
        result = subprocess.run(
            command,
            text=True,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if result.returncode != 0:
        tail = ""
        try:
            tail = "\n".join(
                log_path.read_text(encoding="utf-8", errors="replace").splitlines()[
                    -20:
                ]
            )
        except OSError:
            pass
        raise RuntimeError(
            f"command failed with exit status {result.returncode}; log={log_path}\n{tail}"
        )


def run_radigest_pair(
    *,
    radigest: str,
    fasta: Path,
    enzyme_a: str,
    enzyme_b: str,
    min_size: str,
    max_size: str,
    threads: int,
    bed_out: Path,
    json_out: Path,
    log_out: Path,
) -> None:
    bed_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    command = [
        radigest,
        "-fasta",
        str(fasta),
        "-enzymes",
        f"{enzyme_a},{enzyme_b}",
        "-min",
        str(min_size),
        "-max",
        str(max_size),
        "-score-min",
        str(min_size),
        "-score-max",
        str(max_size),
        "-size-model",
        "hard",
        "-threads",
        str(threads),
        "-bed",
        str(bed_out),
        "-json",
        str(json_out),
    ]
    run_command(command, log_path=log_out)
    # Some candidate enzyme pairs legitimately retain zero fragments in the
    # configured hard window. That is a valid design-space result and should
    # not abort an all-pair panel screen. Ensure a file exists so downstream
    # bookkeeping can record zero hard-window loci and zero target overlap.
    if not bed_out.exists():
        bed_out.touch()
    if bed_out.stat().st_size == 0:
        print(
            f"warning: no hard-window BED intervals for {enzyme_a}+{enzyme_b}; "
            f"recording zero retained loci for {bed_out}",
            file=sys.stderr,
        )


def summarize_pair(
    *,
    args: argparse.Namespace,
    enzyme_a: str,
    enzyme_b: str,
    panel: list[Interval],
    design_row: dict[str, str] | None,
    bed_path: Path,
    json_path: Path,
) -> dict[str, str]:
    fragments = read_bed_or_empty(bed_path, label=f"{enzyme_a}_{enzyme_b}_fragment")
    index = build_fragment_index(fragments)
    fragment_by_key = {
        (item.seqid, item.start, item.end, item.name): item for item in fragments
    }
    hard_loci = len(fragments)
    hard_bp = sum(item.length for item in fragments)

    captured_targets: set[tuple[int, str, int, int, str]] = set()
    read_accessible_targets: set[tuple[int, str, int, int, str]] = set()
    panel_fragment_keys: set[tuple[str, int, int, str]] = set()
    total_overlap_bp = 0

    for target_index, target in enumerate(panel):
        target_key = (target_index, target.seqid, target.start, target.end, target.name)
        hits = overlapping_fragments(index, target)
        if hits:
            captured_targets.add(target_key)
        for fragment in hits:
            key = (fragment.seqid, fragment.start, fragment.end, fragment.name)
            panel_fragment_keys.add(key)
            total_overlap_bp += overlap_bp(target, fragment)
            if read_accessible(
                fragment,
                target,
                read_layout=args.read_layout,
                read_length=args.read_length,
            ):
                read_accessible_targets.add(target_key)

    panel_fragment_bp = sum(fragment_by_key[key].length for key in panel_fragment_keys)
    panel_fragment_count = len(panel_fragment_keys)
    panel_total = len(panel)
    panel_captured = len(captured_targets)
    panel_accessible = len(read_accessible_targets)
    off_panel_loci = max(0, hard_loci - panel_fragment_count)
    off_panel_bp = max(0, hard_bp - panel_fragment_bp)
    panel_per_million_off = None
    if off_panel_bp > 0:
        panel_per_million_off = panel_accessible / (off_panel_bp / 1_000_000.0)
    elif panel_accessible > 0:
        panel_per_million_off = float("inf")
    else:
        panel_per_million_off = 0.0

    metrics = design_metrics(design_row)
    predicted_depth = optional_float(metrics["predicted_mean_locus_depth"])
    expected_panel_depth = predicted_depth if panel_fragment_count > 0 else None

    return {
        "case_id": args.case_id,
        "display_name": args.display_name,
        "enzyme_a": enzyme_a,
        "enzyme_b": enzyme_b,
        "enzyme_pair": f"{enzyme_a}+{enzyme_b}",
        "panel_loci_total": str(panel_total),
        "panel_loci_captured": str(panel_captured),
        "panel_fraction_captured": fmt_float(panel_captured / panel_total),
        "panel_loci_read_accessible": str(panel_accessible),
        "panel_fraction_read_accessible": fmt_float(panel_accessible / panel_total),
        "panel_containing_fragments": str(panel_fragment_count),
        "panel_bp_overlap": str(total_overlap_bp),
        "panel_containing_fragment_bp": str(panel_fragment_bp),
        "hard_loci": str(hard_loci),
        "hard_bp": str(hard_bp),
        "off_panel_fragment_loci": str(off_panel_loci),
        "off_panel_fragment_bp": str(off_panel_bp),
        "panel_loci_per_million_off_panel_bp": fmt_float(panel_per_million_off),
        "target_genome_pct": metrics["target_genome_pct"],
        "coverage_tolerance_pct": metrics["coverage_tolerance_pct"],
        "target_mean_locus_depth": metrics["target_mean_locus_depth"],
        "predicted_weighted_genome_pct": metrics["predicted_weighted_genome_pct"],
        "predicted_mean_locus_depth": metrics["predicted_mean_locus_depth"],
        "expected_mean_depth_panel_fragments": fmt_float(expected_panel_depth),
        "weighted_fragments": metrics["weighted_fragments"],
        "raw_fragments_in_window": metrics["raw_fragments_in_window"],
        "read_pairs_per_sample": metrics["read_pairs_per_sample"],
        "mean_weighted_insert_length": metrics["mean_weighted_insert_length"],
        "feasible": metrics["feasible"],
        "rank_by_panel_read_accessible": NA,
        "rank_by_panel_captured": NA,
        "rank_by_panel_specificity": NA,
        "radigest_bed": str(bed_path),
        "radigest_json": str(json_path),
    }


def numeric(row: dict[str, str], key: str, default: float = float("-inf")) -> float:
    value = optional_float(row.get(key, NA))
    return default if value is None else value


def rank_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_accessible = sorted(
        rows,
        key=lambda row: (
            int(row["panel_loci_read_accessible"]),
            int(row["panel_loci_captured"]),
            numeric(row, "predicted_mean_locus_depth"),
            -int(row["off_panel_fragment_bp"]),
            row["enzyme_pair"],
        ),
        reverse=True,
    )
    for rank, row in enumerate(by_accessible, start=1):
        row["rank_by_panel_read_accessible"] = str(rank)

    by_captured = sorted(
        rows,
        key=lambda row: (
            int(row["panel_loci_captured"]),
            int(row["panel_loci_read_accessible"]),
            numeric(row, "predicted_mean_locus_depth"),
            -int(row["off_panel_fragment_bp"]),
            row["enzyme_pair"],
        ),
        reverse=True,
    )
    for rank, row in enumerate(by_captured, start=1):
        row["rank_by_panel_captured"] = str(rank)

    by_specificity = sorted(
        rows,
        key=lambda row: (
            numeric(row, "panel_loci_per_million_off_panel_bp"),
            int(row["panel_loci_read_accessible"]),
            numeric(row, "predicted_mean_locus_depth"),
            row["enzyme_pair"],
        ),
        reverse=True,
    )
    for rank, row in enumerate(by_specificity, start=1):
        row["rank_by_panel_specificity"] = str(rank)

    return by_accessible


def write_tsv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, NA) for column in columns})


def top_rows_for_manuscript(
    rows: list[dict[str, str]], *, top_n: int
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows[:top_n]:
        panel_total = row["panel_loci_total"]
        interpretation = (
            f"Captures {row['panel_loci_read_accessible']} read-accessible targets "
            f"out of {panel_total} panel intervals; off-panel hard-window burden "
            f"is {row['off_panel_fragment_loci']} fragments."
        )
        out.append({**row, "interpretation": interpretation})
    return out


def summary_row(args: argparse.Namespace, rows: list[dict[str, str]]) -> dict[str, str]:
    best_panel = rows[0]
    rows_with_recovery = [
        row
        for row in rows
        if optional_float(row.get("predicted_weighted_genome_pct", NA)) is not None
    ]
    best_recovery = (
        max(
            rows_with_recovery,
            key=lambda row: numeric(row, "predicted_weighted_genome_pct"),
        )
        if rows_with_recovery
        else best_panel
    )
    same = best_panel["enzyme_pair"] == best_recovery["enzyme_pair"]
    interpretation = (
        f"The top panel-overlap pair was {best_panel['enzyme_pair']}, with "
        f"{best_panel['panel_loci_read_accessible']} read-accessible panel intervals. "
        f"The pair with the largest predicted weighted genome recovery was "
        f"{best_recovery['enzyme_pair']}."
    )
    if not same:
        interpretation += (
            " These differ, showing that target-aware interval screening can change "
            "enzyme-pair choice relative to aggregate genome-recovery ranking."
        )
    else:
        interpretation += (
            " These are the same in this run; report the full ranking to show whether "
            "nearby designs trade panel recovery against off-panel burden or depth."
        )
    return {
        "case_id": args.case_id,
        "display_name": args.display_name,
        "panel_bed": str(args.panel_bed),
        "reference": str(args.fasta),
        "candidate_enzymes": str(args.candidate_enzymes),
        "pairs_screened": str(len(rows)),
        "panel_loci_total": best_panel["panel_loci_total"],
        "best_panel_pair": best_panel["enzyme_pair"],
        "best_panel_loci_captured": best_panel["panel_loci_captured"],
        "best_panel_loci_read_accessible": best_panel["panel_loci_read_accessible"],
        "best_panel_fraction_read_accessible": best_panel[
            "panel_fraction_read_accessible"
        ],
        "best_panel_predicted_mean_depth": best_panel["predicted_mean_locus_depth"],
        "best_panel_predicted_weighted_genome_pct": best_panel[
            "predicted_weighted_genome_pct"
        ],
        "best_panel_off_panel_fragment_bp": best_panel["off_panel_fragment_bp"],
        "max_genome_recovery_pair": best_recovery["enzyme_pair"],
        "max_genome_recovery_pct": best_recovery["predicted_weighted_genome_pct"],
        "max_genome_recovery_panel_loci_read_accessible": best_recovery[
            "panel_loci_read_accessible"
        ],
        "best_panel_pair_same_as_max_genome_recovery_pair": "true" if same else "false",
        "interpretation": interpretation,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--fasta", required=True, type=Path)
    parser.add_argument("--panel-bed", required=True, type=Path)
    parser.add_argument("--candidate-enzymes", required=True, type=Path)
    parser.add_argument("--design-tsv", required=True, type=Path)
    parser.add_argument("--radigest", required=True)
    parser.add_argument("--min-size", required=True)
    parser.add_argument("--max-size", required=True)
    parser.add_argument("--read-layout", choices=["pe", "se"], required=True)
    parser.add_argument("--read-length", required=True, type=int)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--pair-overlap-out", required=True, type=Path)
    parser.add_argument("--top-out", required=True, type=Path)
    parser.add_argument("--summary-out", required=True, type=Path)
    parser.add_argument("--manuscript-table-out", type=Path)
    parser.add_argument("--metadata-out", required=True, type=Path)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        if args.top_n < 1:
            raise ValueError("--top-n must be >= 1")
        if args.threads < 1:
            raise ValueError("--threads must be >= 1")
        if shutil.which(args.radigest) is None and not Path(args.radigest).exists():
            raise FileNotFoundError(f"radigest executable not found: {args.radigest}")
        if not args.fasta.exists():
            raise FileNotFoundError(f"missing reference FASTA: {args.fasta}")
        if not args.panel_bed.exists():
            raise FileNotFoundError(f"missing target panel BED: {args.panel_bed}")

        if args.force and args.work_dir.exists():
            shutil.rmtree(args.work_dir)
        bed_dir = args.work_dir / "beds"
        json_dir = args.work_dir / "json"
        log_dir = args.work_dir / "logs"
        bed_dir.mkdir(parents=True, exist_ok=True)
        json_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)

        panel = read_bed(args.panel_bed, label="panel")
        enzymes = read_candidate_enzymes(args.candidate_enzymes)
        design_by_pair = read_design_by_pair(args.design_tsv)
        rows: list[dict[str, str]] = []

        for enzyme_a, enzyme_b in itertools.combinations(enzymes, 2):
            stem = f"{enzyme_a}__{enzyme_b}"
            bed_path = bed_dir / f"{stem}.bed"
            json_path = json_dir / f"{stem}.json"
            log_path = log_dir / f"{stem}.log"
            if not bed_path.exists():
                run_radigest_pair(
                    radigest=args.radigest,
                    fasta=args.fasta,
                    enzyme_a=enzyme_a,
                    enzyme_b=enzyme_b,
                    min_size=args.min_size,
                    max_size=args.max_size,
                    threads=args.threads,
                    bed_out=bed_path,
                    json_out=json_path,
                    log_out=log_path,
                )
            design_row = design_by_pair.get(frozenset([enzyme_a, enzyme_b]))
            rows.append(
                summarize_pair(
                    args=args,
                    enzyme_a=enzyme_a,
                    enzyme_b=enzyme_b,
                    panel=panel,
                    design_row=design_row,
                    bed_path=bed_path,
                    json_path=json_path,
                )
            )

        ranked = rank_rows(rows)
        write_tsv(args.pair_overlap_out, ranked, PAIR_COLUMNS)
        top = top_rows_for_manuscript(ranked, top_n=args.top_n)
        write_tsv(args.top_out, top, TOP_COLUMNS)
        if args.manuscript_table_out is not None:
            write_tsv(args.manuscript_table_out, top, TOP_COLUMNS)
        write_tsv(args.summary_out, [summary_row(args, ranked)], SUMMARY_COLUMNS)
        args.metadata_out.parent.mkdir(parents=True, exist_ok=True)
        args.metadata_out.write_text(
            json.dumps(
                {
                    "case_id": args.case_id,
                    "display_name": args.display_name,
                    "fasta": str(args.fasta),
                    "panel_bed": str(args.panel_bed),
                    "candidate_enzymes": str(args.candidate_enzymes),
                    "enzymes": enzymes,
                    "pairs_screened": len(ranked),
                    "panel_loci_total": len(panel),
                    "min_size": args.min_size,
                    "max_size": args.max_size,
                    "read_layout": args.read_layout,
                    "read_length": args.read_length,
                    "outputs": {
                        "pair_overlap": str(args.pair_overlap_out),
                        "top_designs": str(args.top_out),
                        "summary": str(args.summary_out),
                        "manuscript_table": (
                            str(args.manuscript_table_out)
                            if args.manuscript_table_out is not None
                            else "NA"
                        ),
                    },
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.pair_overlap_out}", file=sys.stderr)
    print(f"wrote {args.top_out}", file=sys.stderr)
    print(f"wrote {args.summary_out}", file=sys.stderr)
    if args.manuscript_table_out is not None:
        print(f"wrote {args.manuscript_table_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
