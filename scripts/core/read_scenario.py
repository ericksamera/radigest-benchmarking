#!/usr/bin/env python3
"""Read and validate key/value scenario manifests.

Scenario manifests live under config/scenarios/*.tsv and have columns:

  scenario_id  parameter  value  description

The script is intentionally small because Make uses it to populate default
variables at parse time.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

REQUIRED_COLUMNS = ["scenario_id", "parameter", "value", "description"]
QC_FIELDS = ["status", "scenario_id", "parameter", "value", "reason"]


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing scenario manifest: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        missing = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
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


def scenario_map(rows: list[dict[str, str]], scenario_id: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in rows:
        if row.get("scenario_id", "") != scenario_id:
            continue
        key = row.get("parameter", "")
        value = row.get("value", "")
        if key:
            out[key] = value
    return out


def validate(rows: list[dict[str, str]], scenario_id: str) -> list[dict[str, str]]:
    qc: list[dict[str, str]] = []
    seen: dict[tuple[str, str], list[str]] = defaultdict(list)

    for row in rows:
        sid = row.get("scenario_id", "")
        parameter = row.get("parameter", "")
        value = row.get("value", "")
        description = row.get("description", "")
        if scenario_id and sid != scenario_id:
            continue

        if not sid:
            qc.append(
                {
                    "status": "FAIL",
                    "scenario_id": sid,
                    "parameter": parameter,
                    "value": value,
                    "reason": "blank scenario_id",
                }
            )
            continue

        if not parameter:
            qc.append(
                {
                    "status": "FAIL",
                    "scenario_id": sid,
                    "parameter": parameter,
                    "value": value,
                    "reason": "blank parameter",
                }
            )
            continue

        seen[(sid, parameter)].append(value)

        if value == "":
            qc.append(
                {
                    "status": "FAIL",
                    "scenario_id": sid,
                    "parameter": parameter,
                    "value": value,
                    "reason": "blank value",
                }
            )
        elif not description:
            qc.append(
                {
                    "status": "WARN",
                    "scenario_id": sid,
                    "parameter": parameter,
                    "value": value,
                    "reason": "blank description",
                }
            )
        else:
            qc.append(
                {
                    "status": "PASS",
                    "scenario_id": sid,
                    "parameter": parameter,
                    "value": value,
                    "reason": "",
                }
            )

    for (sid, parameter), values in sorted(seen.items()):
        if len(values) > 1:
            qc.append(
                {
                    "status": "FAIL",
                    "scenario_id": sid,
                    "parameter": parameter,
                    "value": ";".join(values),
                    "reason": "duplicate scenario parameter",
                }
            )

    if scenario_id and not any(row.get("scenario_id") == scenario_id for row in rows):
        qc.append(
            {
                "status": "FAIL",
                "scenario_id": scenario_id,
                "parameter": "",
                "value": "",
                "reason": "scenario_id not found",
            }
        )

    return qc


def parse_make_fragment(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"missing scenario makefile fragment: {path}")

    out: dict[str, str] = {}
    pattern = re.compile(r"^([A-Za-z0-9_]+)\s*\?=\s*(.*)$")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = pattern.match(line)
        if match:
            out[match.group(1)] = match.group(2)
    return out


def add_make_fragment_qc(
    qc: list[dict[str, str]],
    rows: list[dict[str, str]],
    scenario_id: str,
    fragment: Path | None,
) -> None:
    if fragment is None:
        return

    try:
        values = parse_make_fragment(fragment)
    except Exception as exc:
        qc.append(
            {
                "status": "FAIL",
                "scenario_id": scenario_id,
                "parameter": "",
                "value": str(fragment),
                "reason": f"could not parse makefile fragment: {exc}",
            }
        )
        return

    for row in rows:
        if scenario_id and row.get("scenario_id", "") != scenario_id:
            continue
        parameter = row.get("parameter", "")
        expected = row.get("value", "")
        if not parameter:
            continue
        make_name = parameter.upper()
        observed = values.get(make_name)
        if observed is None:
            qc.append(
                {
                    "status": "FAIL",
                    "scenario_id": row.get("scenario_id", ""),
                    "parameter": parameter,
                    "value": expected,
                    "reason": f"missing {make_name} in {fragment}",
                }
            )
        elif observed != expected:
            qc.append(
                {
                    "status": "FAIL",
                    "scenario_id": row.get("scenario_id", ""),
                    "parameter": parameter,
                    "value": observed,
                    "reason": f"makefile fragment differs from TSV value {expected!r}",
                }
            )
        else:
            qc.append(
                {
                    "status": "PASS",
                    "scenario_id": row.get("scenario_id", ""),
                    "parameter": parameter,
                    "value": observed,
                    "reason": "makefile fragment synchronized",
                }
            )


def write_tsv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def print_table(rows: list[dict[str, str]], scenario_id: str) -> None:
    print("scenario_id\tparameter\tvalue\tdescription")
    for row in rows:
        if scenario_id and row.get("scenario_id", "") != scenario_id:
            continue
        print(
            "\t".join(
                [
                    row.get("scenario_id", ""),
                    row.get("parameter", ""),
                    row.get("value", ""),
                    row.get("description", ""),
                ]
            )
        )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--scenario", default="nonempirical")
    parser.add_argument("--key", default="")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--makefile-fragment", type=Path, default=None)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)

    try:
        rows = read_rows(args.manifest)

        if args.key:
            values = scenario_map(rows, args.scenario)
            if args.key not in values:
                print(
                    f"error: scenario {args.scenario!r} has no parameter {args.key!r}",
                    file=sys.stderr,
                )
                return 2
            print(values[args.key])
            return 0

        if args.list:
            print_table(rows, args.scenario)
            return 0

        qc = validate(rows, args.scenario)
        add_make_fragment_qc(qc, rows, args.scenario, args.makefile_fragment)
        if args.out is not None:
            write_tsv(args.out, qc, QC_FIELDS)
        else:
            writer = csv.DictWriter(sys.stdout, delimiter="\t", fieldnames=QC_FIELDS)
            writer.writeheader()
            writer.writerows(qc)

        has_fail = any(row["status"] == "FAIL" for row in qc)
        has_warn = any(row["status"] == "WARN" for row in qc)
        if has_fail:
            return 2
        if has_warn and args.strict:
            return 1
        return 0

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
