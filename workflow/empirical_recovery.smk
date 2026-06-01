import csv
import os
from pathlib import Path

shell.executable("/usr/bin/bash")

EMPIRICAL_TABLE = config.get("empirical_table", "config/empirical_recovery.tsv")
RADIGEST = config.get("radigest", "radigest")
RADIGEST_FIT_SIZE_MODEL = config.get("radigest_fit_size_model", "radigest-fit-size-model")
THREADS = int(config.get("threads", 4))
MAPQ_DEFAULT = int(config.get("mapq", 20))
DOWNSAMPLE_PER_SAMPLE = int(config.get("downsample_per_sample", 100000))
DOWNSAMPLE_SEED = int(config.get("downsample_seed", 1))


def read_empirical_table(path):
    rows = {}
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            dataset = row.get("dataset_id") or row.get("dataset")
            if not dataset:
                continue
            rows[dataset] = row
    return rows


EMPIRICAL = read_empirical_table(EMPIRICAL_TABLE)

requested = config.get("datasets", "")
if requested:
    if isinstance(requested, str):
        DATASETS = [x.strip() for x in requested.split(",") if x.strip()]
    else:
        DATASETS = list(requested)
else:
    DATASETS = sorted(EMPIRICAL)

missing = [dataset for dataset in DATASETS if dataset not in EMPIRICAL]
if missing:
    raise ValueError(f"empirical dataset(s) not found in {EMPIRICAL_TABLE}: {missing}")


def row(wildcards):
    return EMPIRICAL[wildcards.dataset]


def ref_fasta(wildcards):
    return row(wildcards)["reference_fasta"]


def bam_glob(wildcards):
    return row(wildcards)["bam_glob"]


def enzymes(wildcards):
    r = row(wildcards)
    return f"{r['enzyme1']},{r['enzyme2']}"


def enzyme_pair_label(wildcards):
    r = row(wildcards)
    return f"{r['enzyme1']}+{r['enzyme2']}"


def nominal_min(wildcards):
    return int(row(wildcards)["nominal_min"])


def nominal_max(wildcards):
    return int(row(wildcards)["nominal_max"])


def score_min(wildcards):
    return int(row(wildcards).get("score_min") or 1)


def score_max(wildcards):
    return int(row(wildcards).get("score_max") or 2000)


def species(wildcards):
    return row(wildcards).get("species", "")


def mapq(wildcards):
    value = row(wildcards).get("mapq")
    return int(value) if value not in (None, "") else MAPQ_DEFAULT


rule all:
    input:
        expand("results/tables/{dataset}.empirical_recovery_summary.tsv", dataset=DATASETS),
        expand(
            "results/tables/{dataset}.size_model_fit.downsampled_100k_per_sample.tsv",
            dataset=DATASETS,
        ),
        "results/tables/empirical_recovery_summary.tsv",
        "results/tables/empirical_recovery_model_sensitivity.tsv"


rule bam_list:
    output:
        "results/processed/empirical_recovery/{dataset}/bam_files.txt"
    params:
        pattern=bam_glob
    shell:
        r"""
        mkdir -p $(dirname {output:q})
        python3 - <<'PY' > {output:q}
import glob
pattern = {params.pattern!r}
files = sorted(glob.glob(pattern, recursive=True))
if not files:
    raise SystemExit(f"no BAM/CRAM files matched: {pattern}")
for path in files:
    print(path)
PY
        """


rule extract_tlens:
    input:
        bam_list="results/processed/empirical_recovery/{dataset}/bam_files.txt"
    output:
        tlens="results/processed/empirical_recovery/{dataset}/all.tlens.tsv",
        sample_summary="results/tables/{dataset}.tlen_sample_summary.tsv"
    params:
        mapq=mapq
    shell:
        r"""
        mkdir -p results/raw/empirical_recovery/{wildcards.dataset} \
                 results/processed/empirical_recovery/{wildcards.dataset} \
                 results/tables \
                 benchmark/logs/empirical_recovery \
                 benchmark/memory/empirical_recovery

        rm -f results/raw/empirical_recovery/{wildcards.dataset}/*.tlens.tsv
        rm -f results/raw/empirical_recovery/{wildcards.dataset}/*.pairs.bed
        rm -f results/raw/empirical_recovery/{wildcards.dataset}/*.summary.tsv

        while read -r bam; do
          base="$(basename "$bam")"
          sample="${base%.bam}"
          sample="${sample%.cram}"

          echo "[TLEN] {wildcards.dataset} ${sample}" >&2

          /usr/bin/time -v \
            -o "benchmark/memory/empirical_recovery/{wildcards.dataset}.${sample}.extract_tlens.time" \
            scripts/empirical/extract_bam_recovery_inputs.sh \
              --bam "$bam" \
              --out-prefix "results/raw/empirical_recovery/{wildcards.dataset}/${sample}" \
              --mapq {params.mapq} \
            > "benchmark/logs/empirical_recovery/{wildcards.dataset}.${sample}.extract_tlens.stdout.log" \
            2> "benchmark/logs/empirical_recovery/{wildcards.dataset}.${sample}.extract_tlens.stderr.log"
        done < {input.bam_list:q}

        cat results/raw/empirical_recovery/{wildcards.dataset}/*.tlens.tsv \
          | awk '$1 ~ /^[0-9]+$/ && $1 > 0 {{print $1}}' \
          > {output.tlens:q}

        awk 'FNR == 1 && NR != 1 {{next}} {{print}}' \
          results/raw/empirical_recovery/{wildcards.dataset}/*.summary.tsv \
          > {output.sample_summary:q}
        """


rule radigest_score_range:
    input:
        ref=ref_fasta
    output:
        fragments="results/processed/empirical_recovery/{dataset}/fragments.score_range.tsv",
        json="results/processed/empirical_recovery/{dataset}/hard_window.json"
    params:
        enzymes=enzymes,
        nominal_min=nominal_min,
        nominal_max=nominal_max,
        score_min=score_min,
        score_max=score_max
    threads:
        THREADS
    shell:
        r"""
        mkdir -p results/processed/empirical_recovery/{wildcards.dataset}

        {RADIGEST:q} \
          -fasta {input.ref:q} \
          -enzymes {params.enzymes:q} \
          -min {params.nominal_min} \
          -max {params.nominal_max} \
          -score-min {params.score_min} \
          -score-max {params.score_max} \
          -threads {threads} \
          -fragments-tsv {output.fragments:q} \
          -json {output.json:q}
        """


rule fit_size_model:
    input:
        fragments="results/processed/empirical_recovery/{dataset}/fragments.score_range.tsv",
        tlens="results/processed/empirical_recovery/{dataset}/all.tlens.tsv"
    output:
        "results/tables/{dataset}.size_model_fit.tsv"
    params:
        nominal_min=nominal_min,
        nominal_max=nominal_max,
        score_min=score_min,
        score_max=score_max
    shell:
        r"""
        mkdir -p results/tables

        {RADIGEST_FIT_SIZE_MODEL:q} \
          --fragments {input.fragments:q} \
          --tlens {input.tlens:q} \
          --min {params.nominal_min} \
          --max {params.nominal_max} \
          --score-min {params.score_min} \
          --score-max {params.score_max} \
          --out {output:q}
        """


rule weighted_digest:
    input:
        ref=ref_fasta,
        fit="results/tables/{dataset}.size_model_fit.tsv"
    output:
        fragments="results/processed/empirical_recovery/{dataset}/fragments.empirical_weighted.tsv",
        json="results/processed/empirical_recovery/{dataset}/empirical_weighted.json"
    params:
        enzymes=enzymes,
        nominal_min=nominal_min,
        nominal_max=nominal_max,
        score_min=score_min,
        score_max=score_max
    threads:
        THREADS
    shell:
        r"""
        MODEL_ARGS="$(
          python3 scripts/empirical/model_args_from_fit.py \
            --fit {input.fit:q} \
            --rank 1
        )"

        read -r -a MODEL_ARRAY <<< "$MODEL_ARGS"

        {RADIGEST:q} \
          -fasta {input.ref:q} \
          -enzymes {params.enzymes:q} \
          -min {params.nominal_min} \
          -max {params.nominal_max} \
          -score-min {params.score_min} \
          -score-max {params.score_max} \
          "${{MODEL_ARRAY[@]}}" \
          -threads {threads} \
          -fragments-tsv {output.fragments:q} \
          -json {output.json:q}
        """


rule summarize_empirical_recovery:
    input:
        tlens="results/processed/empirical_recovery/{dataset}/all.tlens.tsv",
        fit="results/tables/{dataset}.size_model_fit.tsv",
        hard_json="results/processed/empirical_recovery/{dataset}/hard_window.json",
        weighted_json="results/processed/empirical_recovery/{dataset}/empirical_weighted.json",
        sample_summary="results/tables/{dataset}.tlen_sample_summary.tsv"
    output:
        "results/tables/{dataset}.empirical_recovery_summary.tsv"
    params:
        species=species,
        enzyme_pair=enzyme_pair_label,
        nominal_min=nominal_min,
        nominal_max=nominal_max,
        score_min=score_min,
        score_max=score_max
    shell:
        r"""
        python3 scripts/empirical/summarize_empirical_recovery.py \
          --dataset {wildcards.dataset:q} \
          --species {params.species:q} \
          --enzyme-pair {params.enzyme_pair:q} \
          --nominal-min {params.nominal_min} \
          --nominal-max {params.nominal_max} \
          --score-min {params.score_min} \
          --score-max {params.score_max} \
          --tlens {input.tlens:q} \
          --fit-table {input.fit:q} \
          --hard-json {input.hard_json:q} \
          --weighted-json {input.weighted_json:q} \
          --sample-summary {input.sample_summary:q} \
          --out {output:q}
        """


rule downsample_tlens:
    input:
        tlens="results/processed/empirical_recovery/{dataset}/all.tlens.tsv"
    output:
        tlens="results/processed/empirical_recovery/{dataset}/downsampled_100k_per_sample.tlens.tsv",
        summary="results/tables/{dataset}.downsampled_100k_per_sample.summary.tsv"
    shell:
        r"""
        python3 scripts/empirical/downsample_tlens_per_sample.py \
          --input-glob "results/raw/empirical_recovery/{wildcards.dataset}/*.tlens.tsv" \
          --max-per-sample {DOWNSAMPLE_PER_SAMPLE} \
          --seed {DOWNSAMPLE_SEED} \
          --out {output.tlens:q} \
          --summary {output.summary:q}
        """


rule fit_downsampled_size_model:
    input:
        fragments="results/processed/empirical_recovery/{dataset}/fragments.score_range.tsv",
        tlens="results/processed/empirical_recovery/{dataset}/downsampled_100k_per_sample.tlens.tsv"
    output:
        "results/tables/{dataset}.size_model_fit.downsampled_100k_per_sample.tsv"
    params:
        nominal_min=nominal_min,
        nominal_max=nominal_max,
        score_min=score_min,
        score_max=score_max
    shell:
        r"""
        {RADIGEST_FIT_SIZE_MODEL:q} \
          --fragments {input.fragments:q} \
          --tlens {input.tlens:q} \
          --min {params.nominal_min} \
          --max {params.nominal_max} \
          --score-min {params.score_min} \
          --score-max {params.score_max} \
          --out {output:q}
        """


rule combined_empirical_recovery_summary:
    input:
        expand("results/tables/{dataset}.empirical_recovery_summary.tsv", dataset=DATASETS)
    output:
        "results/tables/empirical_recovery_summary.tsv"
    shell:
        r"""
        awk 'FNR == 1 && NR != 1 {{next}} {{print}}' {input:q} > {output:q}
        """


rule empirical_recovery_model_sensitivity:
    input:
        pooled=expand("results/tables/{dataset}.size_model_fit.tsv", dataset=DATASETS),
        downsampled=expand(
            "results/tables/{dataset}.size_model_fit.downsampled_100k_per_sample.tsv",
            dataset=DATASETS,
        )
    output:
        "results/tables/empirical_recovery_model_sensitivity.tsv"
    run:
        import csv
        from pathlib import Path

        fields = [
            "dataset",
            "analysis",
            "rank",
            "model",
            "params",
            "delta_aic",
            "kl",
            "obs_mean",
            "pred_mean",
            "obs_pairs",
            "pred_weight_sum",
            "source",
        ]

        rows = []
        for dataset in DATASETS:
            for analysis, path in [
                ("pooled", Path(f"results/tables/{dataset}.size_model_fit.tsv")),
                (
                    "downsampled_100k_per_sample",
                    Path(
                        f"results/tables/{dataset}."
                        "size_model_fit.downsampled_100k_per_sample.tsv"
                    ),
                ),
            ]:
                with path.open(newline="") as handle:
                    reader = csv.DictReader(handle, delimiter="\t")
                    for row in reader:
                        rows.append(
                            {
                                "dataset": dataset,
                                "analysis": analysis,
                                "rank": row.get("rank", ""),
                                "model": row.get("model", ""),
                                "params": row.get("params", ""),
                                "delta_aic": row.get("delta_aic", ""),
                                "kl": row.get("kl", ""),
                                "obs_mean": row.get("obs_mean", ""),
                                "pred_mean": row.get("pred_mean", ""),
                                "obs_pairs": row.get("obs_pairs", ""),
                                "pred_weight_sum": row.get("pred_weight_sum", ""),
                                "source": str(path),
                            }
                        )

        with open(output[0], "w", newline="") as handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
