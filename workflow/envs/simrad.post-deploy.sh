#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${CONDA_PREFIX:-}" ]]; then
  echo "ERROR: CONDA_PREFIX is not set; Snakemake post-deploy must run inside the SimRAD conda environment." >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

"${CONDA_PREFIX}/bin/Rscript" "${REPO_ROOT}/scripts/comparators/install_simrad_archive.R"
"${CONDA_PREFIX}/bin/Rscript" -e 'library(SimRAD); packageVersion("SimRAD")'
