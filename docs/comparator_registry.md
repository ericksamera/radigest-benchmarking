# Comparator registry

Comparator semantics are declared in `config/comparators.tsv`. Runnable interval-equivalence cases are declared in `config/comparator_cases.tsv`. Runnable lower-resolution cases are declared in `config/noncoordinate_comparator_cases.tsv`.

The comparator claim boundary is:

```text
tool                    comparison_level       allowed_claim
Digital_RADs.py          normalized_interval    coordinate_equivalence
DDRADSEQTOOLS            normalized_interval    coordinate_equivalence
SimRAD                   count_only             count_level_digest
ddgRADer backend         binned_screening        screening_throughput
```

Digital_RADs.py and DDRADSEQTOOLS are normalized to zero-based half-open interval sets before comparison. These are the only Stage 4 comparators that support coordinate-equivalence claims.

SimRAD validates aggregate retained-fragment count agreement only. Retained-base totals, if reported, are trace metadata and are not enforced. ddgRADer validates binned fragment-screening behavior only. Neither supports same-fragment or coordinate-equivalence claims in this repository.

Stage 4c adds two comparator coverage targets:

```bash
make comparator-smoke RADIGEST=/path/to/radigest
make comparator-small-yeast THREADS=4 RADIGEST=/path/to/radigest
```

The smoke matrix uses the same tracked FASTA, enzyme pair, and size window for all comparator tools, but each tool keeps its own claim boundary:

```text
matrix              dataset                  condition  assertion
comparator_smoke    comparator_smoke_single  D1         interval/count/bin depending on tool
small_yeast         small_yeast_s288c_plain  B1         interval/count/bin depending on tool
```

The coverage matrix is written to:

```text
results/comparators/comparator_case_matrix.tsv
```

Install or update comparator tools with:

```bash
make install-comparators
```

This target runs the installer scripts through Snakemake conda environments. The individual targets remain available for focused setup or debugging:

```bash
make install-digital-rads
make install-ddradseqtools
make install-simrad
make install-ddgrader
```

The required executable paths after installation are:

```text
external/Digital_RADs/Digital_RADs.py
external/ddRADseqTools/Package/rsitesearch.py
external/ddRADseqTools/Package/restrictionsites.txt
external/ddRadSeqWebTool/backend/service/DigestSequence.py
```

SimRAD is an R package, not an external checkout. `make install-simrad` now runs the archived SimRAD installer inside `workflow/envs/simrad.yml`, so the active shell no longer needs `seqinr`, `Biostrings`, `ShortRead`, or `zlibbioc` preinstalled.

The manuscript-facing comparator tables are:

```text
results/manuscript/tables/table_03_interval_comparisons.tsv
results/manuscript/tables/table_03_comparator_semantics.tsv
```
