# Scripts layout

Scripts are grouped by workflow role. Top-level compatibility wrappers were
removed after the workflow, Makefile, and documentation references were updated
to point directly at the categorized implementation paths.

## Categories

| Directory              | Purpose                                                                            |
| ---------------------- | ---------------------------------------------------------------------------------- |
| `scripts/core/`        | Repository, environment, local radigest build, and audit helpers                   |
| `scripts/reference/`   | Reference download, preparation, checksum, and FASTA summary helpers               |
| `scripts/validation/`  | Synthetic validation and interval normalization/comparison helpers                 |
| `scripts/comparators/` | External comparator installation, execution, normalization, and comparison helpers |
| `scripts/benchmarks/`  | Benchmark execution and summary helpers                                            |
| `scripts/empirical/`   | Empirical TLEN extraction, recovery fitting, and input checks                      |
| `scripts/manuscript/`  | Manuscript table and figure generation                                             |

Use implementation paths directly, for example:

```bash
python3 scripts/benchmarks/summarize_screening_speed.py --help
bash scripts/reference/download_reference_data.sh --help
Rscript scripts/comparators/run_simrad_ddrad.R --help
```
