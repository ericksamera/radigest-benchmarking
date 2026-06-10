# Quickstart

This document tracks the reviewer-oriented entry points for the clean v2 repository.

## Smoke validation

```bash
make check
make install-radigest
make smoke
```

The smoke run writes:

```text
results/validation/synthetic_validation_results.tsv
results/manuscript/tables/table_s01_synthetic_validation.tsv
```

After `make install-radigest`, the explicit `RADIGEST=` assignment can be omitted. Manual `RADIGEST=/path/to/radigest` overrides still work.

## References

```bash
make references THREADS=8
```

This downloads the public references declared in `config/references.tsv`, writes gzipped and plain FASTA files under `data/reference/`, and records checksums in `results/references/reference_checksums.tsv`.

## Comparators

Install or update comparator tools first:

```bash
make install-comparators
# or, for radigest plus all comparator tools when using the default local binary path:
make install-all
```

The individual installer targets still exist: `make install-digital-rads`, `make install-ddradseqtools`, `make install-simrad`, and `make install-ddgrader`.

Then run:

```bash
make comparators THREADS=8 RADIGEST=/path/to/radigest
```

The comparator target writes exact normalized interval comparison summaries for Digital_RADs.py and DDRADSEQTOOLS `rsitesearch.py`, a SimRAD count-level sanity comparison, a ddgRADer binned-screening comparison, and two manuscript-facing tables:

```text
results/manuscript/tables/table_02_comparator_exact_counts.tsv
results/manuscript/tables/table_03_interval_comparisons.tsv
results/manuscript/tables/table_03_comparator_semantics.tsv
```

## Performance

```bash
make performance-input-format THREADS=8 RADIGEST=/path/to/radigest
make performance-screening-speed THREADS=8 RADIGEST=/path/to/radigest
make performance-thread-scaling THREADS=8 RADIGEST=/path/to/radigest
make performance-pair-screen-scaling THREADS=8 RADIGEST=/path/to/radigest
make performance-matched-tools THREADS=8 RADIGEST=/path/to/radigest
# Optional when the cached binary is not next to RADIGEST or on PATH:
make performance-screening-speed THREADS=8 \
  RADIGEST=/path/to/radigest \
  RADIGEST_SCREEN_PAIRS_CACHED=/path/to/radigest-screen-pairs-cached
```

Screening-speed and pair-screen-scaling targets require the radigest development/helper binary set. The local `make install-radigest` target builds that set with upstream `make build-dev`; for manual radigest installs, run upstream `make install-dev` or pass `RADIGEST_SCREEN_PAIRS_CACHED=/path/to/radigest-screen-pairs-cached`.

The input-format target compares plain and gzip FASTA timing on the small public yeast reference. The screening-speed target benchmarks `radigest-screen-pairs-cached` candidate-pair screening using `config/screening_speed_cases.tsv`. The thread-scaling target benchmarks radigest on the moderate public cannabis Pink Pepper reference using `config/thread_scaling_cases.tsv`. The pair-screen job-scaling target benchmarks `radigest-screen-pairs-cached` across 1, 2, and 4 jobs using `config/pair_screen_scaling_cases.tsv`. The matched-tools target includes both the standalone large-reference wheat timing artifact and required large-reference matched-tool subset; SimRAD is excluded from the wheat subset because it cannot process the full wheat FASTA under R string-size limits.

Expected manuscript-facing performance tables are:

```text
results/manuscript/tables/table_06_input_format.tsv
results/manuscript/tables/table_05_screening_speed.tsv
results/manuscript/tables/table_s02_radigest_thread_scaling.tsv
results/manuscript/tables/table_s03_pair_screen_job_scaling.tsv
results/manuscript/tables/table_s04_large_genome.tsv
results/manuscript/tables/table_04_matched_timing.tsv
```

Generate ggplot2-based performance figures with:

```bash
make figures
```

The figures are written under `results/manuscript/figures/`; `figure_04_matched_tool_timing.pdf` is also built by `make performance-matched-tools`.

Stage 5e/5f large-reference timing is part of the required reference and matched-tools path; the wheat matched-tool subset excludes SimRAD:

```bash
make references THREADS=8
make performance-matched-tools THREADS=8 RADIGEST=/path/to/radigest
```

## Full nonempirical reviewer run

```bash
make reviewer-nonempirical THREADS=8
```

This target runs `make install-all`, `make check`, the nonempirical reviewer workflow, and the manuscript performance figures.

## Build radigest locally

```bash
make install-radigest
make show-radigest
```

This writes:

```text
.local/bin/radigest
.local/bin/radigest-screen-pairs-cached
.local/bin/radigest-design
.local/radigest/build_info.tsv
```

The local build uses upstream `make build-dev` so the cached screening helper is available for performance targets.

Use a pinned release or commit with:

```bash
make install-radigest RADIGEST_REF=<tag-or-commit>
```

When using a manual upstream radigest for screening benchmarks, make sure it was installed with the development/helper target, for example `make install-dev`, or pass `RADIGEST_SCREEN_PAIRS_CACHED=/path/to/radigest-screen-pairs-cached`.

## Empirical scaffold

The publication empirical branch is declared in `config/empirical_libraries.tsv`; depth-validation cases are declared in `config/empirical_depth_validation_cases.tsv`.
The default row points to the public Sockeye `GCF_034236695.1_Oner_Uvic_2.0`
reference and the local BAM drop-off directory
`data/empirical/sockeye_ecori_msei/bam/`.

```bash
make empirical-check
make empirical-references THREADS=8
make empirical-tlens THREADS=8
make empirical-predictions THREADS=8
make empirical-depth-validation THREADS=8
# or run the current full empirical workflow:
make empirical THREADS=8
```

`sockeye_ecori_msei` is enabled in the default publication manifest. `make check` is static and does not require BAMs, but `make reviewer-all` and `make empirical-check` require BAM/BAI files under `data/empirical/sockeye_ecori_msei/bam/`. Enabled rows produce BAM inventories plus TLEN files, histograms, QC summaries, raw/hard radigest predictions, and depth-validation summaries.
