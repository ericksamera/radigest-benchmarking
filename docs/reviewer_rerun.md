# Reviewer rerun

The intended nonempirical reviewer path is:

```bash
mamba env create -f workflow/envs/driver.yml
mamba activate radigest-benchmark-driver
make install-digital-rads
make install-ddradseqtools
make install-ddgrader
make reviewer-nonempirical THREADS=4 RADIGEST=/path/to/radigest
make audit
```

At Stage 5c, the concrete executable pieces are:

```bash
make smoke RADIGEST=/path/to/radigest
make references THREADS=4
make comparator-smoke THREADS=4 RADIGEST=/path/to/radigest
make comparator-small-yeast THREADS=4 RADIGEST=/path/to/radigest
make comparators THREADS=4 RADIGEST=/path/to/radigest
make performance-input-format THREADS=4 RADIGEST=/path/to/radigest
make performance-screening-speed THREADS=4 RADIGEST=/path/to/radigest
make performance-thread-scaling THREADS=4 RADIGEST=/path/to/radigest
# Optional when the cached binary is not next to RADIGEST or on PATH:
make performance-screening-speed THREADS=4 \
  RADIGEST=/path/to/radigest \
  RADIGEST_SCREEN_PAIRS_CACHED=/path/to/radigest-screen-pairs-cached
```

`comparator-smoke` exercises Digital_RADs.py, DDRADSEQTOOLS, SimRAD, and ddgRADer on the same tracked synthetic FASTA and condition `D1`. `comparator-small-yeast` exercises the same tools on the small public yeast reference and condition `B1`.

The assertion is still tool-specific:

```text
Digital_RADs.py    coordinate-equivalence evidence through normalized intervals
DDRADSEQTOOLS      coordinate-equivalence evidence through normalized intervals
SimRAD             retained-fragment count agreement only
ddgRADer backend   binned fragment-count distribution agreement only
```

Stage 5a adds the radigest input-format performance workflow. Stage 5b adds cached `radigest-screen-pairs-cached` screening-speed timing using `config/screening_speed_cases.tsv`. Stage 5c adds intra-tool radigest thread scaling using `config/thread_scaling_cases.tsv`. Later stages will add pair-screen scaling, empirical recovery, and full audit products.
