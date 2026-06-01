# Benchmark categories

Benchmark execution is organized by claim category rather than by individual
script. The category manifest is `config/benchmark_categories.tsv`.

This layer is intentionally lightweight. It does not replace the Snakemake
workflows or the existing output contracts. It records which Make targets and
workflow entrypoints support each manuscript claim family.

## Why this exists

The repository has several valid but different benchmark types:

- synthetic digest validation;
- exact or count-level digest comparators;
- screening throughput;
- input-format controls;
- radigest-only scaling;
- empirical recovery modelling;
- manuscript table and figure exports.

Those categories have different required inputs, runtime cost, and claim scope.
Keeping them explicit prevents a reviewer-facing rerun from becoming a loose
collection of unrelated Makefile recipes.

## Inspect categories

```bash
make benchmark-categories
```

Static validation of the manifest:

```bash
make check-benchmark-categories
```

This writes:

```text
results/processed/benchmark_category_qc.tsv
```

Missing large reference data or empirical BAM directories are reported as
warnings by the static check, because those inputs are intentionally excluded
from Git.

## Claim-oriented entrypoints

| Category                       | Main target                   | Scope                                                            |
| ------------------------------ | ----------------------------- | ---------------------------------------------------------------- |
| Validation                     | `make benchmark-validation`   | Synthetic digest correctness and interval smoke checks           |
| Comparators                    | `make benchmark-comparators`  | Matched external-tool comparisons and timing interpretation      |
| Performance                    | `make benchmark-performance`  | Input-format controls and scaling benchmarks                     |
| Empirical recovery             | `make benchmark-empirical`    | BAM/TLEN-derived recovery modelling                              |
| Non-empirical manuscript rerun | `make benchmark-nonempirical` | Validation, comparators, performance, figures, tables, and audit |

`benchmark-nonempirical` assumes references and external comparator checkouts
already exist. Use `reviewer-prepare` or `reviewer-rerun-nonempirical` for a
clean reviewer-facing run that also builds radigest and prepares dependencies.

## Do not infer claim scope from output location

The repository still uses the existing output directories:

```text
results/raw/
results/processed/
results/tables/
results/figures/
benchmark/memory/
benchmark/logs/
manuscript_tables/
manuscript_figures/
```

The category manifest is the claim-scope layer. The output directories remain
processing-stage locations for now.

A future restructuring can move to claim-oriented directories such as
`results/performance/`, `results/comparators/`, and `results/empirical/`, but
that should happen only after all execution entrypoints are manifest-driven.

## Relationship to artifact contracts

Benchmark categories describe broad workflow groups. `config/artifacts.tsv` is the stricter manuscript-facing contract layer: it maps concrete upstream result files to claims and curated tables. Use `make check-artifacts` before manuscript export.
