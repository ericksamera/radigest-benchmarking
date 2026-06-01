# Reviewer rerun

The intended nonempirical reviewer path is:

```bash
mamba env create -f workflow/envs/driver.yml
mamba activate radigest-benchmark-driver
make reviewer-nonempirical THREADS=4 RADIGEST=/path/to/radigest
make audit
```

At Stage 2, the concrete executable target is the synthetic-validation smoke run:

```bash
make smoke RADIGEST=/path/to/radigest
make references THREADS=4
```

This writes the validation summary and manuscript-facing synthetic-validation table. Later stages will add references, comparators, performance workflows, empirical recovery, and full audit products.

Stage 3 adds public reference acquisition. The reference step requires network access and the NCBI Datasets CLI supplied by `workflow/envs/reference.yml`.
