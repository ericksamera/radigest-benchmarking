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

## Exact interval comparators

Install or update the external comparator checkouts first:

```bash
bash scripts/comparators/install_digital_rads.sh
bash scripts/comparators/install_ddradseqtools.sh
```

Then run:

```bash
make comparators THREADS=4 RADIGEST=/path/to/radigest
```

The comparator target writes exact normalized interval comparison summaries for Digital_RADs.py and DDRADSEQTOOLS `rsitesearch.py`, plus the manuscript-facing interval-comparison table.
