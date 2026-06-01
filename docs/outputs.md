# Outputs

Generated outputs belong under `results/` and benchmark telemetry belongs under `benchmark/`.

Only `.gitkeep` files are committed in generated-output directories. Tables and figures must be produced by Snakemake rules and declared in `config/artifacts.tsv` when they support manuscript claims.

Stage 2 smoke outputs are:

```text
results/validation/synthetic_validation_results.tsv
results/manuscript/tables/table_02_synthetic_validation.tsv
benchmark/logs/validation/synthetic_validation.log
results/validation/raw/synthetic/*.fragments.tsv
results/validation/raw/synthetic/*.json
results/validation/raw/synthetic/*.log
```

Stage 3 reference outputs are:

```text
data/reference/small_yeast_s288c.fa.gz
data/reference/small_yeast_s288c.fa
data/reference/moderate_cannabis_pink-pepper.fa.gz
data/reference/moderate_cannabis_pink-pepper.fa
results/references/reference_checksums.tsv
benchmark/logs/references/*.log
results/references/metadata/*
data/reference/ncbi_packages/*
```

Stage 4/4b/4c comparator outputs are:

```text
results/comparators/digital_rads/digital_rads_smoke_single__D1.summary.tsv
results/comparators/ddradseqtools/ddradseqtools_smoke_single__D1.interval_compare.summary.tsv
results/comparators/digital_rads/digital_rads_small_yeast_s288c_B1.summary.tsv
results/comparators/ddradseqtools/small_yeast_s288c_B1.interval_compare.summary.tsv
results/comparators/simrad/simrad_count_comparison.tsv
results/comparators/simrad/simrad_small_yeast_s288c_B1.tsv
results/comparators/ddgrader/ddgrader_binned_smoke_summary.tsv
results/comparators/ddgrader/ddgrader_binned_smoke_detail.tsv
results/comparators/ddgrader/ddgrader_binned_screening_summary.tsv
results/comparators/ddgrader/ddgrader_binned_screening_detail.tsv
results/comparators/comparator_case_matrix.tsv
results/comparators/cut_equivalence_summary.tsv
results/manuscript/tables/table_03_interval_comparisons.tsv
results/manuscript/tables/table_03_comparator_semantics.tsv
benchmark/logs/comparators/**/*.log
```

Raw comparator output, normalized interval TSVs, binned-count TSVs, detail comparison TSVs, version logs, and benchmark logs are generated artifacts and are not tracked.

Stage 5a input-format performance outputs are:

```text
results/performance/input_format/radigest_input_format_comparison.tsv
results/manuscript/tables/table_06_input_format.tsv
benchmark/logs/performance/input_format/*.log
results/performance/input_format/raw/*.runs.tsv
results/performance/input_format/raw/*/*.fragments.tsv
results/performance/input_format/raw/*/*.json
```

The Stage 5a claim is limited to radigest plain-FASTA versus gzip-FASTA input-format timing on the small public yeast reference. Fragment-count consistency is enforced before wall-time ratios are interpreted.

Stage 5b screening-speed performance outputs are:

```text
results/performance/screening_speed/screening_speed_summary.tsv
results/manuscript/tables/table_05_screening_speed.tsv
benchmark/logs/performance/screening_speed/*.log
results/performance/screening_speed/raw/*.runs.tsv
results/performance/screening_speed/raw/*/json/*.json
results/performance/screening_speed/raw/*/logs/*.log
```

The Stage 5b claim is limited to cached radigest candidate-pair screening throughput from `radigest-screen-pairs-cached`. It does not compare coordinates against external tools and it does not make a cross-tool equivalence claim.

Stage 5c thread-scaling performance outputs are:

```text
results/performance/thread_scaling/radigest_thread_scaling_summary.tsv
results/manuscript/tables/table_s02_radigest_thread_scaling.tsv
benchmark/logs/performance/thread_scaling/*.log
results/performance/thread_scaling/raw/*.runs.tsv
results/performance/thread_scaling/raw/*/*.json
results/performance/thread_scaling/raw/*/*.fragments.tsv
```

The Stage 5c claim is limited to intra-tool radigest thread scaling on the moderate public cannabis Pink Pepper reference. JSON-summary and fragment-TSV output modes are summarized separately, and retained-fragment counts must agree within each thread-scaling comparison group before speedups are interpreted. The default reviewer tier uses 1, 2, and 4 threads so `make performance-thread-scaling THREADS=4` can run without Snakemake thread downscaling.


Stage 5d pair-screen job-scaling performance outputs are:

```text
results/performance/pair_screen_scaling/pair_screen_scaling_summary.tsv
results/manuscript/tables/table_s03_pair_screen_job_scaling.tsv
benchmark/logs/performance/pair_screen_scaling/*.log
results/performance/pair_screen_scaling/raw/*.runs.tsv
results/performance/pair_screen_scaling/raw/*/json/*.json
results/performance/pair_screen_scaling/raw/*/logs/*.log
```

The Stage 5d claim is limited to intra-tool `radigest-screen-pairs-cached` job scaling on the moderate public cannabis Pink Pepper reference. Candidate-pair evaluation and reported JSON coverage must agree within each job-scaling comparison group before speedups are interpreted. The default reviewer tier uses 1, 2, and 4 jobs so `make performance-pair-screen-scaling THREADS=4` can run without Snakemake thread downscaling.
