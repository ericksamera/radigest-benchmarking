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

A claim is release-required only when `required_for_release` is `true`. Empirical recovery remains optional until public empirical inputs are configured.

Stage 5b screening-speed outputs are cached `radigest-screen-pairs-cached` performance measurements. They support a throughput claim for candidate-pair screening only; they do not support cross-tool coordinate equivalence or biological recovery claims.

Stage 5c thread-scaling outputs are intra-tool radigest performance measurements. JSON-summary and fragment-TSV output modes are not pooled; each comparison group must preserve the same retained-fragment count across thread counts before speedups are interpreted. These outputs do not support cross-tool equivalence or empirical recovery claims.

Stage 5d pair-screen job-scaling outputs are intra-tool `radigest-screen-pairs-cached` performance measurements. They support a scaling claim for cached candidate-pair screening across configured job counts only. Candidate-pair evaluation and reported JSON coverage must be consistent across job counts before speedups are interpreted. These outputs do not support cross-tool equivalence or empirical recovery claims.

Stage 5e large-reference outputs support a radigest-only timing claim on the Triticum aestivum Chinese Spring wheat reference. They do not support cross-tool equivalence, screening scaling, or empirical recovery claims. The required wheat row uses JSON output to avoid turning the claim into a fragment-TSV disk-output stress test. Cannabis Pink Pepper rows are retained only as optional moderate-reference guardrails.
