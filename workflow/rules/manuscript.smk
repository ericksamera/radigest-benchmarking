# Manuscript artifact rules for the clean v2 workflow.


HONEYSUCKLE_DESIGN_REFERENCE = "data/reference/honeysuckle_gca021464415.fa"
HONEYSUCKLE_DESIGN_CANDIDATES = "config/candidate_enzymes_30.txt"
HONEYSUCKLE_DESIGN_2PCT_DIR = (
    "results/experimental_design/honeysuckle_gca021464415_2pct_60x_20samples"
)
HONEYSUCKLE_DESIGN_1P5PCT_DIR = (
    "results/experimental_design/honeysuckle_gca021464415_1p5pct_60x_20samples"
)
HONEYSUCKLE_DESIGN_2PCT_TSV = f"{HONEYSUCKLE_DESIGN_2PCT_DIR}/design.tsv"
HONEYSUCKLE_DESIGN_1P5PCT_TSV = f"{HONEYSUCKLE_DESIGN_1P5PCT_DIR}/design.tsv"
MANUSCRIPT_DESIGN_SPACE_FIGURE = (
    "results/manuscript/figures/figure_02_honeysuckle_design_space.pdf"
)
MANUSCRIPT_DESIGN_SPACE_FIGURE_OUTPUTS = [MANUSCRIPT_DESIGN_SPACE_FIGURE]


def _candidate_enzymes_csv(path):
    names = []
    with open(path) as handle:
        for raw in handle:
            text = raw.strip()
            if text and not text.startswith("#"):
                names.append(text)
    if len(names) < 2:
        raise ValueError(f"{path}: expected at least two candidate enzymes")
    return ",".join(names)


rule synthetic_validation_manuscript_table:
    input:
        summary=SYNTHETIC_VALIDATION_SUMMARY,
    output:
        table=SYNTHETIC_VALIDATION_TABLE,
    shell:
        r"""
        python3 scripts/manuscript/make_synthetic_validation_table.py \
            --input {input.summary:q} \
            --out {output.table:q} \
            --require-pass
        """


rule honeysuckle_design_2pct:
    input:
        reference=HONEYSUCKLE_DESIGN_REFERENCE,
        candidates=HONEYSUCKLE_DESIGN_CANDIDATES,
    output:
        summary_tsv=f"{HONEYSUCKLE_DESIGN_2PCT_DIR}/design.summary.tsv",
        tsv=HONEYSUCKLE_DESIGN_2PCT_TSV,
        json=f"{HONEYSUCKLE_DESIGN_2PCT_DIR}/design.json",
    log:
        "benchmark/logs/experimental_design/honeysuckle_gca021464415_2pct_60x_20samples.design.log",
    threads: 8
    params:
        radigest_design=lambda wildcards: config.get(
            "radigest_design", "radigest-design"
        ),
        enzymes=lambda wildcards, input: _candidate_enzymes_csv(input.candidates),
        out_dir=HONEYSUCKLE_DESIGN_2PCT_DIR,
    shell:
        r"""
        mkdir -p {params.out_dir:q} benchmark/logs/experimental_design
        {params.radigest_design:q} \
            --fasta {input.reference:q} \
            --enzymes {params.enzymes:q} \
            --target-genome-pct 2 \
            --coverage-tolerance-pct 0.25 \
            --desired-depth 60 \
            --samples 20 \
            --read-layout pe \
            --read-length 300 \
            --threads {threads} \
            --jobs 8 \
            --build-workers {threads} \
            --flowcell-read-pairs 50M \
            --usable-read-fraction 1.0 \
            --min 200 \
            --max 500 \
            --score-min 1 \
            --score-max 1200 \
            --size-model soft-window \
            --size-mean 0 \
            --size-sd 0 \
            --size-edge-sd 50 \
            --out-dir {params.out_dir:q} \
            --force \
            >{log:q} 2>&1
        test -s {output.summary_tsv:q}
        test -s {output.tsv:q}
        test -s {output.json:q}
        """


rule honeysuckle_design_1p5pct:
    input:
        reference=HONEYSUCKLE_DESIGN_REFERENCE,
        candidates=HONEYSUCKLE_DESIGN_CANDIDATES,
    output:
        summary_tsv=f"{HONEYSUCKLE_DESIGN_1P5PCT_DIR}/design.summary.tsv",
        tsv=HONEYSUCKLE_DESIGN_1P5PCT_TSV,
        json=f"{HONEYSUCKLE_DESIGN_1P5PCT_DIR}/design.json",
    log:
        "benchmark/logs/experimental_design/honeysuckle_gca021464415_1p5pct_60x_20samples.design.log",
    threads: 8
    params:
        radigest_design=lambda wildcards: config.get(
            "radigest_design", "radigest-design"
        ),
        enzymes=lambda wildcards, input: _candidate_enzymes_csv(input.candidates),
        out_dir=HONEYSUCKLE_DESIGN_1P5PCT_DIR,
    shell:
        r"""
        mkdir -p {params.out_dir:q} benchmark/logs/experimental_design
        {params.radigest_design:q} \
            --fasta {input.reference:q} \
            --enzymes {params.enzymes:q} \
            --target-genome-pct 1.5 \
            --coverage-tolerance-pct 0.25 \
            --desired-depth 60 \
            --samples 20 \
            --read-layout pe \
            --read-length 300 \
            --threads {threads} \
            --jobs 8 \
            --build-workers {threads} \
            --flowcell-read-pairs 50M \
            --usable-read-fraction 1.0 \
            --min 200 \
            --max 500 \
            --score-min 1 \
            --score-max 1200 \
            --size-model soft-window \
            --size-mean 0 \
            --size-sd 0 \
            --size-edge-sd 50 \
            --out-dir {params.out_dir:q} \
            --force \
            >{log:q} 2>&1
        test -s {output.summary_tsv:q}
        test -s {output.tsv:q}
        test -s {output.json:q}
        """


rule make_honeysuckle_design_space_figure:
    input:
        design_2pct=HONEYSUCKLE_DESIGN_2PCT_TSV,
        design_1p5pct=HONEYSUCKLE_DESIGN_1P5PCT_TSV,
    output:
        figure=MANUSCRIPT_DESIGN_SPACE_FIGURE,
    log:
        "benchmark/logs/manuscript/figure_02_honeysuckle_design_space.log",
    conda:
        "../envs/figures.yml"
    shell:
        r"""
        mkdir -p results/manuscript/figures benchmark/logs/manuscript
        Rscript scripts/manuscript/make_honeysuckle_design_space_figure.R \
            --design-2pct {input.design_2pct:q} \
            --design-1p5pct {input.design_1p5pct:q} \
            --out {output.figure:q} \
            >{log:q} 2>&1
        """


rule manuscript_design_space_figure_all:
    input:
        MANUSCRIPT_DESIGN_SPACE_FIGURE_OUTPUTS,
