# Artifact contracts

`config/artifacts.tsv` maps manuscript-facing claims and curated artifacts to the upstream outputs that support them.

This layer is intentionally separate from the benchmark-category manifest:

- `config/benchmark_categories.tsv` says which broad benchmark class a workflow belongs to.
- `config/artifacts.tsv` says which concrete file must exist before a manuscript claim or table is treated as supported.

## Manifest columns

| Column | Meaning |
| --- | --- |
| `artifact_id` | Stable row identifier for the contract. |
| `category_id` | Benchmark category from `config/benchmark_categories.tsv`. |
| `claim_id` | Claim identifier used in `manuscript_tables/claim_audit.tsv`; blank for static or optional curated tables. |
| `manuscript_section` | Manuscript or supplement area using the artifact. |
| `claim` | Human-readable claim supported by the artifact. |
| `required_input` | Semicolon-separated upstream outputs that must already exist. Globs are allowed. |
| `generated_artifact` | Curated manuscript output path expected after export. |
| `manuscript_artifact` | Manuscript table or figure filename. |
| `producer_target` | Make target(s) expected to generate the upstream input. |
| `producer_workflow` | Snakemake workflow/target or script responsible for the upstream input. |
| `required_for_release` | Whether missing inputs should fail a strict release check. |
| `notes` | Scope or interpretation notes. |

## Routine checks

Use the non-strict check during development:

```bash
make check-artifacts
```

This writes:

```text
results/processed/artifact_contracts.tsv
```

Missing rows are expected until the corresponding optional/heavy workflows have been run.

## Manuscript table export

`make manuscript-tables` validates upstream manuscript inputs in warning mode before exporting curated tables.

Use the strict target only when preparing a release or final manuscript archive:

```bash
make manuscript-tables-strict
```

The strict target checks release-required upstream inputs, exports tables, then verifies that release-required manuscript artifacts exist.
