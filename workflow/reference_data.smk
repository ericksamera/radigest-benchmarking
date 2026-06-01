import csv
from pathlib import Path

shell.executable("/usr/bin/bash")

DATASETS_TSV = config.get("datasets_tsv", "config/datasets.tsv")
DATASET_IDS_RAW = config.get("dataset_ids", "yeast_small,moderate_genome")
PREPARE_PLAIN = str(config.get("prepare_plain", "true")).lower() in {"1", "true", "yes"}

if isinstance(DATASET_IDS_RAW, str):
    DATASET_IDS = [x.strip() for x in DATASET_IDS_RAW.split(",") if x.strip()]
else:
    DATASET_IDS = list(DATASET_IDS_RAW)


def read_dataset_table(path):
    out = {}
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            dataset = row.get("dataset_id") or row.get("dataset")
            if dataset:
                out[dataset] = row
    return out


DATASETS = read_dataset_table(DATASETS_TSV)

missing = [dataset for dataset in DATASET_IDS if dataset not in DATASETS]
if missing:
    raise ValueError(f"dataset IDs not found in {DATASETS_TSV}: {missing}")


def local_path(dataset):
    return DATASETS[dataset]["local_path"]


def plain_path(dataset):
    path = local_path(dataset)
    if path.endswith(".gz"):
        return path[:-3]
    return path


LOCAL_FASTA = [local_path(dataset) for dataset in DATASET_IDS]
PLAIN_FASTA = [
    plain_path(dataset)
    for dataset in DATASET_IDS
    if PREPARE_PLAIN and local_path(dataset).endswith(".gz")
]
SUMMARY_FILES = [
    f"results/processed/fasta/{dataset}.summary.tsv"
    for dataset in DATASET_IDS
]


rule all:
    input:
        "results/processed/reference_checksums.tsv",
        LOCAL_FASTA,
        PLAIN_FASTA,
        SUMMARY_FILES


rule download_references:
    output:
        checksums="results/processed/reference_checksums.tsv",
        fasta=LOCAL_FASTA,
        plain=PLAIN_FASTA
    params:
        dataset_ids=",".join(DATASET_IDS),
        prepare_plain="--prepare-plain" if PREPARE_PLAIN else ""
    conda:
        "../envs/reference.yml"
    shell:
        r"""
        mkdir -p data/reference results/processed results/processed/fasta

        scripts/reference/download_reference_data.sh \
          --datasets {DATASETS_TSV:q} \
          --out {output.checksums:q} \
          --dataset {params.dataset_ids:q} \
          {params.prepare_plain}
        """


rule summarize_reference_fasta:
    input:
        lambda wildcards: local_path(wildcards.dataset)
    output:
        "results/processed/fasta/{dataset}.summary.tsv"
    conda:
        "../envs/reference.yml"
    shell:
        r"""
        mkdir -p results/processed/fasta
        python3 scripts/reference/summarize_fasta.py \
          -o {output:q} \
          {input:q}
        """
