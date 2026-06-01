# Scenario manifests

Scenario manifests move reusable benchmark parameters out of the Makefile and
into `config/scenarios/*.tsv`. Each TSV has a small Make-readable projection
`config/scenarios/<scenario>.mk` so Make can load defaults without repeatedly
invoking Python at parse time.

The default scenario is:

```text
config/scenarios/nonempirical.tsv
```

It defines reference paths, dataset labels, enzyme pairs, size windows, run
counts, thread/job grids, external-tool paths, and workflow-config paths for the
non-empirical manuscript rerun.

## Inspect the selected scenario

```bash
make scenarios
```

Validate the manifest and its Make-readable projection:

```bash
make check-scenarios
```

This writes:

```text
results/processed/scenario_qc.tsv
```

## Select a different scenario

The Makefile loads `SCENARIO_MAKEFILE`, which defaults to the scenario selected by `SCENARIO`:

```bash
make scenarios SCENARIO=nonempirical
```

By default, `SCENARIO=nonempirical` reads:

```text
config/scenarios/nonempirical.tsv
```

You can also point directly at a different table and Makefile projection:

```bash
make benchmark-nonempirical \
  SCENARIO=my_machine \
  SCENARIO_TABLE=config/scenarios/my_machine.tsv \
  SCENARIO_MAKEFILE=config/scenarios/my_machine.mk
```

## Override one value without editing the manifest

Scenario values are Make defaults. Command-line Make assignments still win:

```bash
make benchmark-screening-speed \
  SCREENING_RUNS=3 \
  SCREENING_JOBS=4
```

## Manifest columns

| Column | Meaning |
| --- | --- |
| `scenario_id` | Scenario identifier. The default is `nonempirical`. |
| `parameter` | Parameter name read by the Makefile. |
| `value` | Default value for that parameter. |
| `description` | Human-readable description of the parameter. |

## Relationship to the other manifests

- `config/scenarios/*.tsv` defines how a benchmark is parameterized.
- `config/benchmark_categories.tsv` defines which claim family a benchmark belongs to.
- `config/artifacts.tsv` defines which upstream outputs support final manuscript claims.

The scenario layer does not change output paths or claim interpretation. It only
centralizes execution parameters that were previously embedded in Makefile
recipes.
