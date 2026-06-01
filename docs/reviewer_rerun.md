# Reviewer rerun

The intended nonempirical reviewer path is:

```bash
mamba env create -f workflow/envs/driver.yml
mamba activate radigest-benchmark-driver
make reviewer-nonempirical THREADS=4
make audit
```

At Stage 0 these targets are placeholders that verify repository contracts only. They will become executable benchmark targets as rules are ported.
