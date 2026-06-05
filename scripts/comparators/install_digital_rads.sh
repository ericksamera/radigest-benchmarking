#!/usr/bin/env bash
set -euo pipefail

DEST="external/Digital_RADs"
REPO="https://github.com/BU-RAD-seq/Digital_RADs.git"

usage() {
  cat <<'USAGE'
Usage:
  scripts/comparators/install_digital_rads.sh [--dest external/Digital_RADs]

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

backup_existing_dest() {
  if [[ ! -e "$DEST" ]]; then
    return
  fi

  local stamp backup suffix
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  backup="${DEST}.bak.${stamp}"
  suffix=1

  while [[ -e "$backup" ]]; do
    backup="${DEST}.bak.${stamp}.${suffix}"
    suffix=$((suffix + 1))
  done

  echo "Moving existing non-reusable path aside: $DEST -> $backup" >&2
  mv "$DEST" "$backup"
}

clone_fresh() {
  echo "Cloning Digital_RADs into: $DEST" >&2
  git clone "$REPO" "$DEST"
}

update_existing_checkout() {
  echo "Updating existing Digital_RADs checkout: $DEST" >&2
  git -C "$DEST" fetch --all --tags --prune
}

if [[ -d "$DEST/.git" ]]; then
  if ! update_existing_checkout; then
    echo "WARNING: existing Digital_RADs checkout could not be updated; recloning." >&2
    backup_existing_dest
    clone_fresh
  fi
elif [[ -e "$DEST" ]]; then
  echo "WARNING: $DEST exists but is not a Git checkout; recloning." >&2
  backup_existing_dest
  clone_fresh
else
  clone_fresh
fi

echo "Digital_RADs path: $DEST"
echo "Digital_RADs commit:"
git -C "$DEST" rev-parse HEAD

if [[ ! -s "$DEST/Digital_RADs.py" ]]; then
  echo "error: Digital_RADs.py was not found in $DEST" >&2
  exit 1
fi
