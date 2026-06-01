# Release checklist

Before tagging a public release:

- [ ] `preflight` passes.
- [ ] `make check-local THREADS=1` passes, or `make check RADIGEST=<path> THREADS=1` passes.
- [ ] `make reference-data-dry-run` passes.
- [ ] `make empirical-recovery-dry-run` passes on a machine with empirical data paths configured.
- [ ] `make audit` reports no `FAIL` entries.
- [ ] `make check-benchmark-categories` reports no manifest `FAIL` entries.
- [ ] Expected release-time `WARN` entries are resolved or documented.
- [ ] `CITATION.cff` has final DOI and release date after archival.
- [ ] `config/datasets.tsv` has final accessions, URLs, and SHA256 checksums where redistribution is possible.
- [ ] `config/empirical_recovery.tsv` matches the manuscript empirical windows.
- [ ] Public reference FASTA files can be downloaded with `make reference-data`.
- [ ] Empirical BAM/CRAM files are either archived externally or documented as required local inputs.
- [ ] BAM/reference compatibility checks pass for empirical recovery datasets where coordinate-level interpretation is used.
- [ ] `make manuscript-tables` was run after all intended analyses were regenerated.
- [ ] Curated manuscript tables are force-added with `git add -f manuscript_tables/*.tsv`.
- [ ] Raw FASTA, FASTQ, BAM, CRAM, external checkouts, and benchmark scratch outputs are not staged.
- [ ] The radigest source commit or release tag used for the analysis is recorded.
- [ ] The repository tag matches the Methods/Data availability text in the manuscript.

## Expected release-time warnings

The following warnings are acceptable during active development but should be
resolved before archival release:

- `CITATION.cff` DOI/date fields marked `TO_BE_FILLED`;
- public or empirical data accessions marked `TO_BE_FILLED`;
- expected SHA256 checksums marked `TO_BE_FILLED`.

## Files that should normally not be tracked

- `data/reference/*`
- `data/empirical/*`
- `external/*`
- `results/raw/*`
- `results/processed/*`
- `results/tables/*`
- `results/figures/*`
- `benchmark/*`
- `.local/*`
- `codebase.json`
