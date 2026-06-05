# radigest benchmark v2 scaffold

This branch is a clean rebuild of the radigest benchmark and manuscript-support repository.

The repository is organized around reviewer execution, manuscript claims, scenario manifests, and artifact contracts. Porting proceeds in staged commits:

```text
scaffold -> validators -> synthetic validation -> references -> comparators -> performance -> empirical -> manuscript/audit
```

## Current stage

Stage 7b adds artifact, claim, environment, output-index, and release-checklist audit tables on top of the implemented validation, comparator, and performance workflows. Stage 4 remains the comparator baseline: Digital_RADs.py and DDRADSEQTOOLS `rsitesearch.py` support normalized interval-equivalence checks, while SimRAD and ddgRADer remain lower-resolution comparator checks.

```bash
make check
make install-all
make smoke
make references THREADS=4
make install-comparators
make comparator-smoke THREADS=4 RADIGEST=/path/to/radigest
make comparator-small-yeast THREADS=4 RADIGEST=/path/to/radigest
make comparators THREADS=4
make performance-input-format THREADS=4
make performance-screening-speed THREADS=4
make performance-thread-scaling THREADS=4
make performance-pair-screen-scaling THREADS=4
make performance-matched-tools THREADS=4
# Optional when the cached binary is not next to RADIGEST or on PATH:
make performance-screening-speed THREADS=4 \
  RADIGEST=/path/to/radigest \
  RADIGEST_SCREEN_PAIRS_CACHED=/path/to/radigest-screen-pairs-cached
```

Comparator installers are run through Snakemake conda environments. `make install-comparators` installs or updates Digital_RADs.py, DDRADSEQTOOLS, SimRAD, and ddgRADer; `make install-all` also builds the local radigest binaries when the default `RADIGEST=.local/bin/radigest` is in use.

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
data/reference/large_wheat_chinese-spring.fa.gz
data/reference/large_wheat_chinese-spring.fa
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

Expected Stage 5 performance outputs:

```text
results/performance/input_format/radigest_input_format_comparison.tsv
results/manuscript/tables/table_06_input_format.tsv
benchmark/logs/performance/input_format/*.log
results/performance/input_format/raw/*.runs.tsv
results/performance/input_format/raw/*/*.fragments.tsv
results/performance/input_format/raw/*/*.json
results/performance/screening_speed/screening_speed_summary.tsv
results/manuscript/tables/table_05_screening_speed.tsv
benchmark/logs/performance/screening_speed/*.log
results/performance/screening_speed/raw/*.runs.tsv
results/performance/screening_speed/raw/*/json/*.json
results/performance/screening_speed/raw/*/logs/*.log
results/performance/thread_scaling/radigest_thread_scaling_summary.tsv
results/manuscript/tables/table_s02_radigest_thread_scaling.tsv
benchmark/logs/performance/thread_scaling/*.log
results/performance/thread_scaling/raw/*.runs.tsv
results/performance/thread_scaling/raw/*/*.json
results/performance/thread_scaling/raw/*/*.fragments.tsv
results/performance/pair_screen_scaling/pair_screen_scaling_summary.tsv
results/manuscript/tables/table_s03_pair_screen_job_scaling.tsv
benchmark/logs/performance/pair_screen_scaling/*.log
results/performance/pair_screen_scaling/raw/*.runs.tsv
results/performance/pair_screen_scaling/raw/*/json/*.json
results/performance/pair_screen_scaling/raw/*/logs/*.log
results/performance/large_genome/large_genome_summary.tsv
results/manuscript/tables/table_s04_large_genome.tsv
results/performance/matched_tools/tool_timing_interpretation.tsv
results/manuscript/tables/table_04_matched_timing.tsv
results/manuscript/figures/figure_04_matched_tool_timing.pdf
results/manuscript/figures/figure_05_screening_speed.pdf
results/manuscript/figures/figure_06_input_format.pdf
results/manuscript/figures/figure_s02_thread_scaling.pdf
results/manuscript/figures/figure_s03_pair_screen_job_scaling.pdf
results/manuscript/figures/figure_s04_large_genome.pdf
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

`make reviewer-nonempirical` now performs the complete nonempirical rerun path: comparator/radigest setup through `make install-all`, `make check`, the reviewer workflow, and performance figure generation.

```bash
make smoke RADIGEST=/path/to/radigest
make comparator-smoke THREADS=4 RADIGEST=/path/to/radigest
make comparator-small-yeast THREADS=4 RADIGEST=/path/to/radigest
make install-comparators
make install-all
make performance-input-format THREADS=4
make performance-screening-speed THREADS=4
make performance-thread-scaling THREADS=4
make performance-pair-screen-scaling THREADS=4
make performance-matched-tools THREADS=4
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
- `config/performance_cases.tsv` for Stage 5 input-format performance cases and run counts.
- `config/screening_speed_cases.tsv` for Stage 5b cached screening-speed cases using `radigest-screen-pairs-cached`.
- `config/thread_scaling_cases.tsv` for Stage 5c intra-tool radigest thread-scaling cases.
- `config/pair_screen_scaling_cases.tsv` for Stage 5d cached pair-screen job-scaling cases.
- `config/artifacts.tsv` for manuscript claim outputs and release requirements.
- `config/synthetic_expected.tsv` for synthetic validation cases.
- `data/synthetic/comparator_ecori_msei_smoke.fa` for shared comparator smoke.
- `config/references.tsv` for public reference accessions and derived FASTA outputs.

Stage 5e/5f large-reference timing is part of the required nonempirical path. `make references` now materializes the wheat reference, and `make performance-matched-tools` includes the large-reference matched-tool timing rows and figures:

```bash
make references THREADS=4
make performance-matched-tools THREADS=4 RADIGEST=/path/to/radigest
```

Expected audit outputs:

```text
results/manuscript/tables/artifact_status.tsv
results/manuscript/tables/claim_audit.tsv
results/manuscript/tables/environment.tsv
results/manuscript/tables/release_checklist.tsv
results/manuscript/tables/output_index.tsv
results/manuscript/tables/audit_passed.txt
```

`make audit` reads `config/artifacts.tsv` and fails when a release-required artifact is missing or empty.

## Building radigest locally

To avoid passing `RADIGEST=/path/to/radigest` to every command, build the local benchmark copy once:

```bash
make install-radigest
make show-radigest
```

This clones `https://github.com/ericksamera/radigest.git` into `external/radigest` and builds:

```text
.local/bin/radigest
.local/bin/radigest-screen-pairs-cached
.local/radigest/build_info.tsv
```

The Makefile then uses those binaries by default. Pin the source for a release with:

```bash
make install-radigest RADIGEST_REF=<tag-or-commit>
```

Manual overrides still work:

```bash
make smoke RADIGEST=/path/to/radigest
```
