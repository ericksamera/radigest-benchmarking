#!/usr/bin/env bash
set -euo pipefail

REPO="external/ddRADseqTools"
OUT="results/processed/ddradseqtools_probe.txt"

usage() {
  cat <<'USAGE'
Usage:
  scripts/comparators/probe_ddradseqtools.sh \
    [--repo external/ddRADseqTools] \
    [--out results/processed/ddradseqtools_probe.txt]

Writes a probe report for DDRADSEQTOOLS rsitesearch.py and its config files.
This is intentionally diagnostic. The exact wrapper should be written after
inspecting this report.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO="$2"
      shift 2
      ;;
    --out)
      OUT="$2"
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

mkdir -p "$(dirname "$OUT")"

{
  echo "===== repo ====="
  echo "$REPO"
  echo

  echo "===== git commit ====="
  git -C "$REPO" rev-parse HEAD || true
  echo

  echo "===== expected files ====="
  for f in \
    "$REPO/Package/rsitesearch.py" \
    "$REPO/Package/rsitesearch-config.txt" \
    "$REPO/Package/restrictionsites.txt" \
    "$REPO/Package/manual/ddRADseqTools-manual.pdf"
  do
    if [[ -e "$f" ]]; then
      ls -lh "$f"
    else
      echo "MISSING $f"
    fi
  done
  echo

  echo "===== rsitesearch-config.txt ====="
  sed -n '1,220p' "$REPO/Package/rsitesearch-config.txt" || true
  echo

  echo "===== restrictionsites.txt first 80 lines ====="
  sed -n '1,80p' "$REPO/Package/restrictionsites.txt" || true
  echo

  echo "===== rsitesearch.py help attempt ====="
  (
    cd "$REPO/Package"
    python3 rsitesearch.py --help
  ) || true
  echo

  echo "===== rsitesearch.py first 160 lines ====="
  sed -n '1,160p' "$REPO/Package/rsitesearch.py" || true
} > "$OUT"

echo "wrote $OUT" >&2
