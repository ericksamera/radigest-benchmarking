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

SimRAD validates aggregate retained-fragment and retained-base agreement only. ddgRADer validates binned fragment-screening behavior only. Neither supports same-fragment or coordinate-equivalence claims in this repository.

Install or update external checkouts with:

```bash
make install-digital-rads
make install-ddradseqtools
make install-ddgrader
```

The required executable paths after installation are:

```text
external/Digital_RADs/Digital_RADs.py
external/ddRADseqTools/Package/rsitesearch.py
external/ddRADseqTools/Package/restrictionsites.txt
external/ddRadSeqWebTool/backend/service/DigestSequence.py
```

SimRAD is an R package, not an external checkout. Snakemake installs it into `workflow/envs/simrad.yml` via `workflow/envs/simrad.post-deploy.sh`. For manual testing in an active R environment, run:

```bash
make install-simrad
```

The manuscript-facing semantics table is:

```text
results/manuscript/tables/table_03_comparator_semantics.tsv
```
