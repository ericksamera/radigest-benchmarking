# Quickstart

This document tracks the reviewer-oriented entry points for the clean v2 repository.

## Smoke validation

```bash
make check
make smoke RADIGEST=/path/to/radigest
```

The smoke run writes:

```text
results/validation/synthetic_validation_results.tsv
results/manuscript/tables/table_02_synthetic_validation.tsv
```

If `radigest` is on `PATH`, the explicit `RADIGEST=` assignment can be omitted.

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
