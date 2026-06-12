# Empirical-library workflow scaffold.
#
# This module makes the BAM-directory input contract executable. Public empirical
# references are downloaded through config/references.tsv; enabled local BAM
# directory rows are inventoried and each matching BAM is converted into TLEN
# observations for downstream empirical size-selection model fitting.

import csv
import re
from pathlib import Path

EMPIRICAL_LIBRARY_MANIFEST = config.get(
    "empirical_libraries", "config/empirical_libraries.tsv"
)
EMPIRICAL_SRA_RUN_MANIFEST = "config/empirical_sra_runs.tsv"
EMPIRICAL_DEPTH_VALIDATION_CASES = config.get(
    "empirical_depth_validation_cases", "config/empirical_depth_validation_cases.tsv"
)
EMPIRICAL_SNP_PANEL_CASES = config.get("snp_panel_cases", "config/snp_panel_cases.tsv")
EMPIRICAL_DEPTH_VALIDATION_TABLE = (
    "results/manuscript/tables/table_08_empirical_depth_validation.tsv"
)
EMPIRICAL_DEPTH_VALIDATION_MANUSCRIPT_FIGURE = (
    "results/manuscript/figures/figure_07_empirical_depth_validation.pdf"
)
EMPIRICAL_SIZE_SELECTION_SUMMARY_FIGURE = (
    "results/manuscript/figures/figure_03_empirical_size_selection_summary.pdf"
)
EMPIRICAL_PLACEHOLDER_OUTPUTS = ["results/empirical/.gitkeep"]


# Keep pooled library outputs from matching nested per-BAM paths such as
# results/empirical/<library_id>/bams/<bam_id>/tlens.txt.
wildcard_constraints:
    library_id=r"[^/]+",
    bam_id=r"[^/]+",
    run_accession=r"SRR[0-9]+",
    prediction_mode=r"raw|hard",
    snp_panel_case_id=r"[^/]+",


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


def _read_optional_tsv_rows(path):
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [
            {key: (value or "").strip() for key, value in row.items() if key}
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]


EMPIRICAL_LIBRARY_ROWS = _read_tsv_rows(EMPIRICAL_LIBRARY_MANIFEST)
EMPIRICAL_ENABLED_ROWS = [
    row
    for row in EMPIRICAL_LIBRARY_ROWS
    if row.get("enabled", "false").strip().lower() == "true"
]
EMPIRICAL_LIBRARY_IDS = [row["library_id"] for row in EMPIRICAL_LIBRARY_ROWS]
EMPIRICAL_ENABLED_LIBRARY_IDS = [row["library_id"] for row in EMPIRICAL_ENABLED_ROWS]
EMPIRICAL_ROWS_BY_ID = {row["library_id"]: row for row in EMPIRICAL_LIBRARY_ROWS}
EMPIRICAL_ENABLED_ROWS_BY_ID = {
    row["library_id"]: row for row in EMPIRICAL_ENABLED_ROWS
}

EMPIRICAL_DEPTH_VALIDATION_ROWS = [
    row
    for row in _read_tsv_rows(EMPIRICAL_DEPTH_VALIDATION_CASES)
    if row.get("enabled", "false").strip().lower() == "true"
]
EMPIRICAL_DEPTH_VALIDATION_ROWS = [
    row
    for row in EMPIRICAL_DEPTH_VALIDATION_ROWS
    if row["library_id"] in EMPIRICAL_ROWS_BY_ID
    and EMPIRICAL_ROWS_BY_ID[row["library_id"]].get("enabled", "false").strip().lower()
    == "true"
]
EMPIRICAL_DEPTH_VALIDATION_BY_LIBRARY = {
    row["library_id"]: row for row in EMPIRICAL_DEPTH_VALIDATION_ROWS
}
EMPIRICAL_DEPTH_VALIDATION_LIBRARY_IDS = sorted(EMPIRICAL_DEPTH_VALIDATION_BY_LIBRARY)
EMPIRICAL_DEPTH_VALIDATION_TABLES = (
    [EMPIRICAL_DEPTH_VALIDATION_TABLE] if EMPIRICAL_DEPTH_VALIDATION_LIBRARY_IDS else []
)

EMPIRICAL_SNP_PANEL_ROWS = [
    row
    for row in _read_tsv_rows(EMPIRICAL_SNP_PANEL_CASES)
    if row.get("enabled", "false").strip().lower() == "true"
]
EMPIRICAL_SNP_PANEL_ROWS = [
    row
    for row in EMPIRICAL_SNP_PANEL_ROWS
    if row.get("library_id", "") in EMPIRICAL_ROWS_BY_ID
    and EMPIRICAL_ROWS_BY_ID[row["library_id"]].get("enabled", "false").strip().lower()
    == "true"
]
EMPIRICAL_SNP_PANEL_BY_CASE = {row["case_id"]: row for row in EMPIRICAL_SNP_PANEL_ROWS}
EMPIRICAL_SNP_PANEL_CASE_IDS = sorted(EMPIRICAL_SNP_PANEL_BY_CASE)

EMPIRICAL_SRA_RUN_ROWS = []
for row in _read_optional_tsv_rows(EMPIRICAL_SRA_RUN_MANIFEST):
    parent = EMPIRICAL_ENABLED_ROWS_BY_ID.get(row.get("library_id", ""))
    if parent is None:
        continue
    if parent.get("source_type") != "sra_fastq":
        continue
    if row.get("enabled", "false").lower() != "true":
        continue
    if row.get("include", "false").lower() != "true":
        continue
    EMPIRICAL_SRA_RUN_ROWS.append(row)
EMPIRICAL_SRA_RUNS_BY_LIBRARY = {}
for row in EMPIRICAL_SRA_RUN_ROWS:
    EMPIRICAL_SRA_RUNS_BY_LIBRARY.setdefault(row["library_id"], []).append(row)

REFERENCE_ROWS_BY_ID_FOR_EMPIRICAL = {
    row["reference_id"]: row for row in _read_tsv_rows("config/references.tsv")
}
EMPIRICAL_REFERENCE_OUTPUTS = []
for row in EMPIRICAL_ENABLED_ROWS:
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
        library_id = row["library_id"]
        source_type = row.get("source_type")
        seen_ids = {}
        if source_type == "local_bam_dir":
            for bam_path in _matching_bam_paths(row):
                bam_id = _safe_bam_id(bam_path)
                if bam_id in seen_ids:
                    raise ValueError(
                        f"{library_id}: duplicate derived bam_id {bam_id!r} for "
                        f"{seen_ids[bam_id]} and {bam_path}"
                    )
                seen_ids[bam_id] = str(bam_path)
                sample_row = dict(row)
                sample_row["bam_id"] = bam_id
                sample_row["bam_path"] = str(bam_path)
                rows.append(sample_row)
        elif source_type == "sra_fastq":
            for sra_row in EMPIRICAL_SRA_RUNS_BY_LIBRARY.get(library_id, []):
                bam_id = sra_row["run_accession"]
                bam_path = f"data/empirical/{library_id}/bam/{bam_id}.bam"
                if bam_id in seen_ids:
                    raise ValueError(
                        f"{library_id}: duplicate SRA-derived bam_id {bam_id!r}"
                    )
                seen_ids[bam_id] = bam_path
                sample_row = dict(row)
                sample_row["bam_id"] = bam_id
                sample_row["bam_path"] = bam_path
                sample_row["sra_run_accession"] = sra_row["run_accession"]
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
    if row.get("source_type") in {"local_bam_dir", "sra_fastq"}
]
EMPIRICAL_PER_BAM_TLEN_OUTPUTS = []
for row in EMPIRICAL_BAM_SAMPLE_ROWS:
    prefix = f"results/empirical/{row['library_id']}/bams/{row['bam_id']}"
    EMPIRICAL_PER_BAM_TLEN_OUTPUTS.extend(
        [
            f"{prefix}/tlens.txt",
            f"{prefix}/tlen_histogram.tsv",
            f"{prefix}/unique_fragment_tlen_histogram.tsv",
            f"{prefix}/capped_fragment_tlen_histogram.tsv",
            f"{prefix}/tlen_qc.tsv",
            f"{prefix}/fragment_depth_qc.tsv",
        ]
    )
EMPIRICAL_LIBRARY_TLEN_OUTPUTS = []
for library_id in EMPIRICAL_ENABLED_BAM_LIBRARY_IDS:
    EMPIRICAL_LIBRARY_TLEN_OUTPUTS.extend(
        [
            f"results/empirical/{library_id}/tlens.txt",
            f"results/empirical/{library_id}/tlen_histogram.tsv",
            f"results/empirical/{library_id}/unique_fragment_tlen_histogram.tsv",
            f"results/empirical/{library_id}/capped_fragment_tlen_histogram.tsv",
            f"results/empirical/{library_id}/tlen_qc.tsv",
            f"results/empirical/{library_id}/fragment_depth_qc.tsv",
        ]
    )
EMPIRICAL_TLEN_OUTPUTS = EMPIRICAL_PER_BAM_TLEN_OUTPUTS + EMPIRICAL_LIBRARY_TLEN_OUTPUTS
EMPIRICAL_SRA_FASTQ_OUTPUTS = []
EMPIRICAL_SRA_TRIMMED_OUTPUTS = []
EMPIRICAL_SRA_BAM_OUTPUTS = []
for row in EMPIRICAL_SRA_RUN_ROWS:
    library_id = row["library_id"]
    run = row["run_accession"]
    EMPIRICAL_SRA_FASTQ_OUTPUTS.extend(
        [
            f"data/empirical/{library_id}/fastq/{run}_1.fastq.gz",
            f"data/empirical/{library_id}/fastq/{run}_2.fastq.gz",
        ]
    )
    EMPIRICAL_SRA_TRIMMED_OUTPUTS.extend(
        [
            f"data/empirical/{library_id}/trimmed/{run}_1.trimmed.fastq.gz",
            f"data/empirical/{library_id}/trimmed/{run}_2.trimmed.fastq.gz",
            f"results/empirical/{library_id}/fastp/{run}.html",
            f"results/empirical/{library_id}/fastp/{run}.json",
        ]
    )
    EMPIRICAL_SRA_BAM_OUTPUTS.extend(
        [
            f"data/empirical/{library_id}/bam/{run}.bam",
            f"data/empirical/{library_id}/bam/{run}.bam.bai",
        ]
    )
EMPIRICAL_PREDICTION_OUTPUTS = []
for row in EMPIRICAL_ENABLED_ROWS:
    prefix = f"results/empirical/{row['library_id']}/predictions"
    for mode in ["raw", "hard"]:
        EMPIRICAL_PREDICTION_OUTPUTS.extend(
            [
                f"{prefix}/{mode}.fragments.tsv",
                f"{prefix}/{mode}.json",
                f"{prefix}/{mode}.length_histogram.tsv",
                f"{prefix}/{mode}.summary.tsv",
            ]
        )
EMPIRICAL_DEPTH_VALIDATION_OUTPUTS = []
for library_id in EMPIRICAL_DEPTH_VALIDATION_LIBRARY_IDS:
    prefix = f"results/empirical/{library_id}/depth_validation"
    EMPIRICAL_DEPTH_VALIDATION_OUTPUTS.extend(
        [
            f"{prefix}/design.summary.tsv",
            f"{prefix}/design.tsv",
            f"{prefix}/design.json",
            f"{prefix}/loci.bed",
            f"{prefix}/loci.json",
            f"{prefix}/per_sample_depth.tsv",
            f"{prefix}/per_locus_depth.tsv",
            f"{prefix}/summary.tsv",
        ]
    )
EMPIRICAL_DEPTH_VALIDATION_FIGURE_OUTPUTS = [
    f"results/empirical/{library_id}/depth_validation/depth_validation.pdf"
    for library_id in EMPIRICAL_DEPTH_VALIDATION_LIBRARY_IDS
]
EMPIRICAL_SNP_PANEL_OUTPUTS = []
EMPIRICAL_SNP_PANEL_MANUSCRIPT_TABLES = []
EMPIRICAL_SNP_PANEL_MANUSCRIPT_FIGURES = []
for row in EMPIRICAL_SNP_PANEL_ROWS:
    prefix = f"results/empirical/{row['library_id']}/snp_panel/{row['case_id']}"
    EMPIRICAL_SNP_PANEL_OUTPUTS.extend(
        [
            f"{prefix}/design.summary.tsv",
            f"{prefix}/design.tsv",
            f"{prefix}/design.json",
            f"{prefix}/pair_overlap.tsv",
            f"{prefix}/top_designs.tsv",
            f"{prefix}/summary.tsv",
            f"{prefix}/run_metadata.json",
        ]
    )
    if row.get("include_for_manuscript", "false").strip().lower() == "true":
        EMPIRICAL_SNP_PANEL_MANUSCRIPT_TABLES.append(
            f"results/manuscript/tables/table_09_{row['case_id']}_target_overlap.tsv"
        )
        EMPIRICAL_SNP_PANEL_MANUSCRIPT_FIGURES.append(
            f"results/manuscript/figures/figure_08_{row['case_id']}_target_overlap.pdf"
        )

EMPIRICAL_DEPTH_VALIDATION_MANUSCRIPT_FIGURE_OUTPUTS = (
    [EMPIRICAL_DEPTH_VALIDATION_MANUSCRIPT_FIGURE]
    if EMPIRICAL_DEPTH_VALIDATION_LIBRARY_IDS
    else []
)
EMPIRICAL_PRIMARY_DEPTH_VALIDATION_LIBRARY_ID = (
    EMPIRICAL_DEPTH_VALIDATION_LIBRARY_IDS[0]
    if EMPIRICAL_DEPTH_VALIDATION_LIBRARY_IDS
    else None
)
EMPIRICAL_CURVE_OUTPUTS = []
for row in EMPIRICAL_ENABLED_ROWS:
    prefix = f"results/empirical/{row['library_id']}"
    EMPIRICAL_CURVE_OUTPUTS.extend(
        [
            f"{prefix}/size_model_curves.tsv",
            f"{prefix}/size_model_short_bias_grid.tsv",
        ]
    )
EMPIRICAL_MODEL_GRID_OUTPUTS = []
for row in EMPIRICAL_ENABLED_ROWS:
    prefix = f"results/empirical/{row['library_id']}"
    EMPIRICAL_MODEL_GRID_OUTPUTS.extend(
        [
            f"{prefix}/size_model_grid.tsv",
            f"{prefix}/best_size_model.tsv",
        ]
    )
EMPIRICAL_OVERLAY_FIGURE_OUTPUTS = [
    f"results/empirical/{row['library_id']}/figures/"
    f"size_model_overlay__{row['library_id']}.pdf"
    for row in EMPIRICAL_ENABLED_ROWS
]
EMPIRICAL_SIZE_SELECTION_SUMMARY_FIGURE_OUTPUTS = (
    [EMPIRICAL_SIZE_SELECTION_SUMMARY_FIGURE] if EMPIRICAL_ENABLED_ROWS else []
)
EMPIRICAL_MODEL_FIT_RANKING_OUTPUTS = (
    [
        "results/empirical/size_model_fit_ranking.tsv",
        "results/empirical/figures/size_model_fit_ranking.pdf",
    ]
    if EMPIRICAL_ENABLED_ROWS
    else []
)
EMPIRICAL_FIGURE_OUTPUTS = (
    EMPIRICAL_OVERLAY_FIGURE_OUTPUTS
    + EMPIRICAL_MODEL_FIT_RANKING_OUTPUTS
    + EMPIRICAL_SIZE_SELECTION_SUMMARY_FIGURE_OUTPUTS
    + EMPIRICAL_DEPTH_VALIDATION_FIGURE_OUTPUTS
    + EMPIRICAL_DEPTH_VALIDATION_MANUSCRIPT_FIGURE_OUTPUTS
    + EMPIRICAL_SNP_PANEL_MANUSCRIPT_FIGURES
)
EMPIRICAL_ALL_OUTPUTS = (
    [EMPIRICAL_LIBRARY_MANIFEST]
    + EMPIRICAL_PLACEHOLDER_OUTPUTS
    + EMPIRICAL_REFERENCE_OUTPUTS
    + EMPIRICAL_BAM_MANIFESTS
    + EMPIRICAL_SRA_FASTQ_OUTPUTS
    + EMPIRICAL_SRA_TRIMMED_OUTPUTS
    + EMPIRICAL_SRA_BAM_OUTPUTS
    + EMPIRICAL_TLEN_OUTPUTS
    + EMPIRICAL_PREDICTION_OUTPUTS
    + EMPIRICAL_DEPTH_VALIDATION_OUTPUTS
    + EMPIRICAL_DEPTH_VALIDATION_TABLES
    + EMPIRICAL_SNP_PANEL_OUTPUTS
    + EMPIRICAL_SNP_PANEL_MANUSCRIPT_TABLES
    + EMPIRICAL_CURVE_OUTPUTS
    + EMPIRICAL_MODEL_GRID_OUTPUTS
    + EMPIRICAL_FIGURE_OUTPUTS
)


def _empirical_depth_case(wildcards):
    if wildcards.library_id not in EMPIRICAL_DEPTH_VALIDATION_BY_LIBRARY:
        raise ValueError(
            f"no enabled depth-validation case for library_id={wildcards.library_id!r}"
        )
    return EMPIRICAL_DEPTH_VALIDATION_BY_LIBRARY[wildcards.library_id]


def _empirical_depth_param(wildcards, name):
    return _empirical_depth_case(wildcards)[name]


def _empirical_depth_read_budget(wildcards):
    row = _empirical_depth_case(wildcards)
    if row.get("flowcell_read_pairs", "NA") not in {"", "NA"}:
        return ["--flowcell-read-pairs", row["flowcell_read_pairs"]]
    if row.get("lane_read_pairs", "NA") not in {"", "NA"}:
        return ["--lane-read-pairs", row["lane_read_pairs"], "--lanes", row["lanes"]]
    raise ValueError(
        f"depth-validation case {wildcards.library_id!r} has no read budget"
    )


def _empirical_snp_panel_case(wildcards):
    case_id = wildcards.snp_panel_case_id
    if case_id not in EMPIRICAL_SNP_PANEL_BY_CASE:
        raise ValueError(f"no enabled SNP-panel case for case_id={case_id!r}")
    row = EMPIRICAL_SNP_PANEL_BY_CASE[case_id]
    if row["library_id"] != wildcards.library_id:
        raise ValueError(
            f"SNP-panel case {case_id!r} belongs to library_id={row['library_id']!r}, "
            f"not {wildcards.library_id!r}"
        )
    return row


def _empirical_snp_panel_param(wildcards, name):
    return _empirical_snp_panel_case(wildcards)[name]


def _empirical_snp_panel_read_budget(wildcards):
    row = _empirical_snp_panel_case(wildcards)
    if row.get("flowcell_read_pairs", "NA") not in {"", "NA"}:
        return ["--flowcell-read-pairs", row["flowcell_read_pairs"]]
    if row.get("lane_read_pairs", "NA") not in {"", "NA"}:
        return ["--lane-read-pairs", row["lane_read_pairs"], "--lanes", row["lanes"]]
    raise ValueError(f"SNP-panel case {row['case_id']!r} has no read budget")


def _candidate_enzymes_csv_from_file(path):
    names = []
    with open(path) as handle:
        for raw in handle:
            text = raw.strip()
            if text and not text.startswith("#"):
                names.append(text)
    if len(names) < 2:
        raise ValueError(f"{path}: expected at least two candidate enzymes")
    return ",".join(names)


def _empirical_reference_path(wildcards):
    return EMPIRICAL_ROWS_BY_ID[wildcards.library_id]["reference_path"]


def _empirical_bam_paths(wildcards):
    row = EMPIRICAL_ROWS_BY_ID[wildcards.library_id]
    if row.get("source_type") == "sra_fastq":
        return [
            f"data/empirical/{wildcards.library_id}/bam/{sra_row['run_accession']}.bam"
            for sra_row in EMPIRICAL_SRA_RUNS_BY_LIBRARY.get(wildcards.library_id, [])
        ]
    if row.get("source_type") == "local_bam_dir":
        return [str(path) for path in _matching_bam_paths(row)]
    return []


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


def _empirical_sra_run_row(wildcards):
    for row in EMPIRICAL_SRA_RUN_ROWS:
        if (
            row["library_id"] == wildcards.library_id
            and row["run_accession"] == wildcards.run_accession
        ):
            return row
    raise ValueError(
        f"unknown empirical SRA run library_id={wildcards.library_id!r} "
        f"run_accession={wildcards.run_accession!r}"
    )


def _empirical_bwa_index_files(wildcards):
    reference = EMPIRICAL_ROWS_BY_ID[wildcards.library_id]["reference_path"]
    return [f"{reference}.{suffix}" for suffix in ["amb", "ann", "bwt", "pac", "sa"]]


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


def _empirical_library_unique_fragment_histogram_files(wildcards):
    return [
        f"results/empirical/{wildcards.library_id}/bams/{bam_id}/unique_fragment_tlen_histogram.tsv"
        for bam_id in _empirical_library_bam_ids(wildcards.library_id)
    ]


def _empirical_library_capped_fragment_histogram_files(wildcards):
    return [
        f"results/empirical/{wildcards.library_id}/bams/{bam_id}/capped_fragment_tlen_histogram.tsv"
        for bam_id in _empirical_library_bam_ids(wildcards.library_id)
    ]


def _empirical_library_qc_files(wildcards):
    return [
        f"results/empirical/{wildcards.library_id}/bams/{bam_id}/tlen_qc.tsv"
        for bam_id in _empirical_library_bam_ids(wildcards.library_id)
    ]


def _empirical_library_fragment_depth_qc_files(wildcards):
    return [
        f"results/empirical/{wildcards.library_id}/bams/{bam_id}/fragment_depth_qc.tsv"
        for bam_id in _empirical_library_bam_ids(wildcards.library_id)
    ]


def _empirical_curve_files(wildcards=None):
    return [
        f"results/empirical/{row['library_id']}/size_model_curves.tsv"
        for row in EMPIRICAL_ENABLED_ROWS
    ]


def _empirical_param(wildcards, name):
    return _empirical_bam_sample_row(wildcards)[name]


def _empirical_library_param(wildcards, name):
    return EMPIRICAL_ROWS_BY_ID[wildcards.library_id][name]


def _empirical_prediction_min(wildcards):
    row = EMPIRICAL_ROWS_BY_ID[wildcards.library_id]
    if wildcards.prediction_mode == "raw":
        return row["score_min"]
    if wildcards.prediction_mode == "hard":
        return row["min_size"]
    raise ValueError(f"unknown empirical prediction_mode={wildcards.prediction_mode!r}")


def _empirical_prediction_max(wildcards):
    row = EMPIRICAL_ROWS_BY_ID[wildcards.library_id]
    if wildcards.prediction_mode == "raw":
        return row["score_max"]
    if wildcards.prediction_mode == "hard":
        return row["max_size"]
    raise ValueError(f"unknown empirical prediction_mode={wildcards.prediction_mode!r}")


rule empirical_manifest_all:
    input:
        EMPIRICAL_LIBRARY_MANIFEST,


rule empirical_references_all:
    input:
        EMPIRICAL_REFERENCE_OUTPUTS,


rule empirical_bam_manifests_all:
    input:
        EMPIRICAL_BAM_MANIFESTS,


rule empirical_tlens_all:
    input:
        EMPIRICAL_BAM_MANIFESTS + EMPIRICAL_TLEN_OUTPUTS,


rule empirical_sra_fastqs_all:
    input:
        EMPIRICAL_SRA_FASTQ_OUTPUTS,


rule empirical_sra_bams_all:
    input:
        EMPIRICAL_SRA_BAM_OUTPUTS,


rule empirical_predictions_all:
    input:
        EMPIRICAL_PREDICTION_OUTPUTS,


rule empirical_depth_validation_all:
    input:
        EMPIRICAL_DEPTH_VALIDATION_OUTPUTS
        + EMPIRICAL_DEPTH_VALIDATION_TABLES
        + EMPIRICAL_DEPTH_VALIDATION_FIGURE_OUTPUTS
        + EMPIRICAL_DEPTH_VALIDATION_MANUSCRIPT_FIGURE_OUTPUTS,


rule empirical_snp_panel_overlap_all:
    input:
        EMPIRICAL_SNP_PANEL_OUTPUTS
        + EMPIRICAL_SNP_PANEL_MANUSCRIPT_TABLES
        + EMPIRICAL_SNP_PANEL_MANUSCRIPT_FIGURES,


rule empirical_curves_all:
    input:
        EMPIRICAL_CURVE_OUTPUTS,


rule empirical_figures_all:
    input:
        EMPIRICAL_FIGURE_OUTPUTS,


rule empirical_model_grid_all:
    input:
        EMPIRICAL_MODEL_GRID_OUTPUTS,


rule empirical_model_fit_ranking_all:
    input:
        EMPIRICAL_MODEL_FIT_RANKING_OUTPUTS,


rule empirical_all:
    input:
        EMPIRICAL_ALL_OUTPUTS,


rule empirical_sra_fastq:
    output:
        r1="data/empirical/{library_id}/fastq/{run_accession}_1.fastq.gz",
        r2="data/empirical/{library_id}/fastq/{run_accession}_2.fastq.gz",
    log:
        "benchmark/logs/empirical/{library_id}.{run_accession}.fasterq_dump.log",
    conda:
        "../envs/sra-align.yml"
    threads: 4
    params:
        sra_run=lambda wildcards: _empirical_sra_run_row(wildcards)["run_accession"],
    shell:
        r"""
        mkdir -p benchmark/logs/empirical data/empirical/{wildcards.library_id}/fastq
        tmpdir="$(mktemp -d)"
        trap 'rm -rf "$tmpdir"' EXIT
        fasterq-dump {params.sra_run:q} --split-files --threads {threads} --outdir "$tmpdir" >{log:q} 2>&1
        test -s "$tmpdir/{params.sra_run}_1.fastq"
        test -s "$tmpdir/{params.sra_run}_2.fastq"
        gzip -c "$tmpdir/{params.sra_run}_1.fastq" >{output.r1:q}
        gzip -c "$tmpdir/{params.sra_run}_2.fastq" >{output.r2:q}
        """


rule empirical_fastp_trim:
    input:
        r1="data/empirical/{library_id}/fastq/{run_accession}_1.fastq.gz",
        r2="data/empirical/{library_id}/fastq/{run_accession}_2.fastq.gz",
    output:
        r1="data/empirical/{library_id}/trimmed/{run_accession}_1.trimmed.fastq.gz",
        r2="data/empirical/{library_id}/trimmed/{run_accession}_2.trimmed.fastq.gz",
        html="results/empirical/{library_id}/fastp/{run_accession}.html",
        json="results/empirical/{library_id}/fastp/{run_accession}.json",
    log:
        "benchmark/logs/empirical/{library_id}.{run_accession}.fastp.log",
    conda:
        "../envs/sra-align.yml"
    threads: 4
    params:
        sra_run=lambda wildcards: _empirical_sra_run_row(wildcards)["run_accession"],
    shell:
        r"""
        mkdir -p benchmark/logs/empirical data/empirical/{wildcards.library_id}/trimmed results/empirical/{wildcards.library_id}/fastp
        fastp --in1 {input.r1:q} --in2 {input.r2:q} --out1 {output.r1:q} --out2 {output.r2:q} --html {output.html:q} --json {output.json:q} --thread {threads} >{log:q} 2>&1
        """


rule empirical_bwa_index:
    input:
        reference="data/reference/{reference_id}.fa",
    output:
        amb="data/reference/{reference_id}.fa.amb",
        ann="data/reference/{reference_id}.fa.ann",
        bwt="data/reference/{reference_id}.fa.bwt",
        pac="data/reference/{reference_id}.fa.pac",
        sa="data/reference/{reference_id}.fa.sa",
    log:
        "benchmark/logs/empirical/{reference_id}.bwa_index.log",
    conda:
        "../envs/sra-align.yml"
    shell:
        r"""
        mkdir -p benchmark/logs/empirical
        bwa index {input.reference:q} >{log:q} 2>&1
        """


rule empirical_align_sra_bam:
    input:
        r1="data/empirical/{library_id}/trimmed/{run_accession}_1.trimmed.fastq.gz",
        r2="data/empirical/{library_id}/trimmed/{run_accession}_2.trimmed.fastq.gz",
        reference=lambda wildcards: EMPIRICAL_ROWS_BY_ID[wildcards.library_id][
            "reference_path"
        ],
        index=_empirical_bwa_index_files,
    output:
        bam="data/empirical/{library_id}/bam/{run_accession}.bam",
        bai="data/empirical/{library_id}/bam/{run_accession}.bam.bai",
    log:
        "benchmark/logs/empirical/{library_id}.{run_accession}.bwa_mem.log",
    conda:
        "../envs/sra-align.yml"
    threads: 4
    params:
        sra_run=lambda wildcards: _empirical_sra_run_row(wildcards)["run_accession"],
    shell:
        r"""
        mkdir -p benchmark/logs/empirical data/empirical/{wildcards.library_id}/bam
        bwa mem -t {threads} {input.reference:q} {input.r1:q} {input.r2:q} 2>{log:q} | samtools sort -@ {threads} -o {output.bam:q} -
        samtools index -@ {threads} {output.bam:q} {output.bai:q}
        """


rule empirical_bam_manifest:
    input:
        manifest=EMPIRICAL_LIBRARY_MANIFEST,
        reference=_empirical_reference_path,
        bams=_empirical_bam_paths,
    output:
        manifest="results/empirical/{library_id}/bam_manifest.tsv",
    log:
        "benchmark/logs/empirical/{library_id}.bam_manifest.log",
    conda:
        "../envs/empirical.yml"
    shell:
        r"""
        mkdir -p benchmark/logs/empirical results/empirical/{wildcards.library_id}
        python3 scripts/empirical/write_bam_manifest.py \
            --manifest {input.manifest:q} \
            --sra-runs {EMPIRICAL_SRA_RUN_MANIFEST:q} \
            --library-id {wildcards.library_id:q} \
            --out {output.manifest:q} \
            >{log:q} 2>&1
        """


rule empirical_extract_tlens:
    input:
        bam_manifest="results/empirical/{library_id}/bam_manifest.tsv",
        bam=_empirical_bam_path,
    output:
        tlens="results/empirical/{library_id}/bams/{bam_id}/tlens.txt",
        histogram="results/empirical/{library_id}/bams/{bam_id}/tlen_histogram.tsv",
        unique_fragment_histogram="results/empirical/{library_id}/bams/{bam_id}/unique_fragment_tlen_histogram.tsv",
        capped_fragment_histogram="results/empirical/{library_id}/bams/{bam_id}/capped_fragment_tlen_histogram.tsv",
        qc="results/empirical/{library_id}/bams/{bam_id}/tlen_qc.tsv",
        fragment_depth_qc="results/empirical/{library_id}/bams/{bam_id}/fragment_depth_qc.tsv",
    log:
        "benchmark/logs/empirical/{library_id}.{bam_id}.extract_tlens.log",
    conda:
        "../envs/empirical.yml"
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
        size_edge_sd=lambda wildcards: _empirical_param(wildcards, "size_edge_sd"),
        min_mapq=lambda wildcards: _empirical_param(wildcards, "min_mapq"),
        exclude_duplicates=lambda wildcards: _empirical_param(
            wildcards, "exclude_duplicates"
        ),
        max_tlen=lambda wildcards: _empirical_param(wildcards, "max_tlen"),
        capped_fragment_depth="5",
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
            --size-edge-sd {params.size_edge_sd:q} \
            --min-mapq {params.min_mapq:q} \
            --exclude-duplicates {params.exclude_duplicates:q} \
            --max-tlen {params.max_tlen:q} \
            --capped-fragment-depth {params.capped_fragment_depth:q} \
            --tlens-out {output.tlens:q} \
            --hist-out {output.histogram:q} \
            --unique-fragment-hist-out {output.unique_fragment_histogram:q} \
            --capped-fragment-hist-out {output.capped_fragment_histogram:q} \
            --qc-out {output.qc:q} \
            --fragment-depth-qc-out {output.fragment_depth_qc:q} \
            >{log:q} 2>&1
        """


rule empirical_combine_tlens:
    input:
        tlens=_empirical_library_tlen_files,
        histograms=_empirical_library_histogram_files,
        unique_fragment_histograms=_empirical_library_unique_fragment_histogram_files,
        capped_fragment_histograms=_empirical_library_capped_fragment_histogram_files,
        qc_tables=_empirical_library_qc_files,
        fragment_depth_qc_tables=_empirical_library_fragment_depth_qc_files,
    output:
        tlens="results/empirical/{library_id}/tlens.txt",
        histogram="results/empirical/{library_id}/tlen_histogram.tsv",
        unique_fragment_histogram="results/empirical/{library_id}/unique_fragment_tlen_histogram.tsv",
        capped_fragment_histogram="results/empirical/{library_id}/capped_fragment_tlen_histogram.tsv",
        qc="results/empirical/{library_id}/tlen_qc.tsv",
        fragment_depth_qc="results/empirical/{library_id}/fragment_depth_qc.tsv",
    log:
        "benchmark/logs/empirical/{library_id}.combine_tlens.log",
    conda:
        "../envs/empirical.yml"
    shell:
        r"""
        mkdir -p benchmark/logs/empirical results/empirical/{wildcards.library_id}
        python3 scripts/empirical/combine_tlens.py \
            --library-id {wildcards.library_id:q} \
            --tlens {input.tlens:q} \
            --histograms {input.histograms:q} \
            --unique-fragment-histograms {input.unique_fragment_histograms:q} \
            --capped-fragment-histograms {input.capped_fragment_histograms:q} \
            --qc-tables {input.qc_tables:q} \
            --fragment-depth-qc-tables {input.fragment_depth_qc_tables:q} \
            --tlens-out {output.tlens:q} \
            --hist-out {output.histogram:q} \
            --unique-fragment-hist-out {output.unique_fragment_histogram:q} \
            --capped-fragment-hist-out {output.capped_fragment_histogram:q} \
            --qc-out {output.qc:q} \
            --fragment-depth-qc-out {output.fragment_depth_qc:q} \
            >{log:q} 2>&1
        """


rule empirical_radigest_prediction:
    input:
        reference=lambda wildcards: _empirical_library_param(
            wildcards, "reference_path"
        ),
    output:
        fragments="results/empirical/{library_id}/predictions/{prediction_mode}.fragments.tsv",
        json="results/empirical/{library_id}/predictions/{prediction_mode}.json",
    log:
        "benchmark/logs/empirical/{library_id}.{prediction_mode}.radigest_prediction.log",
    threads: 4
    params:
        radigest=lambda wildcards: config.get("radigest", "radigest"),
        enzyme_1=lambda wildcards: _empirical_library_param(wildcards, "enzyme_1"),
        enzyme_2=lambda wildcards: _empirical_library_param(wildcards, "enzyme_2"),
        min_size=_empirical_prediction_min,
        max_size=_empirical_prediction_max,
    shell:
        r"""
        mkdir -p benchmark/logs/empirical \
            results/empirical/{wildcards.library_id}/predictions
        {params.radigest:q} \
            -fasta {input.reference:q} \
            -enzymes {params.enzyme_1:q},{params.enzyme_2:q} \
            -min {params.min_size:q} \
            -max {params.max_size:q} \
            -score-min {params.min_size:q} \
            -score-max {params.max_size:q} \
            -size-model hard \
            -threads {threads} \
            -fragments-tsv {output.fragments:q} \
            -json {output.json:q} \
            >{log:q} 2>&1
        """


rule empirical_summarize_radigest_prediction:
    input:
        fragments="results/empirical/{library_id}/predictions/{prediction_mode}.fragments.tsv",
    output:
        histogram="results/empirical/{library_id}/predictions/{prediction_mode}.length_histogram.tsv",
        summary="results/empirical/{library_id}/predictions/{prediction_mode}.summary.tsv",
    log:
        "benchmark/logs/empirical/{library_id}.{prediction_mode}.summarize_prediction.log",
    conda:
        "../envs/empirical.yml"
    params:
        reference_id=lambda wildcards: _empirical_library_param(
            wildcards, "reference_id"
        ),
        reference_path=lambda wildcards: _empirical_library_param(
            wildcards, "reference_path"
        ),
        enzyme_1=lambda wildcards: _empirical_library_param(wildcards, "enzyme_1"),
        enzyme_2=lambda wildcards: _empirical_library_param(wildcards, "enzyme_2"),
        min_size=lambda wildcards: _empirical_library_param(wildcards, "min_size"),
        max_size=lambda wildcards: _empirical_library_param(wildcards, "max_size"),
        score_min=lambda wildcards: _empirical_library_param(wildcards, "score_min"),
        score_max=lambda wildcards: _empirical_library_param(wildcards, "score_max"),
        size_model=lambda wildcards: _empirical_library_param(wildcards, "size_model"),
        size_edge_sd=lambda wildcards: _empirical_library_param(
            wildcards, "size_edge_sd"
        ),
    shell:
        r"""
        mkdir -p benchmark/logs/empirical \
            results/empirical/{wildcards.library_id}/predictions
        python3 scripts/empirical/summarize_radigest_prediction.py \
            --fragments {input.fragments:q} \
            --library-id {wildcards.library_id:q} \
            --prediction-mode {wildcards.prediction_mode:q} \
            --reference-id {params.reference_id:q} \
            --reference-path {params.reference_path:q} \
            --enzyme-1 {params.enzyme_1:q} \
            --enzyme-2 {params.enzyme_2:q} \
            --min-size {params.min_size:q} \
            --max-size {params.max_size:q} \
            --score-min {params.score_min:q} \
            --score-max {params.score_max:q} \
            --size-model {params.size_model:q} \
            --size-edge-sd {params.size_edge_sd:q} \
            --hist-out {output.histogram:q} \
            --summary-out {output.summary:q} \
            >{log:q} 2>&1
        """


rule empirical_snp_panel_design:
    input:
        reference=lambda wildcards: _empirical_snp_panel_param(
            wildcards, "reference_path"
        ),
        candidates=lambda wildcards: _empirical_snp_panel_param(
            wildcards, "candidate_enzymes"
        ),
    output:
        summary_tsv="results/empirical/{library_id}/snp_panel/{snp_panel_case_id}/design.summary.tsv",
        tsv="results/empirical/{library_id}/snp_panel/{snp_panel_case_id}/design.tsv",
        json="results/empirical/{library_id}/snp_panel/{snp_panel_case_id}/design.json",
    log:
        "benchmark/logs/empirical/{library_id}.{snp_panel_case_id}.snp_panel.design.log",
    threads: 8
    params:
        radigest_design=lambda wildcards: config.get(
            "radigest_design", "radigest-design"
        ),
        enzymes=lambda wildcards, input: _candidate_enzymes_csv_from_file(
            input.candidates
        ),
        target_genome_pct=lambda wildcards: _empirical_snp_panel_param(
            wildcards, "target_genome_pct"
        ),
        coverage_tolerance_pct=lambda wildcards: _empirical_snp_panel_param(
            wildcards, "coverage_tolerance_pct"
        ),
        desired_depth=lambda wildcards: _empirical_snp_panel_param(
            wildcards, "desired_depth"
        ),
        samples=lambda wildcards: _empirical_snp_panel_param(wildcards, "samples"),
        read_layout=lambda wildcards: _empirical_snp_panel_param(
            wildcards, "read_layout"
        ),
        read_length=lambda wildcards: _empirical_snp_panel_param(
            wildcards, "read_length"
        ),
        usable_read_fraction=lambda wildcards: _empirical_snp_panel_param(
            wildcards, "usable_read_fraction"
        ),
        min_size=lambda wildcards: _empirical_snp_panel_param(wildcards, "min_size"),
        max_size=lambda wildcards: _empirical_snp_panel_param(wildcards, "max_size"),
        score_min=lambda wildcards: _empirical_snp_panel_param(wildcards, "score_min"),
        score_max=lambda wildcards: _empirical_snp_panel_param(wildcards, "score_max"),
        size_model=lambda wildcards: _empirical_snp_panel_param(wildcards, "size_model"),
        size_mean=lambda wildcards: _empirical_snp_panel_param(wildcards, "size_mean"),
        size_sd=lambda wildcards: _empirical_snp_panel_param(wildcards, "size_sd"),
        size_edge_sd=lambda wildcards: _empirical_snp_panel_param(
            wildcards, "size_edge_sd"
        ),
        read_budget=_empirical_snp_panel_read_budget,
        out_dir=lambda wildcards: (
            f"results/empirical/{wildcards.library_id}/snp_panel/"
            f"{wildcards.snp_panel_case_id}"
        ),
    shell:
        r"""
        mkdir -p benchmark/logs/empirical {params.out_dir:q}
        {params.radigest_design:q} \
            --fasta {input.reference:q} \
            --enzymes {params.enzymes:q} \
            --target-genome-pct {params.target_genome_pct:q} \
            --coverage-tolerance-pct {params.coverage_tolerance_pct:q} \
            --desired-depth {params.desired_depth:q} \
            --samples {params.samples:q} \
            --read-layout {params.read_layout:q} \
            --read-length {params.read_length:q} \
            --threads {threads} \
            --jobs {threads} \
            --build-workers {threads} \
            {params.read_budget:q} \
            --usable-read-fraction {params.usable_read_fraction:q} \
            --min {params.min_size:q} \
            --max {params.max_size:q} \
            --score-min {params.score_min:q} \
            --score-max {params.score_max:q} \
            --size-model {params.size_model:q} \
            --size-mean {params.size_mean:q} \
            --size-sd {params.size_sd:q} \
            --size-edge-sd {params.size_edge_sd:q} \
            --out-dir {params.out_dir:q} \
            --force \
            >{log:q} 2>&1
        test -s {output.summary_tsv:q}
        test -s {output.tsv:q}
        test -s {output.json:q}
        """


rule empirical_snp_panel_overlap:
    input:
        reference=lambda wildcards: _empirical_snp_panel_param(
            wildcards, "reference_path"
        ),
        panel_bed=lambda wildcards: _empirical_snp_panel_param(wildcards, "panel_bed"),
        candidates=lambda wildcards: _empirical_snp_panel_param(
            wildcards, "candidate_enzymes"
        ),
        design="results/empirical/{library_id}/snp_panel/{snp_panel_case_id}/design.tsv",
    output:
        pair_overlap="results/empirical/{library_id}/snp_panel/{snp_panel_case_id}/pair_overlap.tsv",
        top_designs="results/empirical/{library_id}/snp_panel/{snp_panel_case_id}/top_designs.tsv",
        summary="results/empirical/{library_id}/snp_panel/{snp_panel_case_id}/summary.tsv",
        metadata="results/empirical/{library_id}/snp_panel/{snp_panel_case_id}/run_metadata.json",
    log:
        "benchmark/logs/empirical/{library_id}.{snp_panel_case_id}.snp_panel.overlap.log",
    conda:
        "../envs/empirical.yml"
    threads: 4
    params:
        radigest=lambda wildcards: config.get("radigest", "radigest"),
        display_name=lambda wildcards: _empirical_snp_panel_param(
            wildcards, "display_name"
        ),
        min_size=lambda wildcards: _empirical_snp_panel_param(wildcards, "min_size"),
        max_size=lambda wildcards: _empirical_snp_panel_param(wildcards, "max_size"),
        read_layout=lambda wildcards: _empirical_snp_panel_param(
            wildcards, "read_layout"
        ),
        read_length=lambda wildcards: _empirical_snp_panel_param(
            wildcards, "read_length"
        ),
        top_n=lambda wildcards: _empirical_snp_panel_param(wildcards, "top_n"),
        work_dir=lambda wildcards: (
            f"results/empirical/{wildcards.library_id}/snp_panel/"
            f"{wildcards.snp_panel_case_id}/per_pair"
        ),
    shell:
        r"""
        mkdir -p benchmark/logs/empirical results/manuscript/tables
        python3 scripts/empirical/run_target_panel_overlap.py \
            --case-id {wildcards.snp_panel_case_id:q} \
            --display-name {params.display_name:q} \
            --fasta {input.reference:q} \
            --panel-bed {input.panel_bed:q} \
            --candidate-enzymes {input.candidates:q} \
            --design-tsv {input.design:q} \
            --radigest {params.radigest:q} \
            --min-size {params.min_size:q} \
            --max-size {params.max_size:q} \
            --read-layout {params.read_layout:q} \
            --read-length {params.read_length:q} \
            --threads {threads} \
            --work-dir {params.work_dir:q} \
            --pair-overlap-out {output.pair_overlap:q} \
            --top-out {output.top_designs:q} \
            --summary-out {output.summary:q} \
            --metadata-out {output.metadata:q} \
            --top-n {params.top_n:q} \
            --force \
            >{log:q} 2>&1
        """


rule empirical_snp_panel_manuscript_table:
    input:
        top=lambda wildcards: (
            f"results/empirical/"
            f"{EMPIRICAL_SNP_PANEL_BY_CASE[wildcards.snp_panel_case_id]['library_id']}"
            f"/snp_panel/{wildcards.snp_panel_case_id}/top_designs.tsv"
        ),
    output:
        table="results/manuscript/tables/table_09_{snp_panel_case_id}_target_overlap.tsv",
    log:
        "benchmark/logs/manuscript/{snp_panel_case_id}.snp_panel_overlap_table.log",
    shell:
        r"""
        mkdir -p benchmark/logs/manuscript results/manuscript/tables
        cp {input.top:q} {output.table:q} >{log:q} 2>&1
        test -s {output.table:q}
        """


rule empirical_snp_panel_overlap_figure:
    input:
        pairs=lambda wildcards: (
            f"results/empirical/"
            f"{EMPIRICAL_SNP_PANEL_BY_CASE[wildcards.snp_panel_case_id]['library_id']}"
            f"/snp_panel/{wildcards.snp_panel_case_id}/pair_overlap.tsv"
        ),
        top=lambda wildcards: (
            f"results/empirical/"
            f"{EMPIRICAL_SNP_PANEL_BY_CASE[wildcards.snp_panel_case_id]['library_id']}"
            f"/snp_panel/{wildcards.snp_panel_case_id}/top_designs.tsv"
        ),
    output:
        figure="results/manuscript/figures/figure_08_{snp_panel_case_id}_target_overlap.pdf",
    log:
        "benchmark/logs/manuscript/{snp_panel_case_id}.snp_panel_overlap_figure.log",
    conda:
        "../envs/figures.yml"
    params:
        display_name=lambda wildcards: EMPIRICAL_SNP_PANEL_BY_CASE[
            wildcards.snp_panel_case_id
        ]["display_name"],
    shell:
        r"""
        mkdir -p benchmark/logs/manuscript results/manuscript/figures
        Rscript scripts/manuscript/make_snp_panel_overlap_figure.R \
            --pairs {input.pairs:q} \
            --top {input.top:q} \
            --out {output.figure:q} \
            --title {params.display_name:q} \
            >{log:q} 2>&1
        test -s {output.figure:q}
        """


rule empirical_depth_design:
    input:
        reference=lambda wildcards: _empirical_library_param(
            wildcards, "reference_path"
        ),
    output:
        summary_tsv="results/empirical/{library_id}/depth_validation/design.summary.tsv",
        tsv="results/empirical/{library_id}/depth_validation/design.tsv",
        json="results/empirical/{library_id}/depth_validation/design.json",
    log:
        "benchmark/logs/empirical/{library_id}.depth_validation.design.log",
    threads: 4
    params:
        radigest_design=lambda wildcards: config.get(
            "radigest_design", "radigest-design"
        ),
        enzyme_1=lambda wildcards: _empirical_depth_param(wildcards, "enzyme_1"),
        enzyme_2=lambda wildcards: _empirical_depth_param(wildcards, "enzyme_2"),
        target_genome_pct=lambda wildcards: _empirical_depth_param(
            wildcards, "target_genome_pct"
        ),
        coverage_tolerance_pct=lambda wildcards: _empirical_depth_param(
            wildcards, "coverage_tolerance_pct"
        ),
        desired_depth=lambda wildcards: _empirical_depth_param(
            wildcards, "desired_depth"
        ),
        samples=lambda wildcards: _empirical_depth_param(wildcards, "samples"),
        read_layout=lambda wildcards: _empirical_depth_param(wildcards, "read_layout"),
        read_length=lambda wildcards: _empirical_depth_param(wildcards, "read_length"),
        usable_read_fraction=lambda wildcards: _empirical_depth_param(
            wildcards, "usable_read_fraction"
        ),
        min_size=lambda wildcards: _empirical_depth_param(wildcards, "min_size"),
        max_size=lambda wildcards: _empirical_depth_param(wildcards, "max_size"),
        score_min=lambda wildcards: _empirical_depth_param(wildcards, "score_min"),
        score_max=lambda wildcards: _empirical_depth_param(wildcards, "score_max"),
        size_model=lambda wildcards: _empirical_depth_param(wildcards, "size_model"),
        size_mean=lambda wildcards: _empirical_depth_param(wildcards, "size_mean"),
        size_sd=lambda wildcards: _empirical_depth_param(wildcards, "size_sd"),
        size_edge_sd=lambda wildcards: _empirical_depth_param(wildcards, "size_edge_sd"),
        read_budget=_empirical_depth_read_budget,
    shell:
        r"""
        mkdir -p benchmark/logs/empirical results/empirical/{wildcards.library_id}/depth_validation
        {params.radigest_design:q} \
            --fasta {input.reference:q} \
            --enzymes {params.enzyme_1:q},{params.enzyme_2:q} \
            --target-genome-pct {params.target_genome_pct:q} \
            --coverage-tolerance-pct {params.coverage_tolerance_pct:q} \
            --desired-depth {params.desired_depth:q} \
            --samples {params.samples:q} \
            --read-layout {params.read_layout:q} \
            --read-length {params.read_length:q} \
            --threads {threads} \
            --jobs 1 \
            --build-workers {threads} \
            {params.read_budget:q} \
            --usable-read-fraction {params.usable_read_fraction:q} \
            --min {params.min_size:q} \
            --max {params.max_size:q} \
            --score-min {params.score_min:q} \
            --score-max {params.score_max:q} \
            --size-model {params.size_model:q} \
            --size-mean {params.size_mean:q} \
            --size-sd {params.size_sd:q} \
            --size-edge-sd {params.size_edge_sd:q} \
            --out-dir results/empirical/{wildcards.library_id}/depth_validation \
            --force \
            >{log:q} 2>&1
        test -s {output.summary_tsv:q}
        test -s {output.tsv:q}
        test -s {output.json:q}
        """


rule empirical_depth_loci:
    input:
        reference=lambda wildcards: _empirical_library_param(
            wildcards, "reference_path"
        ),
    output:
        bed="results/empirical/{library_id}/depth_validation/loci.bed",
        json="results/empirical/{library_id}/depth_validation/loci.json",
    log:
        "benchmark/logs/empirical/{library_id}.depth_validation.loci.log",
    threads: 4
    params:
        radigest=lambda wildcards: config.get("radigest", "radigest"),
        enzyme_1=lambda wildcards: _empirical_depth_param(wildcards, "enzyme_1"),
        enzyme_2=lambda wildcards: _empirical_depth_param(wildcards, "enzyme_2"),
        min_size=lambda wildcards: _empirical_depth_param(wildcards, "min_size"),
        max_size=lambda wildcards: _empirical_depth_param(wildcards, "max_size"),
    shell:
        r"""
        mkdir -p benchmark/logs/empirical results/empirical/{wildcards.library_id}/depth_validation
        {params.radigest:q} \
            -fasta {input.reference:q} \
            -enzymes {params.enzyme_1:q},{params.enzyme_2:q} \
            -min {params.min_size:q} \
            -max {params.max_size:q} \
            -score-min {params.min_size:q} \
            -score-max {params.max_size:q} \
            -size-model hard \
            -threads {threads} \
            -bed {output.bed:q} \
            -json {output.json:q} \
            >{log:q} 2>&1
        """


rule empirical_depth_per_sample:
    input:
        bam_manifest="results/empirical/{library_id}/bam_manifest.tsv",
        bams=_empirical_bam_paths,
        loci="results/empirical/{library_id}/depth_validation/loci.bed",
    output:
        depth="results/empirical/{library_id}/depth_validation/per_sample_depth.tsv",
        per_locus_depth="results/empirical/{library_id}/depth_validation/per_locus_depth.tsv",
    log:
        "benchmark/logs/empirical/{library_id}.depth_validation.per_sample_depth.log",
    conda:
        "../envs/empirical.yml"
    params:
        min_mapq=lambda wildcards: _empirical_depth_param(wildcards, "min_mapq"),
        exclude_duplicates=lambda wildcards: _empirical_depth_param(
            wildcards, "exclude_duplicates"
        ),
    shell:
        r"""
        mkdir -p benchmark/logs/empirical results/empirical/{wildcards.library_id}/depth_validation
        python3 scripts/empirical/calculate_locus_depth.py \
            --bam-manifest {input.bam_manifest:q} \
            --loci-bed {input.loci:q} \
            --library-id {wildcards.library_id:q} \
            --min-mapq {params.min_mapq:q} \
            --exclude-duplicates {params.exclude_duplicates:q} \
            --out {output.depth:q} \
            --per-locus-out {output.per_locus_depth:q} \
            >{log:q} 2>&1
        """


rule empirical_depth_validation_summary:
    input:
        design="results/empirical/{library_id}/depth_validation/design.tsv",
        per_sample_depth="results/empirical/{library_id}/depth_validation/per_sample_depth.tsv",
        per_locus_depth="results/empirical/{library_id}/depth_validation/per_locus_depth.tsv",
    output:
        summary="results/empirical/{library_id}/depth_validation/summary.tsv",
    log:
        "benchmark/logs/empirical/{library_id}.depth_validation.summary.log",
    conda:
        "../envs/empirical.yml"
    params:
        display_name=lambda wildcards: _empirical_depth_param(wildcards, "display_name"),
        enzyme_1=lambda wildcards: _empirical_depth_param(wildcards, "enzyme_1"),
        enzyme_2=lambda wildcards: _empirical_depth_param(wildcards, "enzyme_2"),
    shell:
        r"""
        mkdir -p benchmark/logs/empirical results/empirical/{wildcards.library_id}/depth_validation results/manuscript/tables
        python3 scripts/empirical/summarize_depth_validation.py \
            --library-id {wildcards.library_id:q} \
            --display-name {params.display_name:q} \
            --enzyme-1 {params.enzyme_1:q} \
            --enzyme-2 {params.enzyme_2:q} \
            --design-tsv {input.design:q} \
            --per-sample-depth {input.per_sample_depth:q} \
            --per-locus-depth {input.per_locus_depth:q} \
            --out {output.summary:q} \
            >{log:q} 2>&1
        """


rule empirical_depth_validation_manuscript_table:
    input:
        summaries=[
            f"results/empirical/{library_id}/depth_validation/summary.tsv"
            for library_id in EMPIRICAL_DEPTH_VALIDATION_LIBRARY_IDS
        ],
    output:
        table=EMPIRICAL_DEPTH_VALIDATION_TABLE,
    log:
        "benchmark/logs/empirical/depth_validation.manuscript_table.log",
    conda:
        "../envs/empirical.yml"
    shell:
        r"""
        mkdir -p benchmark/logs/empirical results/manuscript/tables
        python3 scripts/manuscript/make_empirical_depth_validation_table.py \
            --summaries {input.summaries:q} \
            --out {output.table:q} \
            >{log:q} 2>&1
        """


rule empirical_depth_validation_figure:
    input:
        per_sample_depth="results/empirical/{library_id}/depth_validation/per_sample_depth.tsv",
        per_locus_depth="results/empirical/{library_id}/depth_validation/per_locus_depth.tsv",
        summary="results/empirical/{library_id}/depth_validation/summary.tsv",
        script="scripts/empirical/plot_depth_validation.R",
    output:
        figure="results/empirical/{library_id}/depth_validation/depth_validation.pdf",
    log:
        "benchmark/logs/empirical/{library_id}.depth_validation.figure.log",
    conda:
        "../envs/figures.yml"
    shell:
        r"""
        mkdir -p benchmark/logs/empirical results/empirical/{wildcards.library_id}/depth_validation
        Rscript scripts/empirical/plot_depth_validation.R \
            --per-sample-depth {input.per_sample_depth:q} \
            --per-locus-depth {input.per_locus_depth:q} \
            --summary {input.summary:q} \
            --out {output.figure:q} \
            --formats pdf \
            >{log:q} 2>&1
        """


rule empirical_depth_validation_manuscript_figure:
    input:
        figure=lambda wildcards: f"results/empirical/{EMPIRICAL_PRIMARY_DEPTH_VALIDATION_LIBRARY_ID}/depth_validation/depth_validation.pdf",
    output:
        figure=EMPIRICAL_DEPTH_VALIDATION_MANUSCRIPT_FIGURE,
    log:
        "benchmark/logs/empirical/depth_validation.manuscript_figure.log",
    shell:
        r"""
        mkdir -p benchmark/logs/empirical results/manuscript/figures
        cp {input.figure:q} {output.figure:q}
        """


rule empirical_fit_size_model_grid:
    input:
        manifest=EMPIRICAL_LIBRARY_MANIFEST,
        empirical_histogram="results/empirical/{library_id}/tlen_histogram.tsv",
        raw_histogram="results/empirical/{library_id}/predictions/raw.length_histogram.tsv",
    output:
        grid="results/empirical/{library_id}/size_model_grid.tsv",
        best="results/empirical/{library_id}/best_size_model.tsv",
    log:
        "benchmark/logs/empirical/{library_id}.size_model_grid.log",
    conda:
        "../envs/empirical.yml"
    shell:
        r"""
        mkdir -p benchmark/logs/empirical results/empirical/{wildcards.library_id}
        python3 scripts/empirical/fit_size_model_grid.py \
            --manifest {input.manifest:q} \
            --library-id {wildcards.library_id:q} \
            --empirical-hist {input.empirical_histogram:q} \
            --raw-hist {input.raw_histogram:q} \
            --out {output.grid:q} \
            --best-out {output.best:q} \
            >{log:q} 2>&1
        """


rule empirical_size_model_curves:
    input:
        manifest=EMPIRICAL_LIBRARY_MANIFEST,
        empirical_histogram="results/empirical/{library_id}/tlen_histogram.tsv",
        empirical_unique_fragment_histogram="results/empirical/{library_id}/unique_fragment_tlen_histogram.tsv",
        empirical_capped_fragment_histogram="results/empirical/{library_id}/capped_fragment_tlen_histogram.tsv",
        raw_histogram="results/empirical/{library_id}/predictions/raw.length_histogram.tsv",
        hard_histogram="results/empirical/{library_id}/predictions/hard.length_histogram.tsv",
    output:
        curves="results/empirical/{library_id}/size_model_curves.tsv",
        bias_grid="results/empirical/{library_id}/size_model_short_bias_grid.tsv",
    log:
        "benchmark/logs/empirical/{library_id}.size_model_curves.log",
    conda:
        "../envs/empirical.yml"
    shell:
        r"""
        mkdir -p benchmark/logs/empirical results/empirical/{wildcards.library_id}
        python3 scripts/empirical/make_size_model_curves.py \
            --manifest {input.manifest:q} \
            --library-id {wildcards.library_id:q} \
            --empirical-hist {input.empirical_histogram:q} \
            --empirical-unique-fragment-hist {input.empirical_unique_fragment_histogram:q} \
            --empirical-capped-fragment-hist {input.empirical_capped_fragment_histogram:q} \
            --raw-hist {input.raw_histogram:q} \
            --hard-hist {input.hard_histogram:q} \
            --out {output.curves:q} \
            --bias-grid-out {output.bias_grid:q} \
            >{log:q} 2>&1
        """


rule empirical_size_model_overlay_figure:
    input:
        curves="results/empirical/{library_id}/size_model_curves.tsv",
    output:
        figure="results/empirical/{library_id}/figures/size_model_overlay__{library_id}.pdf",
        legacy_figure="results/empirical/{library_id}/figures/size_model_overlay.pdf",
    log:
        "benchmark/logs/empirical/{library_id}.size_model_overlay.log",
    conda:
        "../envs/figures.yml"
    shell:
        r"""
        mkdir -p benchmark/logs/empirical results/empirical/{wildcards.library_id}/figures
        Rscript scripts/empirical/plot_size_model_overlay.R \
            --curves {input.curves:q} \
            --out {output.figure:q} \
            --formats pdf \
            >{log:q} 2>&1
        cp {output.figure:q} {output.legacy_figure:q}
        """


rule empirical_size_model_fit_ranking_figure:
    input:
        curves=_empirical_curve_files,
    output:
        table="results/empirical/size_model_fit_ranking.tsv",
        figure="results/empirical/figures/size_model_fit_ranking.pdf",
    log:
        "benchmark/logs/empirical/size_model_fit_ranking.log",
    conda:
        "../envs/figures.yml"
    shell:
        r"""
        mkdir -p benchmark/logs/empirical results/empirical/figures
        Rscript scripts/empirical/plot_size_model_fit_ranking.R \
            --curves {input.curves:q} \
            --out-table {output.table:q} \
            --out-figure {output.figure:q} \
            --formats pdf \
            >{log:q} 2>&1
        """


rule empirical_size_selection_summary_figure:
    input:
        ranking="results/empirical/size_model_fit_ranking.tsv",
        script="scripts/manuscript/make_empirical_size_selection_summary_figure.R",
    output:
        figure=EMPIRICAL_SIZE_SELECTION_SUMMARY_FIGURE,
    log:
        "benchmark/logs/empirical/size_selection_summary_figure.log",
    conda:
        "../envs/figures.yml"
    shell:
        r"""
        mkdir -p benchmark/logs/empirical results/manuscript/figures
        Rscript {input.script:q} \
            --ranking {input.ranking:q} \
            --out {output.figure:q} \
            --formats pdf \
            >{log:q} 2>&1
        """
