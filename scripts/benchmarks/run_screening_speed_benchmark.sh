#!/usr/bin/env bash
set -euo pipefail

REFERENCE="data/reference/yeast.fa"
DATASET="yeast_small_plain"
ENZYMES="config/candidate_enzymes.txt"
MIN_SIZE="300"
MAX_SIZE="600"
SCORE_MIN="1"
SCORE_MAX="2000"
SIZE_MODEL="hard"
RUNS="5"

RADIGEST_SCREEN_PAIRS="radigest-screen-pairs"
DDGRADER_REPO="external/ddRadSeqWebTool"

JOBS="2"
RADIGEST_THREADS="1"

OUT_ROOT="results/raw/screening_speed"
PROCESSED_DIR="results/processed/screening_speed"
TIME_DIR="benchmark/memory/screening_speed"
LOG_DIR="benchmark/logs/screening_speed"
TABLE_DIR="results/tables"

usage() {
  cat <<'USAGE'
Usage:
  scripts/run_screening_speed_benchmark.sh [options]

Options:
  --reference PATH              Reference FASTA, preferably plain FASTA for fair timing
  --dataset ID                  Dataset label
  --enzymes PATH                Candidate enzyme list
  --min N                       Minimum fragment size
  --max N                       Maximum fragment size
  --score-min N                 radigest score minimum
  --score-max N                 radigest score maximum
  --size-model MODEL            radigest size model
  --runs N                      Replicates
  --radigest-screen-pairs PATH  radigest-screen-pairs executable
  --ddgrader-repo PATH          ddgRADer/ddRadSeqWebTool checkout
  --jobs N                      radigest-screen-pairs jobs
  --radigest-threads N          radigest threads per pair
  -h, --help                    Show help

Outputs:
  results/tables/screening_speed_runs.tsv
  results/tables/screening_speed_summary.tsv
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --reference) REFERENCE="$2"; shift 2 ;;
    --dataset) DATASET="$2"; shift 2 ;;
    --enzymes) ENZYMES="$2"; shift 2 ;;
    --min) MIN_SIZE="$2"; shift 2 ;;
    --max) MAX_SIZE="$2"; shift 2 ;;
    --score-min) SCORE_MIN="$2"; shift 2 ;;
    --score-max) SCORE_MAX="$2"; shift 2 ;;
    --size-model) SIZE_MODEL="$2"; shift 2 ;;
    --runs) RUNS="$2"; shift 2 ;;
    --radigest-screen-pairs) RADIGEST_SCREEN_PAIRS="$2"; shift 2 ;;
    --ddgrader-repo) DDGRADER_REPO="$2"; shift 2 ;;
    --jobs) JOBS="$2"; shift 2 ;;
    --radigest-threads) RADIGEST_THREADS="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ ! -s "$REFERENCE" ]]; then
  echo "error: reference FASTA not found: $REFERENCE" >&2
  exit 2
fi

if [[ ! -s "$ENZYMES" ]]; then
  echo "error: enzyme list not found: $ENZYMES" >&2
  exit 2
fi

if ! command -v "$RADIGEST_SCREEN_PAIRS" >/dev/null 2>&1 && [[ ! -x "$RADIGEST_SCREEN_PAIRS" ]]; then
  echo "error: radigest-screen-pairs not found: $RADIGEST_SCREEN_PAIRS" >&2
  exit 2
fi

# Make the local radigest tool directory visible to radigest-screen-pairs.
# This matters inside Snakemake-managed Conda environments, where PATH does not
# automatically include .local/bin even when the executable is invoked by path.
if [[ -x "$RADIGEST_SCREEN_PAIRS" ]]; then
  RADIGEST_SCREEN_PAIRS="$(realpath "$RADIGEST_SCREEN_PAIRS")"
  export PATH="$(dirname "$RADIGEST_SCREEN_PAIRS"):$PATH"
fi


if [[ ! -d "$DDGRADER_REPO" ]]; then
  echo "error: ddgRADer repo not found: $DDGRADER_REPO" >&2
  echo "Run: bash scripts/install_ddgrader.sh" >&2
  exit 2
fi

mkdir -p "$OUT_ROOT" "$PROCESSED_DIR" "$TIME_DIR" "$LOG_DIR" "$TABLE_DIR"

PAIR_TSV="$PROCESSED_DIR/enzyme_pairs.tsv"
PAIR_DDGRADER="$PROCESSED_DIR/enzyme_pairs.ddgrader.txt"

python3 scripts/make_enzyme_pair_list.py \
  --enzymes "$ENZYMES" \
  --out-tsv "$PAIR_TSV" \
  --out-ddgrader "$PAIR_DDGRADER"

PAIR_TEXT="$(tr -d '\n' < "$PAIR_DDGRADER")"

for run in $(seq 1 "$RUNS"); do
  echo "[RUN] radigest-screen-pairs run${run}" >&2

  RADIGEST_OUT="$OUT_ROOT/radigest__${DATASET}__run${run}"
  rm -rf "$RADIGEST_OUT"
  mkdir -p "$RADIGEST_OUT"

  /usr/bin/time -v \
    -o "$TIME_DIR/radigest_screen_pairs__${DATASET}__run${run}.time" \
    "$RADIGEST_SCREEN_PAIRS" \
      --fasta "$REFERENCE" \
      --enzymes "$ENZYMES" \
      --min "$MIN_SIZE" \
      --max "$MAX_SIZE" \
      --score-min "$SCORE_MIN" \
      --score-max "$SCORE_MAX" \
      --size-model "$SIZE_MODEL" \
      --jobs "$JOBS" \
      --radigest-threads "$RADIGEST_THREADS" \
      --out-dir "$RADIGEST_OUT" \
      > "$LOG_DIR/radigest_screen_pairs__${DATASET}__run${run}.stdout.log" \
      2> "$LOG_DIR/radigest_screen_pairs__${DATASET}__run${run}.stderr.log"

  echo "[RUN] ddgRADer backend run${run}" >&2

  DDG_OUT="$OUT_ROOT/ddgrader__${DATASET}__run${run}"
  rm -rf "$DDG_OUT"
  mkdir -p "$DDG_OUT"

  /usr/bin/time -v \
    -o "$TIME_DIR/ddgrader_backend__${DATASET}__run${run}.time" \
    python3 scripts/run_ddgrader_backend.py \
      --repo "$DDGRADER_REPO" \
      --reference "$REFERENCE" \
      --enzyme-pairs "$PAIR_TEXT" \
      --min "$MIN_SIZE" \
      --max "$MAX_SIZE" \
      --out-raw-csv "$DDG_OUT/ddgrader.raw.csv" \
      --out-bins "$DDG_OUT/ddgrader.bins.tsv" \
      --out-summary "$DDG_OUT/ddgrader.summary.tsv" \
      --version-log "$DDG_OUT/ddgrader.version.txt" \
      > "$LOG_DIR/ddgrader_backend__${DATASET}__run${run}.stdout.log" \
      2> "$LOG_DIR/ddgrader_backend__${DATASET}__run${run}.stderr.log"
done

python3 scripts/summarize_screening_speed.py \
  --root "$OUT_ROOT" \
  --time-dir "$TIME_DIR" \
  --pair-tsv "$PAIR_TSV" \
  --dataset "$DATASET" \
  --out-runs "$TABLE_DIR/screening_speed_runs.tsv" \
  --out-summary "$TABLE_DIR/screening_speed_summary.tsv"

echo "wrote $TABLE_DIR/screening_speed_runs.tsv" >&2
echo "wrote $TABLE_DIR/screening_speed_summary.tsv" >&2
