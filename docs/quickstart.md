# Quickstart

This document tracks the reviewer-oriented entry points for the clean v2 repository.

Stage 2 supports manifest validation, Snakemake dry-run checking, and synthetic validation:

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
