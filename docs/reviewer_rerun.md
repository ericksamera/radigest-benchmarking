# Reviewer rerun

The intended nonempirical reviewer path is:

```bash
mamba env create -f workflow/envs/driver.yml
mamba activate radigest-benchmark-driver
bash scripts/comparators/install_digital_rads.sh
bash scripts/comparators/install_ddradseqtools.sh
make reviewer-nonempirical THREADS=4 RADIGEST=/path/to/radigest
make audit
```

At Stage 4, the concrete executable pieces are:

```bash
make smoke RADIGEST=/path/to/radigest
make references THREADS=4
make comparators THREADS=4 RADIGEST=/path/to/radigest
```

Stage 4 adds exact interval-equivalence comparator workflows for Digital_RADs.py and DDRADSEQTOOLS `rsitesearch.py`. Later stages will add performance workflows, empirical recovery, and full audit products.
