# Reviewer rerun

The intended nonempirical reviewer path is:

```bash
mamba env create -f workflow/envs/driver.yml
mamba activate radigest-benchmark-driver
make install-digital-rads
make install-ddradseqtools
make install-ddgrader
make reviewer-nonempirical THREADS=4 RADIGEST=/path/to/radigest
make audit
```

At Stage 4b, the concrete executable pieces are:

```bash
make smoke RADIGEST=/path/to/radigest
make references THREADS=4
make comparators THREADS=4 RADIGEST=/path/to/radigest
```

Stage 4b adds explicit lower-resolution comparator checks for SimRAD and ddgRADer. SimRAD is count-level only; ddgRADer is binned-screening only. Coordinate-equivalence claims remain limited to Digital_RADs.py and DDRADSEQTOOLS normalized interval outputs.

Later stages will add performance workflows, empirical recovery, and full audit products.
