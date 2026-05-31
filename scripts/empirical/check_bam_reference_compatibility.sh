#!/usr/bin/env bash
set -euo pipefail

REFERENCE=""
BAM_GLOB=""
OUT=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/check_bam_reference_compatibility.sh \
    --reference data/empirical/sockeye/reference.fa \
    --bam-glob 'data/empirical/sockeye/bam/*.bam' \
    --out results/processed/empirical_recovery/sockeye_ddrad/reference_compatibility.tsv

Checks:
  - FASTA index exists or is created.
  - Each BAM has @SQ records.
  - BAM sequence names and lengths match FASTA .fai.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --reference) REFERENCE="$2"; shift 2 ;;
    --bam-glob) BAM_GLOB="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$REFERENCE" || -z "$BAM_GLOB" || -z "$OUT" ]]; then
  usage >&2
  exit 2
fi

if [[ ! -s "$REFERENCE" ]]; then
  echo "error: missing reference: $REFERENCE" >&2
  exit 2
fi

if ! command -v samtools >/dev/null 2>&1; then
  echo "error: samtools required" >&2
  exit 2
fi

mkdir -p "$(dirname "$OUT")"

if [[ ! -s "${REFERENCE}.fai" ]]; then
  samtools faidx "$REFERENCE"
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

cut -f1,2 "${REFERENCE}.fai" | sort > "$tmpdir/reference.sizes"

mapfile -t bams < <(compgen -G "$BAM_GLOB" | sort)

if [[ "${#bams[@]}" -eq 0 ]]; then
  echo "error: no BAM/CRAM files matched: $BAM_GLOB" >&2
  exit 2
fi

{
  echo -e "bam\treference\tstatus\tbam_sequences\treference_sequences\tshared_sequences\tmissing_from_bam\tmissing_from_reference\tlength_mismatches"
  for bam in "${bams[@]}"; do
    sq="$tmpdir/$(basename "$bam").sq"
    samtools view -H "$bam" \
      | awk -F'\t' '
          $1=="@SQ" {
            sn=""; ln="";
            for (i=2; i<=NF; i++) {
              if ($i ~ /^SN:/) sn=substr($i,4);
              if ($i ~ /^LN:/) ln=substr($i,4);
            }
            if (sn != "" && ln != "") print sn "\t" ln;
          }
        ' \
      | sort > "$sq"

    bam_n="$(wc -l < "$sq" | awk '{print $1}')"
    ref_n="$(wc -l < "$tmpdir/reference.sizes" | awk '{print $1}')"

    cut -f1 "$sq" > "$tmpdir/bam.names"
    cut -f1 "$tmpdir/reference.sizes" > "$tmpdir/ref.names"

    missing_from_bam="$(
      comm -23 "$tmpdir/ref.names" "$tmpdir/bam.names" | wc -l | awk '{print $1}'
    )"
    missing_from_reference="$(
      comm -13 "$tmpdir/ref.names" "$tmpdir/bam.names" | wc -l | awk '{print $1}'
    )"
    shared="$(
      comm -12 "$tmpdir/ref.names" "$tmpdir/bam.names" | wc -l | awk '{print $1}'
    )"

    join "$sq" "$tmpdir/reference.sizes" \
      | awk '$2 != $3 {n++} END {print n+0}' \
      > "$tmpdir/length_mismatches"
    mismatches="$(cat "$tmpdir/length_mismatches")"

    if [[ "$missing_from_bam" == "0" && "$missing_from_reference" == "0" && "$mismatches" == "0" ]]; then
      status="PASS"
    else
      status="FAIL"
    fi

    echo -e "${bam}\t${REFERENCE}\t${status}\t${bam_n}\t${ref_n}\t${shared}\t${missing_from_bam}\t${missing_from_reference}\t${mismatches}"
  done
} > "$OUT"

echo "wrote $OUT" >&2

if awk -F'\t' 'NR > 1 && $3 != "PASS" {bad++} END {exit bad ? 1 : 0}' "$OUT"; then
  exit 0
else
  echo "error: at least one BAM does not match the reference" >&2
  exit 1
fi
