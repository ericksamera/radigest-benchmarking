# Claims and limits

Manuscript claims are governed by `config/artifacts.tsv` and comparator semantics are governed by `config/comparators.tsv`.

Stage 4 comparator claim limits are explicit:

```text
Digital_RADs.py      coordinate-equivalence after interval normalization
DDRADSEQTOOLS        coordinate-equivalence after interval normalization
SimRAD               aggregate count-level digest sanity only
ddgRADer backend     binned fragment-screening behavior only
```

SimRAD and ddgRADer outputs must not be described as same-fragment or coordinate-equivalence validation outputs unless a future workflow normalizes them to the same interval model.

A claim is release-required only when `required_for_release` is `true`. Sockeye empirical depth validation is release-required for the publication reviewer path; the BAM/BAI inputs remain private and must be supplied locally before `make reviewer-all`, unless the Sockeye SRA/archived alignment workflow replaces the local drop-off contract.

Public empirical SRA rows support external size-selection recovery claims, not depth-validation claims, unless a matching depth-validation case is explicitly declared. The Anopheles EcoRI-MseI and Rhododendron DpnII-MspI examples may support qualitative and quantitative insert-size recovery claims such as observed TLEN distributions, Jensen-Shannon divergence, median insert-size agreement, and observed versus predicted in-window fraction. The manuscript Figure 3 summary (`figure_03_empirical_size_selection_summary.pdf`) may claim that weighted size-selection models reduce distributional mismatch relative to strict hard-window predictions across enabled empirical examples, but it must not be described as proving exact depth prediction or wet-lab optimal enzyme choice.

Stage 5b screening-speed outputs are cached `radigest-screen-pairs-cached` performance measurements. They support a throughput claim for candidate-pair screening only; they do not support cross-tool coordinate equivalence or biological recovery claims. Cut-index build workers are pinned to `radigest_threads` so screening-speed and job-scaling cases do not accidentally vary cache-build parallelism when `jobs` changes.

Stage 5c thread-scaling outputs are intra-tool radigest performance measurements. JSON-summary and fragment-TSV output modes are not pooled; each comparison group must preserve the same retained-fragment count across thread counts before speedups are interpreted. These outputs do not support cross-tool equivalence or empirical recovery claims.

Stage 5d pair-screen job-scaling outputs are intra-tool `radigest-screen-pairs-cached` performance measurements. They support a scaling claim for cached candidate-pair screening across configured job counts only. Candidate-pair evaluation and reported JSON coverage must be consistent across job counts before speedups are interpreted. Cut-index build workers are held fixed across job-count rows. These outputs do not support cross-tool equivalence or empirical recovery claims.

Stage 5e large-reference outputs support a radigest-only timing claim on the Triticum aestivum Chinese Spring wheat reference. They do not support cross-tool equivalence, screening scaling, or empirical recovery claims. The required wheat row uses JSON output to avoid turning the claim into a fragment-TSV disk-output stress test. Cannabis Pink Pepper rows are retained only as optional moderate-reference guardrails.

Stage 5f matched-tool timing outputs are semantics-aware timing interpretations. They support a matched timing table and R/ggplot2 timing figure across complete small-yeast and medium-cannabis groups plus a required large-wheat subset. SimRAD is excluded from the wheat subset because it cannot process the full wheat FASTA under R string-size limits. The table does not collapse all tools into a shared coordinate-equivalence claim. Each row carries the tool's comparison level, primary output type, and allowed claim.

## Sockeye SNP-panel target-overlap claim

The SNP-panel target-overlap workflow supports a coordinate-aware design claim: when target intervals are supplied as a BED file on the same reference build, candidate enzyme pairs can be ranked by overlap with that panel, read-accessibility under the configured read layout and read length, predicted mean depth from the matching `radigest-design` table, and off-panel hard-window burden. This claim is conditional on coordinate compatibility between the BED panel and `data/reference/sockeye_oner_uvic_2_0.fa`.

The workflow does not prove that every captured SNP will genotype successfully. It does not model allele dropout, restriction-site polymorphism, mappability, genotype-calling filters, primer/probe performance, or per-locus empirical depth unless those are added as separate inputs. The output should be described as target-aware pre-sequencing interval design and not as guaranteed SNP-panel recovery.
