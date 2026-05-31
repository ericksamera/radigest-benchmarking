#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "${BASH_SOURCE[0]}")/benchmarks/run_radigest_thread_scaling.sh" "$@"
