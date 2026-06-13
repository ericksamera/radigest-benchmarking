#!/usr/bin/env python3
"""Build a comparator-case matrix across shared smoke and small-yeast cases."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

FIELDS = [
    "tier",
    "tool_id",
    "tool",
    "case_id",
    "dataset_id",
    "condition_id",
    "reference_path",
    "comparison_level",
    "output_resolution",
    "claim_allowed",
    "coordinate_equivalence_claim_allowed",
    "required_output",
    "observed_status",
    "status_detail",
    "claim_boundary",
    "notes",
]
TRUE_VALUES = {"1", "true", "yes", "y"}
CLAIM_BOUNDARIES = {
    "coordinate_equivalence": (
        "Normalized interval comparison against radigest; "
        "coordinate-equivalence claim is allowed for this case."
    ),
    "count_level_digest": (
        "Aggregate retained-fragment count against radigest only; "
        "no coordinate-equivalence claim."
    ),
    "screening_throughput": (
        "Binned fragment-screening comparison against radigest only; "
        "no coordinate-equivalence claim."
    ),
}


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return [
            {
                key: "" if value is None else value
                for key, value in row.items()
                if key is not None
            }
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]


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


def tier_for_dataset(dataset_id: str) -> str:
    if dataset_id == "comparator_smoke_single":
        return "shared_synthetic_smoke"
    if dataset_id == "small_yeast_s288c_plain":
        return "small_yeast_radigest_anchor"
    if dataset_id == "moderate_cannabis_pink-pepper_plain":
        return "medium_reference_coordinate_check"
    return "other"


def required_output_for_interval(case: dict[str, str]) -> Path:
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


def summarize_status(path: Path) -> tuple[str, str]:
    if not path.exists():
        return "MISSING", "summary file is absent"
    rows = read_tsv(path)
    if not rows:
        return "EMPTY", "summary file has no data rows"

    statuses = sorted(
        {(row.get("status") or "PRESENT").strip() or "PRESENT" for row in rows}
    )
    claim_statuses = [status for status in statuses if status != "INFO_ONLY"]
    if statuses == ["INFO_ONLY"]:
        observed = "INFO_ONLY"
    elif claim_statuses and set(claim_statuses) <= {"PASS"}:
        observed = "PASS"
    else:
        observed = ";".join(statuses)

    details: list[str] = []
    for row in rows:
        label = (
            row.get("metric")
            or row.get("enzyme_pair")
            or row.get("mode")
            or row.get("tool")
            or "row"
        )
        status = (row.get("status") or "PRESENT").strip() or "PRESENT"
        extra = ""
        for key in [
            "jaccard",
            "difference_simrad_minus_radigest",
            "difference_second_minus_first",
            "bins_with_difference",
        ]:
            value = row.get(key, "")
            if value not in {"", "NA"}:
                extra = f"{key}={value}"
                break
        details.append(f"{label}={status}" + (f"({extra})" if extra else ""))
    return observed, "; ".join(details)


def make_row(
    *,
    case: dict[str, str],
    registry: dict[str, dict[str, str]],
    required_output: Path,
) -> dict[str, str]:
    tool_id = case["tool_id"]
    if tool_id not in registry:
        raise ValueError(f"unknown tool_id={tool_id!r} in case {case['case_id']}")
    tool = registry[tool_id]
    claim = tool["allowed_claim"]
    observed_status, status_detail = summarize_status(required_output)
    return {
        "tier": tier_for_dataset(case["dataset_id"]),
        "tool_id": tool_id,
        "tool": tool["display_name"],
        "case_id": case["case_id"],
        "dataset_id": case["dataset_id"],
        "condition_id": case["condition_id"],
        "reference_path": case["reference_path"],
        "comparison_level": tool["comparison_level"],
        "output_resolution": tool["primary_output_type"],
        "claim_allowed": claim,
        "coordinate_equivalence_claim_allowed": (
            "true" if claim == "coordinate_equivalence" else "false"
        ),
        "required_output": str(required_output),
        "observed_status": observed_status,
        "status_detail": status_detail,
        "claim_boundary": CLAIM_BOUNDARIES.get(
            claim, "Claim boundary declared in config/comparators.tsv."
        ),
        "notes": case.get("notes", ""),
    }


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
        "--out",
        type=Path,
        default=Path("results/comparators/comparator_case_matrix.tsv"),
    )
    parser.add_argument("--require-present", action="store_true")
    args = parser.parse_args(argv)

    try:
        registry = index_rows(read_tsv(args.comparators), "tool_id", args.comparators)
        rows: list[dict[str, str]] = []
        for case in read_tsv(args.comparator_cases):
            if is_true(case.get("required_for_nonempirical", "")):
                rows.append(
                    make_row(
                        case=case,
                        registry=registry,
                        required_output=required_output_for_interval(case),
                    )
                )
        for case in read_tsv(args.noncoordinate_cases):
            if is_true(case.get("required_for_nonempirical", "")):
                rows.append(
                    make_row(
                        case=case,
                        registry=registry,
                        required_output=Path(case["output_path"]),
                    )
                )
        rows.sort(key=lambda row: (row["tier"], row["tool_id"], row["case_id"]))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.require_present:
        missing = [
            row for row in rows if row["observed_status"] in {"MISSING", "EMPTY"}
        ]
        if missing:
            labels = ", ".join(
                f"{row['case_id']}={row['observed_status']}" for row in missing
            )
            print(
                f"error: comparator case matrix has missing outputs: {labels}",
                file=sys.stderr,
            )
            return 1
    print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
