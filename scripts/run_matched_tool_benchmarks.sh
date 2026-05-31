#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "${BASH_SOURCE[0]}")/benchmarks/run_matched_tool_benchmarks.sh" "$@"
