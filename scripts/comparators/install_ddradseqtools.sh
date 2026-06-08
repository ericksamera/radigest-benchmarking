#!/usr/bin/env bash
set -euo pipefail

DEST="external/ddRADseqTools"
REPO="https://github.com/GGFHF/ddRADseqTools.git"

usage() {
  cat <<'USAGE'
Usage:
  scripts/comparators/install_ddradseqtools.sh [--dest external/ddRADseqTools]

Clones or updates DDRADSEQTOOLS into external/.
The external checkout is ignored by Git.

The digest-level target is Package/rsitesearch.py.
Do not use full read simulation workflows for radigest comparison.
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
  echo "Cloning DDRADSEQTOOLS into: $DEST" >&2
  git clone "$REPO" "$DEST"
}

update_existing_checkout() {
  echo "Updating existing DDRADSEQTOOLS checkout: $DEST" >&2
  git -C "$DEST" fetch --all --tags --prune
  git -C "$DEST" pull --ff-only
}

if [[ -d "$DEST/.git" ]]; then
  if ! update_existing_checkout; then
    echo "WARNING: existing DDRADSEQTOOLS checkout could not be updated; recloning." >&2
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

echo "DDRADSEQTOOLS path: $DEST"
echo "DDRADSEQTOOLS commit:"
git -C "$DEST" rev-parse HEAD

test -s "$DEST/Package/rsitesearch.py"
test -s "$DEST/Package/rsitesearch-config.txt"
test -s "$DEST/Package/restrictionsites.txt"

python3 - <<'PY'
import importlib.util
import sys

missing = []
for pkg in ["numpy", "matplotlib"]:
    if importlib.util.find_spec(pkg) is None:
        missing.append(pkg)

if missing:
    print(
        "WARNING: active Python is missing DDRADSEQTOOLS runtime package(s): "
        + ", ".join(missing),
        file=sys.stderr,
    )
    print(
        "Snakemake comparator targets run DDRADSEQTOOLS inside "
        "workflow/envs/comparators.yml, which declares these packages.",
        file=sys.stderr,
    )
else:
    print("DDRADSEQTOOLS Python dependencies available")
PY
