#!/usr/bin/env bash
set -euo pipefail

SOURCE="${RADIGEST_REPO:-../radigest}"
REF="${RADIGEST_REF:-}"
OUT_DIR=".local/radigest"
BIN_DIR=".local/bin"
MANIFEST="results/processed/radigest_build.tsv"
FORCE="false"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ensure_radigest.sh \
    --source ../radigest \
    --ref HEAD \
    --out-dir .local/radigest \
    --bin-dir .local/bin

Builds radigest from a local checkout or Git URL without storing radigest
source code in this benchmarking repository.

Examples:
  scripts/ensure_radigest.sh --source ../radigest --ref HEAD
  scripts/ensure_radigest.sh --source https://github.com/ericksamera/radigest.git --ref v0.2.0
  scripts/ensure_radigest.sh --source ../radigest --ref main --force

Outputs:
  .local/bin/radigest
  .local/bin/radigest-screen-pairs
  .local/bin/radigest-rank-pairs
  .local/bin/radigest-fit-size-model
  results/processed/radigest_build.tsv
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) SOURCE="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    --out-dir) OUT_DIR="$2"; shift 2 ;;
    --bin-dir) BIN_DIR="$2"; shift 2 ;;
    --manifest) MANIFEST="$2"; shift 2 ;;
    --force) FORCE="true"; shift 1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if ! command -v git >/dev/null 2>&1; then
  echo "error: git is required" >&2
  exit 2
fi

if ! command -v make >/dev/null 2>&1; then
  echo "error: make is required" >&2
  exit 2
fi

if ! command -v go >/dev/null 2>&1; then
  echo "error: Go is required to build radigest" >&2
  exit 2
fi

REPO_DIR="${OUT_DIR}/repo"

if [[ "$FORCE" == "true" ]]; then
  rm -rf "$REPO_DIR"
fi

mkdir -p "$OUT_DIR" "$BIN_DIR" "$(dirname "$MANIFEST")"

if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "[clone] $SOURCE -> $REPO_DIR" >&2
  git clone "$SOURCE" "$REPO_DIR"
else
  echo "[reuse] $REPO_DIR" >&2
fi

if [[ -n "$REF" && "$REF" != "HEAD" ]]; then
  echo "[checkout] $REF" >&2
  git -C "$REPO_DIR" fetch --all --tags || true
  git -C "$REPO_DIR" checkout "$REF"
else
  echo "[checkout] existing HEAD" >&2
fi

echo "[build] make build" >&2
make -C "$REPO_DIR" build

required=(
  radigest
  radigest-screen-pairs
  radigest-rank-pairs
  radigest-fit-size-model
)

for exe in "${required[@]}"; do
  if [[ ! -x "$REPO_DIR/bin/$exe" ]]; then
    echo "error: expected executable not found after build: $REPO_DIR/bin/$exe" >&2
    exit 1
  fi
  cp "$REPO_DIR/bin/$exe" "$BIN_DIR/$exe"
  chmod 0755 "$BIN_DIR/$exe"
done

# Optional helper; present in newer radigest checkouts.
if [[ -x "$REPO_DIR/bin/radigest-plan-depth" ]]; then
  cp "$REPO_DIR/bin/radigest-plan-depth" "$BIN_DIR/radigest-plan-depth"
  chmod 0755 "$BIN_DIR/radigest-plan-depth"
fi

commit="$(git -C "$REPO_DIR" rev-parse HEAD)"
describe="$(git -C "$REPO_DIR" describe --tags --dirty --always 2>/dev/null || true)"
status="$(git -C "$REPO_DIR" status --porcelain | wc -l | awk '{print $1}')"
go_version="$(go version)"

{
  echo -e "item\tvalue"
  echo -e "source\t${SOURCE}"
  echo -e "requested_ref\t${REF:-HEAD}"
  echo -e "repo_dir\t${REPO_DIR}"
  echo -e "bin_dir\t${BIN_DIR}"
  echo -e "commit\t${commit}"
  echo -e "describe\t${describe}"
  echo -e "dirty_files\t${status}"
  echo -e "go_version\t${go_version}"
  echo -e "radigest\t${BIN_DIR}/radigest"
  echo -e "radigest_screen_pairs\t${BIN_DIR}/radigest-screen-pairs"
  echo -e "radigest_rank_pairs\t${BIN_DIR}/radigest-rank-pairs"
  echo -e "radigest_fit_size_model\t${BIN_DIR}/radigest-fit-size-model"
} > "$MANIFEST"

echo "wrote $MANIFEST" >&2
echo "Use: RADIGEST=${BIN_DIR}/radigest" >&2
