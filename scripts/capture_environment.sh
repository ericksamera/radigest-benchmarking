#!/usr/bin/env bash
set -euo pipefail

mkdir -p results/processed benchmark/logs

{
  echo "date:"
  date -Iseconds
  echo
  echo "uname:"
  uname -a
  echo
  echo "os-release:"
  cat /etc/os-release || true
  echo
  echo "cpu:"
  lscpu || true
  echo
  echo "memory:"
  free -h || true
  echo
  echo "storage:"
  lsblk -o NAME,MODEL,SIZE,ROTA,TYPE,MOUNTPOINT || true
  df -h . || true
  echo
  echo "software:"
  go version || true
  python3 --version || true
  Rscript --version || true
  julia --version || true
  jq --version || true
  hyperfine --version || true
  /usr/bin/time --version || true
  echo
  echo "git:"
  git rev-parse HEAD || true
  git status --short || true
} > results/processed/environment.txt
