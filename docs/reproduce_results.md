# Reproducing the radigest benchmarking analyses

This repository is organized into lightweight default checks and optional heavy
workflows. Large reference genomes, BAM/CRAM files, FASTQ files, and external
tool checkouts are not stored in Git.

## 1. Build or locate radigest

Use an installed radigest:

```bash
RADIGEST=~/radigest/bin/radigest
RADIGEST_SCREEN_PAIRS=~/radigest/bin/radigest-screen-pairs
RADIGEST_RANK_PAIRS=~/radigest/bin/radigest-rank-pairs
RADIGEST_FIT_SIZE_MODEL=~/radigest/bin/radigest-fit-size-model
```

Or build from a local source checkout:

```bash
make radigest-local RADIGEST_REPO=../radigest RADIGEST_REF=HEAD
```

This writes local executables under `.local/bin/` and records build metadata in
`results/processed/radigest_build.tsv`.

## 2. Lightweight validation

These commands should work from a clean clone after installing dependencies and
providing a radigest executable.

```bash
make check RADIGEST=.local/bin/radigest THREADS=1
make validate-radigest RADIGEST=.local/bin/radigest THREADS=1
```

The lightweight default workflow does not download large genomes and does not
run external comparator tools.

## 3. Matched digest-level comparator checks

Comparator workflows are optional because they require external tools.
Comparator semantics and allowed claims are declared in `config/comparators.tsv`.

```bash
make comparator-registry
make check-comparator-registry
make compare-cut-tools RADIGEST=.local/bin/radigest THREADS=1
```

Interpretation rules are registry-driven:

- Digital_RADs.py is compared after motif-boundary normalization.
- DDRADSEQTOOLS is compared only through `rsitesearch.py` and after coordinate
  and FASTA-defline normalization.
- SimRAD is count-level only.
- ddgRADer is binned screening/speed only.

## 4. Runtime and memory benchmarks

```bash
make benchmark-radigest RADIGEST=.local/bin/radigest THREADS=4
make summarize RADIGEST=.local/bin/radigest THREADS=4
make figures RADIGEST=.local/bin/radigest THREADS=4
```

Benchmark claims should use medians and Q1-Q3 intervals, not single runs.

## 5. Benchmark categories and scenarios

Claim-oriented benchmark categories are declared in `config/benchmark_categories.tsv`:

```bash
make benchmark-categories
make check-benchmark-categories
```

Benchmark parameter defaults are declared in `config/scenarios/nonempirical.tsv`:

```bash
make scenarios
make check-scenarios
```

Use `make benchmark-nonempirical` after references and external comparator
checkouts are already available. Use `make reviewer-rerun-nonempirical` for the
reviewer-facing path that also runs preparation steps.

Override scenario-derived defaults with normal Make assignments when needed:

```bash
make benchmark-screening-speed SCREENING_RUNS=3 SCREENING_JOBS=4
```

## 6. Non-empirical scaling benchmarks

Moderate-genome scaling benchmarks are Snakemake-managed through
`workflow/scaling.smk`. Run these only on the machine intended for final runtime
reporting.

```bash
make radigest-thread-scaling \
  RADIGEST=.local/bin/radigest \
  MODERATE_PLAIN_REF=data/reference/moderate.fa \
  SCALING_SNAKEMAKE_CORES=1

make pair-screen-scaling \
  RADIGEST=.local/bin/radigest \
  RADIGEST_SCREEN_PAIRS=.local/bin/radigest-screen-pairs \
  MODERATE_PLAIN_REF=data/reference/moderate.fa \
  SCALING_SNAKEMAKE_CORES=1
```

## 7. Empirical recovery workflow

Empirical recovery requires local BAM/CRAM files and reference FASTA files
described in `config/empirical_recovery.tsv`.

Dry run:

```bash
make empirical-recovery-dry-run \
  RADIGEST=.local/bin/radigest \
  RADIGEST_FIT_SIZE_MODEL=.local/bin/radigest-fit-size-model \
  THREADS=1
```

Run:

```bash
make empirical-recovery-local \
  RADIGEST_REPO=../radigest \
  RADIGEST_REF=HEAD \
  THREADS=4
```

Outputs include:

- `results/tables/sockeye_ddrad.empirical_recovery_summary.tsv`
- `results/tables/trichoderma_ddrad.empirical_recovery_summary.tsv`
- `results/tables/empirical_recovery_summary.tsv`
- `results/tables/empirical_recovery_model_sensitivity.tsv`

## 8. Manuscript tables

```bash
make manuscript-tables
```

Curated tables are written to `manuscript_tables/`. Raw and intermediate
outputs remain ignored by Git.

## 9. What not to run by default

Do not make the following part of default CI or `make all`:

- empirical BAM/CRAM recovery workflows;
- large reference genome downloads;
- ddgRADer screening-speed comparisons;
- full comparator installation;
- large Cannabis pair-screening runs.

These are optional manuscript analyses and should be reproduced explicitly.

## Environment model

This repository uses three environment layers:

1. `radigest-benchmark-driver`: a named driver environment for Make,
   Snakemake, Python helpers, linting, and audit scripts.
2. Snakemake-managed rule environments under `.snakemake/conda`.
3. `.local/bin/` executables built by the Snakemake rule
   `workflow/radigest_build.smk` from a local or remote radigest source
   checkout.

Do not set Snakemake's `--conda-prefix` to `$CONDA_PREFIX` or to any path
inside an active Conda environment. Rule environments should live under the
workflow cache directory, normally `.snakemake/conda`.

Recommended setup from a clean clone:

```bash
mamba env create -f envs/driver.yml
conda config --set channel_priority strict
mamba activate radigest-benchmark-driver

make build-radigest RADIGEST_REPO=../radigest RADIGEST_REF=HEAD
make check-local THREADS=1
```
