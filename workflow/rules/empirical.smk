# Empirical-library workflow scaffold.
#
# This module makes the BAM-directory input contract executable. Public empirical
# references are downloaded through config/references.tsv; enabled local BAM
# directory rows are inventoried so downstream TLEN extraction can process every
# BAM that matches the configured glob.

import csv

EMPIRICAL_LIBRARY_MANIFEST = "config/empirical_libraries.tsv"
EMPIRICAL_PLACEHOLDER_OUTPUTS = ["results/empirical/.gitkeep"]


def _read_tsv_rows(path):
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = [
            {key: (value or "").strip() for key, value in row.items() if key}
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]
    if not rows:
        raise ValueError(f"{path}: no rows")
    return rows


EMPIRICAL_LIBRARY_ROWS = _read_tsv_rows(EMPIRICAL_LIBRARY_MANIFEST)
EMPIRICAL_ENABLED_ROWS = [
    row
    for row in EMPIRICAL_LIBRARY_ROWS
    if row.get("enabled", "false").strip().lower() == "true"
]
EMPIRICAL_LIBRARY_IDS = [row["library_id"] for row in EMPIRICAL_LIBRARY_ROWS]
EMPIRICAL_ENABLED_LIBRARY_IDS = [row["library_id"] for row in EMPIRICAL_ENABLED_ROWS]
EMPIRICAL_ROWS_BY_ID = {row["library_id"]: row for row in EMPIRICAL_LIBRARY_ROWS}

REFERENCE_ROWS_BY_ID_FOR_EMPIRICAL = {
    row["reference_id"]: row for row in _read_tsv_rows("config/references.tsv")
}
EMPIRICAL_REFERENCE_OUTPUTS = []
for row in EMPIRICAL_LIBRARY_ROWS:
    reference_id = row.get("reference_id", "")
    reference_path = row.get("reference_path", "")
    if reference_id in REFERENCE_ROWS_BY_ID_FOR_EMPIRICAL:
        reference_row = REFERENCE_ROWS_BY_ID_FOR_EMPIRICAL[reference_id]
        if reference_row["output_plain"] == reference_path:
            EMPIRICAL_REFERENCE_OUTPUTS.extend(
                [reference_row["output_gzip"], reference_row["output_plain"]]
            )
    elif reference_path.startswith("data/reference/"):
        raise ValueError(
            f"{EMPIRICAL_LIBRARY_MANIFEST}: unknown reference_id {reference_id!r}; "
            "add downloadable data/reference references to config/references.tsv"
        )
EMPIRICAL_REFERENCE_OUTPUTS = sorted(set(EMPIRICAL_REFERENCE_OUTPUTS))

EMPIRICAL_BAM_MANIFESTS = [
    f"results/empirical/{row['library_id']}/bam_manifest.tsv"
    for row in EMPIRICAL_ENABLED_ROWS
    if row.get("source_type") == "local_bam_dir"
]
EMPIRICAL_ALL_OUTPUTS = (
    [EMPIRICAL_LIBRARY_MANIFEST]
    + EMPIRICAL_PLACEHOLDER_OUTPUTS
    + EMPIRICAL_REFERENCE_OUTPUTS
    + EMPIRICAL_BAM_MANIFESTS
)


def _empirical_reference_path(wildcards):
    return EMPIRICAL_ROWS_BY_ID[wildcards.library_id]["reference_path"]


rule empirical_manifest_all:
    input:
        EMPIRICAL_LIBRARY_MANIFEST


rule empirical_references_all:
    input:
        EMPIRICAL_REFERENCE_OUTPUTS


rule empirical_bam_manifests_all:
    input:
        EMPIRICAL_BAM_MANIFESTS


rule empirical_all:
    input:
        EMPIRICAL_ALL_OUTPUTS


rule empirical_bam_manifest:
    input:
        manifest=EMPIRICAL_LIBRARY_MANIFEST,
        reference=_empirical_reference_path
    output:
        manifest="results/empirical/{library_id}/bam_manifest.tsv"
    log:
        "benchmark/logs/empirical/{library_id}.bam_manifest.log"
    conda:
        "../envs/empirical.yml"
    shell:
        r"""
        mkdir -p benchmark/logs/empirical results/empirical/{wildcards.library_id}
        python3 scripts/empirical/write_bam_manifest.py \
          --manifest {input.manifest:q} \
          --library-id {wildcards.library_id:q} \
          --out {output.manifest:q} \
          > {log:q} 2>&1
        """
