# Comparator registry

Comparator semantics are declared in `config/comparators.tsv`.

Comparator workflows must respect the declared `comparison_level`, `primary_output_type`, and `allowed_claim`. External paths listed in `required_paths` are checked only when the corresponding comparator stage is executed.
