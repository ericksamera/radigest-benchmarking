# Artifact contracts

`config/artifacts.tsv` maps manuscript claims to required outputs, manuscript-ready artifacts, and producer rules.

Comparator claims now include both interval-equivalence outputs and lower-resolution comparator-semantics outputs:

```text
results/manuscript/tables/table_03_interval_comparisons.tsv
results/manuscript/tables/table_03_comparator_semantics.tsv
```

Audit code must use this registry as the source of truth rather than hard-coded table or figure paths.
