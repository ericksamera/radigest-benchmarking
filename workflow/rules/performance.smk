# Stage 5 performance rules.
# Stage 5a covers radigest input-format timing. Stage 5b adds cached
# radigest-screen-pairs-cached candidate-pair screening speed. Stage 5c adds
# intra-tool radigest thread scaling. Stage 5d adds cached pair-screen job
# scaling. Later Stage 5 patches should add large_genome outputs to
# PERFORMANCE_ALL_OUTPUTS.

import csv

PERFORMANCE_CASE_MANIFEST = "config/performance_cases.tsv"
SCREENING_SPEED_CASE_MANIFEST = "config/screening_speed_cases.tsv"
THREAD_SCALING_CASE_MANIFEST = "config/thread_scaling_cases.tsv"
PAIR_SCREEN_SCALING_CASE_MANIFEST = "config/pair_screen_scaling_cases.tsv"
PERFORMANCE_INPUT_FORMAT_SUMMARY = (
    "results/performance/input_format/radigest_input_format_comparison.tsv"
)
PERFORMANCE_INPUT_FORMAT_TABLE = "results/manuscript/tables/table_06_input_format.tsv"
SCREENING_SPEED_SUMMARY = "results/performance/screening_speed/screening_speed_summary.tsv"
SCREENING_SPEED_TABLE = "results/manuscript/tables/table_05_screening_speed.tsv"
THREAD_SCALING_SUMMARY = (
    "results/performance/thread_scaling/radigest_thread_scaling_summary.tsv"
)
THREAD_SCALING_TABLE = "results/manuscript/tables/table_s02_radigest_thread_scaling.tsv"
PAIR_SCREEN_SCALING_SUMMARY = (
    "results/performance/pair_screen_scaling/pair_screen_scaling_summary.tsv"
)
PAIR_SCREEN_SCALING_TABLE = (
    "results/manuscript/tables/table_s03_pair_screen_job_scaling.tsv"
)


def _read_tsv_rows(path):
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


PERFORMANCE_CASE_ROWS = _read_tsv_rows(PERFORMANCE_CASE_MANIFEST)
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

SCREENING_SPEED_CASE_ROWS = _read_tsv_rows(SCREENING_SPEED_CASE_MANIFEST)
SCREENING_SPEED_CASE_BY_ID = {
    row["case_id"]: row for row in SCREENING_SPEED_CASE_ROWS
}
SCREENING_SPEED_CASES = [
    row["case_id"]
    for row in SCREENING_SPEED_CASE_ROWS
    if row.get("required_for_nonempirical", "false").lower() == "true"
]
SCREENING_SPEED_RUN_OUTPUTS = [
    f"results/performance/screening_speed/raw/{case_id}.runs.tsv"
    for case_id in SCREENING_SPEED_CASES
]
SCREENING_SPEED_OUTPUTS = [
    SCREENING_SPEED_SUMMARY,
    SCREENING_SPEED_TABLE,
]

THREAD_SCALING_CASE_ROWS = _read_tsv_rows(THREAD_SCALING_CASE_MANIFEST)
THREAD_SCALING_CASE_BY_ID = {
    row["case_id"]: row for row in THREAD_SCALING_CASE_ROWS
}
THREAD_SCALING_CASES = [
    row["case_id"]
    for row in THREAD_SCALING_CASE_ROWS
    if row.get("required_for_nonempirical", "false").lower() == "true"
]
THREAD_SCALING_RUN_OUTPUTS = [
    f"results/performance/thread_scaling/raw/{case_id}.runs.tsv"
    for case_id in THREAD_SCALING_CASES
]
THREAD_SCALING_OUTPUTS = [
    THREAD_SCALING_SUMMARY,
    THREAD_SCALING_TABLE,
]

PAIR_SCREEN_SCALING_CASE_ROWS = _read_tsv_rows(PAIR_SCREEN_SCALING_CASE_MANIFEST)
PAIR_SCREEN_SCALING_CASE_BY_ID = {
    row["case_id"]: row for row in PAIR_SCREEN_SCALING_CASE_ROWS
}
PAIR_SCREEN_SCALING_CASES = [
    row["case_id"]
    for row in PAIR_SCREEN_SCALING_CASE_ROWS
    if row.get("required_for_nonempirical", "false").lower() == "true"
]
PAIR_SCREEN_SCALING_RUN_OUTPUTS = [
    f"results/performance/pair_screen_scaling/raw/{case_id}.runs.tsv"
    for case_id in PAIR_SCREEN_SCALING_CASES
]
PAIR_SCREEN_SCALING_OUTPUTS = [
    PAIR_SCREEN_SCALING_SUMMARY,
    PAIR_SCREEN_SCALING_TABLE,
]
PERFORMANCE_ALL_OUTPUTS = (
    PERFORMANCE_INPUT_FORMAT_OUTPUTS
    + SCREENING_SPEED_OUTPUTS
    + THREAD_SCALING_OUTPUTS
    + PAIR_SCREEN_SCALING_OUTPUTS
)


def performance_case(case_id):
    try:
        return PERFORMANCE_CASE_BY_ID[case_id]
    except KeyError as exc:
        raise ValueError(f"unknown performance case_id: {case_id}") from exc


def screening_case(case_id):
    try:
        return SCREENING_SPEED_CASE_BY_ID[case_id]
    except KeyError as exc:
        raise ValueError(f"unknown screening_speed case_id: {case_id}") from exc


def thread_scaling_case(case_id):
    try:
        return THREAD_SCALING_CASE_BY_ID[case_id]
    except KeyError as exc:
        raise ValueError(f"unknown thread_scaling case_id: {case_id}") from exc


def pair_screen_scaling_case(case_id):
    try:
        return PAIR_SCREEN_SCALING_CASE_BY_ID[case_id]
    except KeyError as exc:
        raise ValueError(f"unknown pair_screen_scaling case_id: {case_id}") from exc


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


def screening_reference(wc):
    return screening_case(wc.case_id)["reference_path"]


def screening_candidate_enzymes(wc):
    return screening_case(wc.case_id)["candidate_enzymes"]


def screening_value(wc, column):
    return screening_case(wc.case_id)[column]


def screening_int(wc, column):
    return int(screening_case(wc.case_id)[column])


def thread_scaling_reference(wc):
    return thread_scaling_case(wc.case_id)["reference_path"]


def thread_scaling_value(wc, column):
    return thread_scaling_case(wc.case_id)[column]


def thread_scaling_int(wc, column):
    return int(thread_scaling_case(wc.case_id)[column])


def thread_scaling_enzymes(wc):
    row = thread_scaling_case(wc.case_id)
    enzyme2 = row["enzyme_2"]
    if enzyme2 in {"", "NA", "none", "None"}:
        return row["enzyme_1"]
    return f"{row['enzyme_1']},{enzyme2}"


def pair_screen_scaling_reference(wc):
    return pair_screen_scaling_case(wc.case_id)["reference_path"]


def pair_screen_scaling_candidate_enzymes(wc):
    return pair_screen_scaling_case(wc.case_id)["candidate_enzymes"]


def pair_screen_scaling_value(wc, column):
    return pair_screen_scaling_case(wc.case_id)[column]


def pair_screen_scaling_int(wc, column):
    return int(pair_screen_scaling_case(wc.case_id)[column])


rule performance_all:
    input:
        PERFORMANCE_ALL_OUTPUTS


rule performance_input_format_all:
    input:
        PERFORMANCE_INPUT_FORMAT_OUTPUTS


rule performance_screening_speed_all:
    input:
        SCREENING_SPEED_OUTPUTS


rule performance_thread_scaling_all:
    input:
        THREAD_SCALING_OUTPUTS


rule performance_pair_screen_scaling_all:
    input:
        PAIR_SCREEN_SCALING_OUTPUTS


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


rule run_radigest_screening_speed_case:
    input:
        ref=screening_reference,
        candidates=screening_candidate_enzymes,
        cases=SCREENING_SPEED_CASE_MANIFEST
    output:
        "results/performance/screening_speed/raw/{case_id}.runs.tsv"
    log:
        "benchmark/logs/performance/screening_speed/{case_id}.timing.log"
    params:
        screen_binary=lambda wildcards: config.get(
            "radigest_screen_pairs_cached", "radigest-screen-pairs-cached"
        ),
        dataset=lambda wc: screening_value(wc, "dataset_id"),
        condition=lambda wc: screening_value(wc, "condition_id"),
        min_size=lambda wc: screening_int(wc, "min_size"),
        max_size=lambda wc: screening_int(wc, "max_size"),
        score_min=lambda wc: screening_int(wc, "score_min"),
        score_max=lambda wc: screening_int(wc, "score_max"),
        size_model=lambda wc: screening_value(wc, "size_model"),
        jobs=lambda wc: screening_int(wc, "jobs"),
        radigest_threads=lambda wc: screening_int(wc, "radigest_threads"),
        runs=lambda wc: screening_int(wc, "runs"),
        command_template=lambda wc: screening_value(wc, "command_template"),
        raw_dir=lambda wc: f"results/performance/screening_speed/raw/{wc.case_id}"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/performance/screening_speed/raw benchmark/logs/performance/screening_speed
        python3 scripts/performance/run_radigest_screening.py \
          --screen-binary {params.screen_binary:q} \
          --reference {input.ref:q} \
          --case-id {wildcards.case_id:q} \
          --dataset-id {params.dataset:q} \
          --condition-id {params.condition:q} \
          --candidate-enzymes {input.candidates:q} \
          --min {params.min_size} \
          --max {params.max_size} \
          --score-min {params.score_min} \
          --score-max {params.score_max} \
          --size-model {params.size_model:q} \
          --jobs {params.jobs} \
          --radigest-threads {params.radigest_threads} \
          --runs {params.runs} \
          --command-template {params.command_template:q} \
          --raw-dir {params.raw_dir:q} \
          --out {output:q} \
          > {log:q} 2>&1
        """


rule summarize_screening_speed:
    input:
        runs=SCREENING_SPEED_RUN_OUTPUTS,
        cases=SCREENING_SPEED_CASE_MANIFEST
    output:
        SCREENING_SPEED_SUMMARY
    log:
        "benchmark/logs/performance/screening_speed/screening_speed_summary.log"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/performance/screening_speed benchmark/logs/performance/screening_speed
        python3 scripts/performance/summarize_screening_speed.py \
          --cases {input.cases:q} \
          --runs {input.runs:q} \
          --out {output:q} \
          --require-pass \
          > {log:q} 2>&1
        """


rule make_screening_speed_table:
    input:
        summary=SCREENING_SPEED_SUMMARY
    output:
        SCREENING_SPEED_TABLE
    log:
        "benchmark/logs/performance/screening_speed/screening_speed_table.log"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/manuscript/tables benchmark/logs/performance/screening_speed
        python3 scripts/manuscript/make_screening_speed_table.py \
          --summary {input.summary:q} \
          --out {output:q} \
          --require-pass \
          > {log:q} 2>&1
        """

rule run_radigest_thread_scaling_case:
    input:
        ref=thread_scaling_reference,
        cases=THREAD_SCALING_CASE_MANIFEST
    output:
        "results/performance/thread_scaling/raw/{case_id}.runs.tsv"
    log:
        "benchmark/logs/performance/thread_scaling/{case_id}.timing.log"
    threads:
        lambda wc: thread_scaling_int(wc, "threads")
    params:
        radigest=lambda wildcards: config.get("radigest", "radigest"),
        dataset=lambda wc: thread_scaling_value(wc, "dataset_id"),
        condition=lambda wc: thread_scaling_value(wc, "condition_id"),
        input_format=lambda wc: thread_scaling_value(wc, "input_format"),
        output_mode=lambda wc: thread_scaling_value(wc, "output_mode"),
        enzymes=thread_scaling_enzymes,
        min_size=lambda wc: thread_scaling_int(wc, "min_size"),
        max_size=lambda wc: thread_scaling_int(wc, "max_size"),
        runs=lambda wc: thread_scaling_int(wc, "runs"),
        raw_dir=lambda wc: f"results/performance/thread_scaling/raw/{wc.case_id}"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/performance/thread_scaling/raw benchmark/logs/performance/thread_scaling
        python3 scripts/performance/run_radigest_timing.py \
          --radigest {params.radigest:q} \
          --reference {input.ref:q} \
          --case-id {wildcards.case_id:q} \
          --dataset-id {params.dataset:q} \
          --condition-id {params.condition:q} \
          --input-format {params.input_format:q} \
          --output-mode {params.output_mode:q} \
          --enzymes {params.enzymes:q} \
          --min {params.min_size} \
          --max {params.max_size} \
          --threads {threads} \
          --runs {params.runs} \
          --raw-dir {params.raw_dir:q} \
          --out {output:q} \
          > {log:q} 2>&1
        """


rule summarize_thread_scaling:
    input:
        runs=THREAD_SCALING_RUN_OUTPUTS,
        cases=THREAD_SCALING_CASE_MANIFEST
    output:
        THREAD_SCALING_SUMMARY
    log:
        "benchmark/logs/performance/thread_scaling/thread_scaling_summary.log"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/performance/thread_scaling benchmark/logs/performance/thread_scaling
        python3 scripts/performance/summarize_thread_scaling.py \
          --cases {input.cases:q} \
          --runs {input.runs:q} \
          --out {output:q} \
          --require-pass \
          > {log:q} 2>&1
        """


rule make_thread_scaling_table:
    input:
        summary=THREAD_SCALING_SUMMARY,
        datasets="config/datasets.tsv",
        conditions="config/conditions.tsv"
    output:
        THREAD_SCALING_TABLE
    log:
        "benchmark/logs/performance/thread_scaling/thread_scaling_table.log"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/manuscript/tables benchmark/logs/performance/thread_scaling
        python3 scripts/manuscript/make_thread_scaling_table.py \
          --summary {input.summary:q} \
          --datasets {input.datasets:q} \
          --conditions {input.conditions:q} \
          --out {output:q} \
          --require-pass \
          > {log:q} 2>&1
        """

rule run_radigest_pair_screen_scaling_case:
    input:
        ref=pair_screen_scaling_reference,
        candidates=pair_screen_scaling_candidate_enzymes,
        cases=PAIR_SCREEN_SCALING_CASE_MANIFEST
    output:
        "results/performance/pair_screen_scaling/raw/{case_id}.runs.tsv"
    log:
        "benchmark/logs/performance/pair_screen_scaling/{case_id}.timing.log"
    threads:
        lambda wc: pair_screen_scaling_int(wc, "jobs")
    resources:
        pair_screen_benchmark=1
    params:
        screen_binary=lambda wildcards: config.get(
            "radigest_screen_pairs_cached", "radigest-screen-pairs-cached"
        ),
        dataset=lambda wc: pair_screen_scaling_value(wc, "dataset_id"),
        condition=lambda wc: pair_screen_scaling_value(wc, "condition_id"),
        min_size=lambda wc: pair_screen_scaling_int(wc, "min_size"),
        max_size=lambda wc: pair_screen_scaling_int(wc, "max_size"),
        score_min=lambda wc: pair_screen_scaling_int(wc, "score_min"),
        score_max=lambda wc: pair_screen_scaling_int(wc, "score_max"),
        size_model=lambda wc: pair_screen_scaling_value(wc, "size_model"),
        jobs=lambda wc: pair_screen_scaling_int(wc, "jobs"),
        radigest_threads=lambda wc: pair_screen_scaling_int(wc, "radigest_threads"),
        runs=lambda wc: pair_screen_scaling_int(wc, "runs"),
        command_template=lambda wc: pair_screen_scaling_value(wc, "command_template"),
        raw_dir=lambda wc: f"results/performance/pair_screen_scaling/raw/{wc.case_id}"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/performance/pair_screen_scaling/raw benchmark/logs/performance/pair_screen_scaling
        python3 scripts/performance/run_radigest_screening.py \
          --screen-binary {params.screen_binary:q} \
          --reference {input.ref:q} \
          --case-id {wildcards.case_id:q} \
          --dataset-id {params.dataset:q} \
          --condition-id {params.condition:q} \
          --candidate-enzymes {input.candidates:q} \
          --min {params.min_size} \
          --max {params.max_size} \
          --score-min {params.score_min} \
          --score-max {params.score_max} \
          --size-model {params.size_model:q} \
          --jobs {params.jobs} \
          --radigest-threads {params.radigest_threads} \
          --runs {params.runs} \
          --command-template {params.command_template:q} \
          --raw-dir {params.raw_dir:q} \
          --out {output:q} \
          > {log:q} 2>&1
        """


rule summarize_pair_screen_scaling:
    input:
        runs=PAIR_SCREEN_SCALING_RUN_OUTPUTS,
        cases=PAIR_SCREEN_SCALING_CASE_MANIFEST
    output:
        PAIR_SCREEN_SCALING_SUMMARY
    log:
        "benchmark/logs/performance/pair_screen_scaling/pair_screen_scaling_summary.log"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/performance/pair_screen_scaling benchmark/logs/performance/pair_screen_scaling
        python3 scripts/performance/summarize_pair_screen_scaling.py \
          --cases {input.cases:q} \
          --runs {input.runs:q} \
          --out {output:q} \
          --require-pass \
          > {log:q} 2>&1
        """


rule make_pair_screen_scaling_table:
    input:
        summary=PAIR_SCREEN_SCALING_SUMMARY,
        datasets="config/datasets.tsv",
        conditions="config/conditions.tsv"
    output:
        PAIR_SCREEN_SCALING_TABLE
    log:
        "benchmark/logs/performance/pair_screen_scaling/pair_screen_scaling_table.log"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/manuscript/tables benchmark/logs/performance/pair_screen_scaling
        python3 scripts/manuscript/make_pair_screen_scaling_table.py \
          --summary {input.summary:q} \
          --datasets {input.datasets:q} \
          --conditions {input.conditions:q} \
          --out {output:q} \
          --require-pass \
          > {log:q} 2>&1
        """
