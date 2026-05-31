#!/usr/bin/env bash
set -euo pipefail

echo "[simrad post-deploy] CONDA_PREFIX=${CONDA_PREFIX}" >&2

if [[ -z "${CONDA_PREFIX:-}" ]]; then
  echo "error: CONDA_PREFIX is not set" >&2
  exit 2
fi

if [[ ! -x "${CONDA_PREFIX}/bin/Rscript" ]]; then
  echo "error: Rscript not found in ${CONDA_PREFIX}/bin" >&2
  exit 2
fi

"${CONDA_PREFIX}/bin/Rscript" scripts/install_simrad_archive.R

"${CONDA_PREFIX}/bin/Rscript" -e 'library(SimRAD); packageVersion("SimRAD")'
