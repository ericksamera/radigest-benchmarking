# Release checklist

Before release:

1. `make check` passes.
2. `make reviewer-nonempirical THREADS=4 RADIGEST=/path/to/radigest` passes.
3. `make audit` passes.
4. Every `required_for_release=true` row in `config/artifacts.tsv` has present, non-empty outputs and manuscript artifacts.
5. Environment, artifact-status, and claim-audit tables are regenerated.
6. `results/manuscript/tables/audit_passed.txt` exists and contains `PASS`.

Audit outputs:

```text
results/manuscript/tables/artifact_status.tsv
results/manuscript/tables/claim_audit.tsv
results/manuscript/tables/environment.tsv
results/manuscript/tables/audit_passed.txt
```

A missing optional empirical artifact is acceptable while `C11 required_for_release=false`. A missing required release artifact is a release blocker.
