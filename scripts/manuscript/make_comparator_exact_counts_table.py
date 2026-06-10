#!/usr/bin/env python3
"""Build a manuscript Table 2 with exact comparator counts.

The output intentionally combines comparator rows with different resolutions, but
keeps the claim boundary explicit for each tool:

* coordinate-capable tools report interval-set counts, intersections, unions and
  Jaccard agreement;
* SimRAD reports aggregate retained-fragment count differences only; and
* ddgRADer reports binned-count agreement only.

This table is intended to replace qualitative comparator prose/table entries
with reviewer-auditable counts.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import NoReturn

TABLE_COLUMNS = [
    "tier",
    "tool_id",
    "tool",
    "case_id",
    "dataset_id",
    "condition_id",
    "reference_path",
    "enzymes",
    "size_window_bp",
    "comparison_level",
    "output_resolution",
    "claim_allowed",
    "coordinate_equivalence_claim_allowed",
    "metric",
    "radigest_units",
    "comparator_units",
    "matching_units",
    "union_units",
    "only_radigest",
    "only_comparator",
    "count_delta_comparator_minus_radigest",
    "relative_count_delta_vs_radigest",
    "jaccard",
    "bins_compared",
    "bins_with_difference",
    "max_abs_bin_difference",
    "status",
    "claim_boundary",
    "source",
    "notes",
]

TRUE_VALUES = {"1", "true", "yes", "y"}
CLAIM_BOUNDARIES = {
    "coordinate_equivalence": (
        "Exact normalized zero-based half-open interval comparison; Jaccard and "
        "interval counts are interpreted as coordinate-equivalence evidence."
    ),
    "count_level_digest": (
        "Aggregate retained-fragment count comparison only; no coordinate-"
        "equivalence claim."
    ),
    "screening_throughput": (
        "Ten-base fragment-size bin comparison only; no coordinate-equivalence "
        "claim."
    ),
}
CLAIMS_REQUIRED_TO_PASS = {"coordinate_equivalence", "screening_throughput"}


def fail(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def read_tsv(
    path: Path, *, required_columns: list[str] | None = None
) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing TSV: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        if required_columns is not None:
            missing = [
                col for col in required_columns if col not in set(reader.fieldnames)
            ]
            if missing:
                raise ValueError(f"{path}: missing columns: {', '.join(missing)}")
        rows = [
            {
                key: "" if value is None else value
                for key, value in row.items()
                if key is not None
            }
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]
    return rows


def index_rows(
    rows: list[dict[str, str]], key: str, source: Path
) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        value = row.get(key, "")
        if not value:
            raise ValueError(f"{source}: row has empty {key}")
        if value in out:
            raise ValueError(f"{source}: duplicate {key}={value}")
        out[value] = row
    return out


def is_true(value: str) -> bool:
    return value.strip().lower() in TRUE_VALUES


def interval_summary_path(case: dict[str, str]) -> Path:
    tool_id = case["tool_id"]
    case_id = case["case_id"]
    if tool_id == "digital_rads":
        return Path(f"results/comparators/digital_rads/{case_id}.summary.tsv")
    if tool_id == "ddradseqtools":
        return Path(
            f"results/comparators/ddradseqtools/"
            f"{case_id}.interval_compare.summary.tsv"
        )
    raise ValueError(f"unsupported interval comparator tool_id={tool_id!r}")


def condition_metadata(
    case: dict[str, str],
    conditions_by_id: dict[str, dict[str, str]],
) -> tuple[str, str]:
    condition = conditions_by_id.get(case["condition_id"], {})
    enzyme_1 = case.get("enzyme_1") or condition.get("enzyme_1", "")
    enzyme_2 = case.get("enzyme_2") or condition.get("enzyme_2", "")
    min_size = case.get("min_size") or condition.get("min_size", "")
    max_size = case.get("max_size") or condition.get("max_size", "")
    enzymes = (
        enzyme_1 if enzyme_2 in {"", "NA", "none", "None"} else f"{enzyme_1}+{enzyme_2}"
    )
    size_window = f"{min_size}-{max_size}" if min_size and max_size else "NA"
    return enzymes, size_window


def tier_for_dataset(dataset_id: str) -> str:
    if dataset_id == "comparator_smoke_single":
        return "synthetic_smoke"
    if dataset_id == "small_yeast_s288c_plain":
        return "public_yeast"
    return "other"


def safe_int(value: str) -> int | None:
    if value in {"", "NA"}:
        return None
    return int(float(value))


def int_delta(second: str, first: str) -> str:
    first_i = safe_int(first)
    second_i = safe_int(second)
    if first_i is None or second_i is None:
        return "NA"
    return str(second_i - first_i)


def relative_delta(second: str, first: str) -> str:
    first_i = safe_int(first)
    second_i = safe_int(second)
    if first_i is None or second_i is None:
        return "NA"
    if first_i == 0:
        return "0.00000000" if second_i == 0 else "inf"
    return f"{(second_i - first_i) / first_i:.8f}"


def base_row(
    *,
    case: dict[str, str],
    registry: dict[str, dict[str, str]],
    conditions_by_id: dict[str, dict[str, str]],
    source: Path,
) -> dict[str, str]:
    tool_id = case["tool_id"]
    tool = registry[tool_id]
    claim = tool["allowed_claim"]
    enzymes, size_window = condition_metadata(case, conditions_by_id)
    return {
        "tier": tier_for_dataset(case["dataset_id"]),
        "tool_id": tool_id,
        "tool": tool["display_name"],
        "case_id": case["case_id"],
        "dataset_id": case["dataset_id"],
        "condition_id": case["condition_id"],
        "reference_path": case["reference_path"],
        "enzymes": enzymes,
        "size_window_bp": size_window,
        "comparison_level": tool["comparison_level"],
        "output_resolution": tool["primary_output_type"],
        "claim_allowed": claim,
        "coordinate_equivalence_claim_allowed": (
            "true" if claim == "coordinate_equivalence" else "false"
        ),
        "metric": "NA",
        "radigest_units": "NA",
        "comparator_units": "NA",
        "matching_units": "NA",
        "union_units": "NA",
        "only_radigest": "NA",
        "only_comparator": "NA",
        "count_delta_comparator_minus_radigest": "NA",
        "relative_count_delta_vs_radigest": "NA",
        "jaccard": "NA",
        "bins_compared": "NA",
        "bins_with_difference": "NA",
        "max_abs_bin_difference": "NA",
        "status": "NA",
        "claim_boundary": CLAIM_BOUNDARIES.get(
            claim, "Claim boundary declared in config/comparators.tsv."
        ),
        "source": str(source),
        "notes": case.get("notes", ""),
    }


def interval_row(
    *,
    case: dict[str, str],
    registry: dict[str, dict[str, str]],
    conditions_by_id: dict[str, dict[str, str]],
) -> dict[str, str]:
    path = interval_summary_path(case)
    rows = read_tsv(
        path,
        required_columns=[
            "first_intervals",
            "second_intervals",
            "matching_intervals",
            "only_first",
            "only_second",
            "multiset_union",
            "jaccard",
            "status",
        ],
    )
    if len(rows) != 1:
        raise ValueError(f"{path}: expected exactly one summary row, found {len(rows)}")
    summary = rows[0]
    out = base_row(
        case=case, registry=registry, conditions_by_id=conditions_by_id, source=path
    )
    out.update(
        {
            "metric": "normalized_intervals",
            "radigest_units": summary["first_intervals"],
            "comparator_units": summary["second_intervals"],
            "matching_units": summary["matching_intervals"],
            "union_units": summary["multiset_union"],
            "only_radigest": summary["only_first"],
            "only_comparator": summary["only_second"],
            "count_delta_comparator_minus_radigest": int_delta(
                summary["second_intervals"], summary["first_intervals"]
            ),
            "relative_count_delta_vs_radigest": relative_delta(
                summary["second_intervals"], summary["first_intervals"]
            ),
            "jaccard": summary["jaccard"],
            "status": summary["status"],
        }
    )
    return out


def simrad_row(
    *,
    case: dict[str, str],
    registry: dict[str, dict[str, str]],
    conditions_by_id: dict[str, dict[str, str]],
) -> dict[str, str]:
    path = Path(case["output_path"])
    rows = read_tsv(
        path,
        required_columns=[
            "metric",
            "radigest_value",
            "simrad_value",
            "difference_simrad_minus_radigest",
            "relative_difference_vs_radigest",
            "status",
        ],
    )
    fragment_rows = [row for row in rows if row.get("metric") == "fragments"]
    if len(fragment_rows) != 1:
        raise ValueError(f"{path}: expected exactly one metric=fragments row")
    summary = fragment_rows[0]
    out = base_row(
        case=case, registry=registry, conditions_by_id=conditions_by_id, source=path
    )
    notes = out["notes"]
    trace_metrics = sorted(
        row.get("metric", "") for row in rows if row.get("metric") != "fragments"
    )
    if trace_metrics:
        notes = (
            (notes + " " if notes else "")
            + "Trace metric(s) present but not used for the count-level claim: "
            + ",".join(trace_metrics)
            + "."
        )
    out.update(
        {
            "metric": "retained_fragments",
            "radigest_units": summary["radigest_value"],
            "comparator_units": summary["simrad_value"],
            "count_delta_comparator_minus_radigest": summary[
                "difference_simrad_minus_radigest"
            ],
            "relative_count_delta_vs_radigest": summary[
                "relative_difference_vs_radigest"
            ],
            "status": summary["status"],
            "notes": notes,
        }
    )
    return out


def ddgrader_row(
    *,
    case: dict[str, str],
    registry: dict[str, dict[str, str]],
    conditions_by_id: dict[str, dict[str, str]],
) -> dict[str, str]:
    path = Path(case["output_path"])
    rows = read_tsv(
        path,
        required_columns=[
            "first_total",
            "second_total",
            "difference_second_minus_first",
            "bins_compared",
            "bins_with_difference",
            "max_abs_bin_difference",
            "status",
        ],
    )
    if len(rows) != 1:
        raise ValueError(
            f"{path}: expected exactly one binned summary row, found {len(rows)}"
        )
    summary = rows[0]
    out = base_row(
        case=case, registry=registry, conditions_by_id=conditions_by_id, source=path
    )
    out.update(
        {
            "metric": "ten_bp_binned_fragment_counts",
            "radigest_units": summary["first_total"],
            "comparator_units": summary["second_total"],
            "count_delta_comparator_minus_radigest": summary[
                "difference_second_minus_first"
            ],
            "relative_count_delta_vs_radigest": relative_delta(
                summary["second_total"], summary["first_total"]
            ),
            "bins_compared": summary["bins_compared"],
            "bins_with_difference": summary["bins_with_difference"],
            "max_abs_bin_difference": summary["max_abs_bin_difference"],
            "status": summary["status"],
        }
    )
    return out


def build_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    registry = index_rows(read_tsv(args.comparators), "tool_id", args.comparators)
    conditions = index_rows(read_tsv(args.conditions), "condition_id", args.conditions)
    rows: list[dict[str, str]] = []

    for case in read_tsv(args.comparator_cases):
        if not is_true(case.get("required_for_nonempirical", "")):
            continue
        rows.append(
            interval_row(case=case, registry=registry, conditions_by_id=conditions)
        )

    for case in read_tsv(args.noncoordinate_cases):
        if not is_true(case.get("required_for_nonempirical", "")):
            continue
        if case["tool_id"] == "simrad":
            rows.append(
                simrad_row(case=case, registry=registry, conditions_by_id=conditions)
            )
        elif case["tool_id"] == "ddgrader":
            rows.append(
                ddgrader_row(case=case, registry=registry, conditions_by_id=conditions)
            )
        else:
            raise ValueError(f"unsupported non-coordinate tool_id={case['tool_id']!r}")

    rows.sort(
        key=lambda row: (
            row["tier"],
            row["dataset_id"],
            row["condition_id"],
            row["tool_id"],
            row["case_id"],
        )
    )
    return rows


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, delimiter="\t", fieldnames=TABLE_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--comparator-cases", type=Path, default=Path("config/comparator_cases.tsv")
    )
    parser.add_argument(
        "--noncoordinate-cases",
        type=Path,
        default=Path("config/noncoordinate_comparator_cases.tsv"),
    )
    parser.add_argument(
        "--comparators", type=Path, default=Path("config/comparators.tsv")
    )
    parser.add_argument(
        "--conditions", type=Path, default=Path("config/conditions.tsv")
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("results/manuscript/tables/table_02_comparator_exact_counts.tsv"),
    )
    parser.add_argument("--require-present", action="store_true")
    parser.add_argument(
        "--require-claim-pass",
        action="store_true",
        help=(
            "Fail if coordinate-equivalence or binned-screening rows are not PASS. "
            "Count-level SimRAD rows may be DIFFER without failing."
        ),
    )
    args = parser.parse_args(argv)

    try:
        rows = build_rows(args)
        write_tsv(args.out, rows)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.require_present:
        missing = [row for row in rows if row["status"] in {"MISSING", "EMPTY", "NA"}]
        if missing:
            labels = ", ".join(f"{row['case_id']}={row['status']}" for row in missing)
            print(
                f"error: comparator exact-count table has missing rows: {labels}",
                file=sys.stderr,
            )
            return 1

    if args.require_claim_pass:
        failures = [
            row
            for row in rows
            if row["claim_allowed"] in CLAIMS_REQUIRED_TO_PASS
            and row["status"] != "PASS"
        ]
        if failures:
            labels = ", ".join(f"{row['case_id']}={row['status']}" for row in failures)
            print(
                f"error: comparator exact-count claim rows are not PASS: {labels}",
                file=sys.stderr,
            )
            return 1

    print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
