#!/usr/bin/env bash
set -euo pipefail

DEST="external/ddRadSeqWebTool"
REPO="https://github.com/felixglinka/ddRadSeqWebTool.git"
BRANCH="development"

usage() {
  cat <<'USAGE'
Usage:
  scripts/comparators/install_ddgrader.sh [--dest external/ddRadSeqWebTool] [--branch development]

Clones or updates ddgRADer / ddRadSeqWebTool into external/.
The external checkout is ignored by Git.

Python dependencies are not installed automatically by this script.
Install them with, for example:

  python3 -m pip install -r external/ddRadSeqWebTool/requirements.txt

or, if that fails:

  python3 -m pip install django==3.2.3 django-chunked-upload \
    biopython regex pandas numpy matplotlib apscheduler

USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest)
      DEST="$2"
      shift 2
      ;;
    --branch)
      BRANCH="$2"
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
  echo "Cloning ddRadSeqWebTool into: $DEST" >&2
  git clone --branch "$BRANCH" "$REPO" "$DEST"
}

update_existing_checkout() {
  echo "Updating existing ddRadSeqWebTool checkout: $DEST" >&2
  git -C "$DEST" fetch --all --tags --prune
  git -C "$DEST" checkout "$BRANCH"
  git -C "$DEST" pull --ff-only
}

if [[ -d "$DEST/.git" ]]; then
  if ! update_existing_checkout; then
    echo "WARNING: existing ddRadSeqWebTool checkout could not be updated; recloning." >&2
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

echo "ddRadSeqWebTool path: $DEST"
echo "ddRadSeqWebTool commit:"
git -C "$DEST" rev-parse HEAD

test -s "$DEST/backend/service/DigestSequence.py"
test -s "$DEST/backend/service/HandleFastafile.py"
test -s "$DEST/backend/service/DoubleDigestedDnaComparison.py"
test -s "$DEST/resources/restrictionEnzymes/newEnglandEnzymeList.csv"
