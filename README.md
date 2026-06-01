# radigest benchmarking and comparison repository

This repository contains reproducible validation, matched-task comparison, and benchmarking workflows for the associated radigest manuscript.

The repository is designed to make transparent:

1. synthetic digest validation cases;
2. matched-task comparisons against related RADseq/RRS design tools where functionality overlaps;
3. runtime and memory benchmarks under documented conditions;
4. command templates, environment metadata, and output summaries used in the manuscript;
5. artifact contracts linking manuscript tables and claims to upstream outputs.

Large reference genomes and empirical sequencing files are not stored directly in Git. Download commands, accessions, checksums, and derived summaries are recorded instead.

Benchmark categories are declared in `config/benchmark_categories.tsv` and can
be inspected with:

```bash
make benchmark-categories
```

Use category targets such as `benchmark-validation`, `benchmark-comparators`,
`benchmark-performance`, and `benchmark-nonempirical` when rerunning analyses by
claim family.

Artifact and claim contracts are declared in `config/artifacts.tsv` and can be checked with `make check-artifacts`.

Comparator semantics are declared in `config/comparators.tsv` and can be checked with `make check-comparator-registry`.

Scenario defaults are declared in `config/scenarios/nonempirical.tsv` and can be inspected with `make scenarios`.
