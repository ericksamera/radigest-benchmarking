# Stage 5 performance rules.
# Stage 5a covers radigest input-format timing. Stage 5b adds cached
# radigest-screen-pairs-cached candidate-pair screening speed. Stage 5c adds
# intra-tool radigest thread scaling. Stage 5d adds cached pair-screen job
# scaling. Stage 5e adds large-reference timing, now folded into the
# matched-tool timing entry point. Stage 5f adds semantics-aware matched-tool
# timing. Later patches should add audit outputs.

import csv

PERFORMANCE_CASE_MANIFEST = "config/performance_cases.tsv"
SCREENING_SPEED_CASE_MANIFEST = "config/screening_speed_cases.tsv"
THREAD_SCALING_CASE_MANIFEST = "config/thread_scaling_cases.tsv"
PAIR_SCREEN_SCALING_CASE_MANIFEST = "config/pair_screen_scaling_cases.tsv"
LARGE_GENOME_CASE_MANIFEST = "config/large_genome_cases.tsv"
MATCHED_TOOL_TIMING_CASE_MANIFEST = "config/matched_tool_timing_cases.tsv"
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
LARGE_GENOME_SUMMARY = (
    "results/performance/large_genome/large_genome_summary.tsv"
)
LARGE_GENOME_TABLE = "results/manuscript/tables/table_s04_large_genome.tsv"
MATCHED_TOOL_TIMING_RUNS = "results/performance/matched_tools/tool_timing_runs.tsv"
MATCHED_TOOL_TIMING_SUMMARY = "results/performance/matched_tools/tool_timing_summary.tsv"
MATCHED_TOOL_TIMING_INTERPRETATION = (
    "results/performance/matched_tools/tool_timing_interpretation.tsv"
)
MATCHED_TOOL_TIMING_TABLE = "results/manuscript/tables/table_04_matched_timing.tsv"
MATCHED_TOOL_TIMING_FIGURE = (
    "results/manuscript/figures/figure_04_matched_tool_timing.pdf"
)
SCREENING_SPEED_FIGURE = "results/manuscript/figures/figure_05_screening_speed.pdf"
PERFORMANCE_INPUT_FORMAT_FIGURE = (
    "results/manuscript/figures/figure_06_input_format.pdf"
)
THREAD_SCALING_FIGURE = "results/manuscript/figures/figure_s02_thread_scaling.pdf"
PAIR_SCREEN_SCALING_FIGURE = (
    "results/manuscript/figures/figure_s03_pair_screen_job_scaling.pdf"
)
LARGE_GENOME_FIGURE = "results/manuscript/figures/figure_s04_large_genome.pdf"
PERFORMANCE_FIGURE_OUTPUTS = [
    MATCHED_TOOL_TIMING_FIGURE,
    SCREENING_SPEED_FIGURE,
    PERFORMANCE_INPUT_FORMAT_FIGURE,
    THREAD_SCALING_FIGURE,
    PAIR_SCREEN_SCALING_FIGURE,
    LARGE_GENOME_FIGURE,
]


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
    PERFORMANCE_INPUT_FORMAT_FIGURE,
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
    SCREENING_SPEED_FIGURE,
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
    THREAD_SCALING_FIGURE,
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
    PAIR_SCREEN_SCALING_FIGURE,
]

LARGE_GENOME_CASE_ROWS = _read_tsv_rows(LARGE_GENOME_CASE_MANIFEST)
LARGE_GENOME_CASE_BY_ID = {row["case_id"]: row for row in LARGE_GENOME_CASE_ROWS}
LARGE_GENOME_CASES = [
    row["case_id"]
    for row in LARGE_GENOME_CASE_ROWS
    if row.get("required_for_nonempirical", "false").lower() == "true"
]
LARGE_GENOME_RUN_OUTPUTS = [
    f"results/performance/large_genome/raw/{case_id}.runs.tsv"
    for case_id in LARGE_GENOME_CASES
]
LARGE_GENOME_OUTPUTS = [
    LARGE_GENOME_SUMMARY,
    LARGE_GENOME_TABLE,
    LARGE_GENOME_FIGURE,
]

MATCHED_TOOL_TIMING_CASE_ROWS = _read_tsv_rows(MATCHED_TOOL_TIMING_CASE_MANIFEST)
MATCHED_TOOL_TIMING_CASE_BY_ID = {
    row["case_id"]: row for row in MATCHED_TOOL_TIMING_CASE_ROWS
}
MATCHED_TOOL_TIMING_CASES = [
    row["case_id"]
    for row in MATCHED_TOOL_TIMING_CASE_ROWS
    if row.get("required_for_nonempirical", "false").lower() == "true"
]
MATCHED_TOOL_TIMING_RUN_OUTPUTS = [
    f"results/performance/matched_tools/raw/{row['tool_id']}/{row['case_id']}.runs.tsv"
    for row in MATCHED_TOOL_TIMING_CASE_ROWS
    if row.get("required_for_nonempirical", "false").lower() == "true"
]
MATCHED_TOOL_TIMING_OUTPUTS = [
    MATCHED_TOOL_TIMING_RUNS,
    MATCHED_TOOL_TIMING_SUMMARY,
    MATCHED_TOOL_TIMING_INTERPRETATION,
    MATCHED_TOOL_TIMING_TABLE,
    MATCHED_TOOL_TIMING_FIGURE,
]
PERFORMANCE_ALL_OUTPUTS = (
    PERFORMANCE_INPUT_FORMAT_OUTPUTS
    + SCREENING_SPEED_OUTPUTS
    + THREAD_SCALING_OUTPUTS
    + PAIR_SCREEN_SCALING_OUTPUTS
    + LARGE_GENOME_OUTPUTS
    + MATCHED_TOOL_TIMING_OUTPUTS
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


def large_genome_case(case_id):
    try:
        return LARGE_GENOME_CASE_BY_ID[case_id]
    except KeyError as exc:
        raise ValueError(f"unknown large_genome case_id: {case_id}") from exc


def matched_tool_timing_case(case_id):
    try:
        return MATCHED_TOOL_TIMING_CASE_BY_ID[case_id]
    except KeyError as exc:
        raise ValueError(f"unknown matched_tool_timing case_id: {case_id}") from exc


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


def large_genome_reference(wc):
    return large_genome_case(wc.case_id)["reference_path"]


def large_genome_value(wc, column):
    return large_genome_case(wc.case_id)[column]


def large_genome_int(wc, column):
    return int(large_genome_case(wc.case_id)[column])


def large_genome_enzymes(wc):
    row = large_genome_case(wc.case_id)
    enzyme2 = row["enzyme_2"]
    if enzyme2 in {"", "NA", "none", "None"}:
        return row["enzyme_1"]
    return f"{row['enzyme_1']},{enzyme2}"


def matched_tool_timing_reference(wc):
    return matched_tool_timing_case(wc.case_id)["reference_path"]


def matched_tool_timing_value(wc, column):
    return matched_tool_timing_case(wc.case_id)[column]


def matched_tool_timing_int(wc, column):
    return int(matched_tool_timing_case(wc.case_id)[column])


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


rule performance_matched_tools_all:
    input:
        MATCHED_TOOL_TIMING_OUTPUTS + LARGE_GENOME_OUTPUTS


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
    threads:
        lambda wc: max(screening_int(wc, "jobs"), screening_int(wc, "radigest_threads"))
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
        build_workers=lambda wc: screening_int(wc, "radigest_threads"),
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
          --build-workers {params.build_workers} \
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
        build_workers=lambda wc: pair_screen_scaling_int(wc, "radigest_threads"),
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
          --build-workers {params.build_workers} \
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

rule run_radigest_large_genome_case:
    input:
        ref=large_genome_reference,
        cases=LARGE_GENOME_CASE_MANIFEST
    output:
        "results/performance/large_genome/raw/{case_id}.runs.tsv"
    log:
        "benchmark/logs/performance/large_genome/{case_id}.timing.log"
    threads:
        lambda wc: large_genome_int(wc, "threads")
    resources:
        matched_tool_benchmark=1
    params:
        radigest=lambda wildcards: config.get("radigest", "radigest"),
        dataset=lambda wc: large_genome_value(wc, "dataset_id"),
        condition=lambda wc: large_genome_value(wc, "condition_id"),
        input_format=lambda wc: large_genome_value(wc, "input_format"),
        output_mode=lambda wc: large_genome_value(wc, "output_mode"),
        enzymes=large_genome_enzymes,
        min_size=lambda wc: large_genome_int(wc, "min_size"),
        max_size=lambda wc: large_genome_int(wc, "max_size"),
        runs=lambda wc: large_genome_int(wc, "runs"),
        raw_dir=lambda wc: f"results/performance/large_genome/raw/{wc.case_id}"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/performance/large_genome/raw benchmark/logs/performance/large_genome
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


rule summarize_large_genome_performance:
    input:
        runs=LARGE_GENOME_RUN_OUTPUTS,
        cases=LARGE_GENOME_CASE_MANIFEST
    output:
        LARGE_GENOME_SUMMARY
    log:
        "benchmark/logs/performance/large_genome/large_genome_summary.log"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/performance/large_genome benchmark/logs/performance/large_genome
        python3 scripts/performance/summarize_radigest_timing.py \
          --cases {input.cases:q} \
          --runs {input.runs:q} \
          --category large_genome \
          --out {output:q} \
          --require-pass \
          > {log:q} 2>&1
        """


rule make_large_genome_table:
    input:
        summary=LARGE_GENOME_SUMMARY,
        datasets="config/datasets.tsv",
        conditions="config/conditions.tsv"
    output:
        LARGE_GENOME_TABLE
    log:
        "benchmark/logs/performance/large_genome/large_genome_table.log"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/manuscript/tables benchmark/logs/performance/large_genome
        python3 scripts/manuscript/make_large_genome_table.py \
          --summary {input.summary:q} \
          --datasets {input.datasets:q} \
          --conditions {input.conditions:q} \
          --out {output:q} \
          --require-pass \
          > {log:q} 2>&1
        """

rule run_matched_tool_timing_radigest:
    input:
        ref=matched_tool_timing_reference,
        cases=MATCHED_TOOL_TIMING_CASE_MANIFEST
    output:
        "results/performance/matched_tools/raw/radigest/{case_id}.runs.tsv"
    log:
        "benchmark/logs/performance/matched_tools/radigest/{case_id}.timing.log"
    resources:
        matched_tool_benchmark=1
    params:
        tool_id="radigest",
        radigest=lambda wildcards: config.get("radigest", "radigest"),
        ddgrader_repo=lambda wildcards: config.get("ddgrader_repo", "external/ddRadSeqWebTool"),
        dataset=lambda wc: matched_tool_timing_value(wc, "dataset_id"),
        condition=lambda wc: matched_tool_timing_value(wc, "condition_id"),
        enzyme_1=lambda wc: matched_tool_timing_value(wc, "enzyme_1"),
        enzyme_2=lambda wc: matched_tool_timing_value(wc, "enzyme_2"),
        min_size=lambda wc: matched_tool_timing_int(wc, "min_size"),
        max_size=lambda wc: matched_tool_timing_int(wc, "max_size"),
        runs=lambda wc: matched_tool_timing_int(wc, "runs"),
        timing_scope=lambda wc: matched_tool_timing_value(wc, "timing_scope"),
        notes=lambda wc: matched_tool_timing_value(wc, "notes"),
        raw_dir=lambda wc: f"results/performance/matched_tools/raw/radigest/{wc.case_id}"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/performance/matched_tools/raw/radigest benchmark/logs/performance/matched_tools/radigest
        python3 scripts/performance/run_matched_tool_timing.py \
          --case-id {wildcards.case_id:q} \
          --tool-id {params.tool_id:q} \
          --dataset-id {params.dataset:q} \
          --condition-id {params.condition:q} \
          --reference {input.ref:q} \
          --enzyme-1 {params.enzyme_1:q} \
          --enzyme-2 {params.enzyme_2:q} \
          --min {params.min_size} \
          --max {params.max_size} \
          --runs {params.runs} \
          --timing-scope {params.timing_scope:q} \
          --notes {params.notes:q} \
          --radigest {params.radigest:q} \
          --ddgrader-repo {params.ddgrader_repo:q} \
          --raw-dir {params.raw_dir:q} \
          --out {output:q} \
          > {log:q} 2>&1
        """


rule run_matched_tool_timing_digital_rads:
    input:
        ref=matched_tool_timing_reference,
        tool="external/Digital_RADs/Digital_RADs.py",
        cases=MATCHED_TOOL_TIMING_CASE_MANIFEST
    output:
        "results/performance/matched_tools/raw/digital_rads/{case_id}.runs.tsv"
    log:
        "benchmark/logs/performance/matched_tools/digital_rads/{case_id}.timing.log"
    resources:
        matched_tool_benchmark=1
    params:
        tool_id="digital_rads",
        radigest=lambda wildcards: config.get("radigest", "radigest"),
        ddgrader_repo=lambda wildcards: config.get("ddgrader_repo", "external/ddRadSeqWebTool"),
        dataset=lambda wc: matched_tool_timing_value(wc, "dataset_id"),
        condition=lambda wc: matched_tool_timing_value(wc, "condition_id"),
        enzyme_1=lambda wc: matched_tool_timing_value(wc, "enzyme_1"),
        enzyme_2=lambda wc: matched_tool_timing_value(wc, "enzyme_2"),
        min_size=lambda wc: matched_tool_timing_int(wc, "min_size"),
        max_size=lambda wc: matched_tool_timing_int(wc, "max_size"),
        runs=lambda wc: matched_tool_timing_int(wc, "runs"),
        timing_scope=lambda wc: matched_tool_timing_value(wc, "timing_scope"),
        notes=lambda wc: matched_tool_timing_value(wc, "notes"),
        raw_dir=lambda wc: f"results/performance/matched_tools/raw/digital_rads/{wc.case_id}"
    conda:
        "../envs/comparators.yml"
    shell:
        r"""
        mkdir -p results/performance/matched_tools/raw/digital_rads benchmark/logs/performance/matched_tools/digital_rads
        python3 scripts/performance/run_matched_tool_timing.py \
          --case-id {wildcards.case_id:q} \
          --tool-id {params.tool_id:q} \
          --dataset-id {params.dataset:q} \
          --condition-id {params.condition:q} \
          --reference {input.ref:q} \
          --enzyme-1 {params.enzyme_1:q} \
          --enzyme-2 {params.enzyme_2:q} \
          --min {params.min_size} \
          --max {params.max_size} \
          --runs {params.runs} \
          --timing-scope {params.timing_scope:q} \
          --notes {params.notes:q} \
          --radigest {params.radigest:q} \
          --ddgrader-repo {params.ddgrader_repo:q} \
          --raw-dir {params.raw_dir:q} \
          --out {output:q} \
          > {log:q} 2>&1
        """


rule run_matched_tool_timing_ddradseqtools:
    input:
        ref=matched_tool_timing_reference,
        tool=DDRADSEQTOOLS_TOOL,
        restrictionsites=DDRADSEQTOOLS_RESTRICTIONSITES,
        cases=MATCHED_TOOL_TIMING_CASE_MANIFEST
    output:
        "results/performance/matched_tools/raw/ddradseqtools/{case_id}.runs.tsv"
    log:
        "benchmark/logs/performance/matched_tools/ddradseqtools/{case_id}.timing.log"
    resources:
        matched_tool_benchmark=1
    params:
        tool_id="ddradseqtools",
        radigest=lambda wildcards: config.get("radigest", "radigest"),
        ddgrader_repo=lambda wildcards: config.get("ddgrader_repo", "external/ddRadSeqWebTool"),
        dataset=lambda wc: matched_tool_timing_value(wc, "dataset_id"),
        condition=lambda wc: matched_tool_timing_value(wc, "condition_id"),
        enzyme_1=lambda wc: matched_tool_timing_value(wc, "enzyme_1"),
        enzyme_2=lambda wc: matched_tool_timing_value(wc, "enzyme_2"),
        min_size=lambda wc: matched_tool_timing_int(wc, "min_size"),
        max_size=lambda wc: matched_tool_timing_int(wc, "max_size"),
        runs=lambda wc: matched_tool_timing_int(wc, "runs"),
        timing_scope=lambda wc: matched_tool_timing_value(wc, "timing_scope"),
        notes=lambda wc: matched_tool_timing_value(wc, "notes"),
        raw_dir=lambda wc: f"results/performance/matched_tools/raw/ddradseqtools/{wc.case_id}"
    conda:
        "../envs/comparators.yml"
    shell:
        r"""
        mkdir -p results/performance/matched_tools/raw/ddradseqtools benchmark/logs/performance/matched_tools/ddradseqtools
        python3 scripts/performance/run_matched_tool_timing.py \
          --case-id {wildcards.case_id:q} \
          --tool-id {params.tool_id:q} \
          --dataset-id {params.dataset:q} \
          --condition-id {params.condition:q} \
          --reference {input.ref:q} \
          --enzyme-1 {params.enzyme_1:q} \
          --enzyme-2 {params.enzyme_2:q} \
          --min {params.min_size} \
          --max {params.max_size} \
          --runs {params.runs} \
          --timing-scope {params.timing_scope:q} \
          --notes {params.notes:q} \
          --radigest {params.radigest:q} \
          --ddgrader-repo {params.ddgrader_repo:q} \
          --raw-dir {params.raw_dir:q} \
          --out {output:q} \
          > {log:q} 2>&1
        """


rule run_matched_tool_timing_simrad:
    input:
        ref=matched_tool_timing_reference,
        simrad=SIMRAD_INSTALL_MARKER,
        cases=MATCHED_TOOL_TIMING_CASE_MANIFEST
    output:
        "results/performance/matched_tools/raw/simrad/{case_id}.runs.tsv"
    log:
        "benchmark/logs/performance/matched_tools/simrad/{case_id}.timing.log"
    resources:
        matched_tool_benchmark=1
    params:
        tool_id="simrad",
        radigest=lambda wildcards: config.get("radigest", "radigest"),
        ddgrader_repo=lambda wildcards: config.get("ddgrader_repo", "external/ddRadSeqWebTool"),
        dataset=lambda wc: matched_tool_timing_value(wc, "dataset_id"),
        condition=lambda wc: matched_tool_timing_value(wc, "condition_id"),
        enzyme_1=lambda wc: matched_tool_timing_value(wc, "enzyme_1"),
        enzyme_2=lambda wc: matched_tool_timing_value(wc, "enzyme_2"),
        min_size=lambda wc: matched_tool_timing_int(wc, "min_size"),
        max_size=lambda wc: matched_tool_timing_int(wc, "max_size"),
        runs=lambda wc: matched_tool_timing_int(wc, "runs"),
        timing_scope=lambda wc: matched_tool_timing_value(wc, "timing_scope"),
        notes=lambda wc: matched_tool_timing_value(wc, "notes"),
        raw_dir=lambda wc: f"results/performance/matched_tools/raw/simrad/{wc.case_id}"
    conda:
        "../envs/simrad.yml"
    shell:
        r"""
        mkdir -p results/performance/matched_tools/raw/simrad benchmark/logs/performance/matched_tools/simrad
        python3 scripts/performance/run_matched_tool_timing.py \
          --case-id {wildcards.case_id:q} \
          --tool-id {params.tool_id:q} \
          --dataset-id {params.dataset:q} \
          --condition-id {params.condition:q} \
          --reference {input.ref:q} \
          --enzyme-1 {params.enzyme_1:q} \
          --enzyme-2 {params.enzyme_2:q} \
          --min {params.min_size} \
          --max {params.max_size} \
          --runs {params.runs} \
          --timing-scope {params.timing_scope:q} \
          --notes {params.notes:q} \
          --radigest {params.radigest:q} \
          --ddgrader-repo {params.ddgrader_repo:q} \
          --raw-dir {params.raw_dir:q} \
          --out {output:q} \
          > {log:q} 2>&1
        """


rule run_matched_tool_timing_ddgrader:
    input:
        ref=matched_tool_timing_reference,
        tool=DDGRADER_TOOL,
        enzyme_db=DDGRADER_ENZYME_DB,
        cases=MATCHED_TOOL_TIMING_CASE_MANIFEST
    output:
        "results/performance/matched_tools/raw/ddgrader/{case_id}.runs.tsv"
    log:
        "benchmark/logs/performance/matched_tools/ddgrader/{case_id}.timing.log"
    resources:
        matched_tool_benchmark=1
    params:
        tool_id="ddgrader",
        radigest=lambda wildcards: config.get("radigest", "radigest"),
        ddgrader_repo=lambda wildcards: config.get("ddgrader_repo", "external/ddRadSeqWebTool"),
        dataset=lambda wc: matched_tool_timing_value(wc, "dataset_id"),
        condition=lambda wc: matched_tool_timing_value(wc, "condition_id"),
        enzyme_1=lambda wc: matched_tool_timing_value(wc, "enzyme_1"),
        enzyme_2=lambda wc: matched_tool_timing_value(wc, "enzyme_2"),
        min_size=lambda wc: matched_tool_timing_int(wc, "min_size"),
        max_size=lambda wc: matched_tool_timing_int(wc, "max_size"),
        runs=lambda wc: matched_tool_timing_int(wc, "runs"),
        timing_scope=lambda wc: matched_tool_timing_value(wc, "timing_scope"),
        notes=lambda wc: matched_tool_timing_value(wc, "notes"),
        raw_dir=lambda wc: f"results/performance/matched_tools/raw/ddgrader/{wc.case_id}"
    conda:
        "../envs/ddgrader.yml"
    shell:
        r"""
        mkdir -p results/performance/matched_tools/raw/ddgrader benchmark/logs/performance/matched_tools/ddgrader
        python3 scripts/performance/run_matched_tool_timing.py \
          --case-id {wildcards.case_id:q} \
          --tool-id {params.tool_id:q} \
          --dataset-id {params.dataset:q} \
          --condition-id {params.condition:q} \
          --reference {input.ref:q} \
          --enzyme-1 {params.enzyme_1:q} \
          --enzyme-2 {params.enzyme_2:q} \
          --min {params.min_size} \
          --max {params.max_size} \
          --runs {params.runs} \
          --timing-scope {params.timing_scope:q} \
          --notes {params.notes:q} \
          --radigest {params.radigest:q} \
          --ddgrader-repo {params.ddgrader_repo:q} \
          --raw-dir {params.raw_dir:q} \
          --out {output:q} \
          > {log:q} 2>&1
        """


rule summarize_matched_tool_timing:
    input:
        runs=MATCHED_TOOL_TIMING_RUN_OUTPUTS,
        cases=MATCHED_TOOL_TIMING_CASE_MANIFEST,
        comparators="config/comparators.tsv"
    output:
        merged_runs=MATCHED_TOOL_TIMING_RUNS,
        summary=MATCHED_TOOL_TIMING_SUMMARY,
        interpretation=MATCHED_TOOL_TIMING_INTERPRETATION
    log:
        "benchmark/logs/performance/matched_tools/matched_tool_timing_summary.log"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/performance/matched_tools benchmark/logs/performance/matched_tools
        python3 scripts/performance/summarize_matched_tool_timing.py \
          --cases {input.cases:q} \
          --comparators {input.comparators:q} \
          --runs {input.runs:q} \
          --merged-runs {output.merged_runs:q} \
          --summary {output.summary:q} \
          --interpretation {output.interpretation:q} \
          --require-pass \
          > {log:q} 2>&1
        """


rule make_matched_tool_timing_table:
    input:
        interpretation=MATCHED_TOOL_TIMING_INTERPRETATION
    output:
        MATCHED_TOOL_TIMING_TABLE
    log:
        "benchmark/logs/performance/matched_tools/matched_tool_timing_table.log"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/manuscript/tables benchmark/logs/performance/matched_tools
        python3 scripts/manuscript/make_matched_tool_timing_table.py \
          --interpretation {input.interpretation:q} \
          --out {output:q} \
          --require-pass \
          --require-large-genome \
          > {log:q} 2>&1
        """

rule make_matched_tool_timing_figure:
    input:
        table=MATCHED_TOOL_TIMING_TABLE
    output:
        MATCHED_TOOL_TIMING_FIGURE
    log:
        "benchmark/logs/manuscript/figure_04_matched_tool_timing.log"
    conda:
        "../envs/figures.yml"
    shell:
        r"""
        mkdir -p results/manuscript/figures benchmark/logs/manuscript
        Rscript scripts/manuscript/make_performance_figures.R \
          --matched-timing {input.table:q} \
          --out-dir results/manuscript/figures \
          --formats pdf \
          > {log:q} 2>&1
        """


rule make_screening_speed_figure:
    input:
        table=SCREENING_SPEED_TABLE
    output:
        SCREENING_SPEED_FIGURE
    log:
        "benchmark/logs/manuscript/figure_05_screening_speed.log"
    conda:
        "../envs/figures.yml"
    shell:
        r"""
        mkdir -p results/manuscript/figures benchmark/logs/manuscript
        Rscript scripts/manuscript/make_performance_figures.R \
          --screening-speed {input.table:q} \
          --out-dir results/manuscript/figures \
          --formats pdf \
          > {log:q} 2>&1
        """


rule make_input_format_figure:
    input:
        table=PERFORMANCE_INPUT_FORMAT_TABLE
    output:
        PERFORMANCE_INPUT_FORMAT_FIGURE
    log:
        "benchmark/logs/manuscript/figure_06_input_format.log"
    conda:
        "../envs/figures.yml"
    shell:
        r"""
        mkdir -p results/manuscript/figures benchmark/logs/manuscript
        Rscript scripts/manuscript/make_performance_figures.R \
          --input-format {input.table:q} \
          --out-dir results/manuscript/figures \
          --formats pdf \
          > {log:q} 2>&1
        """


rule make_thread_scaling_figure:
    input:
        table=THREAD_SCALING_TABLE
    output:
        THREAD_SCALING_FIGURE
    log:
        "benchmark/logs/manuscript/figure_s02_thread_scaling.log"
    conda:
        "../envs/figures.yml"
    shell:
        r"""
        mkdir -p results/manuscript/figures benchmark/logs/manuscript
        Rscript scripts/manuscript/make_performance_figures.R \
          --thread-scaling {input.table:q} \
          --out-dir results/manuscript/figures \
          --formats pdf \
          > {log:q} 2>&1
        """


rule make_pair_screen_scaling_figure:
    input:
        table=PAIR_SCREEN_SCALING_TABLE
    output:
        PAIR_SCREEN_SCALING_FIGURE
    log:
        "benchmark/logs/manuscript/figure_s03_pair_screen_job_scaling.log"
    conda:
        "../envs/figures.yml"
    shell:
        r"""
        mkdir -p results/manuscript/figures benchmark/logs/manuscript
        Rscript scripts/manuscript/make_performance_figures.R \
          --pair-screen-scaling {input.table:q} \
          --out-dir results/manuscript/figures \
          --formats pdf \
          > {log:q} 2>&1
        """


rule make_large_genome_figure:
    input:
        table=LARGE_GENOME_TABLE
    output:
        LARGE_GENOME_FIGURE
    log:
        "benchmark/logs/manuscript/figure_s04_large_genome.log"
    conda:
        "../envs/figures.yml"
    shell:
        r"""
        mkdir -p results/manuscript/figures benchmark/logs/manuscript
        Rscript scripts/manuscript/make_performance_figures.R \
          --large-genome {input.table:q} \
          --out-dir results/manuscript/figures \
          --formats pdf \
          > {log:q} 2>&1
        """


rule manuscript_figures_all:
    input:
        PERFORMANCE_FIGURE_OUTPUTS

