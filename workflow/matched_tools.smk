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

DIGITAL_ARG = "" if INCLUDE_DIGITAL else "--skip-digital-rads"


rule all:
    input:
        "results/tables/matched_tool_benchmark_runs.tsv",
        "results/tables/matched_tool_benchmark_summary.tsv"


rule matched_tool_benchmarks:
    output:
        runs="results/tables/matched_tool_benchmark_runs.tsv",
        summary="results/tables/matched_tool_benchmark_summary.tsv"
    conda:
        "../envs/simrad.yml"
    shell:
        r"""
        mkdir -p results/tables results/raw/matched_tool_benchmarks \
          benchmark/memory/matched_tools benchmark/logs/matched_tools

        bash scripts/run_matched_tool_benchmarks.sh \
          --reference {REFERENCE:q} \
          --dataset {DATASET:q} \
          --condition {CONDITION:q} \
          --enzymes {ENZYMES:q} \
          --min {MIN_SIZE:q} \
          --max {MAX_SIZE:q} \
          --runs {RUNS:q} \
          --threads {THREADS:q} \
          --radigest {RADIGEST:q} \
          --digital-rads {DIGITAL_RADS:q} \
          {DIGITAL_ARG}
        """
