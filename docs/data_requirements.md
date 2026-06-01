# Data requirements

Reference FASTA files are produced by the Stage 3 references workflow from `config/references.tsv`. The nonempirical reviewer run currently requires two public NCBI assemblies:

- `yeast` -> `data/reference/yeast.fa.gz` and `data/reference/yeast.fa`
- `moderate` -> `data/reference/moderate.fa.gz` and `data/reference/moderate.fa`

The workflow records SHA256 checksums and basic FASTA statistics in `results/references/reference_checksums.tsv`. Empirical BAM/CRAM inputs remain optional until their public input contract is finalized.
