THREADS ?= 4
SNAKEMAKE ?= snakemake
SNAKEFILE ?= workflow/Snakefile
SNAKEMAKE_CONDA_PREFIX ?= .snakemake/conda
SNAKEMAKE_CONDA_ARGS ?= --use-conda --conda-prefix $(SNAKEMAKE_CONDA_PREFIX)

.PHONY: help smoke reviewer-nonempirical reviewer-empirical reviewer-all references manuscript audit check check-manifests

help:
	@printf '%s\n' \
	  'Targets:' \
	  '  make check' \
	  '  make smoke' \
	  '  make references' \
	  '  make reviewer-nonempirical THREADS=4' \
	  '  make reviewer-empirical THREADS=4' \
	  '  make reviewer-all THREADS=4' \
	  '  make manuscript' \
	  '  make audit'

smoke:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 $(SNAKEMAKE_CONDA_ARGS) smoke_all

references:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) references_all

reviewer-nonempirical:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) reviewer_nonempirical_all

reviewer-empirical:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) reviewer_empirical_all

reviewer-all:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) reviewer_all

manuscript:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores $(THREADS) $(SNAKEMAKE_CONDA_ARGS) manuscript_all

audit:
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 $(SNAKEMAKE_CONDA_ARGS) audit_all

check-manifests:
	python3 scripts/core/check_manifests.py

check: check-manifests
	$(SNAKEMAKE) -s $(SNAKEFILE) --cores 1 -n smoke_all
