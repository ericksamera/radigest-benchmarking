# Data requirements

Reference FASTA files are produced by the Stage 3 references workflow from `config/references.tsv`. The nonempirical reviewer run currently requires three public NCBI assemblies:

- `small_yeast_s288c` -> `data/reference/small_yeast_s288c.fa.gz` and `data/reference/small_yeast_s288c.fa`
- `moderate_cannabis_pink-pepper` -> `data/reference/moderate_cannabis_pink-pepper.fa.gz` and `data/reference/moderate_cannabis_pink-pepper.fa`
- `large_wheat_chinese-spring` -> `data/reference/large_wheat_chinese-spring.fa.gz` and `data/reference/large_wheat_chinese-spring.fa`

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

Install helpers live in `scripts/comparators/`. Version metadata is written into generated comparator outputs.

## Optional empirical inputs

Empirical BAM/CRAM/FASTQ/SRA inputs are declared in `config/empirical_libraries.tsv`; depth-validation cases are declared in `config/empirical_depth_validation_cases.tsv`.
The initial local-testing contract is BAM-directory first. The default row uses
the public Sockeye reference `GCF_034236695.1_Oner_Uvic_2.0`, downloaded through
`config/references.tsv`, and private BAM files or symlinks under
`data/empirical/sockeye_ecori_msei/bam/`.

Example local setup:

```bash
make empirical-references THREADS=4
ln -s /absolute/path/to/library_01.bam data/empirical/sockeye_ecori_msei/bam/library_01.bam
ln -s /absolute/path/to/library_01.bam.bai data/empirical/sockeye_ecori_msei/bam/library_01.bam.bai
# repeat for each BAM, then set enabled=true in config/empirical_libraries.tsv
make empirical-check
make empirical-tlens THREADS=4
make empirical-predictions THREADS=4
make empirical-depth-validation THREADS=4
make empirical THREADS=4
```

The `reference_path` entry must point to the exact reference build used for the
BAM alignment. If the manifest row is enabled, `make empirical-check` requires at
least one BAM matching `bam_glob`; downloaded public references are materialized
by `make empirical-references`/`make empirical`. `make empirical-tlens` then
extracts positive TLEN values from every BAM listed in the generated BAM
manifest using the row-level MAPQ, duplicate, and maximum-TLEN filters.
`make empirical-predictions` then runs radigest twice per enabled library: a
broad `raw` prediction using `score_min`/`score_max` and a strict `hard`
prediction using `min_size`/`max_size`. For the default Sockeye EcoRI-MseI row,
the nominal experimental guess is 200-400 bp with `soft-window` edge SD 50; the
broad prediction remains available for plotting the unselected fragment
distribution against empirical TLENs. `make empirical-depth-validation` uses
`config/empirical_depth_validation_cases.tsv` to run `radigest-design`, compute
per-sample BAM depth across the configured predicted loci, and write the
validation summary/manuscript table.

Stage 5b screening-speed runs use the public small yeast reference and the tracked candidate-enzyme list:

```text
data/reference/small_yeast_s288c.fa
config/candidate_enzymes.txt
```

Stage 5b uses the `radigest-screen-pairs-cached` binary. The Makefile derives `RADIGEST_SCREEN_PAIRS_CACHED` from `RADIGEST` when `RADIGEST` is a path, or uses `radigest-screen-pairs-cached` from `PATH`; override it explicitly when needed. Upstream radigest now installs cached screening through its development/helper surface, so manual installs used for these targets should use `make install-dev` or provide an explicit cached-screening binary path.

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

Stage 5e true large-reference timing uses the required wheat reference:

```text
large_wheat_chinese-spring -> data/reference/large_wheat_chinese-spring.fa.gz and data/reference/large_wheat_chinese-spring.fa
```

`make references` materializes this wheat FASTA along with the small and moderate public references. The large-reference timing artifact and the large matched-tool timing subset are included in `make performance-matched-tools THREADS=4 RADIGEST=/path/to/radigest`. SimRAD is intentionally excluded from the wheat subset because it cannot process the full wheat FASTA under R string-size limits.

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
.local/bin/radigest-design
```

For a release, pin `RADIGEST_REF` to a tag or commit and record `results/manuscript/tables/environment.tsv` from `make audit`.
