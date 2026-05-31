# Scripts layout

Scripts are grouped by workflow role.

The top-level `scripts/<name>` files may be compatibility wrappers that forward
to implementation scripts in subdirectories. Existing commands and Snakefiles can
continue to use the old paths while the codebase transitions to the new layout.

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

## Compatibility wrappers

During the transition, compatibility wrappers are kept at the original
`scripts/<name>` paths. This avoids breaking Makefile targets, Snakefiles, and
documentation while keeping implementation code organized.

A later cleanup can patch workflows to call implementation paths directly and
remove wrappers once tests pass.
