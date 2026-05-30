#!/usr/bin/env python3
"""Run ddgRADer / ddRadSeqWebTool backend digestion without the web UI.

This wrapper imports the ddgRADer backend code and writes binned fragment-count
tables. It does not start the web server and does not attempt coordinate-level
comparison.

Output object:
  binned fragment counts by enzyme pair.

Fair use:
  screening-style fragment-size distribution comparison.

Unfair use:
  coordinate-resolved interval comparison against radigest.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import os
import shutil
import subprocess
import sys
import tempfile
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd

BIN_COLUMNS = [
    "enzyme_pair",
    "bin_lower",
    "bin_upper",
    "fragment_count",
]

SUMMARY_COLUMNS = [
    "tool",
    "reference",
    "enzyme_pair",
    "min_size",
    "max_size",
    "total_binned_fragments_0_1010",
    "binned_fragments_in_window",
    "approx_bases_in_window",
    "raw_csv",
    "bins_tsv",
    "version_log",
    "notes",
]


def parse_pairs(text: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []

    for item in text.split(";"):
        item = item.strip()
        if not item:
            continue

        parts = [x.strip() for x in item.replace("+", ",").split(",") if x.strip()]
        if len(parts) != 2:
            raise ValueError(
                f"invalid enzyme pair {item!r}; expected 'EcoRI,MseI' or "
                "'EcoRI+MseI'"
            )
        pairs.append((parts[0], parts[1]))

    if not pairs:
        raise ValueError("no enzyme pairs were supplied")

    return pairs


def find_ddgrader_project_root(repo: Path) -> Path:
    """Find the directory containing the ddgRADer top-level backend package."""
    repo = repo.resolve()

    candidates = [
        repo,
        repo / "ddRadSeqWebTool",
        repo / "ddgrader",
    ]

    for candidate in candidates:
        if (
            (candidate / "backend" / "__init__.py").exists()
            and (candidate / "backend" / "service" / "DigestSequence.py").exists()
            and (
                candidate
                / "resources"
                / "restrictionEnzymes"
                / "newEnglandEnzymeList.csv"
            ).exists()
        ):
            return candidate

    for candidate in repo.rglob("backend/__init__.py"):
        root = candidate.parent.parent
        if (root / "backend" / "service" / "DigestSequence.py").exists() and (
            root / "resources" / "restrictionEnzymes" / "newEnglandEnzymeList.csv"
        ).exists():
            return root

    checked = "\n".join(str(x) for x in candidates)
    raise FileNotFoundError(
        "could not locate ddgRADer project root. Expected a directory with "
        "backend/__init__.py, backend/service/DigestSequence.py, and "
        "resources/restrictionEnzymes/newEnglandEnzymeList.csv. Checked:\n"
        f"{checked}"
    )


def safe_reference_copy(reference: Path, tmpdir: Path) -> Path:
    """Copy/decompress reference to a temporary plain FASTA.

    ddgRADer error paths may remove the input FASTA. This function prevents the
    original reference from being touched by giving ddgRADer a scratch copy.
    """
    if not reference.exists():
        raise FileNotFoundError(f"missing reference FASTA: {reference}")

    out = tmpdir / "input.fa"

    if str(reference).endswith(".gz"):
        with gzip.open(reference, "rt", encoding="utf-8", errors="replace") as inp:
            with out.open("w", encoding="utf-8") as handle:
                shutil.copyfileobj(inp, handle)
    else:
        shutil.copyfile(reference, out)

    return out


def git_commit(repo: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "NA"


def import_ddgrader(repo: Path) -> tuple[Path, dict[str, Any]]:
    """Import ddgRADer backend modules.

    ddgRADer imports modules as backend.*. Therefore the project root must be on
    sys.path, not only the wrapper repository root.
    """
    project_root = find_ddgrader_project_root(repo)

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # ddgRADer uses project-relative resource paths. Change to the project root
    # after all CLI paths have been resolved by main().
    os.chdir(project_root)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

    try:
        from backend.controller.ddRadtoolController import collectRestrictionEnzymePairs
        from backend.service.DoubleDigestedDnaComparison import (
            DoubleDigestedDnaComparison,
        )
        from backend.service.ExtractRestrictionEnzymes import (
            getRestrictionEnzymeObjectByName,
        )
        from backend.service.HandleFastafile import countFragmentLengthOfInputFasta
        from backend.settings import (
            BINNING_STEPS,
            FIRST_BINNING_LIMIT,
            MAX_BINNING_LIMIT,
        )
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            f"{exc}. ddgRADer project_root={project_root}; "
            f"sys.path[0]={sys.path[0]}"
        ) from exc

    return project_root, {
        "collectRestrictionEnzymePairs": collectRestrictionEnzymePairs,
        "DoubleDigestedDnaComparison": DoubleDigestedDnaComparison,
        "getRestrictionEnzymeObjectByName": getRestrictionEnzymeObjectByName,
        "countFragmentLengthOfInputFasta": countFragmentLengthOfInputFasta,
        "BINNING_STEPS": BINNING_STEPS,
        "FIRST_BINNING_LIMIT": FIRST_BINNING_LIMIT,
        "MAX_BINNING_LIMIT": MAX_BINNING_LIMIT,
    }


def dataframe_to_long_bins(csv_text: str) -> pd.DataFrame:
    df = pd.read_csv(StringIO(csv_text))

    first_col = df.columns[0]
    df = df.rename(columns={first_col: "bin_upper"})
    df["bin_upper"] = pd.to_numeric(df["bin_upper"], errors="raise").astype(int)

    long_df = df.melt(
        id_vars=["bin_upper"],
        var_name="enzyme_pair",
        value_name="fragment_count",
    )
    long_df["fragment_count"] = (
        pd.to_numeric(long_df["fragment_count"], errors="coerce").fillna(0).astype(int)
    )

    long_df["bin_lower"] = long_df["bin_upper"] - 10
    long_df.loc[long_df["bin_lower"] < 0, "bin_lower"] = 0

    return long_df[["enzyme_pair", "bin_lower", "bin_upper", "fragment_count"]]


def write_summary(
    long_df: pd.DataFrame,
    reference: Path,
    min_size: int,
    max_size: int,
    raw_csv: Path,
    bins_tsv: Path,
    version_log: Path,
    out_summary: Path,
) -> None:
    rows: list[dict[str, str]] = []

    for enzyme_pair, group in long_df.groupby("enzyme_pair", sort=True):
        in_window = group[
            (group["bin_upper"] >= min_size) & (group["bin_upper"] <= max_size)
        ]
        total_fragments = int(group["fragment_count"].sum())
        window_fragments = int(in_window["fragment_count"].sum())
        approx_bases = int((in_window["fragment_count"] * in_window["bin_upper"]).sum())

        rows.append(
            {
                "tool": "ddgRADer_backend",
                "reference": str(reference),
                "enzyme_pair": str(enzyme_pair),
                "min_size": str(min_size),
                "max_size": str(max_size),
                "total_binned_fragments_0_1010": str(total_fragments),
                "binned_fragments_in_window": str(window_fragments),
                "approx_bases_in_window": str(approx_bases),
                "raw_csv": str(raw_csv),
                "bins_tsv": str(bins_tsv),
                "version_log": str(version_log),
                "notes": (
                    "Binned ddgRADer backend counts; bin_upper is used for "
                    "approximate in-window base totals. Not coordinate-level output."
                ),
            }
        )

    out_summary.parent.mkdir(parents=True, exist_ok=True)
    with out_summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument(
        "--enzyme-pairs",
        required=True,
        help="Semicolon-separated pairs, e.g. 'EcoRI,MseI;PstI,MspI'",
    )
    parser.add_argument("--min", dest="min_size", required=True, type=int)
    parser.add_argument("--max", dest="max_size", required=True, type=int)
    parser.add_argument("--out-raw-csv", required=True, type=Path)
    parser.add_argument("--out-bins", required=True, type=Path)
    parser.add_argument("--out-summary", required=True, type=Path)
    parser.add_argument("--version-log", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        if args.min_size > args.max_size:
            raise ValueError("--min must be <= --max")

        # Resolve before changing into the ddgRADer project root.
        args.repo = args.repo.resolve()
        args.reference = args.reference.resolve()
        args.out_raw_csv = args.out_raw_csv.resolve()
        args.out_bins = args.out_bins.resolve()
        args.out_summary = args.out_summary.resolve()
        args.version_log = args.version_log.resolve()

        project_root, modules = import_ddgrader(args.repo)

        pair_names = parse_pairs(args.enzyme_pairs)
        get_enzyme = modules["getRestrictionEnzymeObjectByName"]

        restriction_pairs = [
            (get_enzyme(enzyme1), get_enzyme(enzyme2))
            for enzyme1, enzyme2 in pair_names
        ]

        pair_labels = modules["collectRestrictionEnzymePairs"](restriction_pairs)

        first = int(modules["FIRST_BINNING_LIMIT"])
        step = int(modules["BINNING_STEPS"])
        max_limit = int(modules["MAX_BINNING_LIMIT"])

        import numpy as np

        binning_sizes = np.append(
            np.arange(first, max_limit + step, step),
            max_limit + step,
        )

        comparison = modules["DoubleDigestedDnaComparison"](
            None,
            None,
            None,
            None,
        )
        comparison.createEmptyDataFrame(pair_labels, binning_sizes)

        with tempfile.TemporaryDirectory(prefix="ddgrader_") as tmp:
            tmp_ref = safe_reference_copy(args.reference, Path(tmp))
            modules["countFragmentLengthOfInputFasta"](
                str(tmp_ref),
                restriction_pairs,
                comparison,
            )

        csv_text = comparison.getFragmentsOfEnzymesCsv()
        if csv_text is None:
            raise ValueError("ddgRADer backend returned no fragment table")

        args.out_raw_csv.parent.mkdir(parents=True, exist_ok=True)
        args.out_raw_csv.write_text(csv_text, encoding="utf-8")

        long_df = dataframe_to_long_bins(csv_text)
        args.out_bins.parent.mkdir(parents=True, exist_ok=True)
        long_df.to_csv(args.out_bins, sep="\t", index=False)

        write_summary(
            long_df=long_df,
            reference=args.reference,
            min_size=args.min_size,
            max_size=args.max_size,
            raw_csv=args.out_raw_csv,
            bins_tsv=args.out_bins,
            version_log=args.version_log,
            out_summary=args.out_summary,
        )

        args.version_log.parent.mkdir(parents=True, exist_ok=True)
        args.version_log.write_text(
            "\n".join(
                [
                    f"repo={args.repo}",
                    f"project_root={project_root}",
                    f"git_commit={git_commit(project_root)}",
                    f"reference={args.reference}",
                    f"enzyme_pairs={args.enzyme_pairs}",
                    f"min_size={args.min_size}",
                    f"max_size={args.max_size}",
                    "tool_scope=binned fragment distribution; not coordinate output",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {args.out_raw_csv}", file=sys.stderr)
    print(f"wrote {args.out_bins}", file=sys.stderr)
    print(f"wrote {args.out_summary}", file=sys.stderr)
    print(f"wrote {args.version_log}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
