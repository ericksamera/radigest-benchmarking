# Stage 7 artifact, claim, environment, output-index, and release-checklist audit rules.

AUDIT_ARTIFACT_STATUS = "results/manuscript/tables/artifact_status.tsv"
AUDIT_CLAIM_AUDIT = "results/manuscript/tables/claim_audit.tsv"
AUDIT_ENVIRONMENT_TABLE = "results/manuscript/tables/environment.tsv"
AUDIT_OUTPUT_INDEX = "results/manuscript/tables/output_index.tsv"
AUDIT_RELEASE_CHECKLIST = "results/manuscript/tables/release_checklist.tsv"
AUDIT_RELEASE_GATE = "results/manuscript/tables/audit_passed.txt"
AUDIT_OUTPUTS = [
    AUDIT_ARTIFACT_STATUS,
    AUDIT_CLAIM_AUDIT,
    AUDIT_ENVIRONMENT_TABLE,
    AUDIT_OUTPUT_INDEX,
    AUDIT_RELEASE_CHECKLIST,
    AUDIT_RELEASE_GATE,
]


rule build_artifact_status:
    input:
        artifacts="config/artifacts.tsv"
    output:
        status=AUDIT_ARTIFACT_STATUS
    log:
        "benchmark/logs/audit/artifact_status.log"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/manuscript/tables benchmark/logs/audit
        python3 scripts/audit/build_artifact_status.py \
          --artifacts {input.artifacts:q} \
          --out {output.status:q} \
          --root . \
          > {log:q} 2>&1
        """


rule build_claim_audit:
    input:
        status=AUDIT_ARTIFACT_STATUS
    output:
        audit=AUDIT_CLAIM_AUDIT
    log:
        "benchmark/logs/audit/claim_audit.log"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/manuscript/tables benchmark/logs/audit
        python3 scripts/audit/build_claim_audit.py \
          --artifact-status {input.status:q} \
          --out {output.audit:q} \
          > {log:q} 2>&1
        """


rule build_environment_table:
    output:
        table=AUDIT_ENVIRONMENT_TABLE
    log:
        "benchmark/logs/audit/environment.log"
    params:
        radigest=lambda wildcards: config.get("radigest", "radigest"),
        screen_pairs_cached=lambda wildcards: config.get(
            "radigest_screen_pairs_cached", "auto"
        ),
        bench_screen_cached=lambda wildcards: config.get(
            "radigest_bench_screen_cached", "auto"
        ),
        radigest_design=lambda wildcards: config.get("radigest_design", "radigest-design")
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/manuscript/tables benchmark/logs/audit
        python3 scripts/audit/build_environment_table.py \
          --out {output.table:q} \
          --root . \
          --radigest {params.radigest:q} \
          --radigest-screen-pairs-cached {params.screen_pairs_cached:q} \
          --radigest-bench-screen-cached {params.bench_screen_cached:q} \
          --radigest-design {params.radigest_design:q} \
          > {log:q} 2>&1
        """


rule build_output_index:
    input:
        status=AUDIT_ARTIFACT_STATUS,
        audit=AUDIT_CLAIM_AUDIT,
        environment=AUDIT_ENVIRONMENT_TABLE
    output:
        index=AUDIT_OUTPUT_INDEX
    log:
        "benchmark/logs/audit/output_index.log"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/manuscript/tables benchmark/logs/audit
        python3 scripts/audit/build_output_index.py \
          --artifact-status {input.status:q} \
          --claim-audit {input.audit:q} \
          --environment {input.environment:q} \
          --out {output.index:q} \
          --root . \
          > {log:q} 2>&1
        """


rule build_release_checklist:
    input:
        audit=AUDIT_CLAIM_AUDIT,
        status=AUDIT_ARTIFACT_STATUS,
        environment=AUDIT_ENVIRONMENT_TABLE,
        output_index=AUDIT_OUTPUT_INDEX
    output:
        checklist=AUDIT_RELEASE_CHECKLIST
    log:
        "benchmark/logs/audit/release_checklist.log"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/manuscript/tables benchmark/logs/audit
        python3 scripts/audit/build_release_checklist.py \
          --claim-audit {input.audit:q} \
          --artifact-status {input.status:q} \
          --environment {input.environment:q} \
          --output-index {input.output_index:q} \
          --out {output.checklist:q} \
          > {log:q} 2>&1
        """


rule audit_release_gate:
    input:
        audit=AUDIT_CLAIM_AUDIT,
        status=AUDIT_ARTIFACT_STATUS,
        environment=AUDIT_ENVIRONMENT_TABLE,
        output_index=AUDIT_OUTPUT_INDEX,
        checklist=AUDIT_RELEASE_CHECKLIST
    output:
        gate=AUDIT_RELEASE_GATE
    log:
        "benchmark/logs/audit/release_gate.log"
    conda:
        "../envs/benchmark.yml"
    shell:
        r"""
        mkdir -p results/manuscript/tables benchmark/logs/audit
        python3 scripts/audit/check_audit_release.py \
          --claim-audit {input.audit:q} \
          --release-checklist {input.checklist:q} \
          --out {output.gate:q} \
          > {log:q} 2>&1
        """
