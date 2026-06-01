shell.executable("/usr/bin/bash")

REFERENCE = config.get("reference", "data/reference/yeast.fa")
DATASET = config.get("dataset", "yeast_small_plain")
ENZYMES = config.get("enzymes", "config/candidate_enzymes.txt")
MIN_SIZE = str(config.get("min_size", 300))
MAX_SIZE = str(config.get("max_size", 600))
SCORE_MIN = str(config.get("score_min", 1))
SCORE_MAX = str(config.get("score_max", 2000))
SIZE_MODEL = config.get("size_model", "hard")
RUNS = str(config.get("runs", 5))
RADIGEST = config.get("radigest", ".local/bin/radigest")
RADIGEST_SCREEN_PAIRS = config.get(
    "radigest_screen_pairs",
    ".local/bin/radigest-screen-pairs",
)
DDGRADER_REPO = config.get("ddgrader_repo", "external/ddRadSeqWebTool")
JOBS = str(config.get("jobs", 2))
RADIGEST_THREADS = str(config.get("radigest_threads", 1))


rule all:
    input:
        "results/tables/screening_speed_runs.tsv",
        "results/tables/screening_speed_summary.tsv"


rule screening_speed:
    output:
        runs="results/tables/screening_speed_runs.tsv",
        summary="results/tables/screening_speed_summary.tsv"
    conda:
        "../envs/ddgrader.yml"
    shell:
        r"""
        set -euo pipefail

        bash scripts/benchmarks/run_screening_speed_benchmark.sh \
          --reference {REFERENCE:q} \
          --dataset {DATASET:q} \
          --enzymes {ENZYMES:q} \
          --min {MIN_SIZE:q} \
          --max {MAX_SIZE:q} \
          --score-min {SCORE_MIN:q} \
          --score-max {SCORE_MAX:q} \
          --size-model {SIZE_MODEL:q} \
          --runs {RUNS:q} \
          --radigest-screen-pairs {RADIGEST_SCREEN_PAIRS:q} \
          --radigest {RADIGEST:q} \
          --ddgrader-repo {DDGRADER_REPO:q} \
          --jobs {JOBS:q} \
          --radigest-threads {RADIGEST_THREADS:q}
        """
