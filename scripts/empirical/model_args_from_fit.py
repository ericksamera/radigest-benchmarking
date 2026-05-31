#!/usr/bin/env python3
"""Emit radigest size-model CLI arguments from radigest-fit-size-model output."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def parse_params(params: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in params.split(","):
        item = item.strip()
        if item == "":
            continue
        if "=" not in item:
            raise ValueError(f"cannot parse parameter: {item!r}")
        key, value = item.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fit", required=True, type=Path)
    parser.add_argument("--rank", type=int, default=1)
    args = parser.parse_args(argv)

    try:
        with args.fit.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            rows = list(reader)

        if not rows:
            raise ValueError(f"empty fit table: {args.fit}")

        selected = None
        for row in rows:
            if int(row["rank"]) == args.rank:
                selected = row
                break

        if selected is None:
            raise ValueError(f"rank {args.rank} not found in {args.fit}")

        model = selected["model"]
        params = parse_params(selected.get("params", ""))

        cli = ["-size-model", model]

        if model == "hard":
            pass
        elif model == "normal":
            cli += ["-size-mean", params["size_mean"], "-size-sd", params["size_sd"]]
        elif model == "triangular":
            cli += ["-size-mean", params["size_mean"]]
        elif model == "soft-window":
            cli += ["-size-edge-sd", params["size_edge_sd"]]
        else:
            raise ValueError(f"unsupported model: {model}")

        print(" ".join(cli))

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
