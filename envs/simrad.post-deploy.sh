#!/usr/bin/env bash
set -euo pipefail

echo "[simrad post-deploy] CONDA_PREFIX=${CONDA_PREFIX}" >&2

if [[ -z "${CONDA_PREFIX:-}" ]]; then
  echo "error: CONDA_PREFIX is not set" >&2
  exit 2
fi

"${CONDA_PREFIX}/bin/Rscript" scripts/comparators/install_simrad_archive.R
"${CONDA_PREFIX}/bin/Rscript" -e 'library(SimRAD); packageVersion("SimRAD")'
