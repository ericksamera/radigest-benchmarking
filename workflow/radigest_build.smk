shell.executable("/usr/bin/bash")

RADIGEST_REPO = config.get("radigest_repo", "../radigest")
RADIGEST_REF = config.get("radigest_ref", "HEAD")
LOCAL_BIN = config.get("local_bin", ".local/bin")
BUILD_DIR = config.get("radigest_build_dir", ".local/radigest")

RADIGEST_BINARIES = [
    f"{LOCAL_BIN}/radigest",
    f"{LOCAL_BIN}/radigest-screen-pairs",
    f"{LOCAL_BIN}/radigest-rank-pairs",
    f"{LOCAL_BIN}/radigest-fit-size-model",
]

# Newer radigest checkouts may also provide radigest-plan-depth and a cached
# Go pair-screening binary. They are copied opportunistically by
# scripts/ensure_radigest.sh if present, but are not required workflow outputs.

rule all:
    input:
        RADIGEST_BINARIES,
        "results/processed/radigest_build.tsv"


rule build_radigest:
    input:
        script="scripts/ensure_radigest.sh"
    output:
        radigest=f"{LOCAL_BIN}/radigest",
        screen=f"{LOCAL_BIN}/radigest-screen-pairs",
        rank=f"{LOCAL_BIN}/radigest-rank-pairs",
        fit=f"{LOCAL_BIN}/radigest-fit-size-model",
        manifest="results/processed/radigest_build.tsv"
    log:
        "benchmark/logs/build_radigest.log"
    conda:
        "../envs/radigest-build.yml"
    params:
        repo=RADIGEST_REPO,
        ref=RADIGEST_REF,
        build_dir=BUILD_DIR,
        bin_dir=LOCAL_BIN
    shell:
        r"""
        mkdir -p benchmark/logs results/processed {params.bin_dir:q}
        bash {input.script:q} \
          --source {params.repo:q} \
          --ref {params.ref:q} \
          --out-dir {params.build_dir:q} \
          --bin-dir {params.bin_dir:q} \
          > {log:q} 2>&1
        """
