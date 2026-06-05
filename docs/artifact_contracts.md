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

Stage 5e implements artifact `C17`:

```text
results/performance/large_genome/large_genome_summary.tsv
results/manuscript/tables/table_s04_large_genome.tsv
```

The table is generated from `config/large_genome_cases.tsv` and is limited to a radigest wheat large-reference timing claim. Optional cannabis rows remain guardrails and are not the release-required large-reference claim.

Stage 5f implements artifacts `C04` and `C18`:

```text
results/performance/matched_tools/tool_timing_interpretation.tsv
results/manuscript/tables/table_04_matched_timing.tsv
results/manuscript/figures/figure_04_matched_tool_timing.pdf
```

The table and R/ggplot2 figure are generated from `config/matched_tool_timing_cases.tsv`. They are intentionally semantics-aware: radigest is the native anchor, Digital_RADs.py and DDRADSEQTOOLS are normalized-interval comparator tools, SimRAD is count-only, and ddgRADer is binned-screening only. The required matched-tool set includes complete small-yeast and moderate-cannabis groups plus a large-wheat subset that excludes SimRAD because SimRAD cannot process the full wheat FASTA under R string-size limits.

## Stage 6 empirical scaffold

Optional empirical recovery remains artifact `C11`. The current empirical stage
declares the local/private input contract in `config/empirical_libraries.tsv` and
keeps `C11 required_for_release=false` until TLEN extraction and public input
provenance are wired.

## Stage 7a/7b audit contract

Stage 7 makes `config/artifacts.tsv` executable as a release contract. Stage 7a generates artifact, claim, and environment audit tables. Stage 7b adds a release checklist and output index. The audit target generates:

```text
results/manuscript/tables/artifact_status.tsv
results/manuscript/tables/claim_audit.tsv
results/manuscript/tables/environment.tsv
results/manuscript/tables/release_checklist.tsv
results/manuscript/tables/output_index.tsv
results/manuscript/tables/audit_passed.txt
```

`artifact_status.tsv` reports file existence, size, modification time, and PASS/WARN/FAIL status for every claim row. `claim_audit.tsv` adds a manuscript-facing claim boundary and release status. `environment.tsv` records Git, Python, Snakemake, radigest, cached-screening-binary, platform, and conda provenance.

`audit_passed.txt` is written only when no `required_for_release=true` claim has a release-blocking failure and all required release-checklist rows pass. Optional empirical artifacts can remain WARN while `C11 required_for_release=false`.

## Stage 7b release checklist and output index

`make audit` generates two derived release-management tables:

```text
results/manuscript/tables/output_index.tsv
results/manuscript/tables/release_checklist.tsv
```

These files are not individual manuscript claim artifacts. They summarize and enforce the release contract declared in `config/artifacts.tsv`. The output index is generated from `artifact_status.tsv`, `claim_audit.tsv`, and `environment.tsv`; the release checklist is generated from artifact status, claim audit, environment metadata, and the output index.
