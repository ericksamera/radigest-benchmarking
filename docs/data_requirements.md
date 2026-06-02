# Data requirements

Reference FASTA files are produced by the Stage 3 references workflow from `config/references.tsv`. The nonempirical reviewer run currently requires two public NCBI assemblies:

- `small_yeast_s288c` -> `data/reference/small_yeast_s288c.fa.gz` and `data/reference/small_yeast_s288c.fa`
- `moderate_cannabis_pink-pepper` -> `data/reference/moderate_cannabis_pink-pepper.fa.gz` and `data/reference/moderate_cannabis_pink-pepper.fa`

Reference IDs use underscores to delimit benchmark scale, organism or commodity, and source label. Hyphens preserve multi-word source labels, as in `moderate_cannabis_pink-pepper`. The workflow records SHA256 checksums and basic FASTA statistics in `results/references/reference_checksums.tsv`.

Stage 4 comparator runs also require a tracked synthetic FASTA for the shared comparator smoke matrix:

```text
data/synthetic/comparator_ecori_msei_smoke.fa
```

External comparator checkouts are ignored and are installed under `external/`:

```text
external/Digital_RADs/Digital_RADs.py
external/ddRADseqTools/Package/rsitesearch.py
external/ddRADseqTools/Package/restrictionsites.txt
external/ddRadSeqWebTool/backend/service/DigestSequence.py
```

Install helpers live in `scripts/comparators/`. Version metadata is written into generated comparator outputs. Empirical BAM/CRAM inputs remain optional until their public input contract is finalized.

Stage 5b screening-speed runs use the public small yeast reference and the tracked candidate-enzyme list:

```text
data/reference/small_yeast_s288c.fa
config/candidate_enzymes.txt
```

Stage 5b uses the `radigest-screen-pairs-cached` binary. The Makefile derives `RADIGEST_SCREEN_PAIRS_CACHED` from `RADIGEST` when `RADIGEST` is a path, or uses `radigest-screen-pairs-cached` from `PATH`; override it explicitly when needed.

Stage 5c thread-scaling runs use the moderate public cannabis Pink Pepper reference:

```text
data/reference/moderate_cannabis_pink-pepper.fa
```

The default reviewer thread-scaling tier uses 1, 2, and 4 radigest threads. Run it with `make performance-thread-scaling THREADS=4 RADIGEST=/path/to/radigest` to avoid Snakemake thread downscaling.

Stage 5d pair-screen job-scaling runs also use the moderate public cannabis Pink Pepper reference and the tracked candidate-enzyme list:

```text
data/reference/moderate_cannabis_pink-pepper.fa
config/candidate_enzymes.txt
```

The default reviewer pair-screen job-scaling tier uses 1, 2, and 4 `radigest-screen-pairs-cached` jobs with one radigest thread per pair. Run it with `make performance-pair-screen-scaling THREADS=4 RADIGEST=/path/to/radigest` to avoid Snakemake job downscaling.

Stage 5e true large-reference timing uses an optional wheat reference:

```text
large_wheat_chinese-spring -> data/reference/large_wheat_chinese-spring.fa.gz and data/reference/large_wheat_chinese-spring.fa
```

This reference is not downloaded by `make references` because it is large. Use `make references-large THREADS=4` or run `make performance-large-genome THREADS=4 RADIGEST=/path/to/radigest`, which will materialize the wheat FASTA through Snakemake before timing.

## Radigest source and local binaries

The benchmark can clone and build radigest locally:

```bash
make install-radigest
```

Defaults:

```text
RADIGEST_REPO=https://github.com/ericksamera/radigest.git
RADIGEST_REF=main
RADIGEST_SRC=external/radigest
LOCAL_BIN=.local/bin
```

Generated local binaries are ignored by Git:

```text
.local/bin/radigest
.local/bin/radigest-screen-pairs-cached
```

For a release, pin `RADIGEST_REF` to a tag or commit and record `results/manuscript/tables/environment.tsv` from `make audit`.
