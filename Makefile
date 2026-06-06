THREADS ?= 4
LOCAL_BIN ?= .local/bin
RADIGEST_SRC ?= external/radigest
RADIGEST ?= $(LOCAL_BIN)/radigest
RADIGEST_REPO ?= https://github.com/ericksamera/radigest.git
RADIGEST_REF ?= main
ifeq ($(dir $(RADIGEST)),./)
RADIGEST_SCREEN_PAIRS_CACHED ?= radigest-screen-pairs-cached
else
RADIGEST_SCREEN_PAIRS_CACHED ?= $(dir $(RADIGEST))radigest-screen-pairs-cached
endif
ifeq ($(abspath $(RADIGEST)),$(abspath $(LOCAL_BIN)/radigest))
RADIGEST_BUILD_PREREQ ?= install-radigest
else
RADIGEST_BUILD_PREREQ ?=
endif
DDGRADER_REPO ?= external/ddRadSeqWebTool
SNAKEMAKE ?= snakemake
SNAKEFILE ?= workflow/Snakefile
SNAKEMAKE_CONDA_PREFIX ?= .snakemake/conda
SNAKEMAKE_CONDA_ARGS ?= --use-conda --conda-prefix $(SNAKEMAKE_CONDA_PREFIX)
SNAKEMAKE_CONFIG_ARGS ?= --config radigest="$(RADIGEST)" radigest_screen_pairs_cached="$(RADIGEST_SCREEN_PAIRS_CACHED)" ddgrader_repo="$(DDGRADER_REPO)" radigest_repo="$(RADIGEST_REPO)" radigest_ref="$(RADIGEST_REF)" radigest_source_dir="$(RADIGEST_SRC)" local_bin_dir="$(LOCAL_BIN)"
PAIR_SCREEN_BENCHMARK_RESOURCE_ARGS ?= --resources pair_screen_benchmark=1
MATCHED_TOOL_BENCHMARK_RESOURCE_ARGS ?= --resources matched_tool_benchmark=1
PERFORMANCE_BENCHMARK_RESOURCE_ARGS ?= --resources pair_screen_benchmark=1 matched_tool_benchmark=1
COMPARATOR_INSTALL_MARKERS ?= .local/comparators/digital_rads.ready .local/comparators/ddradseqtools.ready .local/comparators/simrad.ready .local/comparators/ddgrader.ready
EMPIRICAL_SOCKEYE_OUTPUTS ?= results/empirical/sockeye_ecori_msei/figures/size_model_overlay.pdf results/empirical/sockeye_ecori_msei/size_model_grid.tsv results/empirical/sockeye_ecori_msei/best_size_model.tsv
EMPIRICAL_TRICHODERMA_OUTPUTS ?= results/empirical/trichoderma_sphi_mspi/figures/size_model_overlay.pdf results/empirical/trichoderma_sphi_mspi/size_model_grid.tsv results/empirical/trichoderma_sphi_mspi/best_size_model.tsv
EMPIRICAL_ANOPHELES_REFERENCE_OUTPUTS ?= data/reference/anopheles_darlingi_gcf943734745.fa.gz data/reference/anopheles_darlingi_gcf943734745.fa
EMPIRICAL_ANOPHELES_OUTPUTS ?= results/empirical/anopheles_ecori_msei/figures/size_model_overlay.pdf results/empirical/anopheles_ecori_msei/size_model_grid.tsv results/empirical/anopheles_ecori_msei/best_size_model.tsv

.PHONY: help install-radigest build-radigest radigest-build show-radigest smoke comparator-smoke comparator-small-yeast references install-comparators install-all comparators performance-input-format performance-screening-speed performance-thread-scaling performance-pair-screen-scaling performance-matched-tools performance figures empirical empirical-sockeye empirical-trichoderma empirical-anopheles-reference empirical-anopheles empirical-references empirical-tlens empirical-predictions empirical-curves empirical-model-grid empirical-model-fit-ranking empirical-figures empirical-check reviewer-nonempirical reviewer-empirical reviewer-all manuscript audit check check-manifests install-digital-rads install-ddradseqtools install-simrad install-ddgrader

help:
	@printf '%s\n' \
	  'Targets:' \
	  '  make check' \
	  '  make install-radigest' \
	  '  make show-radigest' \
	  '  make smoke' \
	  '  make references' \
	  '  make install-comparators' \
	  '  make install-all' \
	  '  make install-digital-rads' \
	  '  make install-ddradseqtools' \
	  '  make install-simrad' \
	  '  make install-ddgrader' \
	  '  make comparator-smoke' \
	  '  make comparator-small-yeast' \
	  '  make comparators' \
	  '  make performance-input-format' \
	  '  make performance-screening-speed' \
	  '    # Uses RADIGEST_SCREEN_PAIRS_CACHED=/path/to/radigest-screen-pairs-cached when set.' \
	  '  make performance-thread-scaling THREADS=4' \
	  '  make performance-pair-screen-scaling THREADS=4' \
	  '  make performance-matched-tools THREADS=4' \
	  '    # Uses RADIGEST_SCREEN_PAIRS_CACHED=/path/to/radigest-screen-pairs-cached when set.' \
	  '  make performance THREADS=8' \
	  '  make figures THREADS=4' \
	  '  make empirical-check' \
	  '  make empirical-sockeye THREADS=4' \
	  '  make empirical-trichoderma THREADS=4' \
	  '  make empirical-anopheles-reference THREADS=4' \
	  '  make empirical-anopheles THREADS=4' \
	  '  make empirical-references THREADS=4' \
	  '  make empirical-tlens THREADS=4' \
	  '  make empirical-predictions THREADS=4' \
	  '  make empirical-curves THREADS=4' \
	  '  make empirical-model-grid THREADS=4' \
	  '  make empirical-model-fit-ranking THREADS=4' \
	  '  make empirical-figures THREADS=4' \
	  '  make empirical THREADS=4' \
	  '  make reviewer-nonempirical THREADS=4' \
	  '  make reviewer-empirical THREADS=4' \
	  '  make reviewer-all THREADS=4' \
	  '  make manuscript' \
	  '  make audit'

install-radigest build-radigest radigest-build:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) radigest_build_all $(SNAKEMAKE_CONFIG_ARGS)

show-radigest:
	@printf 'RADIGEST=%s\n' "$(RADIGEST)"
	@printf 'RADIGEST_SCREEN_PAIRS_CACHED=%s\n' "$(RADIGEST_SCREEN_PAIRS_CACHED)"
	@printf 'RADIGEST_REPO=%s\n' "$(RADIGEST_REPO)"
	@printf 'RADIGEST_REF=%s\n' "$(RADIGEST_REF)"
	@if [ -x "$(RADIGEST)" ]; then "$(RADIGEST)" --version 2>/dev/null || "$(RADIGEST)" -version 2>/dev/null || true; else printf 'radigest binary missing; run make install-radigest\n'; fi
	@if [ -x "$(RADIGEST_SCREEN_PAIRS_CACHED)" ]; then "$(RADIGEST_SCREEN_PAIRS_CACHED)" --version 2>/dev/null || "$(RADIGEST_SCREEN_PAIRS_CACHED)" -version 2>/dev/null || true; else printf 'cached screening binary missing; run make install-radigest\n'; fi

smoke: $(RADIGEST_BUILD_PREREQ)
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 $(SNAKEMAKE_CONDA_ARGS) smoke_all $(SNAKEMAKE_CONFIG_ARGS)

references:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) references_all $(SNAKEMAKE_CONFIG_ARGS)

install-comparators:
	rm -f $(COMPARATOR_INSTALL_MARKERS)
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) comparator_tools_all $(SNAKEMAKE_CONFIG_ARGS)

install-all: $(RADIGEST_BUILD_PREREQ) install-comparators

comparator-smoke: $(RADIGEST_BUILD_PREREQ)
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) comparator_smoke_all $(SNAKEMAKE_CONFIG_ARGS)

comparator-small-yeast: $(RADIGEST_BUILD_PREREQ)
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) comparator_small_yeast_all $(SNAKEMAKE_CONFIG_ARGS)

comparators: $(RADIGEST_BUILD_PREREQ)
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) comparators_all $(SNAKEMAKE_CONFIG_ARGS)

performance-input-format: $(RADIGEST_BUILD_PREREQ)
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) performance_input_format_all $(SNAKEMAKE_CONFIG_ARGS)

performance-screening-speed: $(RADIGEST_BUILD_PREREQ)
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) performance_screening_speed_all $(SNAKEMAKE_CONFIG_ARGS)

performance-thread-scaling: $(RADIGEST_BUILD_PREREQ)
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) performance_thread_scaling_all $(SNAKEMAKE_CONFIG_ARGS)

performance-pair-screen-scaling: $(RADIGEST_BUILD_PREREQ)
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) performance_pair_screen_scaling_all $(SNAKEMAKE_CONFIG_ARGS) $(PAIR_SCREEN_BENCHMARK_RESOURCE_ARGS)

performance-matched-tools: $(RADIGEST_BUILD_PREREQ)
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) performance_matched_tools_all $(SNAKEMAKE_CONFIG_ARGS) $(MATCHED_TOOL_BENCHMARK_RESOURCE_ARGS)

performance: $(RADIGEST_BUILD_PREREQ)
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) performance_all $(SNAKEMAKE_CONFIG_ARGS) $(PERFORMANCE_BENCHMARK_RESOURCE_ARGS)

figures: $(RADIGEST_BUILD_PREREQ)
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) manuscript_figures_all $(SNAKEMAKE_CONFIG_ARGS) $(PERFORMANCE_BENCHMARK_RESOURCE_ARGS)

install-digital-rads:
	rm -f .local/comparators/digital_rads.ready
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) comparator_digital_rads_install $(SNAKEMAKE_CONFIG_ARGS)

install-ddradseqtools:
	rm -f .local/comparators/ddradseqtools.ready
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) comparator_ddradseqtools_install $(SNAKEMAKE_CONFIG_ARGS)

install-simrad:
	rm -f .local/comparators/simrad.ready
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) comparator_simrad_install $(SNAKEMAKE_CONFIG_ARGS)

install-ddgrader:
	rm -f .local/comparators/ddgrader.ready
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) comparator_ddgrader_install $(SNAKEMAKE_CONFIG_ARGS)

reviewer-nonempirical: install-all
	$(MAKE) check
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) reviewer_nonempirical_all manuscript_figures_all $(SNAKEMAKE_CONFIG_ARGS) $(PERFORMANCE_BENCHMARK_RESOURCE_ARGS)

empirical-check:
	python3 scripts/core/check_empirical_libraries.py

empirical-references:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) empirical_references_all $(SNAKEMAKE_CONFIG_ARGS)

empirical-tlens:
	$(MAKE) empirical-check
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) empirical_tlens_all $(SNAKEMAKE_CONFIG_ARGS)

empirical-predictions: $(RADIGEST_BUILD_PREREQ)
	$(MAKE) empirical-check
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) empirical_predictions_all $(SNAKEMAKE_CONFIG_ARGS)

empirical-curves: $(RADIGEST_BUILD_PREREQ)
	$(MAKE) empirical-check
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) empirical_curves_all $(SNAKEMAKE_CONFIG_ARGS)

empirical-model-grid: $(RADIGEST_BUILD_PREREQ)
	$(MAKE) empirical-check
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) empirical_model_grid_all $(SNAKEMAKE_CONFIG_ARGS)

empirical-model-fit-ranking: $(RADIGEST_BUILD_PREREQ)
	$(MAKE) empirical-check
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) empirical_model_fit_ranking_all $(SNAKEMAKE_CONFIG_ARGS)

empirical-figures: $(RADIGEST_BUILD_PREREQ)
	$(MAKE) empirical-check
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) empirical_figures_all $(SNAKEMAKE_CONFIG_ARGS)

empirical: $(RADIGEST_BUILD_PREREQ)
	$(MAKE) empirical-check
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) empirical_all $(SNAKEMAKE_CONFIG_ARGS)

empirical-sockeye: $(RADIGEST_BUILD_PREREQ)
	python3 scripts/core/check_empirical_libraries.py --require-enabled sockeye_ecori_msei
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) $(EMPIRICAL_SOCKEYE_OUTPUTS) $(SNAKEMAKE_CONFIG_ARGS)

empirical-trichoderma: $(RADIGEST_BUILD_PREREQ)
	python3 scripts/core/check_empirical_libraries.py --require-enabled trichoderma_sphi_mspi
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) $(EMPIRICAL_TRICHODERMA_OUTPUTS) $(SNAKEMAKE_CONFIG_ARGS)

empirical-anopheles-reference:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) $(EMPIRICAL_ANOPHELES_REFERENCE_OUTPUTS) $(SNAKEMAKE_CONFIG_ARGS)

empirical-anopheles: $(RADIGEST_BUILD_PREREQ) empirical-anopheles-reference
	python3 scripts/core/check_empirical_libraries.py --require-enabled anopheles_ecori_msei
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) $(EMPIRICAL_ANOPHELES_OUTPUTS) $(SNAKEMAKE_CONFIG_ARGS)

reviewer-empirical: $(RADIGEST_BUILD_PREREQ)
	$(MAKE) empirical-check
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) reviewer_empirical_all $(SNAKEMAKE_CONFIG_ARGS)

reviewer-all: install-all
	$(MAKE) check
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) reviewer_all manuscript_figures_all $(SNAKEMAKE_CONFIG_ARGS) $(PERFORMANCE_BENCHMARK_RESOURCE_ARGS)

manuscript: $(RADIGEST_BUILD_PREREQ)
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) manuscript_all $(SNAKEMAKE_CONFIG_ARGS) $(PERFORMANCE_BENCHMARK_RESOURCE_ARGS)

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
	python3 scripts/core/check_empirical_libraries.py
	python3 scripts/core/check_artifacts.py

check: check-manifests
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 -n smoke_all $(SNAKEMAKE_CONFIG_ARGS)
