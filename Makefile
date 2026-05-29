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

.PHONY: help env synthetic validate-radigest benchmark-radigest screen-pairs summarize figures all dry-run dag clean

help:
	@echo "Targets:"
	@echo "  env                    Capture hardware/software metadata"
	@echo "  synthetic              Show synthetic FASTA status"
	@echo "  validate-radigest      Run synthetic interval validation via Snakemake"
	@echo "  benchmark-radigest     Run configured radigest output-mode benchmarks"
	@echo "  screen-pairs           Run configured enzyme-pair screen"
	@echo "  summarize              Generate configured summary tables"
	@echo "  all                    Run lightweight default workflow"
	@echo "  dry-run                Show planned lightweight workflow"
	@echo "  dag                    Write workflow DAG for configured benchmark"
	@echo "  clean                  Remove generated benchmark outputs"

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

clean:
	rm -rf results/raw/* results/processed/* benchmark/time/* benchmark/memory/* benchmark/logs/*
	touch results/raw/.gitkeep results/processed/.gitkeep benchmark/time/.gitkeep benchmark/memory/.gitkeep benchmark/logs/.gitkeep
