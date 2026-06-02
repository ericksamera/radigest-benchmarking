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
results/manuscript/tables/table_02_synthetic_validation.tsv
```

After `make install-radigest`, the explicit `RADIGEST=` assignment can be omitted. Manual `RADIGEST=/path/to/radigest` overrides still work.

## References

```bash
make references THREADS=4
```

This downloads the public references declared in `config/references.tsv`, writes gzipped and plain FASTA files under `data/reference/`, and records checksums in `results/references/reference_checksums.tsv`.

## Comparators

Install or update external comparator checkouts first:

```bash
make install-digital-rads
make install-ddradseqtools
make install-ddgrader
```

Then run:

```bash
make comparators THREADS=4 RADIGEST=/path/to/radigest
```

The comparator target writes exact normalized interval comparison summaries for Digital_RADs.py and DDRADSEQTOOLS `rsitesearch.py`, a SimRAD count-level sanity comparison, a ddgRADer binned-screening comparison, and two manuscript-facing tables:

```text
results/manuscript/tables/table_03_interval_comparisons.tsv
results/manuscript/tables/table_03_comparator_semantics.tsv
```

## Performance

```bash
make performance-input-format THREADS=4 RADIGEST=/path/to/radigest
make performance-screening-speed THREADS=4 RADIGEST=/path/to/radigest
make performance-thread-scaling THREADS=4 RADIGEST=/path/to/radigest
make performance-pair-screen-scaling THREADS=4 RADIGEST=/path/to/radigest
make references-large THREADS=4
make performance-large-genome THREADS=4 RADIGEST=/path/to/radigest
# Optional when the cached binary is not next to RADIGEST or on PATH:
make performance-screening-speed THREADS=4 \
  RADIGEST=/path/to/radigest \
  RADIGEST_SCREEN_PAIRS_CACHED=/path/to/radigest-screen-pairs-cached
```

The input-format target compares plain and gzip FASTA timing on the small public yeast reference. The screening-speed target benchmarks `radigest-screen-pairs-cached` candidate-pair screening using `config/screening_speed_cases.tsv`. The thread-scaling target benchmarks radigest on the moderate public cannabis Pink Pepper reference using `config/thread_scaling_cases.tsv`. The pair-screen job-scaling target benchmarks `radigest-screen-pairs-cached` across 1, 2, and 4 jobs using `config/pair_screen_scaling_cases.tsv`.

Expected manuscript-facing tables are:

```text
results/manuscript/tables/table_06_input_format.tsv
results/manuscript/tables/table_05_screening_speed.tsv
results/manuscript/tables/table_s02_radigest_thread_scaling.tsv
results/manuscript/tables/table_s03_pair_screen_job_scaling.tsv
```

Generate ggplot2-based starter performance figures with:

```bash
make figures
```

The figures are written under `results/manuscript/figures/`.

Stage 5e large-reference timing can be run with:

```bash
make references-large THREADS=4
make performance-large-genome THREADS=4 RADIGEST=/path/to/radigest
make performance-matched-tools THREADS=4 RADIGEST=/path/to/radigest
```

## Build radigest locally

```bash
make install-radigest
make show-radigest
```

This writes:

```text
.local/bin/radigest
.local/bin/radigest-screen-pairs-cached
.local/radigest/build_info.tsv
```

Use a pinned release or commit with:

```bash
make install-radigest RADIGEST_REF=<tag-or-commit>
```
