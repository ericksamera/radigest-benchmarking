# radigest benchmark v2 scaffold

This branch is a clean rebuild of the radigest benchmark and manuscript-support repository.

The repository is organized around reviewer execution, manuscript claims, scenario manifests, and artifact contracts. Porting proceeds in staged commits:

```text
scaffold -> validators -> synthetic validation -> references -> comparators -> performance -> empirical -> manuscript/audit
```

## Current stage

Stage 4 adds exact interval-equivalence comparator workflows. The smoke target still exercises synthetic validation, `make references` downloads the public references, and `make comparators` runs Digital_RADs.py and DDRADSEQTOOLS `rsitesearch.py` interval comparisons.

```bash
make check
make smoke RADIGEST=/path/to/radigest
make references THREADS=4
bash scripts/comparators/install_digital_rads.sh
bash scripts/comparators/install_ddradseqtools.sh
make comparators THREADS=4 RADIGEST=/path/to/radigest
```

Expected smoke outputs:

```text
results/validation/synthetic_validation_results.tsv
results/manuscript/tables/table_02_synthetic_validation.tsv
```

Expected reference outputs:

```text
data/reference/small_yeast_s288c.fa.gz
data/reference/small_yeast_s288c.fa
data/reference/moderate_cannabis_pink-pepper.fa.gz
data/reference/moderate_cannabis_pink-pepper.fa
results/references/reference_checksums.tsv
```

Expected comparator outputs:

```text
results/comparators/digital_rads/digital_rads_smoke_single__D1.summary.tsv
results/comparators/ddradseqtools/small_yeast_s288c_B1.interval_compare.summary.tsv
results/comparators/cut_equivalence_summary.tsv
results/manuscript/tables/table_03_interval_comparisons.tsv
```

`make check` validates manifest shape and asks Snakemake to dry-run the smoke target. It does not execute radigest, download references, or require external comparator repositories.

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
- `config/comparator_cases.tsv` for runnable comparator cases.
- `config/artifacts.tsv` for manuscript claim outputs and release requirements.
- `config/synthetic_expected.tsv` for synthetic validation cases.
- `config/references.tsv` for public reference accessions and derived FASTA outputs.
