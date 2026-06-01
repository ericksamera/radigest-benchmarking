# Comparator registry

Comparator semantics are declared in `config/comparators.tsv`.

Comparator run cases are declared in `config/comparator_cases.tsv`. Stage 4 ports exact interval-equivalence comparators only:

```text
digital_rads_smoke_single__D1 -> Digital_RADs.py normalized interval comparison
small_yeast_s288c_B1          -> DDRADSEQTOOLS rsitesearch.py normalized interval comparison
```

External paths listed in `config/comparators.tsv` are checked only when `make comparators` or a reviewer target that depends on `comparators_all` is executed. `make check` remains a manifest and smoke dry-run check and does not require external comparator repositories.

Install or update the two Stage 4 external checkouts with:

```bash
bash scripts/comparators/install_digital_rads.sh
bash scripts/comparators/install_ddradseqtools.sh
```

The required executable paths after installation are:

```text
external/Digital_RADs/Digital_RADs.py
external/ddRADseqTools/Package/rsitesearch.py
external/ddRADseqTools/Package/restrictionsites.txt
```

Digital_RADs.py reports motif-bounded markers; the Stage 4 normalizer converts them to cut-to-cut zero-based half-open intervals before comparison. DDRADSEQTOOLS `rsitesearch.py` emits fragment FASTA headers; the Stage 4 normalizer converts those coordinates with enzyme cut offsets and first-token sequence identifiers.
