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

The raw per-case files and benchmark logs are generated artifacts and are not tracked.
