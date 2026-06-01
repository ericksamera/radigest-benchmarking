# Data requirements

Reference FASTA files are produced by the Stage 3 references workflow from `config/references.tsv`. The nonempirical reviewer run currently requires two public NCBI assemblies:

- `small_yeast_s288c` -> `data/reference/small_yeast_s288c.fa.gz` and `data/reference/small_yeast_s288c.fa`
- `moderate_cannabis_pink-pepper` -> `data/reference/moderate_cannabis_pink-pepper.fa.gz` and `data/reference/moderate_cannabis_pink-pepper.fa`

Reference IDs use underscores to delimit benchmark scale, organism or commodity, and source label. Hyphens preserve multi-word source labels, as in `moderate_cannabis_pink-pepper`. The workflow records SHA256 checksums and basic FASTA statistics in `results/references/reference_checksums.tsv`.

Stage 4 comparator runs also require tracked synthetic FASTA files:

```text
data/synthetic/digital_rads_ecori_msei_double.fa
data/synthetic/simrad_ecori_msei_double.fa
```

External comparator checkouts are ignored and are installed under `external/`:

```text
external/Digital_RADs/Digital_RADs.py
external/ddRADseqTools/Package/rsitesearch.py
external/ddRADseqTools/Package/restrictionsites.txt
external/ddRadSeqWebTool/backend/service/DigestSequence.py
```

Install helpers live in `scripts/comparators/`. Version metadata is written into generated comparator outputs. Empirical BAM/CRAM inputs remain optional until their public input contract is finalized.
