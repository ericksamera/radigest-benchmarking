#!/usr/bin/env bash
set -euo pipefail

SOURCE=""
DEST=""
OUT="results/processed/plain_reference_checksums.tsv"
FORCE="0"

usage() {
  cat <<'USAGE'
Usage:
  scripts/reference/prepare_plain_reference.sh \
    --source data/reference/yeast.fa.gz \
    --dest data/reference/yeast.fa \
    [--out results/processed/plain_reference_checksums.tsv] \
    [--force]

Creates an uncompressed FASTA from a gzipped FASTA. Existing output is not
overwritten unless --force is supplied.

The output TSV records source/destination sizes and SHA256 checksums.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      SOURCE="$2"
      shift 2
      ;;
    --dest)
      DEST="$2"
      shift 2
      ;;
    --out)
      OUT="$2"
      shift 2
      ;;
    --force)
      FORCE="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$SOURCE" || -z "$DEST" ]]; then
  echo "error: --source and --dest are required" >&2
  usage >&2
  exit 2
fi

if [[ ! -s "$SOURCE" ]]; then
  echo "error: source FASTA does not exist or is empty: $SOURCE" >&2
  exit 1
fi

mkdir -p "$(dirname "$DEST")" "$(dirname "$OUT")"

sha256_file() {
  local path="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$path" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$path" | awk '{print $1}'
  else
    echo "error: neither sha256sum nor shasum is available" >&2
    exit 1
  fi
}

file_size() {
  local path="$1"
  wc -c < "$path" | awk '{print $1}'
}

status="exists"
message="existing destination not overwritten"

if [[ ! -e "$DEST" || "$FORCE" == "1" ]]; then
  tmp="$(mktemp "${DEST}.tmp.XXXXXX")"
  trap 'rm -f "$tmp"' EXIT

  if [[ "$SOURCE" == *.gz ]]; then
    gzip -cd "$SOURCE" > "$tmp"
  else
    cp "$SOURCE" "$tmp"
  fi

  mv "$tmp" "$DEST"
  trap - EXIT

  status="created"
  if [[ "$FORCE" == "1" ]]; then
    status="created_force"
  fi
  message="plain FASTA written from source"
fi

source_sha="$(sha256_file "$SOURCE")"
dest_sha="$(sha256_file "$DEST")"
source_size="$(file_size "$SOURCE")"
dest_size="$(file_size "$DEST")"

{
  printf "source\tdest\tsource_sha256\tdest_sha256\tsource_size_bytes\tdest_size_bytes\tstatus\tmessage\n"
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$SOURCE" "$DEST" "$source_sha" "$dest_sha" "$source_size" "$dest_size" "$status" "$message"
} > "$OUT"

echo "wrote $DEST" >&2
echo "wrote $OUT" >&2
