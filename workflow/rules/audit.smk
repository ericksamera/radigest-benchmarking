# Stage 7a artifact, claim, and environment audit rules.

AUDIT_ARTIFACT_STATUS = "results/manuscript/tables/artifact_status.tsv"
AUDIT_CLAIM_AUDIT = "results/manuscript/tables/claim_audit.tsv"
AUDIT_ENVIRONMENT_TABLE = "results/manuscript/tables/environment.tsv"
AUDIT_RELEASE_GATE = "results/manuscript/tables/audit_passed.txt"
AUDIT_OUTPUTS = [
    AUDIT_ARTIFACT_STATUS,
    AUDIT_CLAIM_AUDIT,
    AUDIT_ENVIRONMENT_TABLE,
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
        )
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
          > {log:q} 2>&1
        """


rule audit_release_gate:
    input:
        audit=AUDIT_CLAIM_AUDIT,
        status=AUDIT_ARTIFACT_STATUS,
        environment=AUDIT_ENVIRONMENT_TABLE
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
          --out {output.gate:q} \
          > {log:q} 2>&1
        """
