#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "${BASH_SOURCE[0]}")/benchmarks/run_screening_speed_benchmark.sh" "$@"
