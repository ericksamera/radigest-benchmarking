#!/usr/bin/env bash
set -euo pipefail

REPO="external/ddRADseqTools"
REFERENCE=""
ENZYME1=""
ENZYME2=""
MIN_SIZE=""
MAX_SIZE=""
WORK_DIR=""
FRAGS_OUT=""
STATS_OUT=""
SUMMARY_OUT=""
VERSION_OUT=""
STDOUT_LOG=""
STDERR_LOG=""
FRAGST_INTERVAL="25"

usage() {
  cat <<'USAGE'
Usage:
  scripts/comparators/run_ddradseqtools_rsitesearch.sh \
    --repo external/ddRADseqTools \
    --reference REF.fa[.gz] \
    --enzyme1 EcoRI \
    --enzyme2 MseI \
    --min 100 \
    --max 300 \
    --work-dir results/raw/comparators/ddradseqtools/work \
    --frags-out results/raw/comparators/ddradseqtools/fragments.fasta \
    --stats-out results/raw/comparators/ddradseqtools/fragments-stats.txt \
    --summary-out results/raw/comparators/ddradseqtools/summary.tsv \
    --version-out results/raw/comparators/ddradseqtools/version.txt \
    --stdout-log benchmark/logs/ddradseqtools.stdout.log \
    --stderr-log benchmark/logs/ddradseqtools.stderr.log

Runs DDRADSEQTOOLS Package/rsitesearch.py only.
Do not use this wrapper for read simulation, PCR duplicate simulation, allele
dropout simulation, adapter trimming, or downstream preprocessing comparisons.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --reference) REFERENCE="$2"; shift 2 ;;
    --enzyme1) ENZYME1="$2"; shift 2 ;;
    --enzyme2) ENZYME2="$2"; shift 2 ;;
    --min) MIN_SIZE="$2"; shift 2 ;;
    --max) MAX_SIZE="$2"; shift 2 ;;
    --work-dir) WORK_DIR="$2"; shift 2 ;;
    --frags-out) FRAGS_OUT="$2"; shift 2 ;;
    --stats-out) STATS_OUT="$2"; shift 2 ;;
    --summary-out) SUMMARY_OUT="$2"; shift 2 ;;
    --version-out) VERSION_OUT="$2"; shift 2 ;;
    --stdout-log) STDOUT_LOG="$2"; shift 2 ;;
    --stderr-log) STDERR_LOG="$2"; shift 2 ;;
    --fragstinterval) FRAGST_INTERVAL="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for required in REFERENCE ENZYME1 ENZYME2 MIN_SIZE MAX_SIZE WORK_DIR FRAGS_OUT STATS_OUT SUMMARY_OUT VERSION_OUT STDOUT_LOG STDERR_LOG; do
  if [[ -z "${!required}" ]]; then
    echo "error: --${required,,} is required" >&2
    usage >&2
    exit 2
  fi
done

PACKAGE_DIR="$REPO/Package"
RSITESEARCH="$PACKAGE_DIR/rsitesearch.py"
RSFILE="$PACKAGE_DIR/restrictionsites.txt"

if [[ ! -s "$RSITESEARCH" ]]; then
  echo "error: rsitesearch.py not found: $RSITESEARCH" >&2
  exit 2
fi

if [[ ! -s "$RSFILE" ]]; then
  echo "error: restrictionsites.txt not found: $RSFILE" >&2
  exit 2
fi

if [[ ! -s "$REFERENCE" ]]; then
  echo "error: reference FASTA not found: $REFERENCE" >&2
  exit 2
fi

mkdir -p "$WORK_DIR" \
         "$(dirname "$FRAGS_OUT")" \
         "$(dirname "$STATS_OUT")" \
         "$(dirname "$SUMMARY_OUT")" \
         "$(dirname "$VERSION_OUT")" \
         "$(dirname "$STDOUT_LOG")" \
         "$(dirname "$STDERR_LOG")"

REFERENCE_ABS="$(readlink -f "$REFERENCE")"
FRAGS_ABS="$(readlink -f "$(dirname "$FRAGS_OUT")")/$(basename "$FRAGS_OUT")"
STATS_ABS="$(readlink -f "$(dirname "$STATS_OUT")")/$(basename "$STATS_OUT")"
RSFILE_ABS="$(readlink -f "$RSFILE")"
PACKAGE_ABS="$(readlink -f "$PACKAGE_DIR")"

# rsitesearch.py supports gzip internally, but a scratch plain FASTA avoids
# ambiguity and makes timing comparable to other plain-FASTA benchmarks.
INPUT_FA="$WORK_DIR/input.fa"

python3 - "$REFERENCE_ABS" "$INPUT_FA" <<'PYREF'
from __future__ import annotations

import gzip
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])

open_in = gzip.open if str(src).endswith(".gz") else open

with open_in(src, "rt", encoding="utf-8", errors="replace") as inp, dst.open(
    "w", encoding="utf-8"
) as out:
    for raw in inp:
        if raw.startswith(">"):
            out.write(raw)
        else:
            out.write(raw.upper())
PYREF

INPUT_ABS="$(readlink -f "$INPUT_FA")"

COMMAND=(
  python3 "$PACKAGE_ABS/rsitesearch.py"
  "--genfile=$INPUT_ABS"
  "--fragsfile=$FRAGS_ABS"
  "--rsfile=$RSFILE_ABS"
  "--enzyme1=$ENZYME1"
  "--enzyme2=$ENZYME2"
  "--minfragsize=$MIN_SIZE"
  "--maxfragsize=$MAX_SIZE"
  "--fragstfile=$STATS_ABS"
  "--fragstinterval=$FRAGST_INTERVAL"
  "--plot=NO"
  "--verbose=NO"
  "--trace=NO"
)

{
  echo "tool=DDRADSEQTOOLS rsitesearch.py"
  echo "repo=$REPO"
  echo "package_dir=$PACKAGE_ABS"
  echo "reference=$REFERENCE_ABS"
  echo "input_plain_fasta=$INPUT_ABS"
  echo "enzyme1=$ENZYME1"
  echo "enzyme2=$ENZYME2"
  echo "min_size=$MIN_SIZE"
  echo "max_size=$MAX_SIZE"
  echo "python_version=$(python3 --version 2>&1)"
  if git -C "$REPO" rev-parse HEAD >/dev/null 2>&1; then
    echo "git_commit=$(git -C "$REPO" rev-parse HEAD)"
  else
    echo "git_commit=NA"
  fi
  echo "command=${COMMAND[*]}"
} > "$VERSION_OUT"

set +e
(
  cd "$PACKAGE_ABS"
  "${COMMAND[@]}"
) > "$STDOUT_LOG" 2> "$STDERR_LOG"
STATUS=$?
set -e

echo "exit_status=$STATUS" >> "$VERSION_OUT"

if [[ "$STATUS" -ne 0 ]]; then
  echo "error: rsitesearch.py exited with status $STATUS; see $STDERR_LOG" >&2
  exit "$STATUS"
fi

python3 scripts/comparators/summarize_ddradseqtools_fragments.py \
  --frags "$FRAGS_OUT" \
  --stats "$STATS_OUT" \
  --reference "$REFERENCE" \
  --enzyme1 "$ENZYME1" \
  --enzyme2 "$ENZYME2" \
  --min "$MIN_SIZE" \
  --max "$MAX_SIZE" \
  --version-log "$VERSION_OUT" \
  --out "$SUMMARY_OUT"
