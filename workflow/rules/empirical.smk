# Empirical-library workflow scaffold.
#
# This module makes the BAM-directory input contract executable. Public empirical
# references are downloaded through config/references.tsv; enabled local BAM
# directory rows are inventoried and each matching BAM is converted into TLEN
# observations for downstream empirical size-selection model fitting.

import csv
import re
from pathlib import Path

EMPIRICAL_LIBRARY_MANIFEST = "config/empirical_libraries.tsv"
EMPIRICAL_PLACEHOLDER_OUTPUTS = ["results/empirical/.gitkeep"]

# Keep pooled library outputs from matching nested per-BAM paths such as
# results/empirical/<library_id>/bams/<bam_id>/tlens.txt.
wildcard_constraints:
    library_id=r"[^/]+",
    bam_id=r"[^/]+"


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


def _safe_bam_id(path):
    name = Path(path).name
    if name.endswith(".bam"):
        name = name[:-4]
    elif name.endswith(".cram"):
        name = name[:-5]
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._")
    if not name:
        raise ValueError(f"could not derive bam_id from {path}")
    return name


def _matching_bam_paths(row):
    if row.get("source_type") != "local_bam_dir":
        return []
    bam_dir = Path(row["bam_dir"])
    if not bam_dir.is_dir():
        return []
    return sorted(
        path
        for path in bam_dir.glob(row["bam_glob"])
        if path.is_file() or path.is_symlink()
    )


def _empirical_bam_sample_rows():
    rows = []
    for row in EMPIRICAL_ENABLED_ROWS:
        if row.get("source_type") != "local_bam_dir":
            continue
        seen_ids = {}
        for bam_path in _matching_bam_paths(row):
            bam_id = _safe_bam_id(bam_path)
            if bam_id in seen_ids:
                raise ValueError(
                    f"{row['library_id']}: duplicate derived bam_id {bam_id!r} for "
                    f"{seen_ids[bam_id]} and {bam_path}"
                )
            seen_ids[bam_id] = bam_path
            sample_row = dict(row)
            sample_row["bam_id"] = bam_id
            sample_row["bam_path"] = str(bam_path)
            rows.append(sample_row)
    return rows


EMPIRICAL_BAM_SAMPLE_ROWS = _empirical_bam_sample_rows()
EMPIRICAL_BAM_SAMPLE_BY_KEY = {
    (row["library_id"], row["bam_id"]): row for row in EMPIRICAL_BAM_SAMPLE_ROWS
}
EMPIRICAL_ENABLED_BAM_LIBRARY_IDS = sorted(
    {row["library_id"] for row in EMPIRICAL_BAM_SAMPLE_ROWS}
)

EMPIRICAL_BAM_MANIFESTS = [
    f"results/empirical/{row['library_id']}/bam_manifest.tsv"
    for row in EMPIRICAL_ENABLED_ROWS
    if row.get("source_type") == "local_bam_dir"
]
EMPIRICAL_PER_BAM_TLEN_OUTPUTS = []
for row in EMPIRICAL_BAM_SAMPLE_ROWS:
    prefix = f"results/empirical/{row['library_id']}/bams/{row['bam_id']}"
    EMPIRICAL_PER_BAM_TLEN_OUTPUTS.extend(
        [
            f"{prefix}/tlens.txt",
            f"{prefix}/tlen_histogram.tsv",
            f"{prefix}/tlen_qc.tsv",
        ]
    )
EMPIRICAL_LIBRARY_TLEN_OUTPUTS = []
for library_id in EMPIRICAL_ENABLED_BAM_LIBRARY_IDS:
    EMPIRICAL_LIBRARY_TLEN_OUTPUTS.extend(
        [
            f"results/empirical/{library_id}/tlens.txt",
            f"results/empirical/{library_id}/tlen_histogram.tsv",
            f"results/empirical/{library_id}/tlen_qc.tsv",
        ]
    )
EMPIRICAL_TLEN_OUTPUTS = EMPIRICAL_PER_BAM_TLEN_OUTPUTS + EMPIRICAL_LIBRARY_TLEN_OUTPUTS
EMPIRICAL_ALL_OUTPUTS = (
    [EMPIRICAL_LIBRARY_MANIFEST]
    + EMPIRICAL_PLACEHOLDER_OUTPUTS
    + EMPIRICAL_REFERENCE_OUTPUTS
    + EMPIRICAL_BAM_MANIFESTS
    + EMPIRICAL_TLEN_OUTPUTS
)


def _empirical_reference_path(wildcards):
    return EMPIRICAL_ROWS_BY_ID[wildcards.library_id]["reference_path"]


def _empirical_bam_paths(wildcards):
    row = EMPIRICAL_ROWS_BY_ID[wildcards.library_id]
    return [str(path) for path in _matching_bam_paths(row)]


def _empirical_bam_sample_row(wildcards):
    key = (wildcards.library_id, wildcards.bam_id)
    if key not in EMPIRICAL_BAM_SAMPLE_BY_KEY:
        raise ValueError(
            f"unknown empirical BAM sample library_id={wildcards.library_id!r} "
            f"bam_id={wildcards.bam_id!r}"
        )
    return EMPIRICAL_BAM_SAMPLE_BY_KEY[key]


def _empirical_bam_path(wildcards):
    return _empirical_bam_sample_row(wildcards)["bam_path"]


def _empirical_library_bam_ids(library_id):
    return [
        row["bam_id"]
        for row in EMPIRICAL_BAM_SAMPLE_ROWS
        if row["library_id"] == library_id
    ]


def _empirical_library_tlen_files(wildcards):
    return [
        f"results/empirical/{wildcards.library_id}/bams/{bam_id}/tlens.txt"
        for bam_id in _empirical_library_bam_ids(wildcards.library_id)
    ]


def _empirical_library_histogram_files(wildcards):
    return [
        f"results/empirical/{wildcards.library_id}/bams/{bam_id}/tlen_histogram.tsv"
        for bam_id in _empirical_library_bam_ids(wildcards.library_id)
    ]


def _empirical_library_qc_files(wildcards):
    return [
        f"results/empirical/{wildcards.library_id}/bams/{bam_id}/tlen_qc.tsv"
        for bam_id in _empirical_library_bam_ids(wildcards.library_id)
    ]


def _empirical_param(wildcards, name):
    return _empirical_bam_sample_row(wildcards)[name]


rule empirical_manifest_all:
    input:
        EMPIRICAL_LIBRARY_MANIFEST


rule empirical_references_all:
    input:
        EMPIRICAL_REFERENCE_OUTPUTS


rule empirical_bam_manifests_all:
    input:
        EMPIRICAL_BAM_MANIFESTS


rule empirical_tlens_all:
    input:
        EMPIRICAL_BAM_MANIFESTS + EMPIRICAL_TLEN_OUTPUTS


rule empirical_all:
    input:
        EMPIRICAL_ALL_OUTPUTS


rule empirical_bam_manifest:
    input:
        manifest=EMPIRICAL_LIBRARY_MANIFEST,
        reference=_empirical_reference_path,
        bams=_empirical_bam_paths
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


rule empirical_extract_tlens:
    input:
        bam_manifest="results/empirical/{library_id}/bam_manifest.tsv",
        bam=_empirical_bam_path
    output:
        tlens="results/empirical/{library_id}/bams/{bam_id}/tlens.txt",
        histogram="results/empirical/{library_id}/bams/{bam_id}/tlen_histogram.tsv",
        qc="results/empirical/{library_id}/bams/{bam_id}/tlen_qc.tsv"
    params:
        reference_id=lambda wildcards: _empirical_param(wildcards, "reference_id"),
        reference_path=lambda wildcards: _empirical_param(wildcards, "reference_path"),
        enzyme_1=lambda wildcards: _empirical_param(wildcards, "enzyme_1"),
        enzyme_2=lambda wildcards: _empirical_param(wildcards, "enzyme_2"),
        min_size=lambda wildcards: _empirical_param(wildcards, "min_size"),
        max_size=lambda wildcards: _empirical_param(wildcards, "max_size"),
        score_min=lambda wildcards: _empirical_param(wildcards, "score_min"),
        score_max=lambda wildcards: _empirical_param(wildcards, "score_max"),
        size_model=lambda wildcards: _empirical_param(wildcards, "size_model"),
        min_mapq=lambda wildcards: _empirical_param(wildcards, "min_mapq"),
        exclude_duplicates=lambda wildcards: _empirical_param(
            wildcards, "exclude_duplicates"
        ),
        max_tlen=lambda wildcards: _empirical_param(wildcards, "max_tlen")
    log:
        "benchmark/logs/empirical/{library_id}.{bam_id}.extract_tlens.log"
    conda:
        "../envs/empirical.yml"
    shell:
        r"""
        mkdir -p benchmark/logs/empirical \
          results/empirical/{wildcards.library_id}/bams/{wildcards.bam_id}
        python3 scripts/empirical/extract_tlens.py \
          --bam {input.bam:q} \
          --library-id {wildcards.library_id:q} \
          --bam-id {wildcards.bam_id:q} \
          --reference-id {params.reference_id:q} \
          --reference-path {params.reference_path:q} \
          --enzyme-1 {params.enzyme_1:q} \
          --enzyme-2 {params.enzyme_2:q} \
          --min-size {params.min_size:q} \
          --max-size {params.max_size:q} \
          --score-min {params.score_min:q} \
          --score-max {params.score_max:q} \
          --size-model {params.size_model:q} \
          --min-mapq {params.min_mapq:q} \
          --exclude-duplicates {params.exclude_duplicates:q} \
          --max-tlen {params.max_tlen:q} \
          --tlens-out {output.tlens:q} \
          --hist-out {output.histogram:q} \
          --qc-out {output.qc:q} \
          > {log:q} 2>&1
        """


rule empirical_combine_tlens:
    input:
        tlens=_empirical_library_tlen_files,
        histograms=_empirical_library_histogram_files,
        qc_tables=_empirical_library_qc_files
    output:
        tlens="results/empirical/{library_id}/tlens.txt",
        histogram="results/empirical/{library_id}/tlen_histogram.tsv",
        qc="results/empirical/{library_id}/tlen_qc.tsv"
    log:
        "benchmark/logs/empirical/{library_id}.combine_tlens.log"
    conda:
        "../envs/empirical.yml"
    shell:
        r"""
        mkdir -p benchmark/logs/empirical results/empirical/{wildcards.library_id}
        python3 scripts/empirical/combine_tlens.py \
          --library-id {wildcards.library_id:q} \
          --tlens {input.tlens:q} \
          --histograms {input.histograms:q} \
          --qc-tables {input.qc_tables:q} \
          --tlens-out {output.tlens:q} \
          --hist-out {output.histogram:q} \
          --qc-out {output.qc:q} \
          > {log:q} 2>&1
        """
