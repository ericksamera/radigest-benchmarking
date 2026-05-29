SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

RADIGEST ?= radigest
RADIGEST_SCREEN_PAIRS ?= radigest-screen-pairs
RADIGEST_RANK_PAIRS ?= radigest-rank-pairs

THREADS ?= 4
RUNS ?= 5

REF ?= data/synthetic/synthetic_validation.fa
REF_SMALL ?= data/reference/yeast.fa.gz
REF_MODERATE ?= data/reference/moderate.fa.gz

.PHONY: help env synthetic validate-radigest benchmark-radigest screen-pairs compare-simrad compare-digital-rads compare-ddradseqtools summarize figures all clean

help:
	@echo "Targets:"
	@echo "  env                    Capture hardware/software metadata"
	@echo "  synthetic              Summarize committed synthetic FASTA"
	@echo "  validate-radigest      Run synthetic interval validation"
	@echo "  benchmark-radigest     Lightweight radigest benchmark; override REF for real genomes"
	@echo "  screen-pairs           Run enzyme-pair screen; override REF for real genomes"
	@echo "  compare-simrad         Placeholder for SimRAD matched-task comparison"
	@echo "  compare-digital-rads   Placeholder for Digital_RADs.py comparison"
	@echo "  compare-ddradseqtools  Placeholder for DDRADSEQTOOLS rsitesearch comparison"
	@echo "  summarize              Build processed TSV summaries"
	@echo "  figures                Generate manuscript figures when inputs exist"
	@echo "  clean                  Remove generated benchmark outputs"

env:
	./scripts/capture_environment.sh

synthetic:
	@echo "Synthetic FASTA: data/synthetic/synthetic_validation.fa"
	@seqkit stats data/synthetic/synthetic_validation.fa || true

validate-radigest:
	mkdir -p results/raw/synthetic results/processed
	python3 scripts/validate_synthetic.py \
	  --radigest "$(RADIGEST)" \
	  --fasta data/synthetic/synthetic_validation.fa \
	  --expected config/synthetic_expected.tsv \
	  --out-dir results/raw/synthetic \
	  --summary results/processed/synthetic_validation_results.tsv

benchmark-radigest:
	mkdir -p benchmark/time benchmark/memory benchmark/logs results/raw/radigest results/tables
	hyperfine --warmup 1 --runs $(RUNS) \
	  --export-json benchmark/time/radigest_json.json \
	  '$(RADIGEST) -fasta $(REF) -enzymes EcoRI,MseI -min 1 -max 1000 -threads $(THREADS) -json results/raw/radigest/benchmark__EcoRI_MseI__json.json'
	for i in $$(seq 1 $(RUNS)); do \
	  /usr/bin/time -v -o benchmark/memory/radigest_json_run$${i}.time \
	    $(RADIGEST) -fasta $(REF) -enzymes EcoRI,MseI -min 1 -max 1000 -threads $(THREADS) \
	    -json results/raw/radigest/benchmark__EcoRI_MseI__json_run$${i}.json ; \
	done

screen-pairs:
	mkdir -p results/raw/pair_screen results/tables benchmark/logs
	$(RADIGEST_SCREEN_PAIRS) \
	  --fasta $(REF) \
	  --enzymes config/candidate_enzymes.txt \
	  --min 300 \
	  --max 600 \
	  --score-min 1 \
	  --score-max 2000 \
	  --size-model hard \
	  --jobs 2 \
	  --radigest-threads 2 \
	  --out-dir results/raw/pair_screen
	$(RADIGEST_RANK_PAIRS) 'results/raw/pair_screen/json/*.json' \
	  --fasta $(REF) \
	  --objective weighted-bases \
	  --out results/tables/ranked_pairs.tsv

compare-simrad:
	@echo "TO_BE_FILLED: run scripts/run_simrad_ddrad.R after SimRAD is installed and reference FASTA is selected."

compare-digital-rads:
	@echo "TO_BE_FILLED: run scripts/run_digital_rads.sh after Digital_RADs.py path and coordinate convention are verified."

compare-ddradseqtools:
	@echo "TO_BE_FILLED: run scripts/run_ddradseqtools_rsitesearch.sh after DDRADSEQTOOLS config syntax is verified."

summarize:
	mkdir -p results/tables
	python3 scripts/summarize_radigest_json.py results/raw/radigest/*.json > results/tables/radigest_json_summary.tsv || true
	python3 scripts/summarize_time_v.py benchmark/memory/*.time > results/tables/radigest_memory_summary.tsv || true

figures:
	@echo "TO_BE_FILLED: add scripts/make_figures.py after processed summary schemas stabilize."

all: env validate-radigest benchmark-radigest summarize

clean:
	rm -rf results/raw/* results/processed/* benchmark/time/* benchmark/memory/* benchmark/logs/*
	touch results/raw/.gitkeep results/processed/.gitkeep benchmark/time/.gitkeep benchmark/memory/.gitkeep benchmark/logs/.gitkeep
