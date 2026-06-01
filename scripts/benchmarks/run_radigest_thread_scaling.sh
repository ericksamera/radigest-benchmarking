#!/usr/bin/env bash
set -euo pipefail

REFERENCE=""
DATASET=""
CONDITION="B1"
ENZYMES="EcoRI,MseI"
MIN_SIZE="100"
MAX_SIZE="300"
THREADS_LIST="1,2,4"
MODES="json,fragments_tsv"
RUNS="5"
RADIGEST="radigest"
EXTRA_ARGS=""

OUT_ROOT="results/raw/radigest_thread_scaling"
TIME_DIR="benchmark/memory/radigest_thread_scaling"
LOG_DIR="benchmark/logs/radigest_thread_scaling"

usage() {
  cat <<'USAGE'
Usage:
  scripts/benchmarks/run_radigest_thread_scaling.sh \
    --reference data/reference/yeast.fa \
    --dataset yeast_small_plain \
    --condition B1 \
    --enzymes EcoRI,MseI \
    --min 100 \
    --max 300 \
    --threads-list 1,2,4,8 \
    --modes json,fragments_tsv \
    --runs 5 \
    --radigest ~/radigest/bin/radigest

Modes:
  json
  gff
  fragments_tsv
  fragments_fasta

Notes:
  - Use plain FASTA for thread scaling if possible.
  - Gzipped-vs-plain input overhead should be measured separately.
  - This benchmark is radigest-only; do not compare thread scaling against
    tools that do not expose equivalent thread controls.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --reference) REFERENCE="$2"; shift 2 ;;
    --dataset) DATASET="$2"; shift 2 ;;
    --condition) CONDITION="$2"; shift 2 ;;
    --enzymes) ENZYMES="$2"; shift 2 ;;
    --min) MIN_SIZE="$2"; shift 2 ;;
    --max) MAX_SIZE="$2"; shift 2 ;;
    --threads-list) THREADS_LIST="$2"; shift 2 ;;
    --modes) MODES="$2"; shift 2 ;;
    --runs) RUNS="$2"; shift 2 ;;
    --radigest) RADIGEST="$2"; shift 2 ;;
    --extra-args) EXTRA_ARGS="$2"; shift 2 ;;
    --out-root) OUT_ROOT="$2"; shift 2 ;;
    --time-dir) TIME_DIR="$2"; shift 2 ;;
    --log-dir) LOG_DIR="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$REFERENCE" || -z "$DATASET" ]]; then
  echo "error: --reference and --dataset are required" >&2
  usage >&2
  exit 2
fi

if [[ ! -s "$REFERENCE" ]]; then
  echo "error: reference FASTA does not exist or is empty: $REFERENCE" >&2
  exit 2
fi

if ! command -v "$RADIGEST" >/dev/null 2>&1 && [[ ! -x "$RADIGEST" ]]; then
  echo "error: radigest executable not found: $RADIGEST" >&2
  exit 2
fi

mkdir -p "$OUT_ROOT" "$TIME_DIR" "$LOG_DIR"

IFS=',' read -r -a THREAD_VALUES <<< "$THREADS_LIST"
IFS=',' read -r -a MODE_VALUES <<< "$MODES"

# shellcheck disable=SC2206
EXTRA_ARRAY=( $EXTRA_ARGS )

for threads in "${THREAD_VALUES[@]}"; do
  for mode in "${MODE_VALUES[@]}"; do
    for run in $(seq 1 "$RUNS"); do
      base="${DATASET}__${CONDITION}__${mode}__threads${threads}__run${run}"

      json_out="${OUT_ROOT}/${base}.json"
      time_out="${TIME_DIR}/${base}.time"
      stdout_log="${LOG_DIR}/${base}.stdout.log"
      stderr_log="${LOG_DIR}/${base}.stderr.log"
      command_log="${LOG_DIR}/${base}.command.txt"

      cmd=(
        "$RADIGEST"
        -fasta "$REFERENCE"
        -enzymes "$ENZYMES"
        -min "$MIN_SIZE"
        -max "$MAX_SIZE"
        -threads "$threads"
      )

      if [[ "${#EXTRA_ARRAY[@]}" -gt 0 ]]; then
        cmd+=( "${EXTRA_ARRAY[@]}" )
      fi

      primary_out="$json_out"

      case "$mode" in
        json)
          ;;
        gff)
          primary_out="${OUT_ROOT}/${base}.gff3"
          cmd+=( -gff "$primary_out" )
          ;;
        fragments_tsv)
          primary_out="${OUT_ROOT}/${base}.fragments.tsv"
          cmd+=( -fragments-tsv "$primary_out" )
          ;;
        fragments_fasta)
          primary_out="${OUT_ROOT}/${base}.fragments.fa"
          cmd+=( -fragments-fasta "$primary_out" )
          ;;
        *)
          echo "error: unsupported mode: $mode" >&2
          exit 2
          ;;
      esac

      cmd+=( -json "$json_out" )

      {
        printf "dataset=%s\n" "$DATASET"
        printf "condition=%s\n" "$CONDITION"
        printf "mode=%s\n" "$mode"
        printf "threads=%s\n" "$threads"
        printf "run=%s\n" "$run"
        printf "reference=%s\n" "$REFERENCE"
        printf "primary_output=%s\n" "$primary_out"
        printf "command="
        printf "%q " "${cmd[@]}"
        printf "\n"
      } > "$command_log"

      echo "[RUN] $base" >&2

      /usr/bin/time -v \
        -o "$time_out" \
        "${cmd[@]}" \
        > "$stdout_log" \
        2> "$stderr_log"
    done
  done
done

echo "wrote raw outputs to $OUT_ROOT" >&2
echo "wrote timing files to $TIME_DIR" >&2
echo "wrote logs to $LOG_DIR" >&2
