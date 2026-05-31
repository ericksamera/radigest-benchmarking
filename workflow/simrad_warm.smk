shell.executable("/usr/bin/bash")

REFERENCE = config.get("reference", "data/reference/yeast.fa.gz")
DATASET = config.get("dataset", "yeast_small")
CONDITION = config.get("condition", "B1")
ENZYME1 = config.get("enzyme1", "EcoRI")
ENZYME2 = config.get("enzyme2", "MseI")
MIN_SIZE = str(config.get("min_size", 100))
MAX_SIZE = str(config.get("max_size", 300))
RUNS = str(config.get("runs", 5))


rule all:
    input:
        "results/tables/simrad_warm_runs.tsv",
        "results/tables/simrad_warm_summary.tsv",
        "results/tables/simrad_warm_version.txt",
        "benchmark/memory/matched_tools/simrad_warm_package_reload_reference.time",
        "results/tables/simrad_reuse_reference_runs.tsv",
        "results/tables/simrad_reuse_reference_summary.tsv",
        "results/tables/simrad_reuse_reference_version.txt",
        "benchmark/memory/matched_tools/simrad_reuse_reference.time"


rule simrad_warm_reload_reference:
    output:
        runs="results/tables/simrad_warm_runs.tsv",
        summary="results/tables/simrad_warm_summary.tsv",
        version="results/tables/simrad_warm_version.txt",
        time="benchmark/memory/matched_tools/simrad_warm_package_reload_reference.time"
    log:
        stdout="benchmark/logs/matched_tools/simrad_warm.stdout.log",
        stderr="benchmark/logs/matched_tools/simrad_warm.stderr.log"
    conda:
        "../envs/simrad.yml"
    shell:
        r"""
        mkdir -p results/tables benchmark/memory/matched_tools benchmark/logs/matched_tools

        /usr/bin/time -v \
          -o {output.time:q} \
          Rscript scripts/run_simrad_warm_benchmark.R \
            --reference {REFERENCE:q} \
            --enzyme1 {ENZYME1:q} \
            --enzyme2 {ENZYME2:q} \
            --min {MIN_SIZE:q} \
            --max {MAX_SIZE:q} \
            --runs {RUNS:q} \
            --enzymes-tsv config/enzymes.tsv \
            --out-runs {output.runs:q} \
            --out-summary {output.summary:q} \
            --version-log {output.version:q} \
            > {log.stdout:q} \
            2> {log.stderr:q}
        """


rule simrad_warm_reuse_reference:
    output:
        runs="results/tables/simrad_reuse_reference_runs.tsv",
        summary="results/tables/simrad_reuse_reference_summary.tsv",
        version="results/tables/simrad_reuse_reference_version.txt",
        time="benchmark/memory/matched_tools/simrad_reuse_reference.time"
    log:
        stdout="benchmark/logs/matched_tools/simrad_reuse_reference.stdout.log",
        stderr="benchmark/logs/matched_tools/simrad_reuse_reference.stderr.log"
    conda:
        "../envs/simrad.yml"
    shell:
        r"""
        mkdir -p results/tables benchmark/memory/matched_tools benchmark/logs/matched_tools

        /usr/bin/time -v \
          -o {output.time:q} \
          Rscript scripts/run_simrad_warm_benchmark.R \
            --reference {REFERENCE:q} \
            --enzyme1 {ENZYME1:q} \
            --enzyme2 {ENZYME2:q} \
            --min {MIN_SIZE:q} \
            --max {MAX_SIZE:q} \
            --runs {RUNS:q} \
            --enzymes-tsv config/enzymes.tsv \
            --out-runs {output.runs:q} \
            --out-summary {output.summary:q} \
            --version-log {output.version:q} \
            --reuse-reference \
            > {log.stdout:q} \
            2> {log.stderr:q}
        """
