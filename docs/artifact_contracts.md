# Artifact contracts

`config/artifacts.tsv` maps manuscript claims to required outputs, manuscript-ready artifacts, and producer rules.

Comparator claims now include both interval-equivalence outputs and lower-resolution comparator-semantics outputs:

```text
results/manuscript/tables/table_03_interval_comparisons.tsv
results/manuscript/tables/table_03_comparator_semantics.tsv
```

Audit code must use this registry as the source of truth rather than hard-coded table or figure paths.

Stage 5a implements artifact `C06`, Stage 5b implements artifact `C05`, Stage 5c implements artifact `C07`, and Stage 5d implements artifact `C08`:

```text
results/performance/input_format/radigest_input_format_comparison.tsv
results/manuscript/tables/table_06_input_format.tsv
results/performance/screening_speed/screening_speed_summary.tsv
results/manuscript/tables/table_05_screening_speed.tsv
results/performance/thread_scaling/radigest_thread_scaling_summary.tsv
results/manuscript/tables/table_s02_radigest_thread_scaling.tsv
results/performance/pair_screen_scaling/pair_screen_scaling_summary.tsv
results/manuscript/tables/table_s03_pair_screen_job_scaling.tsv
```

The input-format table is generated from `config/performance_cases.tsv`. The screening-speed table is generated from `config/screening_speed_cases.tsv` and measures cached `radigest-screen-pairs-cached` candidate-pair screening throughput only. The thread-scaling table is generated from `config/thread_scaling_cases.tsv` and measures intra-tool radigest scaling across 1, 2, and 4 threads on the moderate public reference. The pair-screen job-scaling table is generated from `config/pair_screen_scaling_cases.tsv` and measures cached pair-screen job scaling across 1, 2, and 4 jobs on the moderate public reference.
