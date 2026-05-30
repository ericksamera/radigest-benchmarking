SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

SNAKEMAKE ?= snakemake
SNAKEFILE ?= workflow/Snakefile
WORKFLOW_CONFIG ?= workflow/config.yml

RADIGEST ?= radigest
RADIGEST_SCREEN_PAIRS ?= radigest-screen-pairs
RADIGEST_RANK_PAIRS ?= radigest-rank-pairs

THREADS ?= 4

SMK_BASE = RADIGEST_WORKFLOW_CONFIG="$(WORKFLOW_CONFIG)" $(SNAKEMAKE) -s $(SNAKEFILE) \
           --cores $(THREADS) \
           --rerun-incomplete \
           --printshellcmds

SMK_CONFIG = --config \
             radigest="$(RADIGEST)" \
             radigest_screen_pairs="$(RADIGEST_SCREEN_PAIRS)" \
             radigest_rank_pairs="$(RADIGEST_RANK_PAIRS)" \
             threads=$(THREADS)

# Usage:
#   $(call smk,<target-or-options-and-target>)
smk = $(SMK_BASE) $(1) $(SMK_CONFIG)

.PHONY: help env synthetic validate-radigest benchmark-radigest screen-pairs download-reference-data fasta-summary summarize benchmark-tables figures all dry-run dag check check-benchmark check-comparators clean interval-smoke compare-simrad compare-digital-rads pair-screen-tables pair-screen-figures check-pair-screen benchmark-matched-tools benchmark-matched-tools-with-digital summarize-matched-tools prepare-plain-reference input-format-table

help:
	@echo "Targets:"
	@echo "  env                      Capture hardware/software metadata"
	@echo "  synthetic                Show synthetic FASTA status"
	@echo "  validate-radigest        Run synthetic interval validation via Snakemake"
	@echo "  benchmark-radigest       Run configured radigest output-mode benchmarks"
	@echo "  screen-pairs             Run configured enzyme-pair screen"
	@echo "  pair-screen-tables      Summarize ranked enzyme-pair screening table"
	@echo "  pair-screen-figures     Generate enzyme-pair screening heatmap"
	@echo "  download-reference-data  Download/checksum reference datasets from config/datasets.tsv"
	@echo "  fasta-summary            Summarize FASTA files for configured benchmark datasets"
	@echo "  prepare-plain-reference  Decompress yeast reference for input-format benchmark"
	@echo "  summarize                Generate JSON/time summary tables"
	@echo "  benchmark-tables         Build run-level and aggregate benchmark tables"
	@echo "  input-format-table       Compare radigest gzipped vs plain FASTA benchmark rows"
	@echo "  figures                  Generate benchmark figures"
	@echo "  interval-smoke           Normalize radigest TSV intervals and compare interval set to itself"
	@echo "  compare-simrad           Run optional SimRAD count-level comparison"
	@echo "  compare-digital-rads     Run optional Digital_RADs.py coordinate comparison"
	@echo "  benchmark-matched-tools Run timed matched radigest/SimRAD tasks"
	@echo "  benchmark-matched-tools-with-digital Run optional matched Digital_RADs timing"
	@echo "  summarize-matched-tools Summarize matched tool benchmark outputs"
	@echo "  all                      Run lightweight default workflow"
	@echo "  dry-run                  Show planned lightweight workflow"
	@echo "  dag                      Write workflow DAG for configured benchmark"
	@echo "  check                    Syntax checks + default all dry-run only"
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
	python3 -m py_compile scripts/*.py
	@if compgen -G "scripts/*.R" > /dev/null; then \
	  Rscript -e 'files <- list.files("scripts", pattern="[.]R$$", full.names=TRUE); invisible(lapply(files, parse))' ; \
	fi
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
	  --skip-digital-rads

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
	  --digital-rads external/Digital_RADs/Digital_RADs.py

summarize-matched-tools:
	python3 scripts/summarize_matched_tool_benchmarks.py \
	  --root results/raw/matched_tool_benchmarks \
	  --time-dir benchmark/memory/matched_tools \
	  --dataset yeast_small \
	  --condition B1 \
	  --out-runs results/tables/matched_tool_benchmark_runs.tsv \
	  --out-summary results/tables/matched_tool_benchmark_summary.tsv

.PHONY: benchmark-simrad-warm tool-timing-table prepare-plain-reference input-format-table

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

.PHONY: benchmark-simrad-warm tool-timing-table prepare-plain-reference input-format-table

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

.PHONY: tool-comparison-figures input-format-figures

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
