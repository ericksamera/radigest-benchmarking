# Data requirements

Reference FASTA files are produced by the Stage 3 references workflow from `config/references.tsv`. The nonempirical reviewer run currently requires two public NCBI assemblies:

- `small_yeast_s288c` -> `data/reference/small_yeast_s288c.fa.gz` and `data/reference/small_yeast_s288c.fa`
- `moderate_cannabis_pink_pepper` -> `data/reference/moderate_cannabis_pink_pepper.fa.gz` and `data/reference/moderate_cannabis_pink_pepper.fa`

The reference IDs encode both benchmark scale and organism/cultivar source. The workflow records SHA256 checksums and basic FASTA statistics in `results/references/reference_checksums.tsv`. Empirical BAM/CRAM inputs remain optional until their public input contract is finalized.
