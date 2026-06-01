# Scenarios

Scenario files live under `config/scenarios/`.

- `smoke.yml` is for minimal scaffold and synthetic validation checks. It also declares the separate comparator-smoke tier, but `make smoke` remains radigest-only so it does not require external comparator checkouts.
- `reviewer_nonempirical.yml` is for public-reference reviewer reruns. It now declares both comparator matrices: tracked synthetic smoke and small public yeast.
- `reviewer_empirical.yml` is for empirical recovery when inputs are available.
- `reviewer_all.yml` combines nonempirical and empirical contracts.

Useful comparator-specific execution targets are:

```bash
make comparator-smoke RADIGEST=/path/to/radigest
make references THREADS=4
make comparator-small-yeast THREADS=4 RADIGEST=/path/to/radigest
make comparators THREADS=4 RADIGEST=/path/to/radigest
```

`comparator-smoke` exercises Digital_RADs.py, DDRADSEQTOOLS, SimRAD, and ddgRADer on the same tracked synthetic FASTA and condition `D1`. `comparator-small-yeast` exercises the same tools on `small_yeast_s288c_plain` and condition `B1`.

Stage 5a/5b add performance tiers:

```bash
make references THREADS=4
make performance-input-format THREADS=4 RADIGEST=/path/to/radigest
make performance-screening-speed THREADS=4 RADIGEST=/path/to/radigest
# Optional when the cached binary is not next to RADIGEST or on PATH:
make performance-screening-speed THREADS=4 \
  RADIGEST=/path/to/radigest \
  RADIGEST_SCREEN_PAIRS_CACHED=/path/to/radigest-screen-pairs-cached
make performance THREADS=4 RADIGEST=/path/to/radigest
```

The input-format tier compares plain and gzip FASTA inputs for `small_yeast_s288c_B1` using `config/performance_cases.tsv`. The screening-speed tier measures cached `radigest-screen-pairs-cached` candidate-pair screening on `small_yeast_s288c_plain` using `config/screening_speed_cases.tsv`. Later Stage 5 patches should add thread scaling, pair-screen scaling, and large-genome cases.
