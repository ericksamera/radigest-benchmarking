#!/usr/bin/env bash
set -euo pipefail

DIGITAL_RADS=""
REFERENCE=""
ENZYME1=""
ENZYME2=""
MIN_SIZE=""
MAX_SIZE=""
ENZYMES_TSV="config/enzymes.tsv"
WORK_DIR=""
RAW_OUT=""
SUMMARY_OUT=""
VERSION_OUT=""
STDOUT_LOG=""
STDERR_LOG=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/comparators/run_digital_rads.sh \
    --digital-rads external/Digital_RADs/Digital_RADs.py \
    --reference REF.fa[.gz] \
    --enzyme1 EcoRI \
    --enzyme2 MseI \
    --min 1 \
    --max 100 \
    --enzymes-tsv config/enzymes.tsv \
    --work-dir results/raw/comparators/digital_rads/work \
    --raw-out results/raw/comparators/digital_rads/raw.tsv \
    --summary-out results/raw/comparators/digital_rads/summary.tsv \
    --version-out results/raw/comparators/digital_rads/version.txt \
    --stdout-log benchmark/logs/digital_rads.stdout.log \
    --stderr-log benchmark/logs/digital_rads.stderr.log

Notes:
  Digital_RADs.py filters on motif-bounded marker length. radigest filters on
  cut-to-cut interval length. This wrapper therefore runs Digital_RADs.py with
  a deliberately wider motif-bounded window. The downstream normalizer applies
  the true cut-to-cut size window.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --digital-rads) DIGITAL_RADS="$2"; shift 2 ;;
    --reference) REFERENCE="$2"; shift 2 ;;
    --enzyme1) ENZYME1="$2"; shift 2 ;;
    --enzyme2) ENZYME2="$2"; shift 2 ;;
    --min) MIN_SIZE="$2"; shift 2 ;;
    --max) MAX_SIZE="$2"; shift 2 ;;
    --enzymes-tsv) ENZYMES_TSV="$2"; shift 2 ;;
    --work-dir) WORK_DIR="$2"; shift 2 ;;
    --raw-out) RAW_OUT="$2"; shift 2 ;;
    --summary-out) SUMMARY_OUT="$2"; shift 2 ;;
    --version-out) VERSION_OUT="$2"; shift 2 ;;
    --stdout-log) STDOUT_LOG="$2"; shift 2 ;;
    --stderr-log) STDERR_LOG="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for name in DIGITAL_RADS REFERENCE ENZYME1 ENZYME2 MIN_SIZE MAX_SIZE ENZYMES_TSV WORK_DIR RAW_OUT SUMMARY_OUT VERSION_OUT STDOUT_LOG STDERR_LOG; do
  if [[ -z "${!name}" ]]; then
    echo "error: missing required argument for $name" >&2
    usage >&2
    exit 2
  fi
done

[[ -s "$DIGITAL_RADS" ]] || { echo "error: missing Digital_RADs.py: $DIGITAL_RADS" >&2; exit 1; }
[[ -s "$REFERENCE" ]] || { echo "error: missing reference FASTA: $REFERENCE" >&2; exit 1; }
[[ -s "$ENZYMES_TSV" ]] || { echo "error: missing enzyme table: $ENZYMES_TSV" >&2; exit 1; }

mkdir -p "$WORK_DIR" "$(dirname "$RAW_OUT")" "$(dirname "$SUMMARY_OUT")" "$(dirname "$VERSION_OUT")" "$(dirname "$STDOUT_LOG")" "$(dirname "$STDERR_LOG")"

read -r MOTIF1 MOTIF2 DIGITAL_MIN DIGITAL_MAX < <(
  python3 - "$ENZYMES_TSV" "$ENZYME1" "$ENZYME2" "$MIN_SIZE" "$MAX_SIZE" <<'PY'
from __future__ import annotations

import csv
import sys
from pathlib import Path

table = Path(sys.argv[1])
enzyme1 = sys.argv[2]
enzyme2 = sys.argv[3]
min_size = int(sys.argv[4])
max_size = int(sys.argv[5])

with table.open(newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    rows = list(reader)

def motif_for(name: str) -> str:
    for row in rows:
        if row.get("enzyme") == name:
            motif = row.get("recognition_motif") or row.get("motif") or ""
            motif = motif.replace("^", "").upper()
            if not motif:
                raise SystemExit(f"missing motif for enzyme {name}")
            if any(ch not in "ACGT" for ch in motif):
                raise SystemExit(f"Digital_RADs wrapper does not support degenerate motif {motif} for {name}")
            return motif
    raise SystemExit(f"enzyme not found in table: {name}")

m1 = motif_for(enzyme1)
m2 = motif_for(enzyme2)

# Digital_RADs.py filters using motif-bounded marker length. To avoid losing
# valid cut-to-cut fragments, run a broader motif-bounded window, then filter
# cut-to-cut lengths downstream in normalize_digital_rads.py.
digital_min = 1
digital_max = max_size + len(m1) + len(m2)

print(m1, m2, digital_min, digital_max)
PY
)

rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"

DIGITAL_RADS_ABS=$(readlink -f "$DIGITAL_RADS")

python3 - "$REFERENCE" "$WORK_DIR/input.fa" <<'PYREF'
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

pushd "$WORK_DIR" >/dev/null

COMMAND=(python3 "$DIGITAL_RADS_ABS" input.fa digital_rads.raw.tsv 2 "$MOTIF1" "$MOTIF2" "$DIGITAL_MIN" "$DIGITAL_MAX")

printf "%q " "${COMMAND[@]}" > command.txt
printf "\n" >> command.txt

set +e
"${COMMAND[@]}" > stdout.log 2> stderr.log
STATUS=$?
set -e

popd >/dev/null

cp "$WORK_DIR/digital_rads.raw.tsv" "$RAW_OUT"
cp "$WORK_DIR/stdout.log" "$STDOUT_LOG"
cp "$WORK_DIR/stderr.log" "$STDERR_LOG"

{
  echo "Digital_RADs.py: $DIGITAL_RADS"
  echo "reference: $REFERENCE"
  echo "enzyme1: $ENZYME1"
  echo "enzyme2: $ENZYME2"
  echo "motif1: $MOTIF1"
  echo "motif2: $MOTIF2"
  echo "requested_cut_window_min: $MIN_SIZE"
  echo "requested_cut_window_max: $MAX_SIZE"
  echo "digital_motif_window_min: $DIGITAL_MIN"
  echo "digital_motif_window_max: $DIGITAL_MAX"
  echo "exit_status: $STATUS"
  echo "command:"
  cat "$WORK_DIR/command.txt"
  if git -C "$(dirname "$DIGITAL_RADS_ABS")" rev-parse HEAD >/dev/null 2>&1; then
    echo "git_commit: $(git -C "$(dirname "$DIGITAL_RADS_ABS")" rev-parse HEAD)"
  else
    echo "git_commit: NA"
  fi
} > "$VERSION_OUT"

ROWS=$(( $(wc -l < "$RAW_OUT") - 1 ))
if [[ "$ROWS" -lt 0 ]]; then
  ROWS=0
fi

TOTAL_DIGITAL_LENGTH=$(
  awk -F'\t' 'NR>1 {s += $3} END {print s+0}' "$RAW_OUT"
)

{
  printf "tool\treference\tenzyme1\tenzyme2\tmotif1\tmotif2\trequested_min\trequested_max\tdigital_min\tdigital_max\traw_records\traw_digital_length_sum\traw_out\tversion_out\texit_status\tnotes\n"
  printf "Digital_RADs.py\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$REFERENCE" "$ENZYME1" "$ENZYME2" "$MOTIF1" "$MOTIF2" "$MIN_SIZE" "$MAX_SIZE" "$DIGITAL_MIN" "$DIGITAL_MAX" "$ROWS" "$TOTAL_DIGITAL_LENGTH" "$RAW_OUT" "$VERSION_OUT" "$STATUS" \
    "Digital window is motif-bounded and intentionally broader; downstream normalizer filters cut-to-cut intervals."
} > "$SUMMARY_OUT"

if [[ "$STATUS" -ne 0 ]]; then
  echo "error: Digital_RADs.py exited with status $STATUS; see $STDERR_LOG" >&2
  exit "$STATUS"
fi

echo "wrote $RAW_OUT" >&2
echo "wrote $SUMMARY_OUT" >&2
