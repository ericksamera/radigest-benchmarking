# radigest benchmark v2 scaffold

This branch is a clean rebuild scaffold for the radigest benchmark and manuscript-support repository.

The repository is organized around reviewer execution, manuscript claims, scenario manifests, and artifact contracts. Analysis logic is intentionally absent from this first patch. Porting should proceed in staged commits:

```text
scaffold -> validators -> synthetic validation -> references -> comparators -> performance -> empirical -> manuscript/audit
```

## Stage 0 check

```bash
make check
```

The Stage 0 check validates manifest shape and asks Snakemake to dry-run the scaffold smoke target. It must not require reference FASTA files, radigest binaries, external comparator repositories, or empirical BAM/CRAM inputs.

## Reviewer entry points

These targets are dispatch shims. Implementation will be added in later stages under `workflow/rules/` and `scripts/`.

```bash
make smoke
make reviewer-nonempirical THREADS=4
make reviewer-empirical THREADS=4
make reviewer-all THREADS=4
make audit
```

## Contracts

Primary contracts live in:

- `config/scenarios/*.yml` for runnable reviewer scenarios.
- `config/comparators.tsv` for comparator semantics and required external paths.
- `config/artifacts.tsv` for manuscript claim outputs and release requirements.
