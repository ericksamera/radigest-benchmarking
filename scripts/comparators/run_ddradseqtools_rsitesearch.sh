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
ENZYMES_TSV="config/enzymes.tsv"
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
    --stderr-log benchmark/logs/ddradseqtools.stderr.log \
    [--enzymes-tsv config/enzymes.tsv]

Runs DDRADSEQTOOLS Package/rsitesearch.py only.
If an enzyme name is absent from DDRADSEQTOOLS restrictionsites.txt, the wrapper
falls back to the star-marked recognition sequence from config/enzymes.tsv.
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
    --enzymes-tsv) ENZYMES_TSV="$2"; shift 2 ;;
    --fragstinterval) FRAGST_INTERVAL="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for required in REFERENCE ENZYME1 ENZYME2 MIN_SIZE MAX_SIZE WORK_DIR FRAGS_OUT STATS_OUT SUMMARY_OUT VERSION_OUT STDOUT_LOG STDERR_LOG ENZYMES_TSV; do
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

if [[ ! -s "$ENZYMES_TSV" ]]; then
  echo "error: enzyme TSV not found: $ENZYMES_TSV" >&2
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
ENZYMES_TSV_ABS="$(readlink -f "$ENZYMES_TSV")"
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

read -r DDRADSEQTOOLS_ENZYME1 DDRADSEQTOOLS_ENZYME1_MODE DDRADSEQTOOLS_ENZYME2 DDRADSEQTOOLS_ENZYME2_MODE < <(
  python3 - "$ENZYME1" "$ENZYME2" "$ENZYMES_TSV_ABS" "$RSFILE_ABS" <<'PYENZ'
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

enzyme1 = sys.argv[1]
enzyme2 = sys.argv[2]
enzymes_tsv = Path(sys.argv[3])
restrictionsites = Path(sys.argv[4])
iupac_re = re.compile(r"^[ACGTRYSWKMBDHVN]+$", re.IGNORECASE)


def known_ddradseqtools_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    text = path.read_text(encoding="utf-8", errors="replace")
    for record in re.split(r"\s+", text):
        if not record or record.startswith("#") or ";" not in record:
            continue
        name, _site = record.split(";", 1)
        if name:
            ids.add(name)
    return ids


def read_enzyme_defs(path: Path) -> dict[str, tuple[str, int]]:
    out: dict[str, tuple[str, int]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit(f"{path}: missing header")
        for row in reader:
            name = (row.get("enzyme_id") or row.get("enzyme") or "").strip()
            if not name:
                continue
            motif = (
                row.get("recognition_sequence")
                or row.get("recognition_motif")
                or row.get("motif")
                or ""
            ).replace("^", "").replace("*", "").upper()
            cut_raw = (row.get("cut_offset") or "").strip()
            if motif and cut_raw:
                out[name] = (motif, int(cut_raw))
    return out


def star_marked_site(enzyme: str, defs: dict[str, tuple[str, int]]) -> str:
    if enzyme not in defs:
        raise SystemExit(
            f"{enzymes_tsv}: enzyme {enzyme} not found; cannot build "
            "DDRADSEQTOOLS fallback token"
        )
    motif, cut_offset = defs[enzyme]
    if not iupac_re.fullmatch(motif):
        raise SystemExit(
            f"{enzymes_tsv}: enzyme {enzyme} has unsupported motif {motif!r}"
        )
    if cut_offset < 0 or cut_offset > len(motif):
        raise SystemExit(
            f"{enzymes_tsv}: enzyme {enzyme} cut_offset outside motif length"
        )
    return motif[:cut_offset] + "*" + motif[cut_offset:]


ids = known_ddradseqtools_ids(restrictionsites)
defs = read_enzyme_defs(enzymes_tsv)
tokens: list[str] = []
for enzyme in (enzyme1, enzyme2):
    if enzyme in ids:
        tokens.extend([enzyme, "id"])
    else:
        tokens.extend([star_marked_site(enzyme, defs), "star_sequence"])
print("\t".join(tokens))
PYENZ
)


COMMAND=(
  python3 "$PACKAGE_ABS/rsitesearch.py"
  "--genfile=$INPUT_ABS"
  "--fragsfile=$FRAGS_ABS"
  "--rsfile=$RSFILE_ABS"
  "--enzyme1=$DDRADSEQTOOLS_ENZYME1"
  "--enzyme2=$DDRADSEQTOOLS_ENZYME2"
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
  echo "ddradseqtools_enzyme1=$DDRADSEQTOOLS_ENZYME1"
  echo "ddradseqtools_enzyme2=$DDRADSEQTOOLS_ENZYME2"
  echo "ddradseqtools_enzyme1_mode=$DDRADSEQTOOLS_ENZYME1_MODE"
  echo "ddradseqtools_enzyme2_mode=$DDRADSEQTOOLS_ENZYME2_MODE"
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
