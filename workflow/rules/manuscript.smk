# Manuscript artifact rules for the clean v2 workflow.

rule synthetic_validation_manuscript_table:
    input:
        summary=SYNTHETIC_VALIDATION_SUMMARY
    output:
        table=SYNTHETIC_VALIDATION_TABLE
    shell:
        r"""
        python3 scripts/manuscript/make_synthetic_validation_table.py \
          --input {input.summary:q} \
          --out {output.table:q} \
          --require-pass
        """
