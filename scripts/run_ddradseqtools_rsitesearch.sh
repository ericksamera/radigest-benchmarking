#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "${BASH_SOURCE[0]}")/comparators/run_ddradseqtools_rsitesearch.sh" "$@"
