SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

SNAKEMAKE ?= snakemake
SNAKEFILE ?= workflow/Snakefile
MATCHED_TOOLS_SNAKEFILE ?= workflow/matched_tools.smk
DDGRADER_BINNED_SNAKEFILE ?= workflow/ddgrader_binned.smk
SCREENING_SPEED_SNAKEFILE ?= workflow/screening_speed.smk
SCALING_SNAKEFILE ?= workflow/scaling.smk
WORKFLOW_CONFIG ?= workflow/config.yml
BENCHMARK_CATEGORIES ?= config/benchmark_categories.tsv
ARTIFACT_CONTRACTS ?= config/artifacts.tsv

RADIGEST ?= $(LOCAL_RADIGEST)
RADIGEST_SCREEN_PAIRS ?= $(LOCAL_RADIGEST_SCREEN_PAIRS)
RADIGEST_RANK_PAIRS ?= $(LOCAL_RADIGEST_RANK_PAIRS)

THREADS ?= 4


SNAKEMAKE_CONDA_PREFIX ?= .snakemake/conda
SNAKEMAKE_CONDA_ARGS ?= --use-conda --conda-prefix $(SNAKEMAKE_CONDA_PREFIX)
RADIGEST_BUILD_SNAKEFILE ?= workflow/radigest_build.smk
RADIGEST_BUILD_DIR ?= .local/radigest


REFERENCE_SNAKEFILE ?= workflow/reference_data.smk
REFERENCE_DATASETS ?= yeast_small,moderate_genome,sockeye_reference,trichoderma_reference


RADIGEST_REPO ?= ../radigest
RADIGEST_REF ?= HEAD
LOCAL_BIN ?= .local/bin
LOCAL_RADIGEST ?= $(LOCAL_BIN)/radigest
LOCAL_RADIGEST_SCREEN_PAIRS ?= $(LOCAL_BIN)/radigest-screen-pairs
LOCAL_RADIGEST_RANK_PAIRS ?= $(LOCAL_BIN)/radigest-rank-pairs
LOCAL_RADIGEST_FIT_SIZE_MODEL ?= $(LOCAL_BIN)/radigest-fit-size-model
EMPIRICAL_SNAKEFILE ?= workflow/empirical_recovery.smk
EMPIRICAL_DATASETS ?= sockeye_ddrad,trichoderma_ddrad
RADIGEST_FIT_SIZE_MODEL ?= radigest-fit-size-model


EFFECTIVE_RADIGEST = $(if $(strip $(RADIGEST)),$(RADIGEST),$(LOCAL_RADIGEST))
EFFECTIVE_RADIGEST_SCREEN_PAIRS = $(if $(strip $(RADIGEST_SCREEN_PAIRS)),$(RADIGEST_SCREEN_PAIRS),$(LOCAL_RADIGEST_SCREEN_PAIRS))
EFFECTIVE_RADIGEST_RANK_PAIRS = $(if $(strip $(RADIGEST_RANK_PAIRS)),$(RADIGEST_RANK_PAIRS),$(LOCAL_RADIGEST_RANK_PAIRS))

SMK_BASE = RADIGEST_WORKFLOW_CONFIG="$(WORKFLOW_CONFIG)" $(SNAKEMAKE) -s $(SNAKEFILE) \
           --cores $(THREADS) \
           --rerun-incomplete \
           --printshellcmds \
           $(SNAKEMAKE_CONDA_ARGS)

SMK_CONFIG = --config \
             radigest="$(EFFECTIVE_RADIGEST)" \
             radigest_screen_pairs="$(EFFECTIVE_RADIGEST_SCREEN_PAIRS)" \
             radigest_rank_pairs="$(EFFECTIVE_RADIGEST_RANK_PAIRS)" \
             threads=$(THREADS)

# Usage:
#   $(call smk,<target-or-options-and-target>)
smk = $(SMK_BASE) $(1) $(SMK_CONFIG)

help:
	@echo "Targets:"
	@echo "  env                      Capture hardware/software metadata"
	@echo "  build-radigest           Build radigest via Snakemake rule env"
	@echo "  radigest-local           Show local radigest executable paths"
	@echo "  check-local              Build local radigest and run checks"
	@echo "  validate-local           Build local radigest and validate synthetic data"
	@echo "  radigest-local           Build radigest from RADIGEST_REPO/RADIGEST_REF into .local/bin"
	@echo "  check-local              Build local radigest and run lightweight checks"
	@echo "  validate-local           Build local radigest and run synthetic validation"
	@echo "  synthetic                Show synthetic FASTA status"
	@echo "  validate-radigest        Run synthetic interval validation via Snakemake"
	@echo "  empirical-recovery       Run optional empirical TLEN recovery workflow"
	@echo "  empirical-recovery-local Build local radigest and run empirical recovery"
	@echo "  manuscript-tables        Build curated manuscript tables"
	@echo "  manuscript-tables-strict Build curated manuscript tables with strict artifact checks"
	@echo "  artifact-contracts       Show manuscript artifact contracts"
	@echo "  check-artifacts          Validate manuscript artifact contract manifest"
	@echo "  check-manuscript-inputs  Validate upstream inputs for manuscript-table export"
	@echo "  benchmark-categories     Show claim-oriented benchmark categories"
	@echo "  check-benchmark-categories Validate benchmark category manifest"
	@echo "  benchmark-validation     Run lightweight validation category"
	@echo "  benchmark-comparators    Run comparator categories"
	@echo "  benchmark-performance    Run input-format and scaling categories"
	@echo "  benchmark-nonempirical   Run non-empirical manuscript benchmark categories"
	@echo "  benchmark-radigest       Run configured radigest output-mode benchmarks"
	@echo "  screen-pairs             Run configured enzyme-pair screen"
	@echo "  pair-screen-tables      Summarize ranked enzyme-pair screening table"
	@echo "  pair-screen-figures     Generate enzyme-pair screening heatmap"
	@echo "  download-reference-data  Download/checksum reference datasets from config/datasets.tsv"
	@echo "  reference-data           Download public references via NCBI Datasets"
	@echo "  reference-data-dry-run   Dry-run public reference download workflow"
	@echo "  reference-checksums      Check/download configured public references directly"
	@echo "  fasta-summary            Summarize FASTA files for configured benchmark datasets"
	@echo "  prepare-plain-reference  Decompress yeast reference for input-format benchmark"
	@echo "  summarize                Generate JSON/time summary tables"
	@echo "  benchmark-tables         Build run-level and aggregate benchmark tables"
	@echo "  input-format-table       Compare radigest gzipped vs plain FASTA benchmark rows"
	@echo "  figures                  Generate benchmark figures"
	@echo "  interval-smoke           Normalize radigest TSV intervals and compare interval set to itself"
	@echo "  compare-simrad           Run optional SimRAD count-level comparison"
	@echo "  compare-digital-rads     Run optional Digital_RADs.py coordinate comparison"
	@echo "  compare-ddradseqtools    Run optional DDRADSEQTOOLS rsitesearch interval comparison"
	@echo "  compare-cut-tools        Run installed digest-level comparator cut checks"
	@echo "  benchmark-matched-tools Run timed matched radigest/SimRAD tasks"
	@echo "  benchmark-matched-tools-with-digital Run optional matched Digital_RADs timing"
	@echo "  summarize-matched-tools Summarize matched tool benchmark outputs"
	@echo "  all                      Run lightweight default workflow"
	@echo "  dry-run                  Show planned lightweight workflow"
	@echo "  dag                      Write workflow DAG for configured benchmark"
	@echo "  check                    Syntax checks + default all dry-run only"
	@echo "  lint                     Run shellcheck and Python compile checks"
	@echo "  audit                    Check reproducibility repo state"
	@echo "  audit-strict             Treat audit warnings as failures"
	@echo "  check-benchmark          Dry-run benchmark/summary/table/figure targets"
	@echo "  check-pair-screen       Dry-run pair-screening summary and figure targets"
	@echo "  check-comparators        Dry-run optional comparator targets; requires reference paths to exist"
	@echo "  clean                    Remove generated benchmark outputs"

env:
	$(call smk,results/processed/environment.txt --force)

synthetic:
	@echo "Synthetic FASTA: data/synthetic/synthetic_validation.fa"
	@seqkit stats data/synthetic/synthetic_validation.fa || true

validate-radigest:
	$(call smk,results/processed/synthetic_validation_results.tsv)

benchmark-radigest:
	$(call smk,benchmark_radigest_all)

screen-pairs:
	$(call smk,pair_screen_all)

download-reference-data:
	$(call smk,results/processed/reference_checksums.tsv)

fasta-summary:
	$(call smk,fasta_summary_all)

summarize:
	$(call smk,summaries_all)

benchmark-tables:
	$(call smk,benchmark_tables_all)

figures:
	$(call smk,figures_all)

interval-smoke:
	$(call smk,interval_smoke_all)

compare-simrad:
	$(call smk,compare_simrad_all)

compare-digital-rads:
	$(call smk,compare_digital_rads_all)

all:
	$(call smk,all)

dry-run:
	$(call smk,-n all)

dag:
	mkdir -p workflow
	$(call smk,--dag benchmark_radigest_all) > workflow/benchmark_dag.dot

.PHONY: lint
lint:
	find scripts envs -name '*.sh' -print0 | xargs -0 shellcheck
	python3 scripts/core/compile_python_tree.py scripts

check:
	bash -n scripts/core/capture_environment.sh
	bash -n scripts/reference/download_reference_data.sh
	python3 scripts/core/compile_python_tree.py scripts
	python3 scripts/core/check_benchmark_categories.py \
	  --categories "$(BENCHMARK_CATEGORIES)" \
	  --makefile Makefile \
	  --out results/processed/benchmark_category_qc.tsv
	python3 scripts/core/check_artifacts.py --manifest "$(ARTIFACT_CONTRACTS)" --out results/processed/artifact_contracts.tsv
	@echo "Skipping R syntax check in driver env; run \"make check-r\" for SimRAD/R scripts."
	RADIGEST_WORKFLOW_CONFIG="$(WORKFLOW_CONFIG)" $(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 -n all \
	  --config radigest="$(EFFECTIVE_RADIGEST)" \
	           radigest_screen_pairs="$(EFFECTIVE_RADIGEST_SCREEN_PAIRS)" \
	           radigest_rank_pairs="$(EFFECTIVE_RADIGEST_RANK_PAIRS)" \
	           threads=1

check-benchmark:
	RADIGEST_WORKFLOW_CONFIG="$(WORKFLOW_CONFIG)" $(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 -n \
	  benchmark_radigest_all summaries_all benchmark_tables_all figures_all fasta_summary_all \
	  --config radigest="$(EFFECTIVE_RADIGEST)" \
	           radigest_screen_pairs="$(EFFECTIVE_RADIGEST_SCREEN_PAIRS)" \
	           radigest_rank_pairs="$(EFFECTIVE_RADIGEST_RANK_PAIRS)" \
	           threads=1

check-comparators:
	RADIGEST_WORKFLOW_CONFIG="$(WORKFLOW_CONFIG)" $(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 -n \
	  compare_simrad_all compare_digital_rads_all \
	  --config radigest="$(EFFECTIVE_RADIGEST)" \
	           radigest_screen_pairs="$(EFFECTIVE_RADIGEST_SCREEN_PAIRS)" \
	           radigest_rank_pairs="$(EFFECTIVE_RADIGEST_RANK_PAIRS)" \
	           threads=1

clean:
	rm -rf results/raw/* results/processed/* benchmark/time/* benchmark/memory/* benchmark/logs/*
	touch results/raw/.gitkeep results/processed/.gitkeep benchmark/time/.gitkeep benchmark/memory/.gitkeep benchmark/logs/.gitkeep

pair-screen-tables:
	$(call smk,pair_screen_tables_all)

pair-screen-figures:
	$(call smk,pair_screen_figures_all)

check-pair-screen:
	RADIGEST_WORKFLOW_CONFIG="$(WORKFLOW_CONFIG)" $(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 -n \
	  pair_screen_all pair_screen_tables_all pair_screen_figures_all \
	  --config radigest="$(EFFECTIVE_RADIGEST)" \
	           radigest_screen_pairs="$(EFFECTIVE_RADIGEST_SCREEN_PAIRS)" \
	           radigest_rank_pairs="$(EFFECTIVE_RADIGEST_RANK_PAIRS)" \
	           threads=1

benchmark-categories:
	@python3 scripts/core/check_benchmark_categories.py \
	  --categories "$(BENCHMARK_CATEGORIES)" \
	  --list

check-benchmark-categories:
	@python3 scripts/core/check_benchmark_categories.py \
	  --categories "$(BENCHMARK_CATEGORIES)" \
	  --makefile Makefile \
	  --out results/processed/benchmark_category_qc.tsv

artifact-contracts:
	@column -t -s $$'\t' "$(ARTIFACT_CONTRACTS)" 2>/dev/null || cat "$(ARTIFACT_CONTRACTS)"

check-artifacts:
	python3 scripts/core/check_artifacts.py \
	  --manifest "$(ARTIFACT_CONTRACTS)" \
	  --out results/processed/artifact_contracts.tsv \
	  --check-generated

check-manuscript-inputs:
	python3 scripts/core/check_artifacts.py \
	  --manifest "$(ARTIFACT_CONTRACTS)" \
	  --out results/processed/manuscript_input_contracts.tsv

benchmark-matched-tools:
	bash scripts/benchmarks/run_matched_tool_benchmarks.sh \
	  --reference data/reference/yeast.fa.gz \
	  --dataset yeast_small \
	  --condition B1 \
	  --enzymes EcoRI,MseI \
	  --min 100 \
	  --max 300 \
	  --runs 5 \
	  --threads $(THREADS) \
	  --radigest "$(EFFECTIVE_RADIGEST)" \
	  --digital-rads external/Digital_RADs/Digital_RADs.py \
	  --skip-digital-rads \
	  --skip-simrad

benchmark-matched-tools-with-digital:
	bash scripts/benchmarks/run_matched_tool_benchmarks.sh \
	  --reference data/reference/yeast.fa.gz \
	  --dataset yeast_small \
	  --condition B1 \
	  --enzymes EcoRI,MseI \
	  --min 100 \
	  --max 300 \
	  --runs 5 \
	  --threads $(THREADS) \
	  --radigest "$(EFFECTIVE_RADIGEST)" \
	  --digital-rads external/Digital_RADs/Digital_RADs.py \
	  --skip-simrad

summarize-matched-tools:
	python3 scripts/benchmarks/summarize_matched_tool_benchmarks.py \
	  --root results/raw/matched_tool_benchmarks \
	  --time-dir benchmark/memory/matched_tools \
	  --dataset yeast_small \
	  --condition B1 \
	  --out-runs results/tables/matched_tool_benchmark_runs.tsv \
	  --out-summary results/tables/matched_tool_benchmark_summary.tsv

benchmark-simrad-warm:
	mkdir -p results/tables benchmark/memory/matched_tools benchmark/logs/matched_tools
	/usr/bin/time -v \
	  -o benchmark/memory/matched_tools/simrad_warm_package_reload_reference.time \
	  Rscript scripts/benchmarks/run_simrad_warm_benchmark.R \
	    --reference data/reference/yeast.fa.gz \
	    --enzyme1 EcoRI \
	    --enzyme2 MseI \
	    --min 100 \
	    --max 300 \
	    --runs 5 \
	    --enzymes-tsv config/enzymes.tsv \
	    --out-runs results/tables/simrad_warm_runs.tsv \
	    --out-summary results/tables/simrad_warm_summary.tsv \
	    --version-log results/tables/simrad_warm_version.txt \
	    > benchmark/logs/matched_tools/simrad_warm.stdout.log \
	    2> benchmark/logs/matched_tools/simrad_warm.stderr.log
	/usr/bin/time -v \
	  -o benchmark/memory/matched_tools/simrad_reuse_reference.time \
	  Rscript scripts/benchmarks/run_simrad_warm_benchmark.R \
	    --reference data/reference/yeast.fa.gz \
	    --enzyme1 EcoRI \
	    --enzyme2 MseI \
	    --min 100 \
	    --max 300 \
	    --runs 5 \
	    --enzymes-tsv config/enzymes.tsv \
	    --out-runs results/tables/simrad_reuse_reference_runs.tsv \
	    --out-summary results/tables/simrad_reuse_reference_summary.tsv \
	    --version-log results/tables/simrad_reuse_reference_version.txt \
	    --reuse-reference \
	    > benchmark/logs/matched_tools/simrad_reuse_reference.stdout.log \
	    2> benchmark/logs/matched_tools/simrad_reuse_reference.stderr.log

prepare-plain-reference:
	$(call smk,prepare_plain_reference_all)

input-format-table:
	$(call smk,input_format_table_all)

.PHONY: tool-comparison-figures input-format-figures compare-ddradseqtools check-ddradseqtools compare-cut-tools radigest-local radigest-local-version check-local validate-local empirical-recovery-dry-run empirical-recovery-local manuscript-tables audit audit-strict reference-data reference-data-dry-run reference-checksums build-radigest

tool-comparison-figures:
	python3 scripts/manuscript/make_tool_comparison_figures.py \
	  --timing-table results/tables/tool_timing_interpretation.tsv \
	  --out-dir results/figures \
	  --manuscript-dir manuscript_figures

input-format-figures:
	python3 scripts/manuscript/make_input_format_figures.py \
	  --comparison results/tables/radigest_input_format_comparison.tsv \
	  --out-dir results/figures \
	  --manuscript-dir manuscript_figures

compare-ddradseqtools:
	$(call smk,compare_ddradseqtools_all)

check-ddradseqtools:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 -n compare_ddradseqtools_all $(SMK_CONFIG)

compare-cut-tools:
	$(call smk,compare_simrad_all compare_digital_rads_all compare_ddradseqtools_all)
	$(MAKE) compare-ddgrader-binned \
	  RADIGEST="$(EFFECTIVE_RADIGEST)" \
	  YEAST_PLAIN_REF="$(YEAST_PLAIN_REF)"
	$(MAKE) build-cut-equivalence-table


radigest-local: build-radigest
	@echo "RADIGEST=$(LOCAL_RADIGEST)"
	@echo "RADIGEST_SCREEN_PAIRS=$(LOCAL_RADIGEST_SCREEN_PAIRS)"
	@echo "RADIGEST_RANK_PAIRS=$(LOCAL_RADIGEST_RANK_PAIRS)"
	@echo "RADIGEST_FIT_SIZE_MODEL=$(LOCAL_RADIGEST_FIT_SIZE_MODEL)"
radigest-local-version: radigest-local
	$(LOCAL_RADIGEST) -version || true
	@echo "RADIGEST=$(LOCAL_RADIGEST)"
	@echo "RADIGEST_SCREEN_PAIRS=$(LOCAL_RADIGEST_SCREEN_PAIRS)"
	@echo "RADIGEST_RANK_PAIRS=$(LOCAL_RADIGEST_RANK_PAIRS)"

check-local: build-radigest
	$(MAKE) check \
	  RADIGEST="$(LOCAL_RADIGEST)" \
	  RADIGEST_SCREEN_PAIRS="$(LOCAL_RADIGEST_SCREEN_PAIRS)" \
	  RADIGEST_RANK_PAIRS="$(LOCAL_RADIGEST_RANK_PAIRS)" \
	  THREADS=1
validate-local: build-radigest
	$(MAKE) validate-radigest \
	  RADIGEST="$(LOCAL_RADIGEST)" \
	  RADIGEST_SCREEN_PAIRS="$(LOCAL_RADIGEST_SCREEN_PAIRS)" \
	  RADIGEST_RANK_PAIRS="$(LOCAL_RADIGEST_RANK_PAIRS)" \
	  THREADS=1
empirical-recovery-dry-run:
	$(SNAKEMAKE) -s $(EMPIRICAL_SNAKEFILE) --cores 1 -n all \
	  --config empirical_table="config/empirical_recovery.tsv" \
	           datasets="$(EMPIRICAL_DATASETS)" \
	           radigest="$(EFFECTIVE_RADIGEST)" \
	           radigest_fit_size_model="$(RADIGEST_FIT_SIZE_MODEL)" \
	           threads=1

empirical-recovery:
	$(SNAKEMAKE) -s $(EMPIRICAL_SNAKEFILE) --cores $(THREADS) --rerun-incomplete --printshellcmds all \
	  --config empirical_table="config/empirical_recovery.tsv" \
	           datasets="$(EMPIRICAL_DATASETS)" \
	           radigest="$(EFFECTIVE_RADIGEST)" \
	           radigest_fit_size_model="$(RADIGEST_FIT_SIZE_MODEL)" \
	           threads=$(THREADS)

empirical-recovery-local: radigest-local
	$(MAKE) empirical-recovery \
	  RADIGEST="$(LOCAL_RADIGEST)" \
	  RADIGEST_FIT_SIZE_MODEL="$(LOCAL_RADIGEST_FIT_SIZE_MODEL)" \
	  THREADS="$(THREADS)"

manuscript-tables: check-manuscript-inputs
	python3 scripts/manuscript/make_manuscript_tables.py --out-dir manuscript_tables
	@if [ -s results/tables/cut_equivalence_summary.tsv ]; then \
	  python3 scripts/comparators/build_cut_equivalence_table.py; \
	fi

manuscript-tables-strict:
	python3 scripts/core/check_artifacts.py \
	  --manifest "$(ARTIFACT_CONTRACTS)" \
	  --out results/processed/manuscript_input_contracts.tsv \
	  --release-only \
	  --strict
	python3 scripts/manuscript/make_manuscript_tables.py --out-dir manuscript_tables
	@if [ -s results/tables/cut_equivalence_summary.tsv ]; then \
	  python3 scripts/comparators/build_cut_equivalence_table.py; \
	fi
	python3 scripts/core/check_artifacts.py \
	  --manifest "$(ARTIFACT_CONTRACTS)" \
	  --out results/processed/artifact_contracts.tsv \
	  --check-generated \
	  --release-only \
	  --strict

audit:
	python3 scripts/core/audit_reproducibility.py

audit-strict:
	python3 scripts/core/audit_reproducibility.py --fail-on-warn

.PHONY: reference-data-dry-run reference-data reference-checksums

reference-data-dry-run:
	$(SNAKEMAKE) -s $(REFERENCE_SNAKEFILE) --cores 1 -n $(SNAKEMAKE_CONDA_ARGS) all \
	  --config datasets_tsv="config/datasets.tsv" \
	           dataset_ids="$(REFERENCE_DATASETS)" \
	           prepare_plain=true

reference-data:
	$(SNAKEMAKE) -s $(REFERENCE_SNAKEFILE) --cores 1 $(SNAKEMAKE_CONDA_ARGS) --rerun-incomplete --printshellcmds all \
	  --config datasets_tsv="config/datasets.tsv" \
	           dataset_ids="$(REFERENCE_DATASETS)" \
	           prepare_plain=true

reference-checksums:
	scripts/reference/download_reference_data.sh \
	  --datasets config/datasets.tsv \
	  --dataset "$(REFERENCE_DATASETS)" \
	  --prepare-plain \
	  --out results/processed/reference_checksums.tsv

build-radigest:
	$(SNAKEMAKE) -s $(RADIGEST_BUILD_SNAKEFILE) --cores 1 \
	  $(SNAKEMAKE_CONDA_ARGS) \
	  --rerun-incomplete --printshellcmds all \
	  --config radigest_repo="$(RADIGEST_REPO)" \
	           radigest_ref="$(RADIGEST_REF)" \
	           local_bin="$(LOCAL_BIN)" \
	           radigest_build_dir="$(RADIGEST_BUILD_DIR)"

.PHONY: check-r
check-r:
	@echo "R/SimRAD checks are Snakemake-managed; no named SimRAD env is required."


benchmark-matched-tools-with-simrad:
	$(SNAKEMAKE) -s $(MATCHED_TOOLS_SNAKEFILE) --cores 1 \
	  $(SNAKEMAKE_CONDA_ARGS) \
	  --rerun-incomplete --printshellcmds --forceall all \
	  --config reference="data/reference/yeast.fa.gz" \
	           dataset="yeast_small" \
	           condition="B1" \
	           enzymes="EcoRI,MseI" \
	           min_size=100 \
	           max_size=300 \
	           runs=5 \
	           threads=$(THREADS) \
	           radigest="$(EFFECTIVE_RADIGEST)" \
	           digital_rads="external/Digital_RADs/Digital_RADs.py" \
	           include_digital=false

SIMRAD_WARM_SNAKEFILE ?= workflow/simrad_warm.smk

.PHONY: benchmark-simrad-warm-managed tool-timing-table

benchmark-simrad-warm-managed:
	$(SNAKEMAKE) -s $(SIMRAD_WARM_SNAKEFILE) --cores 1 \
	  $(SNAKEMAKE_CONDA_ARGS) \
	  --rerun-incomplete --printshellcmds --forceall all \
	  --config reference="$(YEAST_PLAIN_REF)" \
	           dataset="$(YEAST_PLAIN_DATASET)" \
	           condition="$(YEAST_CONDITION)" \
	           enzyme1="EcoRI" \
	           enzyme2="MseI" \
	           min_size=100 \
	           max_size=300 \
	           runs=$(MATCHED_RUNS)

tool-timing-table:
	python3 scripts/benchmarks/build_tool_timing_interpretation_table.py \
	  --matched-summary results/tables/matched_tool_benchmark_summary.tsv \
	  --simrad-warm-summary results/tables/simrad_warm_summary.tsv \
	  --simrad-warm-time benchmark/memory/matched_tools/simrad_warm_package_reload_reference.time \
	  --simrad-reuse-summary results/tables/simrad_reuse_reference_summary.tsv \
	  --simrad-reuse-time benchmark/memory/matched_tools/simrad_reuse_reference.time \
	  --dataset "$(YEAST_PLAIN_DATASET)" \
	  --condition "$(YEAST_CONDITION)" \
	  --out results/tables/tool_timing_interpretation.tsv

# ----------------------------------------------------------------------
# Reviewer-facing non-empirical rerun targets
# ----------------------------------------------------------------------

YEAST_PLAIN_REF ?= data/reference/yeast.fa
YEAST_PLAIN_DATASET ?= yeast_small_plain
YEAST_CONDITION ?= B1
MATCHED_RUNS ?= 5
SCREENING_RUNS ?= 5
THREAD_SCALING_RUNS ?= 7
PAIR_SCREEN_RUNS ?= 3
PAIR_SCREEN_JOBS ?= 1 2 4 8
SCALING_THREADS_LIST ?= 1,2,4,8
MODERATE_PLAIN_REF ?= data/reference/moderate.fa
SCALING_SNAKEMAKE_CORES ?= 1
THREAD_SCALING_CONDITIONS ?= B1,B2
SCALING_MODES ?= json,fragments_tsv
PAIR_SCREEN_STEM_PREFIX ?= cannabis

.PHONY: reviewer-prepare benchmark-digest-tool-comparison benchmark-tool-comparison
.PHONY: benchmark-input-format benchmark-scaling radigest-thread-scaling
.PHONY: pair-screen-scaling benchmark-screening-speed figures-nonempirical
.PHONY: reviewer-rerun-nonempirical
.PHONY: benchmark-categories check-benchmark-categories artifact-contracts check-artifacts check-manuscript-inputs manuscript-tables-strict benchmark-validation
.PHONY: benchmark-comparators benchmark-performance benchmark-nonempirical
.PHONY: benchmark-empirical benchmark-manuscript-artifacts

reviewer-prepare: build-radigest
	$(MAKE) reference-data
	$(MAKE) prepare-plain-reference \
	  RADIGEST="$(LOCAL_RADIGEST)" \
	  RADIGEST_SCREEN_PAIRS="$(LOCAL_RADIGEST_SCREEN_PAIRS)" \
	  RADIGEST_RANK_PAIRS="$(LOCAL_RADIGEST_RANK_PAIRS)" \
	  THREADS=1
	$(MAKE) validate-local THREADS=1
	$(MAKE) env \
	  RADIGEST="$(LOCAL_RADIGEST)" \
	  RADIGEST_SCREEN_PAIRS="$(LOCAL_RADIGEST_SCREEN_PAIRS)" \
	  RADIGEST_RANK_PAIRS="$(LOCAL_RADIGEST_RANK_PAIRS)" \
	  THREADS=1
	bash scripts/comparators/install_digital_rads.sh
	bash scripts/comparators/install_ddradseqtools.sh
	bash scripts/comparators/install_ddgrader.sh

benchmark-digest-tool-comparison:
	test -s "$(YEAST_PLAIN_REF)"
	$(SNAKEMAKE) -s $(MATCHED_TOOLS_SNAKEFILE) --cores 1 \
	  $(SNAKEMAKE_CONDA_ARGS) \
	  --rerun-incomplete --printshellcmds --forceall all \
	  --config reference="$(YEAST_PLAIN_REF)" \
	           dataset="$(YEAST_PLAIN_DATASET)" \
	           condition="$(YEAST_CONDITION)" \
	           enzymes="EcoRI,MseI" \
	           min_size=100 \
	           max_size=300 \
	           runs=$(MATCHED_RUNS) \
	           threads=1 \
	           radigest="$(EFFECTIVE_RADIGEST)" \
	           digital_rads="external/Digital_RADs/Digital_RADs.py" \
	           include_digital=true
	$(SNAKEMAKE) -s $(SIMRAD_WARM_SNAKEFILE) --cores 1 \
	  $(SNAKEMAKE_CONDA_ARGS) \
	  --rerun-incomplete --printshellcmds --forceall all \
	  --config reference="$(YEAST_PLAIN_REF)" \
	           dataset="$(YEAST_PLAIN_DATASET)" \
	           condition="$(YEAST_CONDITION)" \
	           enzyme1="EcoRI" \
	           enzyme2="MseI" \
	           min_size=100 \
	           max_size=300 \
	           runs=$(MATCHED_RUNS)
	python3 scripts/benchmarks/build_tool_timing_interpretation_table.py \
	  --matched-summary results/tables/matched_tool_benchmark_summary.tsv \
	  --simrad-warm-summary results/tables/simrad_warm_summary.tsv \
	  --simrad-warm-time benchmark/memory/matched_tools/simrad_warm_package_reload_reference.time \
	  --simrad-reuse-summary results/tables/simrad_reuse_reference_summary.tsv \
	  --simrad-reuse-time benchmark/memory/matched_tools/simrad_reuse_reference.time \
	  --dataset "$(YEAST_PLAIN_DATASET)" \
	  --condition "$(YEAST_CONDITION)" \
	  --out results/tables/tool_timing_interpretation.tsv

benchmark-matched-tools-full: benchmark-digest-tool-comparison

benchmark-screening-speed:
	$(SNAKEMAKE) -s $(SCREENING_SPEED_SNAKEFILE) --cores 1 \
	  $(SNAKEMAKE_CONDA_ARGS) \
	  --rerun-incomplete --printshellcmds --forceall all \
	  --config reference="$(YEAST_PLAIN_REF)" \
	           dataset="$(YEAST_PLAIN_DATASET)" \
	           enzymes="config/candidate_enzymes.txt" \
	           min_size=300 \
	           max_size=600 \
	           score_min=1 \
	           score_max=2000 \
	           size_model="hard" \
	           runs=$(SCREENING_RUNS) \
	           radigest="$(EFFECTIVE_RADIGEST)" \
	           radigest_screen_pairs="$(EFFECTIVE_RADIGEST_SCREEN_PAIRS)" \
	           ddgrader_repo="external/ddRadSeqWebTool" \
	           jobs=2 \
	           radigest_threads=1

benchmark-tool-comparison: benchmark-digest-tool-comparison benchmark-screening-speed

benchmark-input-format:
	$(MAKE) benchmark-radigest \
	  WORKFLOW_CONFIG=workflow/config.yeast_input_formats.yml \
	  RADIGEST="$(EFFECTIVE_RADIGEST)" \
	  RADIGEST_SCREEN_PAIRS="$(EFFECTIVE_RADIGEST_SCREEN_PAIRS)" \
	  RADIGEST_RANK_PAIRS="$(EFFECTIVE_RADIGEST_RANK_PAIRS)" \
	  THREADS=1
	$(MAKE) benchmark-tables \
	  WORKFLOW_CONFIG=workflow/config.yeast_input_formats.yml \
	  RADIGEST="$(EFFECTIVE_RADIGEST)" \
	  RADIGEST_SCREEN_PAIRS="$(EFFECTIVE_RADIGEST_SCREEN_PAIRS)" \
	  RADIGEST_RANK_PAIRS="$(EFFECTIVE_RADIGEST_RANK_PAIRS)" \
	  THREADS=1
	$(MAKE) input-format-table \
	  WORKFLOW_CONFIG=workflow/config.yeast_input_formats.yml \
	  RADIGEST="$(EFFECTIVE_RADIGEST)" \
	  RADIGEST_SCREEN_PAIRS="$(EFFECTIVE_RADIGEST_SCREEN_PAIRS)" \
	  RADIGEST_RANK_PAIRS="$(EFFECTIVE_RADIGEST_RANK_PAIRS)" \
	  THREADS=1

radigest-thread-scaling:
	test -s "$(MODERATE_PLAIN_REF)"
	$(SNAKEMAKE) -s $(SCALING_SNAKEFILE) --cores $(SCALING_SNAKEMAKE_CORES) \
	  $(SNAKEMAKE_CONDA_ARGS) \
	  --rerun-incomplete --printshellcmds radigest_thread_scaling_all \
	  --config reference="$(MODERATE_PLAIN_REF)" \
	           dataset="cannabis_pink_pepper_plain" \
	           thread_scaling_conditions="$(THREAD_SCALING_CONDITIONS)" \
	           thread_scaling_modes="$(SCALING_MODES)" \
	           thread_scaling_threads="$(SCALING_THREADS_LIST)" \
	           thread_scaling_runs=$(THREAD_SCALING_RUNS) \
	           radigest="$(EFFECTIVE_RADIGEST)"

pair-screen-scaling:
	test -s "$(MODERATE_PLAIN_REF)"
	$(SNAKEMAKE) -s $(SCALING_SNAKEFILE) --cores $(SCALING_SNAKEMAKE_CORES) \
	  $(SNAKEMAKE_CONDA_ARGS) \
	  --rerun-incomplete --printshellcmds pair_screen_scaling_all \
	  --config reference="$(MODERATE_PLAIN_REF)" \
	           dataset="cannabis_pink_pepper_plain" \
	           pair_screen_stem_prefix="$(PAIR_SCREEN_STEM_PREFIX)" \
	           pair_screen_enzymes="config/candidate_enzymes.txt" \
	           pair_screen_min_size=300 \
	           pair_screen_max_size=600 \
	           pair_screen_score_min=1 \
	           pair_screen_score_max=2000 \
	           pair_screen_size_model="hard" \
	           pair_screen_runs=$(PAIR_SCREEN_RUNS) \
	           pair_screen_jobs="$(PAIR_SCREEN_JOBS)" \
	           pair_screen_radigest_threads=1 \
	           radigest="$(EFFECTIVE_RADIGEST)" \
	           radigest_screen_pairs="$(EFFECTIVE_RADIGEST_SCREEN_PAIRS)"

benchmark-scaling: radigest-thread-scaling pair-screen-scaling

benchmark-validation: validate-radigest interval-smoke

benchmark-comparators: compare-cut-tools benchmark-tool-comparison

benchmark-performance: benchmark-input-format benchmark-scaling

benchmark-empirical: empirical-recovery

benchmark-manuscript-artifacts: figures-nonempirical manuscript-tables

benchmark-nonempirical: benchmark-validation benchmark-comparators benchmark-performance benchmark-manuscript-artifacts audit

figures-nonempirical:
	mkdir -p results/figures manuscript_figures
	python3 scripts/manuscript/make_figures.py \
	  --benchmark-summary results/tables/radigest_benchmark_summary.tsv \
	  --out-dir results/figures \
	  --manuscript-dir manuscript_figures
	python3 scripts/manuscript/make_tool_comparison_figures.py \
	  --timing-table results/tables/tool_timing_interpretation.tsv \
	  --out-dir results/figures \
	  --manuscript-dir manuscript_figures
	python3 scripts/manuscript/make_input_format_figures.py \
	  --comparison results/tables/radigest_input_format_comparison.tsv \
	  --out-dir results/figures \
	  --manuscript-dir manuscript_figures
	python3 scripts/manuscript/make_screening_speed_figures.py \
	  --summary results/tables/screening_speed_summary.tsv \
	  --out-dir results/figures \
	  --manuscript-dir manuscript_figures
	python3 scripts/manuscript/make_pair_screen_scaling_figures.py \
	  --summary results/tables/pair_screen_scaling_summary.tsv \
	  --out-dir results/figures \
	  --manuscript-dir manuscript_figures

reviewer-rerun-nonempirical:
	$(MAKE) reviewer-prepare \
	  RADIGEST_REPO="$(RADIGEST_REPO)" \
	  RADIGEST_REF="$(RADIGEST_REF)"
	$(MAKE) benchmark-nonempirical \
	  RADIGEST="$(LOCAL_RADIGEST)" \
	  RADIGEST_SCREEN_PAIRS="$(LOCAL_RADIGEST_SCREEN_PAIRS)" \
	  RADIGEST_RANK_PAIRS="$(LOCAL_RADIGEST_RANK_PAIRS)" \
	  THREADS="$(THREADS)"


.PHONY: compare-ddgrader-binned build-cut-equivalence-table

compare-ddgrader-binned:
	$(SNAKEMAKE) -s $(DDGRADER_BINNED_SNAKEFILE) --cores 1 \
	  $(SNAKEMAKE_CONDA_ARGS) \
	  --rerun-incomplete --printshellcmds --forceall all \
	  --config reference="$(YEAST_PLAIN_REF)" \
	           dataset="$(YEAST_PLAIN_DATASET)" \
	           condition="$(YEAST_CONDITION)" \
	           enzymes="EcoRI,MseI" \
	           enzyme_pair="EcoRI+MseI" \
	           min_size=100 \
	           max_size=300 \
	           radigest="$(EFFECTIVE_RADIGEST)" \
	           ddgrader_repo="external/ddRadSeqWebTool"

build-cut-equivalence-table:
	python3 scripts/comparators/build_cut_equivalence_table.py
