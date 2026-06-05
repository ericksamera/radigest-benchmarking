# Empirical-library workflow scaffold.
#
# This module currently makes the empirical input contract executable without
# running private analyses. TLEN extraction, model fitting, and empirical figures
# will consume the enabled rows from config/empirical_libraries.tsv in later
# staged commits.

import csv

EMPIRICAL_LIBRARY_MANIFEST = "config/empirical_libraries.tsv"
EMPIRICAL_PLACEHOLDER_OUTPUTS = ["results/empirical/.gitkeep"]


def _read_empirical_library_rows(path):
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = [
            row
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]
    if not rows:
        raise ValueError(f"{path}: no empirical-library rows")
    return rows


EMPIRICAL_LIBRARY_ROWS = _read_empirical_library_rows(EMPIRICAL_LIBRARY_MANIFEST)
EMPIRICAL_ENABLED_ROWS = [
    row
    for row in EMPIRICAL_LIBRARY_ROWS
    if row.get("enabled", "false").strip().lower() == "true"
]
EMPIRICAL_LIBRARY_IDS = [row["library_id"] for row in EMPIRICAL_LIBRARY_ROWS]
EMPIRICAL_ENABLED_LIBRARY_IDS = [row["library_id"] for row in EMPIRICAL_ENABLED_ROWS]
EMPIRICAL_ALL_OUTPUTS = [EMPIRICAL_LIBRARY_MANIFEST] + EMPIRICAL_PLACEHOLDER_OUTPUTS


rule empirical_manifest_all:
    input:
        EMPIRICAL_ALL_OUTPUTS


rule empirical_all:
    input:
        EMPIRICAL_ALL_OUTPUTS
