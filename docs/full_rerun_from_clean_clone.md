# Full rerun from a clean clone

This document describes how to rerun the radigest manuscript analyses on a new
machine. It assumes the Git repository is clean and that large reference and BAM
files are supplied locally, not committed to Git.

## 0. Clone and create the environment

```bash
git clone https://github.com/ericksamera/radigest-comparison-bmc.git
cd radigest-comparison-bmc

mamba env create -f envs/benchmark.yml
mamba activate radigest-benchmarking
```

Optional SimRAD environment:

```bash
mamba env create -f envs/simrad.yml
```

## 1. Provide large data files

Large files are excluded from Git. Place or symlink them at the paths used in
the config files.

Required for lightweight validation:

```text
none beyond tracked synthetic FASTA files
```

Required for yeast/comparator benchmarks:

```text
data/reference/yeast.fa.gz
data/reference/yeast.fa
external/Digital_RADs/Digital_RADs.py
external/ddRADseqTools/
external/ddRadSeqWebTool/
```

Required for moderate-genome scaling:

```text
data/reference/moderate.fa.gz
data/reference/moderate.fa
```

Required for empirical recovery:

```text
data/empirical/sockeye/reference.fa
data/empirical/sockeye/bam/*.bam
data/empirical/trichoderma/reference.fa
data/empirical/trichoderma/bam/*.bam
```

## 2. Build or locate radigest

Use an installed radigest:

```bash
RADIGEST=~/radigest/bin/radigest
RADIGEST_SCREEN_PAIRS=~/radigest/bin/radigest-screen-pairs
RADIGEST_RANK_PAIRS=~/radigest/bin/radigest-rank-pairs
RADIGEST_FIT_SIZE_MODEL=~/radigest/bin/radigest-fit-size-model
```

Or build from a source checkout:

```bash
make radigest-local RADIGEST_REPO=../radigest RADIGEST_REF=HEAD
RADIGEST=.local/bin/radigest
RADIGEST_SCREEN_PAIRS=.local/bin/radigest-screen-pairs
RADIGEST_RANK_PAIRS=.local/bin/radigest-rank-pairs
RADIGEST_FIT_SIZE_MODEL=.local/bin/radigest-fit-size-model
```

## 3. Lightweight checks

These should pass without large empirical data.

```bash
preflight

make check \
  RADIGEST="$RADIGEST" \
  RADIGEST_SCREEN_PAIRS="$RADIGEST_SCREEN_PAIRS" \
  RADIGEST_RANK_PAIRS="$RADIGEST_RANK_PAIRS" \
  THREADS=1

make validate-radigest \
  RADIGEST="$RADIGEST" \
  THREADS=1

make audit
make benchmark-categories
make check-benchmark-categories
```

## 4. Reference metadata

```bash
make env \
  RADIGEST="$RADIGEST" \
  THREADS=1

make download-reference-data \
  RADIGEST="$RADIGEST" \
  THREADS=1

make fasta-summary \
  RADIGEST="$RADIGEST" \
  THREADS=1
```

## 5. Matched digest comparator checks

Run only after external comparator tools and yeast FASTA are available.

```bash
make compare-cut-tools \
  RADIGEST="$RADIGEST" \
  THREADS=1
```

Expected key outputs include exact interval PASS rows for Digital_RADs.py and
DDRADSEQTOOLS rsitesearch.py after normalization.

## 6. Matched timing and screening benchmarks

Run only on the machine intended for final runtime reporting.

```bash
make benchmark-matched-tools \
  RADIGEST="$RADIGEST" \
  THREADS=1

make benchmark-simrad-warm \
  THREADS=1

make tool-timing-table
```

Optional screening-speed benchmarks:

```bash
bash scripts/benchmarks/run_screening_speed_benchmark.sh
python3 scripts/benchmarks/summarize_screening_speed.py
```

## 7. Moderate-genome radigest scaling

Run only after `data/reference/moderate.fa` exists. The scaling runs are
Snakemake-managed through `workflow/scaling.smk`; the Make target below keeps
the original output filenames and summary tables.

```bash
make radigest-thread-scaling \
  RADIGEST="$RADIGEST" \
  MODERATE_PLAIN_REF=data/reference/moderate.fa \
  THREAD_SCALING_RUNS=7 \
  SCALING_THREADS_LIST=1,2,4,8 \
  SCALING_SNAKEMAKE_CORES=1
```

## 8. Pair-screening job scaling

Run only on the final benchmark machine. This is also Snakemake-managed through
`workflow/scaling.smk`, with one rule instance per jobs × replicate combination.

```bash
make pair-screen-scaling \
  RADIGEST="$RADIGEST" \
  RADIGEST_SCREEN_PAIRS="$RADIGEST_SCREEN_PAIRS" \
  MODERATE_PLAIN_REF=data/reference/moderate.fa \
  PAIR_SCREEN_RUNS=3 \
  PAIR_SCREEN_JOBS="1 2 4 8" \
  SCALING_SNAKEMAKE_CORES=1
```

## 9. Empirical recovery

Run only after empirical BAMs and references are present.

```bash
make empirical-recovery \
  RADIGEST="$RADIGEST" \
  RADIGEST_FIT_SIZE_MODEL="$RADIGEST_FIT_SIZE_MODEL" \
  THREADS=4
```

Expected outputs:

```text
results/tables/sockeye_ddrad.empirical_recovery_summary.tsv
results/tables/trichoderma_ddrad.empirical_recovery_summary.tsv
results/tables/empirical_recovery_summary.tsv
results/tables/empirical_recovery_model_sensitivity.tsv
```

## 10. Manuscript tables and figures

```bash
make manuscript-tables

python3 scripts/manuscript/make_empirical_recovery_figures.py \
  --tlens results/processed/empirical_recovery/sockeye_ddrad/all.tlens.tsv \
  --hard-fragments results/processed/empirical_recovery/sockeye_ddrad/fragments.score_range.tsv \
  --weighted-fragments results/processed/empirical_recovery/sockeye_ddrad/fragments.empirical_weighted.tsv \
  --nominal-min 200 \
  --nominal-max 400 \
  --max-length 1000 \
  --bin-width 10 \
  --label "Sockeye ddRAD empirical recovery" \
  --prefix sockeye_empirical_recovery \
  --out-dir results/figures \
  --manuscript-dir manuscript_figures

python3 scripts/manuscript/make_empirical_recovery_figures.py \
  --tlens results/processed/empirical_recovery/trichoderma_ddrad/all.tlens.tsv \
  --hard-fragments results/processed/empirical_recovery/trichoderma_ddrad/fragments.score_range.tsv \
  --weighted-fragments results/processed/empirical_recovery/trichoderma_ddrad/fragments.empirical_weighted.tsv \
  --nominal-min 200 \
  --nominal-max 500 \
  --max-length 800 \
  --bin-width 10 \
  --label "Trichoderma ddRAD empirical recovery" \
  --prefix trichoderma_empirical_recovery \
  --out-dir results/figures \
  --manuscript-dir manuscript_figures
```

## 11. Final checks

```bash
preflight
make audit
git status --short
```

Track only source/config/docs and curated manuscript tables:

```bash
git add README.md Makefile .gitignore CITATION.cff
git add config/ docs/ workflow/ scripts/
git add -f manuscript_tables/*.tsv

git restore --staged \
  data/reference \
  data/empirical \
  external \
  results/raw \
  results/processed \
  results/tables \
  results/figures \
  benchmark \
  manuscript_figures \
  codebase.json \
  2>/dev/null || true
```
