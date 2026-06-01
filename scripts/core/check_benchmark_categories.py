#!/usr/bin/env python3
"""Validate and display benchmark category metadata.

The category manifest is static metadata. This script checks that Makefile
targets and Snakemake workflow files referenced by the manifest are present. It
does not require generated benchmark outputs to exist unless --require-outputs
is supplied.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

TARGET_RE = re.compile(r"^([A-Za-z0-9_.-]+)\s*:")

FIELDNAMES = [
    "category_id",
    "check",
    "item",
    "status",
    "details",
]

LIST_COLUMNS = [
    "category_id",
    "claim_tier",
    "scope",
    "make_targets",
    "run_by_default",
]

REQUIRED_COLUMNS = {
    "category_id",
    "claim_tier",
    "scope",
    "make_targets",
    "workflow_entrypoints",
    "required_inputs",
    "primary_outputs",
    "manuscript_artifacts",
    "run_by_default",
    "notes",
}


def split_items(value: str) -> list[str]:
    value = (value or "").strip()
    if value in {"", "NA", "none", "None"}:
        return []
    return [item.strip() for item in value.split(";") if item.strip()]


def read_categories(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing benchmark category manifest: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")

        missing = sorted(REQUIRED_COLUMNS - set(reader.fieldnames))
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")

        return [
            {
                key: "" if value is None else value
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]


def is_target_line(line: str) -> bool:
    if not line or line.startswith((" ", "\t", "#", ".")):
        return False
    if ":=" in line or "?=" in line or "+=" in line:
        return False
    before = line.split(":", 1)[0]
    if "=" in before:
        return False
    return bool(TARGET_RE.match(line))


def read_make_targets(path: Path) -> set[str]:
    if not path.exists():
        raise FileNotFoundError(f"missing Makefile: {path}")

    targets: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if is_target_line(line):
            match = TARGET_RE.match(line)
            if match:
                targets.add(match.group(1))
    return targets


def check_make_targets(
    category: dict[str, str],
    targets: set[str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for target in split_items(category.get("make_targets", "")):
        status = "PASS" if target in targets else "FAIL"
        rows.append(
            {
                "category_id": category["category_id"],
                "check": "make_target",
                "item": target,
                "status": status,
                "details": "" if status == "PASS" else "target not found in Makefile",
            }
        )
    return rows


def check_workflow_entrypoints(category: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for entrypoint in split_items(category.get("workflow_entrypoints", "")):
        if ":" in entrypoint:
            workflow_text, target = entrypoint.split(":", 1)
        else:
            workflow_text, target = entrypoint, ""

        workflow = Path(workflow_text)
        if not workflow.exists():
            rows.append(
                {
                    "category_id": category["category_id"],
                    "check": "workflow_entrypoint",
                    "item": entrypoint,
                    "status": "FAIL",
                    "details": "workflow file not found",
                }
            )
            continue

        if not target:
            rows.append(
                {
                    "category_id": category["category_id"],
                    "check": "workflow_entrypoint",
                    "item": entrypoint,
                    "status": "PASS",
                    "details": "workflow file exists",
                }
            )
            continue

        text = workflow.read_text(encoding="utf-8", errors="replace")
        status = "PASS" if target in text else "WARN"
        rows.append(
            {
                "category_id": category["category_id"],
                "check": "workflow_entrypoint",
                "item": entrypoint,
                "status": status,
                "details": "" if status == "PASS" else "target string not found in workflow",
            }
        )

    return rows


def check_required_inputs(category: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in split_items(category.get("required_inputs", "")):
        path = Path(item)
        if any(char in item for char in "*?[]"):
            status = "PASS"
            details = "glob pattern; existence not checked"
        elif path.exists():
            status = "PASS"
            details = ""
        else:
            status = "WARN"
            details = "input path is absent in this checkout"
        rows.append(
            {
                "category_id": category["category_id"],
                "check": "required_input",
                "item": item,
                "status": status,
                "details": details,
            }
        )
    return rows


def check_outputs(
    category: dict[str, str],
    require_outputs: bool,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not require_outputs:
        return rows

    for field in ["primary_outputs", "manuscript_artifacts"]:
        for item in split_items(category.get(field, "")):
            if any(char in item for char in "*?[]"):
                rows.append(
                    {
                        "category_id": category["category_id"],
                        "check": field,
                        "item": item,
                        "status": "WARN",
                        "details": "glob pattern; existence not checked",
                    }
                )
                continue

            status = "PASS" if Path(item).exists() else "FAIL"
            rows.append(
                {
                    "category_id": category["category_id"],
                    "check": field,
                    "item": item,
                    "status": status,
                    "details": "" if status == "PASS" else "output path missing",
                }
            )
    return rows


def validate_categories(
    categories: list[dict[str, str]],
    makefile: Path,
    require_outputs: bool,
) -> list[dict[str, str]]:
    targets = read_make_targets(makefile)
    rows: list[dict[str, str]] = []

    seen: set[str] = set()
    for category in categories:
        category_id = category.get("category_id", "")
        duplicate = category_id in seen
        seen.add(category_id)

        rows.append(
            {
                "category_id": category_id,
                "check": "category_id",
                "item": category_id,
                "status": "FAIL" if duplicate or not category_id else "PASS",
                "details": "duplicate or empty category_id" if duplicate or not category_id else "",
            }
        )
        rows.extend(check_make_targets(category, targets))
        rows.extend(check_workflow_entrypoints(category))
        rows.extend(check_required_inputs(category))
        rows.extend(check_outputs(category, require_outputs=require_outputs))

    return rows


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def print_list(categories: list[dict[str, str]]) -> None:
    widths = {
        column: max(
            len(column),
            *(len(category.get(column, "")) for category in categories),
        )
        for column in LIST_COLUMNS
    }

    print("  ".join(column.ljust(widths[column]) for column in LIST_COLUMNS))
    print("  ".join("-" * widths[column] for column in LIST_COLUMNS))

    for category in categories:
        print(
            "  ".join(
                category.get(column, "").ljust(widths[column])
                for column in LIST_COLUMNS
            )
        )


def print_summary(rows: list[dict[str, str]]) -> None:
    failures = sum(1 for row in rows if row["status"] == "FAIL")
    warnings = sum(1 for row in rows if row["status"] == "WARN")
    passes = sum(1 for row in rows if row["status"] == "PASS")
    print(
        f"benchmark category checks: PASS={passes} WARN={warnings} FAIL={failures}",
        file=sys.stderr,
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--categories",
        type=Path,
        default=Path("config/benchmark_categories.tsv"),
    )
    parser.add_argument("--makefile", type=Path, default=Path("Makefile"))
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("results/processed/benchmark_category_qc.tsv"),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print a compact category table instead of validating.",
    )
    parser.add_argument(
        "--require-outputs",
        action="store_true",
        help="Also require generated primary and manuscript output paths to exist.",
    )
    args = parser.parse_args(argv)

    try:
        categories = read_categories(args.categories)
        if args.list:
            print_list(categories)
            return 0

        rows = validate_categories(
            categories=categories,
            makefile=args.makefile,
            require_outputs=args.require_outputs,
        )
        write_tsv(args.out, rows)
        print_summary(rows)
        if any(row["status"] == "FAIL" for row in rows):
            return 1
        return 0

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
