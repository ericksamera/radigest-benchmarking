shell.executable("/usr/bin/bash")

import re


def split_config_values(value, default=None):
    if value is None:
        value = default
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(x).strip() for x in value if str(x).strip()]
    return [x for x in re.split(r"[,\s]+", str(value).strip()) if x]


def numbered_runs(value, default):
    return [str(i) for i in range(1, int(config.get(value, default)) + 1)]


REFERENCE = config.get("reference", "data/reference/moderate.fa")
DATASET = config.get("dataset", "cannabis_pink_pepper_plain")

RADIGEST = config.get("radigest", ".local/bin/radigest")
RADIGEST_SCREEN_PAIRS = config.get(
    "radigest_screen_pairs",
    ".local/bin/radigest-screen-pairs",
)

THREAD_CONDITIONS = split_config_values(
    config.get("thread_scaling_conditions"),
    "B1,B2",
)
THREAD_MODES = split_config_values(
    config.get("thread_scaling_modes"),
    "json,fragments_tsv",
)
THREAD_VALUES = split_config_values(
    config.get("thread_scaling_threads"),
    "1,2,4,8",
)
THREAD_RUNS = numbered_runs("thread_scaling_runs", 7)

PAIR_SCREEN_JOBS = split_config_values(
    config.get("pair_screen_jobs"),
    "1,2,4,8",
)
PAIR_SCREEN_RUNS = numbered_runs("pair_screen_runs", 3)
PAIR_SCREEN_STEM_PREFIX = config.get("pair_screen_stem_prefix", "cannabis")

CONDITION_DEFAULTS = {
    "B1": {"enzymes": "EcoRI,MseI", "min_size": "100", "max_size": "300"},
    "B2": {"enzymes": "PstI,MspI", "min_size": "250", "max_size": "500"},
}


def condition_value(condition, key):
    conditions = config.get("thread_scaling_condition_params", {})
    if condition in conditions and key in conditions[condition]:
        return str(conditions[condition][key])
    if condition in CONDITION_DEFAULTS and key in CONDITION_DEFAULTS[condition]:
        return CONDITION_DEFAULTS[condition][key]
    raise ValueError(f"missing thread-scaling {key} for condition {condition!r}")


RADIGEST_THREAD_BASE = (
    f"{DATASET}__{{condition}}__{{mode}}__threads{{threads}}__run{{run}}"
)
PAIR_SCREEN_BASE = f"{PAIR_SCREEN_STEM_PREFIX}_jobs{{jobs}}_run{{run}}"

RADIGEST_THREAD_MARKERS = expand(
    f"results/processed/scaling/radigest_thread_scaling/{RADIGEST_THREAD_BASE}.done",
    condition=THREAD_CONDITIONS,
    mode=THREAD_MODES,
    threads=THREAD_VALUES,
    run=THREAD_RUNS,
)
RADIGEST_THREAD_TIMES = expand(
    f"benchmark/memory/radigest_thread_scaling/{RADIGEST_THREAD_BASE}.time",
    condition=THREAD_CONDITIONS,
    mode=THREAD_MODES,
    threads=THREAD_VALUES,
    run=THREAD_RUNS,
)
PAIR_SCREEN_DIRS = expand(
    f"results/raw/pair_screen_scaling/{PAIR_SCREEN_BASE}",
    jobs=PAIR_SCREEN_JOBS,
    run=PAIR_SCREEN_RUNS,
)
PAIR_SCREEN_TIMES = expand(
    f"benchmark/memory/pair_screen_scaling/{PAIR_SCREEN_BASE}.time",
    jobs=PAIR_SCREEN_JOBS,
    run=PAIR_SCREEN_RUNS,
)


rule all:
    input:
        "results/tables/radigest_thread_scaling_summary.tsv",
        "results/tables/pair_screen_scaling_summary.tsv"


rule scaling_all:
    input:
        "results/tables/radigest_thread_scaling_summary.tsv",
        "results/tables/pair_screen_scaling_summary.tsv"


rule radigest_thread_scaling_all:
    input:
        "results/tables/radigest_thread_scaling_summary.tsv"


rule pair_screen_scaling_all:
    input:
        "results/tables/pair_screen_scaling_summary.tsv"


rule run_radigest_thread_scaling:
    input:
        reference=REFERENCE
    output:
        done=f"results/processed/scaling/radigest_thread_scaling/{RADIGEST_THREAD_BASE}.done",
        json=f"results/raw/radigest_thread_scaling/{RADIGEST_THREAD_BASE}.json",
        time=f"benchmark/memory/radigest_thread_scaling/{RADIGEST_THREAD_BASE}.time",
        stdout=f"benchmark/logs/radigest_thread_scaling/{RADIGEST_THREAD_BASE}.stdout.log",
        stderr=f"benchmark/logs/radigest_thread_scaling/{RADIGEST_THREAD_BASE}.stderr.log",
        command=f"benchmark/logs/radigest_thread_scaling/{RADIGEST_THREAD_BASE}.command.txt",
    params:
        radigest=RADIGEST,
        enzymes=lambda wc: condition_value(wc.condition, "enzymes"),
        min_size=lambda wc: condition_value(wc.condition, "min_size"),
        max_size=lambda wc: condition_value(wc.condition, "max_size"),
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        set -euo pipefail

        mkdir -p \
          results/raw/radigest_thread_scaling \
          results/processed/scaling/radigest_thread_scaling \
          benchmark/memory/radigest_thread_scaling \
          benchmark/logs/radigest_thread_scaling

        cmd=(
          {params.radigest:q}
          -fasta {input.reference:q}
          -enzymes {params.enzymes:q}
          -min {params.min_size:q}
          -max {params.max_size:q}
          -threads {wildcards.threads:q}
        )

        primary_out={output.json:q}
        case {wildcards.mode:q} in
          json)
            ;;
          gff)
            primary_out="results/raw/radigest_thread_scaling/{DATASET}__{wildcards.condition}__{wildcards.mode}__threads{wildcards.threads}__run{wildcards.run}.gff3"
            cmd+=( -gff "$primary_out" )
            ;;
          fragments_tsv)
            primary_out="results/raw/radigest_thread_scaling/{DATASET}__{wildcards.condition}__{wildcards.mode}__threads{wildcards.threads}__run{wildcards.run}.fragments.tsv"
            cmd+=( -fragments-tsv "$primary_out" )
            ;;
          fragments_fasta)
            primary_out="results/raw/radigest_thread_scaling/{DATASET}__{wildcards.condition}__{wildcards.mode}__threads{wildcards.threads}__run{wildcards.run}.fragments.fa"
            cmd+=( -fragments-fasta "$primary_out" )
            ;;
          *)
            echo "error: unsupported mode: {wildcards.mode}" >&2
            exit 2
            ;;
        esac

        cmd+=( -json {output.json:q} )

        {{
          printf "dataset=%s\n" {DATASET:q}
          printf "condition=%s\n" {wildcards.condition:q}
          printf "mode=%s\n" {wildcards.mode:q}
          printf "threads=%s\n" {wildcards.threads:q}
          printf "run=%s\n" {wildcards.run:q}
          printf "reference=%s\n" {input.reference:q}
          printf "primary_output=%s\n" "$primary_out"
          printf "command="
          printf "%q " "${{cmd[@]}}"
          printf "\n"
        }} > {output.command:q}

        echo "[RUN] {DATASET}__{wildcards.condition}__{wildcards.mode}__threads{wildcards.threads}__run{wildcards.run}" >&2
        /usr/bin/time -v \
          -o {output.time:q} \
          "${{cmd[@]}}" \
          > {output.stdout:q} \
          2> {output.stderr:q}

        touch {output.done:q}
        """


rule summarize_radigest_thread_scaling:
    input:
        markers=RADIGEST_THREAD_MARKERS,
        times=RADIGEST_THREAD_TIMES,
    output:
        runs="results/tables/radigest_thread_scaling_runs.tsv",
        summary="results/tables/radigest_thread_scaling_summary.tsv",
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        set -euo pipefail
        mkdir -p results/tables
        python3 scripts/benchmarks/summarize_radigest_thread_scaling.py \
          --root results/raw/radigest_thread_scaling \
          --time-dir benchmark/memory/radigest_thread_scaling \
          --out-runs {output.runs:q} \
          --out-summary {output.summary:q}
        """


rule run_pair_screen_scaling:
    input:
        reference=REFERENCE,
        enzymes=config.get("pair_screen_enzymes", "config/candidate_enzymes.txt"),
    output:
        outdir=directory(f"results/raw/pair_screen_scaling/{PAIR_SCREEN_BASE}"),
        time=f"benchmark/memory/pair_screen_scaling/{PAIR_SCREEN_BASE}.time",
        stdout=f"benchmark/logs/pair_screen_scaling/{PAIR_SCREEN_BASE}.stdout.log",
        stderr=f"benchmark/logs/pair_screen_scaling/{PAIR_SCREEN_BASE}.stderr.log",
    params:
        radigest=RADIGEST,
        screen_pairs=RADIGEST_SCREEN_PAIRS,
        min_size=str(config.get("pair_screen_min_size", config.get("min_size", 300))),
        max_size=str(config.get("pair_screen_max_size", config.get("max_size", 600))),
        score_min=str(config.get("pair_screen_score_min", config.get("score_min", 1))),
        score_max=str(config.get("pair_screen_score_max", config.get("score_max", 2000))),
        size_model=str(config.get("pair_screen_size_model", config.get("size_model", "hard"))),
        radigest_threads=str(config.get("pair_screen_radigest_threads", config.get("radigest_threads", 1))),
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        set -euo pipefail

        mkdir -p \
          results/raw/pair_screen_scaling \
          benchmark/memory/pair_screen_scaling \
          benchmark/logs/pair_screen_scaling

        resolve_exe() {{
          local exe="$1"
          if [[ -x "$exe" ]]; then
            realpath "$exe"
          else
            command -v "$exe"
          fi
        }}

        screen_pairs="$(resolve_exe {params.screen_pairs:q})"
        radigest="$(resolve_exe {params.radigest:q})"
        export PATH="$(dirname "$screen_pairs"):$(dirname "$radigest"):$PATH"

        rm -rf {output.outdir:q}
        mkdir -p {output.outdir:q}

        echo "[RUN] {PAIR_SCREEN_STEM_PREFIX}_jobs{wildcards.jobs}_run{wildcards.run}" >&2
        /usr/bin/time -v \
          -o {output.time:q} \
          "$screen_pairs" \
            --radigest "$radigest" \
            --fasta {input.reference:q} \
            --enzymes {input.enzymes:q} \
            --min {params.min_size:q} \
            --max {params.max_size:q} \
            --score-min {params.score_min:q} \
            --score-max {params.score_max:q} \
            --size-model {params.size_model:q} \
            --jobs {wildcards.jobs:q} \
            --radigest-threads {params.radigest_threads:q} \
            --out-dir {output.outdir:q} \
          > {output.stdout:q} \
          2> {output.stderr:q}
        """


rule summarize_pair_screen_scaling:
    input:
        outdirs=PAIR_SCREEN_DIRS,
        times=PAIR_SCREEN_TIMES,
    output:
        runs="results/tables/pair_screen_scaling_runs.tsv",
        summary="results/tables/pair_screen_scaling_summary.tsv",
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        set -euo pipefail
        mkdir -p results/tables
        python3 scripts/benchmarks/summarize_pair_screen_scaling.py \
          --dataset {DATASET:q} \
          --stem-prefix {PAIR_SCREEN_STEM_PREFIX:q} \
          --time-dir benchmark/memory/pair_screen_scaling \
          --output-root results/raw/pair_screen_scaling \
          --out-runs {output.runs:q} \
          --out-summary {output.summary:q}
        """
