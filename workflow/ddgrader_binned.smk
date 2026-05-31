shell.executable("/usr/bin/bash")

REFERENCE = config.get("reference", "data/reference/yeast.fa")
DATASET = config.get("dataset", "yeast_small_plain")
CONDITION = config.get("condition", "B1")
ENZYMES = config.get("enzymes", "EcoRI,MseI")
ENZYME_PAIR = config.get("enzyme_pair", "EcoRI+MseI")
MIN_SIZE = str(config.get("min_size", 100))
MAX_SIZE = str(config.get("max_size", 300))
RADIGEST = config.get("radigest", ".local/bin/radigest")
DDGRADER_REPO = config.get("ddgrader_repo", "external/ddRadSeqWebTool")


rule all:
    input:
        "results/processed/comparisons/ddgrader/yeast_B1.binned.detail.tsv",
        "results/processed/comparisons/ddgrader/yeast_B1.binned.summary.tsv"


rule ddgrader_binned_cut_equivalence:
    output:
        radigest_json="results/raw/comparators/ddgrader/yeast_B1.radigest.json",
        radigest_fragments="results/raw/comparators/ddgrader/yeast_B1.radigest.fragments.tsv",
        radigest_bins="results/raw/comparators/ddgrader/yeast_B1.radigest.bins.tsv",
        radigest_summary="results/raw/comparators/ddgrader/yeast_B1.radigest.summary.tsv",
        ddgrader_raw="results/raw/comparators/ddgrader/yeast_B1.raw.csv",
        ddgrader_bins="results/raw/comparators/ddgrader/yeast_B1.bins.tsv",
        ddgrader_summary="results/raw/comparators/ddgrader/yeast_B1.summary.tsv",
        ddgrader_version="results/raw/comparators/ddgrader/yeast_B1.version.txt",
        detail="results/processed/comparisons/ddgrader/yeast_B1.binned.detail.tsv",
        summary="results/processed/comparisons/ddgrader/yeast_B1.binned.summary.tsv"
    conda:
        "../envs/ddgrader.yml"
    shell:
        r"""
        set -euo pipefail

        mkdir -p results/raw/comparators/ddgrader \
          results/processed/comparisons/ddgrader

        {RADIGEST:q} \
          -fasta {REFERENCE:q} \
          -enzymes {ENZYMES:q} \
          -min 1 \
          -max 1010 \
          -threads 1 \
          -fragments-tsv {output.radigest_fragments:q} \
          -json {output.radigest_json:q}

        python3 scripts/bin_radigest_fragments.py \
          --input {output.radigest_fragments:q} \
          --enzyme-pair {ENZYME_PAIR:q} \
          --min {MIN_SIZE:q} \
          --max {MAX_SIZE:q} \
          --out-bins {output.radigest_bins:q} \
          --out-summary {output.radigest_summary:q}

        python3 scripts/run_ddgrader_backend.py \
          --repo {DDGRADER_REPO:q} \
          --reference {REFERENCE:q} \
          --enzyme-pairs {ENZYMES:q} \
          --min {MIN_SIZE:q} \
          --max {MAX_SIZE:q} \
          --out-raw-csv {output.ddgrader_raw:q} \
          --out-bins {output.ddgrader_bins:q} \
          --out-summary {output.ddgrader_summary:q} \
          --version-log {output.ddgrader_version:q}

        python3 scripts/compare_binned_fragment_tables.py \
          --first {output.radigest_bins:q} \
          --second {output.ddgrader_bins:q} \
          --first-name radigest_binned \
          --second-name ddgRADer_backend \
          --out-detail {output.detail:q} \
          --out-summary {output.summary:q}
        """
