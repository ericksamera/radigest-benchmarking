# Reference acquisition rules for the clean v2 workflow.

import csv

REFERENCE_MANIFEST = "config/references.tsv"
REFERENCE_CHECKSUMS = "results/references/reference_checksums.tsv"


def _read_reference_rows(path):
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = [row for row in reader if any((value or "").strip() for value in row.values())]
    if not rows:
        raise ValueError(f"{path}: no reference rows")
    return rows


REFERENCE_ROWS = _read_reference_rows(REFERENCE_MANIFEST)
REFERENCE_GZIP_OUTPUTS = [row["output_gzip"] for row in REFERENCE_ROWS]
REFERENCE_PLAIN_OUTPUTS = [row["output_plain"] for row in REFERENCE_ROWS]
REFERENCE_FASTA_OUTPUTS = REFERENCE_GZIP_OUTPUTS + REFERENCE_PLAIN_OUTPUTS
REFERENCE_ALL_OUTPUTS = REFERENCE_FASTA_OUTPUTS + [REFERENCE_CHECKSUMS]


rule download_reference_gzip:
    input:
        manifest=REFERENCE_MANIFEST
    output:
        gzip="data/reference/{reference_id}.fa.gz"
    log:
        "benchmark/logs/references/{reference_id}.download.log"
    conda:
        "../envs/reference.yml"
    shell:
        r"""
        mkdir -p benchmark/logs/references data/reference
        python3 scripts/reference/fetch_ncbi_reference.py \
          --manifest {input.manifest:q} \
          --reference-id {wildcards.reference_id:q} \
          --output {output.gzip:q} \
          > {log:q} 2>&1
        """


rule prepare_plain_reference:
    input:
        gzip="data/reference/{reference_id}.fa.gz"
    output:
        plain="data/reference/{reference_id}.fa"
    log:
        "benchmark/logs/references/{reference_id}.plain.log"
    conda:
        "../envs/reference.yml"
    shell:
        r"""
        mkdir -p benchmark/logs/references data/reference
        python3 scripts/reference/prepare_plain_reference.py \
          --source {input.gzip:q} \
          --dest {output.plain:q} \
          > {log:q} 2>&1
        """


rule reference_checksums:
    input:
        manifest=REFERENCE_MANIFEST,
        fastas=REFERENCE_FASTA_OUTPUTS
    output:
        checksums=REFERENCE_CHECKSUMS
    log:
        "benchmark/logs/references/reference_checksums.log"
    conda:
        "../envs/reference.yml"
    shell:
        r"""
        mkdir -p benchmark/logs/references results/references
        python3 scripts/reference/write_reference_checksums.py \
          --manifest {input.manifest:q} \
          --out {output.checksums:q} \
          > {log:q} 2>&1
        """
