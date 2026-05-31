#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "${BASH_SOURCE[0]}")/reference/prepare_plain_reference.sh" "$@"
