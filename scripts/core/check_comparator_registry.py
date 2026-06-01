#!/usr/bin/env python3
"""Validate and display the comparator registry.

The comparator registry records each external tool's benchmark scope, workflow
entrypoints, normalization semantics, and allowed manuscript claims. This check
is intentionally static: it validates the manifest and repository-owned helper
paths, and it reports external checkout paths as warnings unless --strict is
used.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REQUIRED_COLUMNS = [
    "tool_id",
    "display_name",
    "role",
    "install_target",
    "install_command",
    "check_command",
    "version_command",
    "workflow",
    "comparison_level",
    "normalizer",
    "summary_script",
    "supported_conditions",
    "primary_output_type",
    "allowed_claim",
    "required_paths",
    "mismatch_issue",
    "mismatch_resolution",
    "notes",
]

ALLOWED_COMPARISON_LEVELS = {
    "count_only",
    "normalized_interval",
    "binned_screening",
    "limited_digest_locus",
    "discussion_only",
}

ALLOWED_OUTPUT_TYPES = {
    "aggregate_count",
    "normalized_interval_set",
    "binned_fragment_distribution",
    "locus_count",
    "selected_gbs_fragment_count",
    "NA",
}

PLACEHOLDERS = {"", "NA", "TO_BE_FILLED", "TO_BE_STANDARDIZED"}
PATHLIKE_PREFIXES = (
    "scripts/",
    "workflow/",
    "config/",
    "data/",
    "external/",
    "results/",
    "benchmark/",
)

FIELDS = [
    "status",
    "tool_id",
    "check",
    "item",
    "details",
]

LIST_FIELDS = [
    "tool_id",
    "display_name",
    "comparison_level",
    "primary_output_type",
    "normalizer",
    "workflow",
    "allowed_claim",
]


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise FileNotFoundError(f"missing comparator registry: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        rows = [
            {
                key: "" if value is None else value
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]

    return list(reader.fieldnames), rows


def split_semicolon(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def is_placeholder(value: str) -> bool:
    return value.strip() in PLACEHOLDERS


def looks_pathlike(value: str) -> bool:
    return value.startswith(PATHLIKE_PREFIXES) or "/" in value


def path_part(value: str) -> str:
    """Extract path from workflow entries like workflow/Snakefile:target."""
    if value.startswith("workflow/") and ":" in value:
        return value.split(":", 1)[0]
    return value


def severity_for_missing_path(path_text: str) -> str:
    if path_text.startswith("external/") or path_text.startswith("data/"):
        return "WARN"
    return "FAIL"


def check_required_columns(fieldnames: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    extra = [column for column in fieldnames if column not in REQUIRED_COLUMNS]

    if missing:
        rows.append(
            qc_row(
                "FAIL",
                "registry",
                "required_columns",
                "missing",
                ";".join(missing),
            )
        )
    else:
        rows.append(qc_row("PASS", "registry", "required_columns", "all", ""))

    if extra:
        rows.append(
            qc_row(
                "WARN",
                "registry",
                "extra_columns",
                "present",
                ";".join(extra),
            )
        )

    return rows


def qc_row(
    status: str,
    tool_id: str,
    check: str,
    item: str,
    details: str,
) -> dict[str, str]:
    return {
        "status": status,
        "tool_id": tool_id,
        "check": check,
        "item": item,
        "details": details,
    }


def check_unique_tool_ids(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: dict[str, int] = {}
    out: list[dict[str, str]] = []

    for row in rows:
        tool_id = row.get("tool_id", "").strip()
        seen[tool_id] = seen.get(tool_id, 0) + 1

    for tool_id, count in sorted(seen.items()):
        if tool_id == "":
            out.append(qc_row("FAIL", "registry", "tool_id", "blank", ""))
        elif count > 1:
            out.append(
                qc_row("FAIL", tool_id, "tool_id", "duplicate", f"count={count}")
            )

    if not any(row["status"] == "FAIL" for row in out):
        out.append(qc_row("PASS", "registry", "tool_id", "unique", ""))

    return out


def check_enum(
    row: dict[str, str],
    column: str,
    allowed: set[str],
) -> dict[str, str]:
    tool_id = row.get("tool_id", "")
    value = row.get(column, "").strip()

    if value in allowed:
        return qc_row("PASS", tool_id, column, value, "")

    return qc_row(
        "FAIL",
        tool_id,
        column,
        value or "blank",
        f"allowed={';'.join(sorted(allowed))}",
    )


def check_required_text(row: dict[str, str], column: str) -> dict[str, str]:
    tool_id = row.get("tool_id", "")
    value = row.get(column, "").strip()

    if value:
        return qc_row("PASS", tool_id, column, "present", "")

    return qc_row("FAIL", tool_id, column, "blank", "")


def check_repo_path(tool_id: str, column: str, value: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []

    if is_placeholder(value):
        if value in {"TO_BE_FILLED", "TO_BE_STANDARDIZED"}:
            out.append(qc_row("WARN", tool_id, column, value, "placeholder"))
        return out

    for raw_part in split_semicolon(value):
        if is_placeholder(raw_part):
            if raw_part in {"TO_BE_FILLED", "TO_BE_STANDARDIZED"}:
                out.append(qc_row("WARN", tool_id, column, raw_part, "placeholder"))
            continue

        path_text = path_part(raw_part)
        if not looks_pathlike(path_text):
            continue

        path = Path(path_text)
        if path.exists():
            out.append(qc_row("PASS", tool_id, column, path_text, ""))
        else:
            out.append(
                qc_row(
                    severity_for_missing_path(path_text),
                    tool_id,
                    column,
                    path_text,
                    "path does not exist in current checkout",
                )
            )

    return out


def check_workflow_entries(row: dict[str, str]) -> list[dict[str, str]]:
    tool_id = row.get("tool_id", "")
    workflow = row.get("workflow", "")
    out: list[dict[str, str]] = []

    if is_placeholder(workflow):
        if workflow in {"TO_BE_FILLED", "TO_BE_STANDARDIZED"}:
            out.append(qc_row("WARN", tool_id, "workflow", workflow, "placeholder"))
        return out

    for entry in split_semicolon(workflow):
        path = path_part(entry)
        if not path.startswith("workflow/"):
            out.append(
                qc_row(
                    "WARN",
                    tool_id,
                    "workflow",
                    entry,
                    "workflow entry does not start with workflow/",
                )
            )
            continue
        if Path(path).exists():
            out.append(qc_row("PASS", tool_id, "workflow", entry, ""))
        else:
            out.append(qc_row("FAIL", tool_id, "workflow", entry, "file missing"))

    return out


def validate(rows: list[dict[str, str]], fieldnames: list[str]) -> list[dict[str, str]]:
    out = check_required_columns(fieldnames)
    out.extend(check_unique_tool_ids(rows))

    if any(row["status"] == "FAIL" for row in out):
        return out

    for row in rows:
        for column in ["tool_id", "display_name", "role", "allowed_claim", "notes"]:
            out.append(check_required_text(row, column))

        out.append(
            check_enum(row, "comparison_level", ALLOWED_COMPARISON_LEVELS)
        )
        out.append(
            check_enum(row, "primary_output_type", ALLOWED_OUTPUT_TYPES)
        )

        for column in [
            "install_target",
            "normalizer",
            "summary_script",
            "required_paths",
        ]:
            out.extend(check_repo_path(row.get("tool_id", ""), column, row.get(column, "")))

        out.extend(check_workflow_entries(row))

    return out


def write_tsv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def print_list(rows: list[dict[str, str]]) -> None:
    writer = csv.DictWriter(sys.stdout, delimiter="\t", fieldnames=LIST_FIELDS)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in LIST_FIELDS})


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("config/comparators.tsv"),
        help="Comparator registry TSV.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("results/processed/comparator_registry_qc.tsv"),
        help="QC output TSV.",
    )
    parser.add_argument("--list", action="store_true", help="Print compact registry.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures.",
    )
    args = parser.parse_args(argv)

    try:
        fieldnames, rows = read_rows(args.registry)
        if args.list:
            print_list(rows)
            return 0

        qc_rows = validate(rows, fieldnames)
        write_tsv(args.out, qc_rows, FIELDS)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    fail_count = sum(1 for row in qc_rows if row["status"] == "FAIL")
    warn_count = sum(1 for row in qc_rows if row["status"] == "WARN")

    print(f"wrote {args.out}", file=sys.stderr)
    print(
        f"comparator registry checks: {fail_count} failure(s), {warn_count} warning(s)",
        file=sys.stderr,
    )

    if fail_count:
        return 2
    if warn_count and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
