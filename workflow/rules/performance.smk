# Stage 5a performance rules.
# This module starts with radigest input-format timing only. Later Stage 5
# patches should add screening_speed, thread_scaling, pair_screen_scaling, and
# large_genome outputs to PERFORMANCE_ALL_OUTPUTS.

import csv

PERFORMANCE_CASE_MANIFEST = "config/performance_cases.tsv"
PERFORMANCE_INPUT_FORMAT_SUMMARY = (
    "results/performance/input_format/radigest_input_format_comparison.tsv"
)
PERFORMANCE_INPUT_FORMAT_TABLE = "results/manuscript/tables/table_06_input_format.tsv"


def _read_performance_rows(path):
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = [
            row
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]
    if not rows:
        raise ValueError(f"{path}: no rows")
    return rows


PERFORMANCE_CASE_ROWS = _read_performance_rows(PERFORMANCE_CASE_MANIFEST)
PERFORMANCE_CASE_BY_ID = {row["case_id"]: row for row in PERFORMANCE_CASE_ROWS}
PERFORMANCE_INPUT_FORMAT_CASES = [
    row["case_id"]
    for row in PERFORMANCE_CASE_ROWS
    if row["category"] == "input_format"
    and row.get("required_for_nonempirical", "false").lower() == "true"
]
PERFORMANCE_INPUT_FORMAT_RUN_OUTPUTS = [
    f"results/performance/input_format/raw/{case_id}.runs.tsv"
    for case_id in PERFORMANCE_INPUT_FORMAT_CASES
]
PERFORMANCE_INPUT_FORMAT_OUTPUTS = [
    PERFORMANCE_INPUT_FORMAT_SUMMARY,
    PERFORMANCE_INPUT_FORMAT_TABLE,
]
PERFORMANCE_ALL_OUTPUTS = PERFORMANCE_INPUT_FORMAT_OUTPUTS


def performance_case(case_id):
    try:
        return PERFORMANCE_CASE_BY_ID[case_id]
    except KeyError as exc:
        raise ValueError(f"unknown performance case_id: {case_id}") from exc


def performance_reference(wc):
    return performance_case(wc.case_id)["reference_path"]


def performance_value(wc, column):
    return performance_case(wc.case_id)[column]


def performance_enzymes(wc):
    row = performance_case(wc.case_id)
    enzyme2 = row["enzyme_2"]
    if enzyme2 in {"", "NA", "none", "None"}:
        return row["enzyme_1"]
    return f"{row['enzyme_1']},{enzyme2}"


def performance_min_size(wc):
    return int(performance_case(wc.case_id)["min_size"])


def performance_max_size(wc):
    return int(performance_case(wc.case_id)["max_size"])


def performance_threads(wc):
    return int(performance_case(wc.case_id)["threads"])


def performance_runs(wc):
    return int(performance_case(wc.case_id)["runs"])


rule performance_all:
    input:
        PERFORMANCE_ALL_OUTPUTS


rule performance_input_format_all:
    input:
        PERFORMANCE_INPUT_FORMAT_OUTPUTS


rule run_radigest_input_format_case:
    input:
        ref=performance_reference,
        cases=PERFORMANCE_CASE_MANIFEST
    output:
        "results/performance/input_format/raw/{case_id}.runs.tsv"
    log:
        "benchmark/logs/performance/input_format/{case_id}.timing.log"
    params:
        radigest=lambda wildcards: config.get("radigest", "radigest"),
        dataset=lambda wc: performance_value(wc, "dataset_id"),
        condition=lambda wc: performance_value(wc, "condition_id"),
        input_format=lambda wc: performance_value(wc, "input_format"),
        enzymes=performance_enzymes,
        min_size=performance_min_size,
        max_size=performance_max_size,
        threads=performance_threads,
        runs=performance_runs,
        raw_dir=lambda wc: f"results/performance/input_format/raw/{wc.case_id}"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/performance/input_format/raw benchmark/logs/performance/input_format
        python3 scripts/performance/run_radigest_timing.py \
          --radigest {params.radigest:q} \
          --reference {input.ref:q} \
          --case-id {wildcards.case_id:q} \
          --dataset-id {params.dataset:q} \
          --condition-id {params.condition:q} \
          --input-format {params.input_format:q} \
          --enzymes {params.enzymes:q} \
          --min {params.min_size} \
          --max {params.max_size} \
          --threads {params.threads} \
          --runs {params.runs} \
          --raw-dir {params.raw_dir:q} \
          --out {output:q} \
          > {log:q} 2>&1
        """


rule summarize_radigest_input_format:
    input:
        runs=PERFORMANCE_INPUT_FORMAT_RUN_OUTPUTS,
        cases=PERFORMANCE_CASE_MANIFEST
    output:
        PERFORMANCE_INPUT_FORMAT_SUMMARY
    log:
        "benchmark/logs/performance/input_format/input_format_summary.log"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/performance/input_format benchmark/logs/performance/input_format
        python3 scripts/performance/summarize_radigest_timing.py \
          --cases {input.cases:q} \
          --runs {input.runs:q} \
          --category input_format \
          --out {output:q} \
          --require-pass \
          > {log:q} 2>&1
        """


rule make_input_format_table:
    input:
        summary=PERFORMANCE_INPUT_FORMAT_SUMMARY,
        datasets="config/datasets.tsv",
        conditions="config/conditions.tsv"
    output:
        PERFORMANCE_INPUT_FORMAT_TABLE
    log:
        "benchmark/logs/performance/input_format/input_format_table.log"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/manuscript/tables benchmark/logs/performance/input_format
        python3 scripts/manuscript/make_input_format_table.py \
          --summary {input.summary:q} \
          --datasets {input.datasets:q} \
          --conditions {input.conditions:q} \
          --out {output:q} \
          --require-pass \
          > {log:q} 2>&1
        """
