#!/usr/bin/env bash
set -euo pipefail

DEST="external/Digital_RADs"
REPO="https://github.com/BU-RAD-seq/Digital_RADs.git"

usage() {
  cat <<'USAGE'
Usage:
  scripts/install_digital_rads.sh [--dest external/Digital_RADs]

Clones or updates BU-RAD-seq/Digital_RADs into external/.
The external checkout is ignored by Git; record commit/version metadata in workflow outputs.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest)
      DEST="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

mkdir -p "$(dirname "$DEST")"

if [[ -d "$DEST/.git" ]]; then
  echo "Updating existing Digital_RADs checkout: $DEST" >&2
  git -C "$DEST" fetch --all --tags --prune
else
  echo "Cloning Digital_RADs into: $DEST" >&2
  git clone "$REPO" "$DEST"
fi

echo "Digital_RADs path: $DEST"
echo "Digital_RADs commit:"
git -C "$DEST" rev-parse HEAD

if [[ ! -s "$DEST/Digital_RADs.py" ]]; then
  echo "error: Digital_RADs.py was not found in $DEST" >&2
  exit 1
fi
