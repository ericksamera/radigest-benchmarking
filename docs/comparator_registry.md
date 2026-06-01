# Comparator registry

Comparator handling is centralized in `config/comparators.tsv`.

The registry records each comparator's benchmark scope, workflow entrypoints,
normalization semantics, output object, and allowed claim type. It is the source
of truth for whether a tool is an exact interval comparator, a count-level
comparator, a binned screening comparator, a limited qualitative comparator, or
discussion-only software.

## Why this exists

The external tools used in this repository do not expose equivalent output
objects:

- SimRAD is a count-level comparator for overlapping digest and size-selection
tasks.
- Digital_RADs.py emits motif-bounded records and must be normalized to
cut-coordinate intervals before interval comparison.
- DDRADSEQTOOLS `rsitesearch.py` emits FASTA records with header coordinates
that must be normalized before interval comparison.
- ddgRADer is used through its backend as a binned screening comparator, not as
a coordinate-level interval comparator.
- RADinitio, SimGBS, and Stacks are not release-required quantitative
comparators in the current workflow.

Keeping these semantics in one registry prevents claim scope from being
implicitly spread across wrappers, normalizers, manuscript builders, and prose
documentation.

## Inspect and validate

Show the compact registry:

```bash
make comparator-registry
```

Validate the registry:

```bash
make check-comparator-registry
```

This writes:

```text
results/processed/comparator_registry_qc.tsv
```

The validator checks the TSV schema, allowed comparison-level values,
repository-owned helper paths, and workflow file references. Missing `data/` and
`external/` paths are warnings because those inputs are intentionally not stored
in Git.

## Registry columns

| Column | Meaning |
| --- | --- |
| `tool_id` | Stable machine-readable identifier. |
| `display_name` | Human-readable tool name used in tables. |
| `role` | Short description of the tool and its benchmark role. |
| `install_target` | Repository helper script or target used to install/check out the comparator. |
| `install_command` | Human-readable installation command. |
| `check_command` | Command or check indicating whether the tool is available. |
| `version_command` | Command used to record version/commit metadata. |
| `workflow` | Workflow entrypoint(s), using `workflow/file.smk:target` notation where applicable. |
| `comparison_level` | One of `count_only`, `normalized_interval`, `binned_screening`, `limited_digest_locus`, or `discussion_only`. |
| `normalizer` | Normalizer script when raw output requires conversion; `NA` otherwise. |
| `summary_script` | Summary or comparison script used for generated tables. |
| `supported_conditions` | Benchmark condition IDs or labels where the comparator is in scope. |
| `primary_output_type` | Output object being compared, such as `normalized_interval_set` or `aggregate_count`. |
| `allowed_claim` | Claim types that may be made from this comparator. |
| `required_paths` | Repository-owned scripts/config paths and external checkout paths required for the comparator. |
| `mismatch_issue` | Short reason why raw output may not be directly comparable. |
| `mismatch_resolution` | Required normalization or interpretation rule. |
| `notes` | Additional limits and caveats. |

## Relationship to artifact contracts

The comparator registry defines what kind of comparison is valid. The artifact
contract manifest `config/artifacts.tsv` defines which concrete generated files
support manuscript claims. A valid manuscript claim should be compatible with
both layers.
