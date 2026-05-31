SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

SNAKEMAKE ?= snakemake
SNAKEFILE ?= workflow/Snakefile
MATCHED_TOOLS_SNAKEFILE ?= workflow/matched_tools.smk
WORKFLOW_CONFIG ?= workflow/config.yml

RADIGEST ?= radigest
RADIGEST_SCREEN_PAIRS ?= radigest-screen-pairs
RADIGEST_RANK_PAIRS ?= radigest-rank-pairs

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


SMK_BASE = RADIGEST_WORKFLOW_CONFIG="$(WORKFLOW_CONFIG)" $(SNAKEMAKE) -s $(SNAKEFILE) \
           --cores $(THREADS) \
           --rerun-incomplete \
           --printshellcmds \
           $(SNAKEMAKE_CONDA_ARGS)

SMK_CONFIG = --config \
             radigest="$(RADIGEST)" \
             radigest_screen_pairs="$(RADIGEST_SCREEN_PAIRS)" \
             radigest_rank_pairs="$(RADIGEST_RANK_PAIRS)" \
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

check:
	bash -n scripts/capture_environment.sh
	bash -n scripts/download_reference_data.sh
	python3 scripts/core/compile_python_tree.py scripts
	@echo "Skipping R syntax check in driver env; run \"make check-r\" for SimRAD/R scripts."
	RADIGEST_WORKFLOW_CONFIG="$(WORKFLOW_CONFIG)" $(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 -n all \
	  --config radigest="$(RADIGEST)" \
	           radigest_screen_pairs="$(RADIGEST_SCREEN_PAIRS)" \
	           radigest_rank_pairs="$(RADIGEST_RANK_PAIRS)" \
	           threads=1

check-benchmark:
	RADIGEST_WORKFLOW_CONFIG="$(WORKFLOW_CONFIG)" $(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 -n \
	  benchmark_radigest_all summaries_all benchmark_tables_all figures_all fasta_summary_all \
	  --config radigest="$(RADIGEST)" \
	           radigest_screen_pairs="$(RADIGEST_SCREEN_PAIRS)" \
	           radigest_rank_pairs="$(RADIGEST_RANK_PAIRS)" \
	           threads=1

check-comparators:
	RADIGEST_WORKFLOW_CONFIG="$(WORKFLOW_CONFIG)" $(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 -n \
	  compare_simrad_all compare_digital_rads_all \
	  --config radigest="$(RADIGEST)" \
	           radigest_screen_pairs="$(RADIGEST_SCREEN_PAIRS)" \
	           radigest_rank_pairs="$(RADIGEST_RANK_PAIRS)" \
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
	  --config radigest="$(RADIGEST)" \
	           radigest_screen_pairs="$(RADIGEST_SCREEN_PAIRS)" \
	           radigest_rank_pairs="$(RADIGEST_RANK_PAIRS)" \
	           threads=1

benchmark-matched-tools:
	bash scripts/run_matched_tool_benchmarks.sh \
	  --reference data/reference/yeast.fa.gz \
	  --dataset yeast_small \
	  --condition B1 \
	  --enzymes EcoRI,MseI \
	  --min 100 \
	  --max 300 \
	  --runs 5 \
	  --threads $(THREADS) \
	  --radigest "$(RADIGEST)" \
	  --digital-rads external/Digital_RADs/Digital_RADs.py \
	  --skip-digital-rads \
	  --skip-simrad

benchmark-matched-tools-with-digital:
	bash scripts/run_matched_tool_benchmarks.sh \
	  --reference data/reference/yeast.fa.gz \
	  --dataset yeast_small \
	  --condition B1 \
	  --enzymes EcoRI,MseI \
	  --min 100 \
	  --max 300 \
	  --runs 5 \
	  --threads $(THREADS) \
	  --radigest "$(RADIGEST)" \
	  --digital-rads external/Digital_RADs/Digital_RADs.py \
	  --skip-simrad

summarize-matched-tools:
	python3 scripts/summarize_matched_tool_benchmarks.py \
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
	  Rscript scripts/run_simrad_warm_benchmark.R \
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
	  Rscript scripts/run_simrad_warm_benchmark.R \
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

tool-timing-table:
	python3 scripts/build_tool_timing_interpretation_table.py \
	  --matched-summary results/tables/matched_tool_benchmark_summary.tsv \
	  --simrad-warm-summary results/tables/simrad_warm_summary.tsv \
	  --simrad-warm-time benchmark/memory/matched_tools/simrad_warm_package_reload_reference.time \
	  --simrad-reuse-summary results/tables/simrad_reuse_reference_summary.tsv \
	  --simrad-reuse-time benchmark/memory/matched_tools/simrad_reuse_reference.time \
	  --dataset yeast_small \
	  --condition B1 \
	  --out results/tables/tool_timing_interpretation.tsv

prepare-plain-reference:
	$(call smk,prepare_plain_reference_all)

input-format-table:
	$(call smk,input_format_table_all)

.PHONY: tool-comparison-figures input-format-figures compare-ddradseqtools check-ddradseqtools compare-cut-tools radigest-local radigest-local-version check-local validate-local empirical-recovery-dry-run empirical-recovery-local manuscript-tables audit audit-strict reference-data reference-data-dry-run reference-checksums build-radigest

tool-comparison-figures:
	python3 scripts/make_tool_comparison_figures.py \
	  --timing-table results/tables/tool_timing_interpretation.tsv \
	  --out-dir results/figures \
	  --manuscript-dir manuscript_figures

input-format-figures:
	python3 scripts/make_input_format_figures.py \
	  --comparison results/tables/radigest_input_format_comparison.tsv \
	  --out-dir results/figures \
	  --manuscript-dir manuscript_figures

compare-ddradseqtools:
	$(call smk,compare_ddradseqtools_all)

check-ddradseqtools:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 -n compare_ddradseqtools_all $(SMK_CONFIG)

compare-cut-tools:
	$(call smk,compare_simrad_all compare_digital_rads_all compare_ddradseqtools_all)

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
	           radigest="$(RADIGEST)" \
	           radigest_fit_size_model="$(RADIGEST_FIT_SIZE_MODEL)" \
	           threads=1

empirical-recovery:
	$(SNAKEMAKE) -s $(EMPIRICAL_SNAKEFILE) --cores $(THREADS) --rerun-incomplete --printshellcmds all \
	  --config empirical_table="config/empirical_recovery.tsv" \
	           datasets="$(EMPIRICAL_DATASETS)" \
	           radigest="$(RADIGEST)" \
	           radigest_fit_size_model="$(RADIGEST_FIT_SIZE_MODEL)" \
	           threads=$(THREADS)

empirical-recovery-local: radigest-local
	$(MAKE) empirical-recovery \
	  RADIGEST="$(LOCAL_RADIGEST)" \
	  RADIGEST_FIT_SIZE_MODEL="$(LOCAL_RADIGEST_FIT_SIZE_MODEL)" \
	  THREADS="$(THREADS)"

manuscript-tables:
	python3 scripts/make_manuscript_tables.py --out-dir manuscript_tables

audit:
	python3 scripts/audit_reproducibility.py

audit-strict:
	python3 scripts/audit_reproducibility.py --fail-on-warn

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
	scripts/download_reference_data.sh \
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
	           radigest="$(RADIGEST)" \
	           digital_rads="external/Digital_RADs/Digital_RADs.py" \
	           include_digital=false

benchmark-matched-tools-full:
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
	           radigest="$(RADIGEST)" \
	           digital_rads="external/Digital_RADs/Digital_RADs.py" \
	           include_digital=true
