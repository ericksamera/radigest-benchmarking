shell.executable("/usr/bin/bash")

REFERENCE = config.get("reference", "data/reference/yeast.fa.gz")
DATASET = config.get("dataset", "yeast_small")
CONDITION = config.get("condition", "B1")
ENZYMES = config.get("enzymes", "EcoRI,MseI")
MIN_SIZE = str(config.get("min_size", 100))
MAX_SIZE = str(config.get("max_size", 300))
RUNS = str(config.get("runs", 5))
THREADS = str(config.get("threads", 1))
RADIGEST = config.get("radigest", "radigest")
DIGITAL_RADS = config.get(
    "digital_rads",
    "external/Digital_RADs/Digital_RADs.py",
)
INCLUDE_DIGITAL = str(config.get("include_digital", "false")).lower() in {
    "1",
    "true",
    "yes",
}


rule all:
    input:
        "results/tables/matched_tool_benchmark_runs.tsv",
        "results/tables/matched_tool_benchmark_summary.tsv"


rule matched_tool_benchmarks:
    output:
        runs="results/tables/matched_tool_benchmark_runs.tsv",
        summary="results/tables/matched_tool_benchmark_summary.tsv"
    params:
        reference=REFERENCE,
        dataset=DATASET,
        condition=CONDITION,
        enzymes=ENZYMES,
        min_size=MIN_SIZE,
        max_size=MAX_SIZE,
        runs=RUNS,
        threads=THREADS,
        radigest=RADIGEST,
        digital_rads=DIGITAL_RADS,
        include_digital="true" if INCLUDE_DIGITAL else "false"
    conda:
        "../envs/simrad.yml"
    shell:
        r"""
        set -euo pipefail

        mkdir -p results/tables results/raw/matched_tool_benchmarks \
          benchmark/memory/matched_tools benchmark/logs/matched_tools

        digital_args=()
        if [[ "{params.include_digital}" != "true" ]]; then
          digital_args+=(--skip-digital-rads)
        fi

        bash scripts/run_matched_tool_benchmarks.sh \
          --reference {params.reference:q} \
          --dataset {params.dataset:q} \
          --condition {params.condition:q} \
          --enzymes {params.enzymes:q} \
          --min {params.min_size:q} \
          --max {params.max_size:q} \
          --runs {params.runs:q} \
          --threads {params.threads:q} \
          --radigest {params.radigest:q} \
          --digital-rads {params.digital_rads:q} \
          "${{digital_args[@]}}"
        """
