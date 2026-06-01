#!/usr/bin/env bash
set -euo pipefail

OUT="results/processed/environment.txt"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      OUT="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: scripts/core/capture_environment.sh [--out results/processed/environment.txt]"
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p "$(dirname "$OUT")" benchmark/logs

run_section() {
  local title="$1"
  shift

  echo "===== ${title} ====="

  if command -v "$1" >/dev/null 2>&1; then
    "$@" 2>&1 || true
  else
    echo "MISSING: $1"
  fi

  echo
}

run_shell_section() {
  local title="$1"
  shift

  echo "===== ${title} ====="
  "$@" 2>&1 || true
  echo
}

{
  echo "# Environment metadata"
  echo "captured_at: $(date -Iseconds)"
  echo

  run_section "uname" uname -a

  echo "===== os-release ====="
  if [[ -r /etc/os-release ]]; then
    cat /etc/os-release
  else
    echo "MISSING: /etc/os-release"
  fi
  echo

  run_section "cpu" lscpu
  run_section "memory" free -h
  run_section "storage-lsblk" lsblk -o NAME,MODEL,SIZE,ROTA,TYPE,MOUNTPOINT
  run_section "storage-df" df -h .

  run_section "go" go version
  run_section "python" python3 --version
  run_section "r" Rscript --version
  run_section "julia" julia --version
  run_section "jq" jq --version
  run_section "hyperfine" hyperfine --version
  run_section "gnu-time" /usr/bin/time --version
  run_section "samtools" samtools --version
  run_section "seqkit" seqkit version
  run_section "snakemake" snakemake --version

  echo "===== radigest ====="
  echo "RADIGEST=${RADIGEST:-radigest}"
  if command -v "${RADIGEST:-radigest}" >/dev/null 2>&1; then
    command -v "${RADIGEST:-radigest}" || true
    "${RADIGEST:-radigest}" -version || true
    "${RADIGEST:-radigest}" -list-enzymes 2>/dev/null \
      | wc -l \
      | awk '{print "radigest_enzyme_count:", $1}' || true
  else
    echo "MISSING: ${RADIGEST:-radigest}"
  fi
  echo

  echo "===== python packages ====="
  python3 -m pip freeze 2>&1 || true
  echo

  echo "===== git-head ====="
  git rev-parse HEAD 2>&1 || true
  echo

  echo "===== git-status ====="
  git status --short 2>&1 || true
  echo
} > "$OUT"

echo "wrote $OUT" >&2
