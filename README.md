# radigest benchmark v2 scaffold

This branch is a clean rebuild of the radigest benchmark and manuscript-support repository.

The repository is organized around reviewer execution, manuscript claims, scenario manifests, and artifact contracts. Porting proceeds in staged commits:

```text
scaffold -> validators -> synthetic validation -> references -> comparators -> performance -> empirical -> manuscript/audit
```

## Current stage

Stage 3 adds public reference acquisition. The smoke target still exercises synthetic validation, while `make references` now downloads and prepares the public yeast and moderate-reference FASTA files declared in `config/references.tsv`.

```bash
make check
make smoke RADIGEST=/path/to/radigest
make references THREADS=4
```

Expected smoke outputs:

```text
results/validation/synthetic_validation_results.tsv
results/manuscript/tables/table_02_synthetic_validation.tsv
```

Expected reference outputs:

```text
data/reference/yeast.fa.gz
data/reference/yeast.fa
data/reference/moderate.fa.gz
data/reference/moderate.fa
results/references/reference_checksums.tsv
```

`make check` validates manifest shape and asks Snakemake to dry-run the smoke target. It does not execute radigest or download references.

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
- `config/references.tsv` for public reference accessions and derived FASTA outputs.
