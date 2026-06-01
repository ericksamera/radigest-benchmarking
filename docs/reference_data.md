# Reference data acquisition

Large reference FASTA files are excluded from Git. Public reference genomes used
for manuscript benchmarks are declared in `config/datasets.tsv` and downloaded
with the NCBI Datasets CLI.

NCBI Datasets genome packages are downloaded by assembly accession and include
the genomic FASTA and metadata reports.

## Public references

| dataset               | accession       | local gzipped FASTA                        | local plain FASTA                       | purpose                                        |
| --------------------- | --------------- | ------------------------------------------ | --------------------------------------- | ---------------------------------------------- |
| yeast_small           | GCF_000146045.2 | data/reference/yeast.fa.gz                 | data/reference/yeast.fa                 | small matched digest benchmark                 |
| moderate_genome       | GCA_029168945.1 | data/reference/moderate.fa.gz              | data/reference/moderate.fa              | Cannabis moderate-genome scaling and screening |
| sockeye_reference     | GCF_034236695.1 | data/empirical/sockeye/reference.fa.gz     | data/empirical/sockeye/reference.fa     | sockeye empirical recovery reference           |
| trichoderma_reference | GCF_020647795.1 | data/empirical/trichoderma/reference.fa.gz | data/empirical/trichoderma/reference.fa | Trichoderma empirical recovery reference       |

## Install environment

```bash
mamba env create -f envs/benchmark.yml
mamba activate radigest-benchmarking
```

The benchmark environment includes Go for building radigest and
`ncbi-datasets-cli` for reference downloads.

## Download public references

```bash
make reference-data
```

Equivalent direct command:

```bash
scripts/reference/download_reference_data.sh \
  --datasets config/datasets.tsv \
  --dataset yeast_small,moderate_genome,sockeye_reference,trichoderma_reference \
  --prepare-plain \
  --out results/processed/reference_checksums.tsv
```

## Outputs

```text
data/reference/yeast.fa.gz
data/reference/yeast.fa
data/reference/moderate.fa.gz
data/reference/moderate.fa
data/empirical/sockeye/reference.fa.gz
data/empirical/sockeye/reference.fa
data/empirical/trichoderma/reference.fa.gz
data/empirical/trichoderma/reference.fa
results/processed/reference_checksums.tsv
results/processed/fasta/*.summary.tsv
results/processed/reference_metadata/
```

## Empirical BAM/CRAM inputs

The NCBI reference workflow downloads genome FASTA files. It does not download
the empirical BAM/CRAM files used for TLEN recovery modelling.

For full empirical reproducibility, empirical BAM/CRAM inputs must be provided
through one of the following:

1. public SRA/ENA/Zenodo/OSF accessions and a download script;
2. archived BAM/CRAM files with checksums;
3. local files documented in an empirical-input manifest.

The BAM/CRAM alignment reference must match the corresponding FASTA downloaded
above.
