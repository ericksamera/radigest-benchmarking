SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

SNAKEMAKE ?= snakemake
SNAKEFILE ?= workflow/Snakefile

RADIGEST ?= radigest
RADIGEST_SCREEN_PAIRS ?= radigest-screen-pairs
RADIGEST_RANK_PAIRS ?= radigest-rank-pairs

THREADS ?= 4

SMK_BASE = $(SNAKEMAKE) -s $(SNAKEFILE) \
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

.PHONY: help env synthetic validate-radigest benchmark-radigest screen-pairs download-reference-data fasta-summary summarize figures all dry-run dag check clean interval-smoke compare-simrad compare-digital-rads

help:
	@echo "Targets:"
	@echo "  env                      Capture hardware/software metadata"
	@echo "  synthetic                Show synthetic FASTA status"
	@echo "  validate-radigest        Run synthetic interval validation via Snakemake"
	@echo "  benchmark-radigest       Run configured radigest output-mode benchmarks"
	@echo "  screen-pairs             Run configured enzyme-pair screen"
	@echo "  download-reference-data  Download/checksum reference datasets from config/datasets.tsv"
	@echo "  fasta-summary            Summarize FASTA files for configured benchmark datasets"
	@echo "  interval-smoke          Normalize radigest TSV intervals and compare interval set to itself"
	@echo "  compare-simrad           Run optional SimRAD count-level comparison"
	@echo "  compare-digital-rads     Run optional Digital_RADs.py coordinate comparison"
	@echo "  summarize                Generate configured summary tables"
	@echo "  figures                  Generate figures when figure rules are added"
	@echo "  all                      Run lightweight default workflow"
	@echo "  dry-run                  Show planned lightweight workflow"
	@echo "  dag                      Write workflow DAG for configured benchmark"
	@echo "  check                    Run syntax and workflow dry-run checks"
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

figures:
	@echo "TO_BE_FILLED: add figure rules after scripts/make_figures.py is committed."

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
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 -n all \
	  --config radigest="$(RADIGEST)" \
	           radigest_screen_pairs="$(RADIGEST_SCREEN_PAIRS)" \
	           radigest_rank_pairs="$(RADIGEST_RANK_PAIRS)" \
	           threads=1
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 -n benchmark_radigest_all summaries_all fasta_summary_all interval_smoke_all compare_simrad_all compare_digital_rads_all \
	  --config radigest="$(RADIGEST)" \
	           radigest_screen_pairs="$(RADIGEST_SCREEN_PAIRS)" \
	           radigest_rank_pairs="$(RADIGEST_RANK_PAIRS)" \
	           threads=1

clean:
	rm -rf results/raw/* results/processed/* benchmark/time/* benchmark/memory/* benchmark/logs/*
	touch results/raw/.gitkeep results/processed/.gitkeep benchmark/time/.gitkeep benchmark/memory/.gitkeep benchmark/logs/.gitkeep

interval-smoke:
	$(call smk,interval_smoke_all)

compare-simrad:
	$(call smk,compare_simrad_all)

compare-digital-rads:
	$(call smk,compare_digital_rads_all)
