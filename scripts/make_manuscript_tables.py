#!/usr/bin/env python3
"""Build curated manuscript-ready summary tables.

This script consumes already generated result TSVs and writes concise,
reviewer-facing tables under manuscript_tables/. It does not rerun benchmarks.

Large raw data and intermediate outputs remain ignored by Git. Curated final
tables can be tracked explicitly with:

  git add -f manuscript_tables/*.tsv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

MISSING = "MISSING"


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            return []
        return [
            {
                key: "" if value is None else value
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]


def write_tsv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def exists_text(path: str) -> str:
    return "present" if Path(path).exists() else MISSING


def first_existing(paths: list[str]) -> str:
    for path in paths:
        if Path(path).exists():
            return path
    return ""


def table_interval_comparisons(out_dir: Path) -> None:
    rows: list[dict[str, str]] = []

    sources = [
        (
            "Digital_RADs.py",
            "results/processed/comparisons/digital_rads/"
            "digital_rads_smoke_single__D1.summary.tsv",
            "synthetic/smoke",
            "exact normalized interval comparison",
            (
                "Digital_RADs.py motif-bounded output normalized to "
                "cut-to-cut intervals"
            ),
        ),
        (
            "DDRADSEQTOOLS rsitesearch.py",
            "results/processed/comparisons/ddradseqtools/"
            "yeast_B1.interval_compare.summary.tsv",
            "yeast_small_plain B1",
            "exact normalized interval comparison",
            (
                "rsitesearch.py FASTA header coordinates normalized with "
                "enzyme cut offsets and first-token sequence identifiers"
            ),
        ),
    ]

    for tool, source, dataset_condition, comparison_scope, notes in sources:
        data = read_tsv(Path(source))
        if data:
            row = data[0]
            status = row.get("status", "")
            first_intervals = row.get("first_intervals", "")
            second_intervals = row.get("second_intervals", "")
            matching = row.get("matching_intervals", "")
            jaccard = row.get("jaccard", "")
        else:
            status = MISSING
            first_intervals = ""
            second_intervals = ""
            matching = ""
            jaccard = ""

        rows.append(
            {
                "tool": tool,
                "dataset_condition": dataset_condition,
                "comparison_scope": comparison_scope,
                "radigest_intervals": first_intervals,
                "tool_intervals": second_intervals,
                "matching_intervals": matching,
                "jaccard": jaccard,
                "status": status,
                "source": source,
                "notes": notes,
            }
        )

    write_tsv(
        out_dir / "table_03_interval_comparisons.tsv",
        rows,
        [
            "tool",
            "dataset_condition",
            "comparison_scope",
            "radigest_intervals",
            "tool_intervals",
            "matching_intervals",
            "jaccard",
            "status",
            "source",
            "notes",
        ],
    )


def table_tool_timing(out_dir: Path) -> None:
    source = Path("results/tables/tool_timing_interpretation.tsv")
    rows = read_tsv(source)

    fields = [
        "dataset",
        "condition",
        "tool",
        "task",
        "timing_scope",
        "output_object",
        "n_runs",
        "median_elapsed_wall_seconds",
        "q1_elapsed_wall_seconds",
        "q3_elapsed_wall_seconds",
        "median_max_rss_kb",
        "process_max_rss_kb",
        "median_fragments",
        "median_bases",
        "notes",
    ]

    curated = [{field: row.get(field, "") for field in fields} for row in rows]
    write_tsv(out_dir / "table_04_matched_timing.tsv", curated, fields)


def table_screening_speed(out_dir: Path) -> None:
    source = Path("results/tables/screening_speed_summary.tsv")
    rows = read_tsv(source)

    fields = [
        "dataset",
        "tool",
        "task",
        "n_runs",
        "candidate_pairs",
        "median_completed_pairs",
        "median_elapsed_wall_seconds",
        "q1_elapsed_wall_seconds",
        "q3_elapsed_wall_seconds",
        "median_max_rss_kb",
        "median_pairs_per_second",
        "notes",
    ]

    curated = [{field: row.get(field, "") for field in fields} for row in rows]
    write_tsv(out_dir / "table_05_screening_speed.tsv", curated, fields)


def table_input_format(out_dir: Path) -> None:
    source = Path("results/tables/radigest_input_format_comparison.tsv")
    rows = read_tsv(source)

    if not rows:
        write_tsv(
            out_dir / "table_06_input_format.tsv",
            [
                {
                    "status": MISSING,
                    "source": str(source),
                    "notes": "Input-format comparison table not found.",
                }
            ],
            ["status", "source", "notes"],
        )
        return

    fields = list(rows[0].keys())
    write_tsv(out_dir / "table_06_input_format.tsv", rows, fields)


def table_thread_scaling(out_dir: Path) -> None:
    source = Path("results/tables/radigest_thread_scaling_summary.tsv")
    rows = read_tsv(source)

    fields = [
        "dataset",
        "condition",
        "mode",
        "threads",
        "n_runs",
        "median_elapsed_wall_seconds",
        "q1_elapsed_wall_seconds",
        "q3_elapsed_wall_seconds",
        "median_max_rss_kb",
        "median_total_fragments",
        "median_total_bases",
        "speedup_vs_threads1",
        "parallel_efficiency_vs_threads1",
        "notes",
    ]

    curated = [{field: row.get(field, "") for field in fields} for row in rows]
    write_tsv(out_dir / "table_s02_radigest_thread_scaling.tsv", curated, fields)


def table_pair_screen_scaling(out_dir: Path) -> None:
    source = Path("results/tables/pair_screen_scaling_summary.tsv")
    rows = read_tsv(source)

    fields = [
        "dataset",
        "jobs",
        "n_runs",
        "median_elapsed_wall_seconds",
        "q1_elapsed_wall_seconds",
        "q3_elapsed_wall_seconds",
        "median_max_rss_kb",
        "median_completed_pairs",
        "median_pairs_per_second",
        "speedup_vs_jobs1",
        "parallel_efficiency_vs_jobs1",
        "notes",
    ]

    curated = [{field: row.get(field, "") for field in fields} for row in rows]
    write_tsv(out_dir / "table_s03_pair_screen_job_scaling.tsv", curated, fields)


def table_mismatch_explanations(out_dir: Path) -> None:
    rows = [
        {
            "tool_or_analysis": "SimRAD",
            "comparison_level": "count-level only",
            "issue": "SimRAD does not expose radigest-style genomic intervals.",
            "resolution": (
                "Report aggregate fragment/locus counts and bases separately; "
                "do not use for coordinate-level claims."
            ),
        },
        {
            "tool_or_analysis": "Digital_RADs.py",
            "comparison_level": "interval after normalization",
            "issue": (
                "Raw output is motif-bounded rather than "
                "cut-coordinate interval output."
            ),
            "resolution": (
                "Normalize Digital_RADs.py output to zero-based half-open "
                "cut-coordinate intervals using enzyme cut offsets."
            ),
        },
        {
            "tool_or_analysis": "DDRADSEQTOOLS rsitesearch.py",
            "comparison_level": "interval after normalization",
            "issue": (
                "Raw FASTA records include restriction-site residual sequence, "
                "and locus identifiers preserve the full FASTA defline."
            ),
            "resolution": (
                "Normalize header coordinates using cut offsets and canonicalize "
                "sequence IDs to first FASTA defline token."
            ),
        },
        {
            "tool_or_analysis": "ddgRADer backend",
            "comparison_level": "binned screening throughput",
            "issue": (
                "Backend reports binned fragment distributions, "
                "not native intervals."
            ),
            "resolution": (
                "Use as binned screening/speed comparator only; do not claim "
                "coordinate equivalence."
            ),
        },
        {
            "tool_or_analysis": "radigest single-digest thread scaling",
            "comparison_level": "radigest-only performance",
            "issue": (
                "Single digest jobs on Cannabis did not show consistent speedup "
                "with additional per-digest threads."
            ),
            "resolution": (
                "Report measured wall time/RSS and invariant fragment totals; "
                "do not claim linear per-digest scaling."
            ),
        },
        {
            "tool_or_analysis": "radigest-screen-pairs job scaling",
            "comparison_level": "radigest-only screening throughput",
            "issue": (
                "Job-level parallelism improves throughput, but returns diminish "
                "at high job counts."
            ),
            "resolution": (
                "Report observed speedup and parallel efficiency with Q1-Q3; "
                "do not claim linear scaling beyond supported results."
            ),
        },
    ]

    write_tsv(
        out_dir / "table_07_mismatch_explanations.tsv",
        rows,
        ["tool_or_analysis", "comparison_level", "issue", "resolution"],
    )


def table_environment_data(out_dir: Path) -> None:
    fields = ["section", "item", "value", "source", "notes"]
    rows: list[dict[str, str]] = []

    env_path = Path("results/processed/environment.txt")
    checksums_path = Path("results/processed/reference_checksums.tsv")

    rows.append(
        {
            "section": "environment",
            "item": "environment_metadata",
            "value": exists_text(str(env_path)),
            "source": str(env_path),
            "notes": (
                "Captured hardware, OS, software, and git metadata. "
                "See full environment text for details."
            ),
        }
    )

    rows.append(
        {
            "section": "reference_data",
            "item": "reference_checksums",
            "value": exists_text(str(checksums_path)),
            "source": str(checksums_path),
            "notes": "Reference-data checksum table.",
        }
    )

    for row in read_tsv(checksums_path):
        dataset = row.get("dataset") or row.get("dataset_id") or row.get("id") or ""
        status = row.get("status", "")
        expected = row.get("expected_sha256", "")
        observed = row.get("observed_sha256", "")
        local_path = row.get("local_path", "")

        value = (
            f"status={status}; "
            f"expected_sha256={expected}; "
            f"observed_sha256={observed}"
        )

        rows.append(
            {
                "section": "reference_checksum",
                "item": dataset,
                "value": value,
                "source": str(checksums_path),
                "notes": local_path,
            }
        )

    write_tsv(out_dir / "table_s01_environment.tsv", rows, fields)


def claim_audit(out_dir: Path) -> None:
    claims = [
        {
            "claim_id": "C01",
            "manuscript_section": "Methods validation",
            "claim": "Synthetic digest and coordinate cases were validated.",
            "required_output": "results/processed/synthetic_validation_results.tsv",
            "status": exists_text("results/processed/synthetic_validation_results.tsv"),
            "manuscript_artifact": "table_02_synthetic_validation.tsv",
            "notes": "Use exact pass/fail summary, not inferred counts.",
        },
        {
            "claim_id": "C02",
            "manuscript_section": "Matched comparisons",
            "claim": "Digital_RADs.py matched radigest on normalized interval output.",
            "required_output": (
                "results/processed/comparisons/digital_rads/"
                "digital_rads_smoke_single__D1.summary.tsv"
            ),
            "status": exists_text(
                "results/processed/comparisons/digital_rads/"
                "digital_rads_smoke_single__D1.summary.tsv"
            ),
            "manuscript_artifact": "table_03_interval_comparisons.tsv",
            "notes": "Only valid after motif-boundary normalization.",
        },
        {
            "claim_id": "C03",
            "manuscript_section": "Matched comparisons",
            "claim": (
                "DDRADSEQTOOLS rsitesearch.py matched radigest after coordinate "
                "and seqid normalization."
            ),
            "required_output": (
                "results/processed/comparisons/ddradseqtools/"
                "yeast_B1.interval_compare.summary.tsv"
            ),
            "status": exists_text(
                "results/processed/comparisons/ddradseqtools/"
                "yeast_B1.interval_compare.summary.tsv"
            ),
            "manuscript_artifact": "table_03_interval_comparisons.tsv",
            "notes": "Only rsitesearch.py is in scope.",
        },
        {
            "claim_id": "C04",
            "manuscript_section": "Runtime/memory",
            "claim": "Matched digest-task timing was measured under defined scopes.",
            "required_output": "results/tables/tool_timing_interpretation.tsv",
            "status": exists_text("results/tables/tool_timing_interpretation.tsv"),
            "manuscript_artifact": "table_04_matched_timing.tsv",
            "notes": "Cold command and warm-session timings must remain separate.",
        },
        {
            "claim_id": "C05",
            "manuscript_section": "Screening",
            "claim": (
                "ddgRADer backend and radigest screening throughput " "were measured."
            ),
            "required_output": "results/tables/screening_speed_summary.tsv",
            "status": exists_text("results/tables/screening_speed_summary.tsv"),
            "manuscript_artifact": "table_05_screening_speed.tsv",
            "notes": (
                "ddgRADer is binned screening comparator, " "not interval comparator."
            ),
        },
        {
            "claim_id": "C06",
            "manuscript_section": "Input format",
            "claim": "Plain and gzipped FASTA input effects were measured.",
            "required_output": "results/tables/radigest_input_format_comparison.tsv",
            "status": exists_text(
                "results/tables/radigest_input_format_comparison.tsv"
            ),
            "manuscript_artifact": "table_06_input_format.tsv",
            "notes": "Use only as input-format control, not general performance claim.",
        },
        {
            "claim_id": "C07",
            "manuscript_section": "Scaling",
            "claim": "Cannabis moderate-genome radigest runtime/RSS were measured.",
            "required_output": "results/tables/radigest_thread_scaling_summary.tsv",
            "status": exists_text("results/tables/radigest_thread_scaling_summary.tsv"),
            "manuscript_artifact": "table_s02_radigest_thread_scaling.tsv",
            "notes": "Do not claim per-digest linear scaling.",
        },
        {
            "claim_id": "C08",
            "manuscript_section": "Scaling",
            "claim": "Pair-screening job-level scaling was measured on Cannabis.",
            "required_output": "results/tables/pair_screen_scaling_summary.tsv",
            "status": exists_text("results/tables/pair_screen_scaling_summary.tsv"),
            "manuscript_artifact": "table_s03_pair_screen_job_scaling.tsv",
            "notes": "Report observed speedup and efficiency.",
        },
        {
            "claim_id": "C09",
            "manuscript_section": "Reproducibility",
            "claim": "Environment metadata were captured.",
            "required_output": "results/processed/environment.txt",
            "status": exists_text("results/processed/environment.txt"),
            "manuscript_artifact": "table_s01_environment.tsv",
            "notes": "Include OS, CPU, memory, tool versions, and git status.",
        },
        {
            "claim_id": "C10",
            "manuscript_section": "Data",
            "claim": "Reference-data checksums were recorded.",
            "required_output": "results/processed/reference_checksums.tsv",
            "status": exists_text("results/processed/reference_checksums.tsv"),
            "manuscript_artifact": "table_s01_environment.tsv",
            "notes": "Large FASTA files should not be tracked in Git.",
        },
        {
            "claim_id": "C11",
            "manuscript_section": "Empirical recovery",
            "claim": (
                "Sockeye ddRAD insert-length recovery was modelled "
                "from observed TLENs."
            ),
            "required_output": (
                "results/tables/sockeye_ddrad.empirical_recovery_summary.tsv"
            ),
            "status": exists_text(
                "results/tables/sockeye_ddrad.empirical_recovery_summary.tsv"
            ),
            "manuscript_artifact": "table_08_empirical_recovery.tsv",
            "notes": (
                "Use as empirical recovery model validation; "
                "do not claim exact locus recovery."
            ),
        },
        {
            "claim_id": "C12",
            "manuscript_section": "Empirical recovery",
            "claim": (
                "Trichoderma ddRAD insert-length recovery was modelled "
                "from observed TLENs."
            ),
            "required_output": (
                "results/tables/trichoderma_ddrad.empirical_recovery_summary.tsv"
            ),
            "status": exists_text(
                "results/tables/trichoderma_ddrad.empirical_recovery_summary.tsv"
            ),
            "manuscript_artifact": "table_08_empirical_recovery.tsv",
            "notes": (
                "Second empirical dataset with a different taxon "
                "and enzyme pair."
            ),
        },
        {
            "claim_id": "C13",
            "manuscript_section": "Empirical recovery",
            "claim": (
                "Empirical recovery model choice was stable under "
                "per-sample TLEN downsampling."
            ),
            "required_output": (
                "results/tables/empirical_recovery_model_sensitivity.tsv"
            ),
            "status": exists_text(
                "results/tables/empirical_recovery_model_sensitivity.tsv"
            ),
            "manuscript_artifact": (
                "table_s04_empirical_recovery_sensitivity.tsv"
            ),
            "notes": (
                "Robustness check against high-depth samples dominating "
                "pooled TLENs."
            ),
        },
    ]

    write_tsv(
        out_dir / "claim_audit.tsv",
        claims,
        [
            "claim_id",
            "manuscript_section",
            "claim",
            "required_output",
            "status",
            "manuscript_artifact",
            "notes",
        ],
    )


def synthetic_validation_table(out_dir: Path) -> None:
    source = Path("results/processed/synthetic_validation_results.tsv")
    rows = read_tsv(source)

    if not rows:
        write_tsv(
            out_dir / "table_02_synthetic_validation.tsv",
            [
                {
                    "status": MISSING,
                    "source": str(source),
                    "notes": "Synthetic validation summary not found.",
                }
            ],
            ["status", "source", "notes"],
        )
        return

    write_tsv(out_dir / "table_02_synthetic_validation.tsv", rows, list(rows[0].keys()))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=Path("manuscript_tables"))
    args = parser.parse_args(argv)

    try:
        out_dir = args.out_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        synthetic_validation_table(out_dir)
        table_interval_comparisons(out_dir)
        table_tool_timing(out_dir)
        table_screening_speed(out_dir)
        table_input_format(out_dir)
        table_thread_scaling(out_dir)
        table_pair_screen_scaling(out_dir)
        table_mismatch_explanations(out_dir)
        table_environment_data(out_dir)
        claim_audit(out_dir)

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote manuscript tables to {args.out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
