SHELL := /usr/bin/env bash

RADIGEST ?= radigest
THREADS ?= 4
RUNS ?= 5

REF_SMALL ?= data/reference/yeast.fa.gz
REF_MODERATE ?= data/reference/moderate.fa.gz

.PHONY: env synthetic validate-radigest benchmark-radigest screen-pairs summarize clean

env:
	./scripts/capture_environment.sh

synthetic:
	@echo "Synthetic FASTA: data/synthetic/synthetic_validation.fa"
	@seqkit stats data/synthetic/synthetic_validation.fa || true

validate-radigest:
	mkdir -p results/raw/synthetic results/processed/synthetic
	$(RADIGEST) -fasta data/synthetic/synthetic_validation.fa -enzymes EcoRI,MseI -min 1 -max 100 \
	  -threads 1 \
	  -fragments-tsv results/raw/synthetic/ecori_msei.tsv \
	  -gff results/raw/synthetic/ecori_msei.gff3 \
	  -json results/raw/synthetic/ecori_msei.json
	jq '.' results/raw/synthetic/ecori_msei.json > results/processed/synthetic/ecori_msei.pretty.json

benchmark-radigest:
	mkdir -p benchmark/time benchmark/memory results/raw/radigest
	hyperfine --warmup 1 --runs $(RUNS) \
	  --export-json benchmark/time/radigest_json_small.json \
	  '$(RADIGEST) -fasta $(REF_SMALL) -enzymes EcoRI,MseI -min 100 -max 300 -threads $(THREADS) -json results/raw/radigest/small_ecori_msei.json'
	for i in $$(seq 1 $(RUNS)); do \
	  /usr/bin/time -v -o benchmark/memory/radigest_json_small_run$${i}.time \
	    $(RADIGEST) -fasta $(REF_SMALL) -enzymes EcoRI,MseI -min 100 -max 300 -threads $(THREADS) \
	    -json results/raw/radigest/small_ecori_msei_run$${i}.json ; \
	done

screen-pairs:
	mkdir -p results/raw/pair_screen
	radigest-screen-pairs \
	  --fasta $(REF_SMALL) \
	  --enzymes config/candidate_enzymes.txt \
	  --min 300 \
	  --max 600 \
	  --score-min 1 \
	  --score-max 2000 \
	  --size-model hard \
	  --jobs 2 \
	  --radigest-threads 2 \
	  --out-dir results/raw/pair_screen
	radigest-rank-pairs 'results/raw/pair_screen/json/*.json' \
	  --fasta $(REF_SMALL) \
	  --objective weighted-bases \
	  --out results/tables/ranked_pairs.tsv

summarize:
	python3 scripts/summarize_radigest_json.py results/raw/radigest/*.json > results/tables/radigest_json_summary.tsv || true
	python3 scripts/summarize_time_v.py benchmark/memory/*.time > results/tables/radigest_memory_summary.tsv || true

clean:
	rm -rf results/raw/* results/processed/* benchmark/time/* benchmark/memory/* benchmark/logs/*
