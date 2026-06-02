THREADS ?= 4
RADIGEST ?= radigest
ifeq ($(dir $(RADIGEST)),./)
RADIGEST_SCREEN_PAIRS_CACHED ?= radigest-screen-pairs-cached
else
RADIGEST_SCREEN_PAIRS_CACHED ?= $(dir $(RADIGEST))radigest-screen-pairs-cached
endif
DDGRADER_REPO ?= external/ddRadSeqWebTool
SNAKEMAKE ?= snakemake
SNAKEFILE ?= workflow/Snakefile
SNAKEMAKE_CONDA_PREFIX ?= .snakemake/conda
SNAKEMAKE_CONDA_ARGS ?= --use-conda --conda-prefix $(SNAKEMAKE_CONDA_PREFIX)
SNAKEMAKE_CONFIG_ARGS ?= --config radigest="$(RADIGEST)" radigest_screen_pairs_cached="$(RADIGEST_SCREEN_PAIRS_CACHED)" ddgrader_repo="$(DDGRADER_REPO)"
PAIR_SCREEN_BENCHMARK_RESOURCE_ARGS ?= --resources pair_screen_benchmark=1
MATCHED_TOOL_BENCHMARK_RESOURCE_ARGS ?= --resources matched_tool_benchmark=1
PERFORMANCE_BENCHMARK_RESOURCE_ARGS ?= --resources pair_screen_benchmark=1 matched_tool_benchmark=1

.PHONY: help smoke comparator-smoke comparator-small-yeast references references-large comparators performance-input-format performance-screening-speed performance-thread-scaling performance-pair-screen-scaling performance-large-genome performance-matched-tools performance reviewer-nonempirical reviewer-empirical reviewer-all manuscript audit check check-manifests install-digital-rads install-ddradseqtools install-simrad install-ddgrader

help:
	@printf '%s\n' \
	  'Targets:' \
	  '  make check' \
	  '  make smoke RADIGEST=/path/to/radigest' \
	  '  make references' \
	  '  make references-large' \
	  '  make install-digital-rads' \
	  '  make install-ddradseqtools' \
	  '  make install-simrad' \
	  '  make install-ddgrader' \
	  '  make comparator-smoke RADIGEST=/path/to/radigest' \
	  '  make comparator-small-yeast RADIGEST=/path/to/radigest' \
	  '  make comparators RADIGEST=/path/to/radigest' \
	  '  make performance-input-format RADIGEST=/path/to/radigest' \
	  '  make performance-screening-speed RADIGEST=/path/to/radigest' \
	  '    # Uses RADIGEST_SCREEN_PAIRS_CACHED=/path/to/radigest-screen-pairs-cached when set.' \
	  '  make performance-thread-scaling THREADS=4 RADIGEST=/path/to/radigest' \
	  '  make performance-pair-screen-scaling THREADS=4 RADIGEST=/path/to/radigest' \
	  '  make performance-large-genome THREADS=4 RADIGEST=/path/to/radigest' \
	  '  make performance-matched-tools THREADS=4 RADIGEST=/path/to/radigest' \
	  '    # Uses RADIGEST_SCREEN_PAIRS_CACHED=/path/to/radigest-screen-pairs-cached when set.' \
	  '  make performance RADIGEST=/path/to/radigest' \
	  '  make reviewer-nonempirical THREADS=4' \
	  '  make reviewer-empirical THREADS=4' \
	  '  make reviewer-all THREADS=4' \
	  '  make manuscript' \
	  '  make audit'

smoke:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 $(SNAKEMAKE_CONDA_ARGS) smoke_all $(SNAKEMAKE_CONFIG_ARGS)

references:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) references_all $(SNAKEMAKE_CONFIG_ARGS)

references-large:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) references_optional_all $(SNAKEMAKE_CONFIG_ARGS)

comparator-smoke:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) comparator_smoke_all $(SNAKEMAKE_CONFIG_ARGS)

comparator-small-yeast:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) comparator_small_yeast_all $(SNAKEMAKE_CONFIG_ARGS)

comparators:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) comparators_all $(SNAKEMAKE_CONFIG_ARGS)

performance-input-format:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) performance_input_format_all $(SNAKEMAKE_CONFIG_ARGS)

performance-screening-speed:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) performance_screening_speed_all $(SNAKEMAKE_CONFIG_ARGS)

performance-thread-scaling:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) performance_thread_scaling_all $(SNAKEMAKE_CONFIG_ARGS)

performance-pair-screen-scaling:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) performance_pair_screen_scaling_all $(SNAKEMAKE_CONFIG_ARGS) $(PAIR_SCREEN_BENCHMARK_RESOURCE_ARGS)

performance-large-genome:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) performance_large_genome_all $(SNAKEMAKE_CONFIG_ARGS)

performance-matched-tools:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) performance_matched_tools_all $(SNAKEMAKE_CONFIG_ARGS) $(MATCHED_TOOL_BENCHMARK_RESOURCE_ARGS)

performance:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) performance_all $(SNAKEMAKE_CONFIG_ARGS) $(PERFORMANCE_BENCHMARK_RESOURCE_ARGS)

install-digital-rads:
	bash scripts/comparators/install_digital_rads.sh

install-ddradseqtools:
	bash scripts/comparators/install_ddradseqtools.sh

install-simrad:
	Rscript scripts/comparators/install_simrad_archive.R

install-ddgrader:
	bash scripts/comparators/install_ddgrader.sh

reviewer-nonempirical:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) reviewer_nonempirical_all $(SNAKEMAKE_CONFIG_ARGS)

reviewer-empirical:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) reviewer_empirical_all $(SNAKEMAKE_CONFIG_ARGS)

reviewer-all:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) reviewer_all $(SNAKEMAKE_CONFIG_ARGS)

manuscript:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) manuscript_all $(SNAKEMAKE_CONFIG_ARGS)

audit:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 $(SNAKEMAKE_CONDA_ARGS) audit_all $(SNAKEMAKE_CONFIG_ARGS)

check-manifests:
	python3 scripts/core/check_manifests.py
	python3 scripts/core/check_noncoordinate_comparators.py
	python3 scripts/core/check_performance_cases.py
	python3 scripts/core/check_screening_speed_cases.py
	python3 scripts/core/check_thread_scaling_cases.py
	python3 scripts/core/check_pair_screen_scaling_cases.py
	python3 scripts/core/check_large_genome_cases.py
	python3 scripts/core/check_matched_tool_timing_cases.py

check: check-manifests
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 -n smoke_all $(SNAKEMAKE_CONFIG_ARGS)
