# Scenarios

Scenario files live under `config/scenarios/`.

- `smoke.yml` is for minimal scaffold and synthetic validation checks. It also declares the separate comparator-smoke tier, but `make smoke` remains radigest-only so it does not require external comparator checkouts.
- `reviewer_nonempirical.yml` is for public-reference reviewer reruns. It now declares both comparator matrices: tracked synthetic smoke and small public yeast.
- `reviewer_empirical.yml` is for empirical recovery when inputs are available; it points to `config/empirical_libraries.tsv` for the local input contract.
- `reviewer_all.yml` combines nonempirical and empirical contracts.

Useful comparator-specific execution targets are:

```bash
make install-comparators
make comparator-smoke RADIGEST=/path/to/radigest
make references THREADS=4
make comparator-small-yeast THREADS=4 RADIGEST=/path/to/radigest
make comparators THREADS=4 RADIGEST=/path/to/radigest
make empirical-check
make empirical-references THREADS=4
make empirical THREADS=4 RADIGEST=/path/to/radigest
```

`comparator-smoke` exercises Digital_RADs.py, DDRADSEQTOOLS, SimRAD, and ddgRADer on the same tracked synthetic FASTA and condition `D1`. `comparator-small-yeast` exercises the same tools on `small_yeast_s288c_plain` and condition `B1`.

Stage 5a/5b/5c/5d/5e add performance tiers:

```bash
make references THREADS=4
make performance-input-format THREADS=4 RADIGEST=/path/to/radigest
make performance-screening-speed THREADS=4 RADIGEST=/path/to/radigest
make performance-thread-scaling THREADS=4 RADIGEST=/path/to/radigest
make performance-pair-screen-scaling THREADS=4 RADIGEST=/path/to/radigest
make performance-matched-tools THREADS=4 RADIGEST=/path/to/radigest
# Optional when the cached binary is not next to RADIGEST or on PATH:
make performance-screening-speed THREADS=4 \
  RADIGEST=/path/to/radigest \
  RADIGEST_SCREEN_PAIRS_CACHED=/path/to/radigest-screen-pairs-cached
make performance THREADS=4 RADIGEST=/path/to/radigest
```

The input-format tier compares plain and gzip FASTA inputs for `small_yeast_s288c_B1` using `config/performance_cases.tsv`. The screening-speed tier measures cached `radigest-screen-pairs-cached` candidate-pair screening on `small_yeast_s288c_plain` using `config/screening_speed_cases.tsv`. The thread-scaling tier measures radigest JSON-summary and fragment-TSV output modes on `moderate_cannabis_pink-pepper_plain` using `config/thread_scaling_cases.tsv`. The pair-screen job-scaling tier measures cached screening across 1, 2, and 4 jobs on `moderate_cannabis_pink-pepper_plain` using `config/pair_screen_scaling_cases.tsv`. The matched-tools tier includes the standalone large-reference wheat timing artifact and the required large wheat matched-tool subset; SimRAD is excluded from the wheat subset because it cannot process the full wheat FASTA under R string-size limits. `make reviewer-nonempirical` runs `make install-all`, `make check`, the nonempirical workflow, and figure generation in one entry point.

Stage 5e/5f large-reference timing is included in the required reference and matched-tools path:

```bash
make references THREADS=4
make performance-matched-tools THREADS=4 RADIGEST=/path/to/radigest
```

## Empirical scenario scaffold

The empirical scenario is optional until public inputs are available. Local testing
is driven by `config/empirical_libraries.tsv`; disabled rows are metadata only,
while enabled `local_bam_dir` rows process every BAM matching `bam_glob` under
the configured drop-off directory. Current empirical targets validate and expose
the manifest/reference/BAM-inventory contract; TLEN extraction and model-fitting
rules are added in the next empirical workflow stage.

```bash
make empirical-check
make empirical-references THREADS=4
make empirical THREADS=4 RADIGEST=/path/to/radigest
make reviewer-empirical THREADS=4 RADIGEST=/path/to/radigest
```
