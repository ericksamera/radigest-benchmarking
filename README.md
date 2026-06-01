# radigest benchmark v2 scaffold

This branch is a clean rebuild of the radigest benchmark and manuscript-support repository.

The repository is organized around reviewer execution, manuscript claims, scenario manifests, and artifact contracts. Porting proceeds in staged commits:

```text
scaffold -> validators -> synthetic validation -> references -> comparators -> performance -> empirical -> manuscript/audit
```

## Current stage

Stage 2 ports synthetic validation. The smoke target now runs radigest against tracked synthetic FASTA records and writes both the validation summary and the manuscript-facing table.

```bash
make check
make smoke RADIGEST=/path/to/radigest
```

Expected smoke outputs:

```text
results/validation/synthetic_validation_results.tsv
results/manuscript/tables/table_02_synthetic_validation.tsv
```

`make check` validates manifest shape and asks Snakemake to dry-run the smoke target. It does not execute radigest.

## Reviewer entry points

These targets remain dispatch shims while later stages are ported.

```bash
make smoke RADIGEST=/path/to/radigest
make reviewer-nonempirical THREADS=4 RADIGEST=/path/to/radigest
make reviewer-empirical THREADS=4
make reviewer-all THREADS=4 RADIGEST=/path/to/radigest
make audit
```

## Contracts

Primary contracts live in:

- `config/scenarios/*.yml` for runnable reviewer scenarios.
- `config/comparators.tsv` for comparator semantics and required external paths.
- `config/artifacts.tsv` for manuscript claim outputs and release requirements.
- `config/synthetic_expected.tsv` for synthetic validation cases.
