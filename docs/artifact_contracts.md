# Artifact contracts

`config/artifacts.tsv` maps manuscript claims to required outputs, manuscript-ready artifacts, and producer rules.

Comparator claims now include both interval-equivalence outputs and lower-resolution comparator-semantics outputs:

```text
results/manuscript/tables/table_03_interval_comparisons.tsv
results/manuscript/tables/table_03_comparator_semantics.tsv
```

Audit code must use this registry as the source of truth rather than hard-coded table or figure paths.

Stage 5a implements artifact `C06`, and Stage 5b implements artifact `C05`:

```text
results/performance/input_format/radigest_input_format_comparison.tsv
results/manuscript/tables/table_06_input_format.tsv
results/performance/screening_speed/screening_speed_summary.tsv
results/manuscript/tables/table_05_screening_speed.tsv
```

The input-format table is generated from `config/performance_cases.tsv`. The screening-speed table is generated from `config/screening_speed_cases.tsv` and measures cached `radigest-screen-pairs-cached` candidate-pair screening throughput only.
