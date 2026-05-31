#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "${BASH_SOURCE[0]}")/empirical/check_bam_reference_compatibility.sh" "$@"
