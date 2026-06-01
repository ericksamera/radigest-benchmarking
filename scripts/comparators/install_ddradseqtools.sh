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

if [[ -d "$DEST/.git" ]]; then
  echo "Updating existing DDRADSEQTOOLS checkout: $DEST" >&2
  git -C "$DEST" fetch --all --tags --prune
  git -C "$DEST" pull --ff-only || true
else
  echo "Cloning DDRADSEQTOOLS into: $DEST" >&2
  git clone "$REPO" "$DEST"
fi

echo "DDRADSEQTOOLS path: $DEST"
echo "DDRADSEQTOOLS commit:"
git -C "$DEST" rev-parse HEAD

test -s "$DEST/Package/rsitesearch.py"
test -s "$DEST/Package/rsitesearch-config.txt"
test -s "$DEST/Package/restrictionsites.txt"

python3 - <<'PY'
import importlib.util
missing = []
for pkg in ["numpy", "matplotlib"]:
    if importlib.util.find_spec(pkg) is None:
        missing.append(pkg)
if missing:
    raise SystemExit(
        "Missing Python packages for DDRADSEQTOOLS: " + ", ".join(missing)
        + "\nInstall with: python3 -m pip install numpy matplotlib"
    )
print("DDRADSEQTOOLS Python dependencies available")
PY
