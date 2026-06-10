# Synthetic validation rules for the clean v2 workflow.

SYNTHETIC_FASTA = "data/synthetic/synthetic_validation.fa"
SYNTHETIC_EXPECTED = "config/synthetic_expected.tsv"
SYNTHETIC_VALIDATION_SUMMARY = "results/validation/synthetic_validation_results.tsv"
SYNTHETIC_VALIDATION_TABLE = (
    "results/manuscript/tables/table_s01_synthetic_validation.tsv"
)
SYNTHETIC_VALIDATION_OUTPUTS = [
    SYNTHETIC_VALIDATION_SUMMARY,
    SYNTHETIC_VALIDATION_TABLE,
]


rule validation_all:
    input:
        SYNTHETIC_VALIDATION_OUTPUTS,


rule synthetic_validation:
    input:
        fasta=SYNTHETIC_FASTA,
        expected=SYNTHETIC_EXPECTED,
    output:
        summary=SYNTHETIC_VALIDATION_SUMMARY,
    log:
        "benchmark/logs/validation/synthetic_validation.log",
    params:
        radigest=lambda wildcards: config.get("radigest", "radigest"),
        out_dir="results/validation/raw/synthetic",
    shell:
        r"""
        mkdir -p benchmark/logs/validation results/validation/raw/synthetic
        python3 scripts/validation/validate_synthetic.py \
            --radigest {params.radigest:q} \
            --fasta {input.fasta:q} \
            --expected {input.expected:q} \
            --out-dir {params.out_dir:q} \
            --summary {output.summary:q} \
            >{log:q} 2>&1
        """
