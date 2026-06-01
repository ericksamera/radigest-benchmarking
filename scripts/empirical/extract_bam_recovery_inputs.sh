#!/usr/bin/env bash
set -euo pipefail

BAM=""
OUT_PREFIX=""
MAPQ="20"
KEEP_DUPLICATES="false"

usage() {
  cat <<'USAGE'
Usage:
  scripts/empirical/extract_bam_recovery_inputs.sh \
    --bam alignments.bam \
    --out-prefix results/raw/empirical_recovery/dataset/sample \
    --mapq 20

Outputs:
  <out-prefix>.tlens.tsv
  <out-prefix>.pairs.bed
  <out-prefix>.summary.tsv

Notes:
  - Extracts proper paired-end alignments with positive TLEN.
  - Excludes unmapped, mate-unmapped, secondary, QC-fail, duplicate, and
    supplementary records by default.
  - Use --keep-duplicates to retain duplicate-marked reads.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bam) BAM="$2"; shift 2 ;;
    --out-prefix) OUT_PREFIX="$2"; shift 2 ;;
    --mapq) MAPQ="$2"; shift 2 ;;
    --keep-duplicates) KEEP_DUPLICATES="true"; shift 1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$BAM" || -z "$OUT_PREFIX" ]]; then
  echo "error: --bam and --out-prefix are required" >&2
  usage >&2
  exit 2
fi

if [[ ! -s "$BAM" ]]; then
  echo "error: BAM/CRAM does not exist or is empty: $BAM" >&2
  exit 2
fi

if ! command -v samtools >/dev/null 2>&1; then
  echo "error: samtools is required" >&2
  exit 2
fi

mkdir -p "$(dirname "$OUT_PREFIX")"

TLENS="${OUT_PREFIX}.tlens.tsv"
PAIRS="${OUT_PREFIX}.pairs.bed"
SUMMARY="${OUT_PREFIX}.summary.tsv"

# Exclude flags:
#   4    read unmapped
#   8    mate unmapped
#   256  secondary
#   512  QC fail
#   1024 duplicate
#   2048 supplementary
if [[ "$KEEP_DUPLICATES" == "true" ]]; then
  EXCLUDE_FLAGS=$((4 + 8 + 256 + 512 + 2048))
else
  EXCLUDE_FLAGS=$((4 + 8 + 256 + 512 + 1024 + 2048))
fi

tmp="${OUT_PREFIX}.tmp.tsv"
rm -f "$tmp" "$TLENS" "$PAIRS" "$SUMMARY"

samtools view \
  -f 2 \
  -F "$EXCLUDE_FLAGS" \
  -q "$MAPQ" \
  "$BAM" \
  | awk -v OFS='\t' '
      $9 > 0 && ($7 == "=" || $7 == $3) {
        start0 = $4 - 1
        end0 = start0 + $9
        print $3, start0, end0, $9, $1, $5, $2
      }
    ' > "$tmp"

cut -f4 "$tmp" > "$TLENS"
cat "$tmp" > "$PAIRS"

{
  echo -e "bam\tmapq\tkeep_duplicates\texclude_flags\tpairs\tmin_tlen\tmax_tlen\tmean_tlen"
  awk -v bam="$BAM" -v mapq="$MAPQ" -v keep="$KEEP_DUPLICATES" -v flags="$EXCLUDE_FLAGS" '
    BEGIN { n=0; sum=0; min=""; max="" }
    {
      t=$4
      n++
      sum += t
      if (min == "" || t < min) min=t
      if (max == "" || t > max) max=t
    }
    END {
      mean = (n > 0 ? sum / n : 0)
      print bam "\t" mapq "\t" keep "\t" flags "\t" n "\t" min "\t" max "\t" mean
    }
  ' "$tmp"
} > "$SUMMARY"

rm -f "$tmp"

echo "wrote $TLENS" >&2
echo "wrote $PAIRS" >&2
echo "wrote $SUMMARY" >&2
