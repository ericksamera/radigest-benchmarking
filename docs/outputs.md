# Outputs

Generated outputs belong under `results/` and benchmark telemetry belongs under `benchmark/`.

Only `.gitkeep` files are committed in generated-output directories. Tables and figures must be produced by Snakemake rules and declared in `config/artifacts.tsv` when they support manuscript claims.

Stage 2 smoke outputs are:

```text
results/validation/synthetic_validation_results.tsv
results/manuscript/tables/table_s01_synthetic_validation.tsv
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
results/manuscript/tables/table_02_comparator_exact_counts.tsv
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

The Stage 5c claim is limited to intra-tool radigest thread scaling on the moderate public cannabis Pink Pepper reference. JSON-summary and fragment-TSV output modes are summarized separately, and retained-fragment counts must agree within each thread-scaling comparison group before speedups are interpreted. The default reviewer tier uses 1, 2, and 4 threads so `make performance-thread-scaling THREADS=8` can run without Snakemake thread downscaling.

Stage 5d pair-screen job-scaling performance outputs are:

```text
results/performance/pair_screen_scaling/pair_screen_scaling_summary.tsv
results/manuscript/tables/table_s03_pair_screen_job_scaling.tsv
benchmark/logs/performance/pair_screen_scaling/*.log
results/performance/pair_screen_scaling/raw/*.runs.tsv
results/performance/pair_screen_scaling/raw/*/json/*.json
results/performance/pair_screen_scaling/raw/*/logs/*.log
```

The Stage 5d claim is limited to intra-tool `radigest-screen-pairs-cached` job scaling on the moderate public cannabis Pink Pepper reference. Candidate-pair evaluation and reported JSON coverage must agree within each job-scaling comparison group before speedups are interpreted. The default reviewer tier uses 1, 2, 4, and 8 jobs so `make performance-pair-screen-scaling THREADS=8` can run without Snakemake thread downscaling.

Stage 5e large-reference performance outputs are:

```text
results/performance/large_genome/large_genome_summary.tsv
results/manuscript/tables/table_s04_large_genome.tsv
benchmark/logs/performance/large_genome/*.log
results/performance/large_genome/raw/*.runs.tsv
results/performance/large_genome/raw/*/*.json
```

The Stage 5e claim is limited to radigest JSON timing on the large public Triticum aestivum Chinese Spring wheat reference. The moderate cannabis case remains optional as a guardrail. This is a large-reference performance check, not a cross-tool equivalence or empirical recovery claim.

Stage 5f matched-tool timing outputs are:

```text
results/performance/matched_tools/tool_timing_runs.tsv
results/performance/matched_tools/tool_timing_summary.tsv
results/performance/matched_tools/tool_timing_interpretation.tsv
results/manuscript/tables/table_04_matched_timing.tsv
results/manuscript/figures/figure_04_matched_tool_timing.pdf
benchmark/logs/performance/matched_tools/*.log
results/performance/matched_tools/raw/*/*.runs.tsv
```

The Stage 5f claim is semantics-aware matched timing across complete small-yeast and medium-cannabis groups plus the required large-wheat subset. SimRAD is excluded from the wheat subset because it cannot process the full wheat FASTA under R string-size limits. The table records each tool path's comparison level, primary output type, and allowed claim so that interval, count-only, and binned-screening timings are not treated as identical evidence. The matched-tool figure uses the same manuscript table as the tabular artifact.

Stage 5 manuscript figures are generated from manuscript-facing performance tables with R/ggplot2:

```text
results/manuscript/figures/figure_04_matched_tool_timing.pdf
results/manuscript/figures/figure_05_screening_speed.pdf
results/manuscript/figures/figure_06_input_format.pdf
results/manuscript/figures/figure_s02_thread_scaling.pdf
results/manuscript/figures/figure_s03_pair_screen_job_scaling.pdf
results/manuscript/figures/figure_s04_large_genome.pdf
```

These figures are generated by `make figures`, `make performance`, or `make manuscript`. The matched-tool timing figure is promoted in `config/artifacts.tsv` because it is the figure-level view of release-required matched timing.

Stage 6 empirical outputs declare the tracked manifest contract, the Sockeye
reference download, per-library BAM inventories, and BAM-derived TLEN tables for
enabled rows:

```text
config/empirical_libraries.tsv
data/reference/sockeye_oner_uvic_2_0.fa.gz
data/reference/sockeye_oner_uvic_2_0.fa
results/empirical/{library_id}/bam_manifest.tsv
results/empirical/{library_id}/bams/{bam_id}/tlens.txt
results/empirical/{library_id}/bams/{bam_id}/tlen_histogram.tsv
results/empirical/{library_id}/bams/{bam_id}/tlen_qc.tsv
results/empirical/{library_id}/tlens.txt
results/empirical/{library_id}/tlen_histogram.tsv
results/empirical/{library_id}/tlen_qc.tsv
results/empirical/{library_id}/predictions/raw.fragments.tsv
results/empirical/{library_id}/predictions/raw.length_histogram.tsv
results/empirical/{library_id}/predictions/raw.summary.tsv
results/empirical/{library_id}/predictions/hard.fragments.tsv
results/empirical/{library_id}/predictions/hard.length_histogram.tsv
results/empirical/{library_id}/predictions/hard.summary.tsv
results/empirical/{library_id}/depth_validation/design.summary.tsv
results/empirical/{library_id}/depth_validation/design.tsv
results/empirical/{library_id}/depth_validation/design.json
results/empirical/{library_id}/depth_validation/loci.bed
results/empirical/{library_id}/depth_validation/loci.json
results/empirical/{library_id}/depth_validation/per_sample_depth.tsv
results/empirical/{library_id}/depth_validation/summary.tsv
results/manuscript/tables/table_08_empirical_depth_validation.tsv
results/empirical/{library_id}/size_model_grid.tsv
results/empirical/{library_id}/best_size_model.tsv
results/empirical/{library_id}/size_model_curves.tsv
results/empirical/{library_id}/figures/size_model_overlay__{library_id}.pdf
results/empirical/{library_id}/figures/size_model_overlay.pdf
results/empirical/size_model_fit_ranking.tsv
results/empirical/figures/size_model_fit_ranking.pdf
results/manuscript/figures/figure_03_empirical_size_selection_summary.pdf
results/empirical/.gitkeep
```

The depth-validation summary records the configured `radigest-design` run, the
BED predicted-locus set, per-sample empirical mean read-pair depth per locus,
and read-budget-normalized predicted depths. Size-selection outputs record
per-library model grids, curves, dataset-prefixed overlay figures, the cross-library
model-fit ranking table, and the manuscript Figure 3 empirical size-selection
summary.

Stage 7 audit outputs are:

```text
results/manuscript/tables/artifact_status.tsv
results/manuscript/tables/claim_audit.tsv
results/manuscript/tables/environment.tsv
results/manuscript/tables/output_index.tsv
results/manuscript/tables/release_checklist.tsv
results/manuscript/tables/audit_passed.txt
benchmark/logs/audit/*.log
```

`artifact_status.tsv` and `claim_audit.tsv` are generated from `config/artifacts.tsv`. `output_index.tsv` indexes release-relevant outputs. `release_checklist.tsv` converts audit results into release checks. `audit_passed.txt` is written only when all `required_for_release=true` artifacts are present and non-empty and no checklist row has a blocking failure.
