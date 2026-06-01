# Release checklist

Before release:

1. `make check` passes.
2. `make reviewer-nonempirical THREADS=4` passes.
3. `make audit` passes.
4. Every `required_for_release=true` row in `config/artifacts.tsv` has present, current outputs.
5. Environment and artifact-status tables are regenerated.
