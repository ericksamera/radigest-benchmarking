#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "${BASH_SOURCE[0]}")/empirical/extract_bam_recovery_inputs.sh" "$@"
