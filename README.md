# radigest benchmark v2 scaffold

This branch is a clean rebuild of the radigest benchmark and manuscript-support repository.

The repository is organized around reviewer execution, manuscript claims, scenario manifests, and artifact contracts. Porting proceeds in staged commits:

```text
scaffold -> validators -> synthetic validation -> references -> comparators -> performance -> empirical -> manuscript/audit
```

## Current stage

Stage 4 now includes comparator workflows with explicit claim boundaries. Digital_RADs.py and DDRADSEQTOOLS `rsitesearch.py` are normalized to interval sets and support coordinate-equivalence checks. Stage 4b adds non-coordinate comparator checks: SimRAD is count-level only, and ddgRADer is binned-screening only. Stage 4c adds shared synthetic comparator smoke and a small-yeast radigest-anchor comparator matrix.

```bash
make check
make smoke RADIGEST=/path/to/radigest
make references THREADS=4
make install-digital-rads
make install-ddradseqtools
make install-ddgrader
make comparator-smoke THREADS=4 RADIGEST=/path/to/radigest
make comparator-small-yeast THREADS=4 RADIGEST=/path/to/radigest
make comparators THREADS=4 RADIGEST=/path/to/radigest
```

SimRAD is installed into the Snakemake conda environment through `workflow/envs/simrad.post-deploy.sh`. `make install-simrad` is available for a manual active R environment.

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
results/comparators/ddradseqtools/ddradseqtools_smoke_single__D1.interval_compare.summary.tsv
results/comparators/digital_rads/digital_rads_small_yeast_s288c_B1.summary.tsv
results/comparators/ddradseqtools/small_yeast_s288c_B1.interval_compare.summary.tsv
results/comparators/simrad/simrad_count_comparison.tsv
results/comparators/simrad/simrad_small_yeast_s288c_B1.tsv
results/comparators/ddgrader/ddgrader_binned_smoke_summary.tsv
results/comparators/ddgrader/ddgrader_binned_screening_summary.tsv
results/comparators/comparator_case_matrix.tsv
results/comparators/cut_equivalence_summary.tsv
results/manuscript/tables/table_03_interval_comparisons.tsv
results/manuscript/tables/table_03_comparator_semantics.tsv
```

`make check` validates manifest shape and asks Snakemake to dry-run the smoke target. It does not execute radigest, download references, or require external comparator repositories.

## Comparator matrix boundaries

All comparator tools can be exercised on the same smoke FASTA and on small yeast, but they are not all tested with the same assertion:

```text
tool              smoke/yeast assertion
Digital_RADs.py    normalized interval equivalence
DDRADSEQTOOLS      normalized interval equivalence
SimRAD             aggregate retained-fragment count agreement only
ddgRADer backend   binned fragment-count distribution agreement only
```

The shared comparator smoke FASTA is:

```text
data/synthetic/comparator_ecori_msei_smoke.fa
```

## Reviewer entry points

These targets remain dispatch shims while later stages are ported.

```bash
make smoke RADIGEST=/path/to/radigest
make comparator-smoke THREADS=4 RADIGEST=/path/to/radigest
make comparator-small-yeast THREADS=4 RADIGEST=/path/to/radigest
make reviewer-nonempirical THREADS=4 RADIGEST=/path/to/radigest
make reviewer-empirical THREADS=4
make reviewer-all THREADS=4 RADIGEST=/path/to/radigest
make audit
```

## Contracts

Primary contracts live in:

- `config/scenarios/*.yml` for runnable reviewer scenarios.
- `config/comparators.tsv` for comparator semantics and required external paths.
- `config/comparator_cases.tsv` for normalized interval-equivalence comparator cases.
- `config/noncoordinate_comparator_cases.tsv` for count-only and binned-screening comparator cases.
- `config/artifacts.tsv` for manuscript claim outputs and release requirements.
- `config/synthetic_expected.tsv` for synthetic validation cases.
- `data/synthetic/comparator_ecori_msei_smoke.fa` for shared comparator smoke.
- `config/references.tsv` for public reference accessions and derived FASTA outputs.
