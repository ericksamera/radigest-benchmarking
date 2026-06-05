# Reviewer rerun

The intended nonempirical reviewer path is:

```bash
mamba env create -f workflow/envs/driver.yml
mamba activate radigest-benchmark-driver
make reviewer-nonempirical THREADS=4
make audit
```

Run `make install-all` separately only when you want to prefetch or refresh tool installations without running the reviewer workflow.

At Stage 5e/7b, `make reviewer-nonempirical` wraps setup, checks, the nonempirical workflow, and figure generation. The concrete executable pieces remain available for debugging:

```bash
make smoke RADIGEST=/path/to/radigest
make references THREADS=4
make install-comparators
make comparator-smoke THREADS=4 RADIGEST=/path/to/radigest
make comparator-small-yeast THREADS=4 RADIGEST=/path/to/radigest
make comparators THREADS=4 RADIGEST=/path/to/radigest
make performance-input-format THREADS=4 RADIGEST=/path/to/radigest
make performance-screening-speed THREADS=4 RADIGEST=/path/to/radigest
make performance-thread-scaling THREADS=4 RADIGEST=/path/to/radigest
make performance-pair-screen-scaling THREADS=4 RADIGEST=/path/to/radigest
make performance-matched-tools THREADS=4 RADIGEST=/path/to/radigest
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

Stage 5a adds the radigest input-format performance workflow. Stage 5b adds cached `radigest-screen-pairs-cached` screening-speed timing using `config/screening_speed_cases.tsv`. Stage 5c adds intra-tool radigest thread scaling using `config/thread_scaling_cases.tsv`. Stage 5d adds cached pair-screen job scaling using `config/pair_screen_scaling_cases.tsv`. Stage 5e/5f large-reference timing is included in the required reference and matched-tools path, including the large wheat matched-tool timing group. Stage 7a adds artifact, claim, and environment audit products from `config/artifacts.tsv`. Stage 7b adds the release checklist and output index. Later stages will add empirical recovery.

Stage 5e/5f large-reference timing is included in the required reference and matched-tools path:

```bash
make references THREADS=4
make performance-matched-tools THREADS=4 RADIGEST=/path/to/radigest
```

## Audit

After nonempirical workflows finish, run:

```bash
make audit
```

Audit outputs are:

```text
results/manuscript/tables/artifact_status.tsv
results/manuscript/tables/claim_audit.tsv
results/manuscript/tables/environment.tsv
results/manuscript/tables/release_checklist.tsv
results/manuscript/tables/output_index.tsv
results/manuscript/tables/audit_passed.txt
```

`make audit` fails if any `required_for_release=true` artifact is missing or zero bytes. Optional empirical artifacts remain nonblocking while `required_for_release=false`.

## Stage 7b release checklist

`make audit` now also writes:

```text
results/manuscript/tables/output_index.tsv
results/manuscript/tables/release_checklist.tsv
```

The release gate fails if a required claim fails or if any blocking checklist item fails.

After `make audit`, inspect the release-checklist and output-index tables:

```bash
column -t -s $'\t' results/manuscript/tables/release_checklist.tsv | less -S
column -t -s $'\t' results/manuscript/tables/output_index.tsv | less -S
```

## Local radigest build

Run once before reviewer commands:

```bash
make install-radigest
make show-radigest
```

After this, `RADIGEST` and `RADIGEST_SCREEN_PAIRS_CACHED` default to `.local/bin/` paths.
