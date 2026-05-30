#!/usr/bin/env bash
set -euo pipefail

REFERENCE="data/reference/yeast.fa.gz"
DATASET="yeast_small"
CONDITION="B1"
ENZYMES="EcoRI,MseI"
MIN_SIZE="100"
MAX_SIZE="300"
RUNS="5"
THREADS="1"

RADIGEST="radigest"
DIGITAL_RADS="external/Digital_RADs/Digital_RADs.py"
ENZYMES_TSV="config/enzymes.tsv"

OUT_ROOT="results/raw/matched_tool_benchmarks"
TIME_DIR="benchmark/memory/matched_tools"
LOG_DIR="benchmark/logs/matched_tools"
TABLE_DIR="results/tables"

SKIP_SIMRAD="0"
SKIP_DIGITAL="0"

usage() {
  cat <<'USAGE'
Usage:
  scripts/run_matched_tool_benchmarks.sh [options]

Options:
  --reference PATH       Reference FASTA. Default: data/reference/yeast.fa.gz
  --dataset ID           Dataset label. Default: yeast_small
  --condition ID         Condition label. Default: B1
  --enzymes A,B          Enzyme pair. Default: EcoRI,MseI
  --min N                Minimum fragment length. Default: 100
  --max N                Maximum fragment length. Default: 300
  --runs N               Replicate runs. Default: 5
  --threads N            radigest threads. Default: 1
  --radigest PATH        radigest executable. Default: radigest
  --digital-rads PATH    Digital_RADs.py path. Default: external/Digital_RADs/Digital_RADs.py
  --enzymes-tsv PATH     Enzyme table. Default: config/enzymes.tsv
  --skip-simrad          Do not run SimRAD task
  --skip-digital-rads    Do not run Digital_RADs.py task
  -h, --help             Show help

Tasks:
  radigest_count      radigest JSON-only digest count task
  simrad_count        SimRAD digest + AB/BA + size selection task
  radigest_interval   radigest fragments TSV + interval normalization
  digital_rads_interval
                      Digital_RADs.py + cut-coordinate normalization

The output is raw benchmark output plus:
  results/tables/matched_tool_benchmark_runs.tsv
  results/tables/matched_tool_benchmark_summary.tsv
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
    --runs) RUNS="$2"; shift 2 ;;
    --threads) THREADS="$2"; shift 2 ;;
    --radigest) RADIGEST="$2"; shift 2 ;;
    --digital-rads) DIGITAL_RADS="$2"; shift 2 ;;
    --enzymes-tsv) ENZYMES_TSV="$2"; shift 2 ;;
    --skip-simrad) SKIP_SIMRAD="1"; shift ;;
    --skip-digital-rads) SKIP_DIGITAL="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ ! -s "$REFERENCE" ]]; then
  echo "error: reference FASTA not found: $REFERENCE" >&2
  exit 2
fi

if ! command -v "$RADIGEST" >/dev/null 2>&1 && [[ ! -x "$RADIGEST" ]]; then
  echo "error: radigest executable not found: $RADIGEST" >&2
  exit 2
fi

if [[ ! -s "$ENZYMES_TSV" ]]; then
  echo "error: enzyme table not found: $ENZYMES_TSV" >&2
  exit 2
fi

IFS=',' read -r ENZYME1 ENZYME2 <<< "$ENZYMES"
ENZYME1="${ENZYME1:-}"
ENZYME2="${ENZYME2:-}"

if [[ -z "$ENZYME1" || -z "$ENZYME2" ]]; then
  echo "error: --enzymes must be a two-enzyme pair, e.g. EcoRI,MseI" >&2
  exit 2
fi

if [[ "$SKIP_SIMRAD" == "0" ]]; then
  if ! Rscript -e 'quit(status = ifelse(requireNamespace("SimRAD", quietly = TRUE), 0, 1))' >/dev/null 2>&1; then
    echo "error: SimRAD is not installed. Run scripts/install_simrad_archive.R or use --skip-simrad." >&2
    exit 2
  fi
fi

if [[ "$SKIP_DIGITAL" == "0" && ! -s "$DIGITAL_RADS" ]]; then
  echo "error: Digital_RADs.py not found: $DIGITAL_RADS" >&2
  echo "Install with: bash scripts/install_digital_rads.sh" >&2
  echo "Or use --skip-digital-rads." >&2
  exit 2
fi

mkdir -p "$OUT_ROOT" "$TIME_DIR" "$LOG_DIR" "$TABLE_DIR"

quote() {
  printf "%q" "$1"
}

write_header() {
  local path="$1"
  {
    echo "#!/usr/bin/env bash"
    echo "set -euo pipefail"
    echo
  } > "$path"
}

run_command_script() {
  local task="$1"
  local run="$2"
  local command_script="$3"

  local time_file="${TIME_DIR}/${task}__${DATASET}__${CONDITION}__run${run}.time"
  local stdout_log="${LOG_DIR}/${task}__${DATASET}__${CONDITION}__run${run}.stdout.log"
  local stderr_log="${LOG_DIR}/${task}__${DATASET}__${CONDITION}__run${run}.stderr.log"

  chmod +x "$command_script"

  echo "[RUN] $task run${run}" >&2
  /usr/bin/time -v -o "$time_file" \
    bash "$command_script" \
    > "$stdout_log" \
    2> "$stderr_log"
}

make_task_dir() {
  local task="$1"
  local run="$2"
  local out_dir="${OUT_ROOT}/${task}__${DATASET}__${CONDITION}__run${run}"
  mkdir -p "$out_dir"
  printf "%s" "$out_dir"
}

for run in $(seq 1 "$RUNS"); do
  # radigest count-level JSON task
  out_dir="$(make_task_dir radigest_count "$run")"
  cmd="${out_dir}/command.sh"
  write_header "$cmd"
  {
    echo "$(quote "$RADIGEST") \\"
    echo "  -fasta $(quote "$REFERENCE") \\"
    echo "  -enzymes $(quote "$ENZYMES") \\"
    echo "  -min $(quote "$MIN_SIZE") \\"
    echo "  -max $(quote "$MAX_SIZE") \\"
    echo "  -threads $(quote "$THREADS") \\"
    echo "  -json $(quote "${out_dir}/radigest.json")"
  } >> "$cmd"
  run_command_script "radigest_count" "$run" "$cmd"

  # radigest interval task: TSV + normalization
  out_dir="$(make_task_dir radigest_interval "$run")"
  cmd="${out_dir}/command.sh"
  write_header "$cmd"
  {
    echo "$(quote "$RADIGEST") \\"
    echo "  -fasta $(quote "$REFERENCE") \\"
    echo "  -enzymes $(quote "$ENZYMES") \\"
    echo "  -min $(quote "$MIN_SIZE") \\"
    echo "  -max $(quote "$MAX_SIZE") \\"
    echo "  -threads $(quote "$THREADS") \\"
    echo "  -fragments-tsv $(quote "${out_dir}/radigest.fragments.tsv") \\"
    echo "  -json $(quote "${out_dir}/radigest.json")"
    echo
    echo "python3 scripts/normalize_radigest_tsv.py \\"
    echo "  --input $(quote "${out_dir}/radigest.fragments.tsv") \\"
    echo "  --output $(quote "${out_dir}/radigest.normalized.tsv") \\"
    echo "  --source-tool radigest \\"
    echo "  --hard-kept-only"
  } >> "$cmd"
  run_command_script "radigest_interval" "$run" "$cmd"

  if [[ "$SKIP_SIMRAD" == "0" ]]; then
    out_dir="$(make_task_dir simrad_count "$run")"
    cmd="${out_dir}/command.sh"
    write_header "$cmd"
    {
      echo "Rscript scripts/run_simrad_ddrad.R \\"
      echo "  --reference $(quote "$REFERENCE") \\"
      echo "  --enzyme1 $(quote "$ENZYME1") \\"
      echo "  --enzyme2 $(quote "$ENZYME2") \\"
      echo "  --min $(quote "$MIN_SIZE") \\"
      echo "  --max $(quote "$MAX_SIZE") \\"
      echo "  --enzymes-tsv $(quote "$ENZYMES_TSV") \\"
      echo "  --out $(quote "${out_dir}/simrad.tsv") \\"
      echo "  --version-log $(quote "${out_dir}/simrad.version.txt")"
    } >> "$cmd"
    run_command_script "simrad_count" "$run" "$cmd"
  fi

  if [[ "$SKIP_DIGITAL" == "0" ]]; then
    out_dir="$(make_task_dir digital_rads_interval "$run")"
    cmd="${out_dir}/command.sh"
    write_header "$cmd"
    {
      echo "bash scripts/run_digital_rads.sh \\"
      echo "  --digital-rads $(quote "$DIGITAL_RADS") \\"
      echo "  --reference $(quote "$REFERENCE") \\"
      echo "  --enzyme1 $(quote "$ENZYME1") \\"
      echo "  --enzyme2 $(quote "$ENZYME2") \\"
      echo "  --min $(quote "$MIN_SIZE") \\"
      echo "  --max $(quote "$MAX_SIZE") \\"
      echo "  --enzymes-tsv $(quote "$ENZYMES_TSV") \\"
      echo "  --work-dir $(quote "${out_dir}/digital_work") \\"
      echo "  --raw-out $(quote "${out_dir}/digital.raw.tsv") \\"
      echo "  --summary-out $(quote "${out_dir}/digital.run_summary.tsv") \\"
      echo "  --version-out $(quote "${out_dir}/digital.version.txt") \\"
      echo "  --stdout-log $(quote "${out_dir}/digital.stdout.log") \\"
      echo "  --stderr-log $(quote "${out_dir}/digital.stderr.log")"
      echo
      echo "python3 scripts/normalize_digital_rads.py \\"
      echo "  --input $(quote "${out_dir}/digital.raw.tsv") \\"
      echo "  --output $(quote "${out_dir}/digital.normalized.tsv") \\"
      echo "  --summary $(quote "${out_dir}/digital.normalize_summary.tsv") \\"
      echo "  --enzymes-tsv $(quote "$ENZYMES_TSV") \\"
      echo "  --enzyme1 $(quote "$ENZYME1") \\"
      echo "  --enzyme2 $(quote "$ENZYME2") \\"
      echo "  --min $(quote "$MIN_SIZE") \\"
      echo "  --max $(quote "$MAX_SIZE")"
    } >> "$cmd"
    run_command_script "digital_rads_interval" "$run" "$cmd"
  fi
done

python3 scripts/summarize_matched_tool_benchmarks.py \
  --root "$OUT_ROOT" \
  --time-dir "$TIME_DIR" \
  --dataset "$DATASET" \
  --condition "$CONDITION" \
  --out-runs "${TABLE_DIR}/matched_tool_benchmark_runs.tsv" \
  --out-summary "${TABLE_DIR}/matched_tool_benchmark_summary.tsv"

echo "wrote ${TABLE_DIR}/matched_tool_benchmark_runs.tsv" >&2
echo "wrote ${TABLE_DIR}/matched_tool_benchmark_summary.tsv" >&2
