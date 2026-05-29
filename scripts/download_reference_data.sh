#!/usr/bin/env bash
set -euo pipefail

DATASETS="config/datasets.tsv"
OUT="results/processed/reference_checksums.tsv"
FORCE="0"
DATASET_FILTER=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/download_reference_data.sh [options]

Options:
  --datasets PATH     Dataset TSV. Default: config/datasets.tsv
  --out PATH          Output checksum/status TSV. Default: results/processed/reference_checksums.tsv
  --dataset ID        Optional single dataset ID, or comma-separated IDs, to process.
  --force             Overwrite existing local files when a URL is available.
  -h, --help          Show this help.

Behavior:
  - Downloads only rows whose accession_or_url starts with http://, https://, or ftp://.
  - Does not overwrite existing files unless --force is supplied.
  - Computes SHA256 for any existing local file.
  - Treats TO_BE_FILLED, NA, blank URLs, and directory paths as placeholders.
  - Exits nonzero only on checksum mismatch or download failure.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --datasets)
      DATASETS="$2"
      shift 2
      ;;
    --out)
      OUT="$2"
      shift 2
      ;;
    --dataset)
      DATASET_FILTER="$2"
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

mkdir -p data/reference results/processed

python3 - "$DATASETS" "$OUT" "$FORCE" "$DATASET_FILTER" <<'PY'
from __future__ import annotations

import csv
import hashlib
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

datasets_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
force = sys.argv[3] == "1"
dataset_filter_raw = sys.argv[4].strip()

if dataset_filter_raw:
    dataset_filter = {x.strip() for x in dataset_filter_raw.split(",") if x.strip()}
else:
    dataset_filter = None

PLACEHOLDERS = {"", "NA", "N/A", "TO_BE_FILLED", "TBD", "NONE", "NULL"}


def is_url(value: str) -> bool:
    lower = value.lower()
    return lower.startswith(("http://", "https://", "ftp://"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_url(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(prefix=dest.name + ".", suffix=".tmp", dir=str(dest.parent))
    os.close(fd)
    tmp_path = Path(tmp_name)

    try:
        with urllib.request.urlopen(url) as response, tmp_path.open("wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        tmp_path.replace(dest)
    except Exception:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def row_value(row: dict[str, str], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value is not None:
            return value.strip()
    return ""


if not datasets_path.exists():
    raise SystemExit(f"error: dataset table not found: {datasets_path}")

out_path.parent.mkdir(parents=True, exist_ok=True)

status_rows: list[dict[str, str]] = []
had_error = False

with datasets_path.open(newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    for row in reader:
        dataset = row_value(row, "dataset_id", "dataset")
        species = row_value(row, "species")
        assembly = row_value(row, "assembly")
        url = row_value(row, "accession_or_url", "url", "accession")
        local_path_raw = row_value(row, "local_path")
        expected = row_value(row, "expected_sha256", "expected_SHA256", "sha256")

        if dataset_filter is not None and dataset not in dataset_filter:
            continue

        status = "skipped"
        message = ""
        observed = ""

        if not dataset:
            status = "skipped_bad_row"
            message = "missing dataset identifier"
            dest = Path("")
        elif not local_path_raw:
            status = "skipped_bad_row"
            message = "missing local_path"
            dest = Path("")
        else:
            dest = Path(local_path_raw)

            # Directory-style entries are placeholders for empirical datasets or folders.
            if local_path_raw.endswith("/") or (dest.exists() and dest.is_dir()):
                dest.mkdir(parents=True, exist_ok=True)
                status = "skipped_directory"
                message = "local_path is a directory placeholder"
            elif dest.exists() and not force:
                observed = sha256_file(dest)
                status = "exists"
                message = "existing file not overwritten"
            elif is_url(url):
                try:
                    download_url(url, dest)
                    observed = sha256_file(dest)
                    status = "downloaded" if not force else "downloaded_force"
                    message = "download completed"
                except Exception as exc:
                    status = "download_failed"
                    message = str(exc)
                    had_error = True
            else:
                if dest.exists():
                    observed = sha256_file(dest)
                    status = "exists"
                    message = "existing file; no URL needed"
                else:
                    status = "missing_no_url"
                    message = "no downloadable URL; fill accession_or_url/local file manually"

        if observed and expected and expected not in PLACEHOLDERS:
            if observed.lower() != expected.lower():
                status = "checksum_mismatch"
                message = f"expected {expected}, observed {observed}"
                had_error = True
            else:
                if status == "exists":
                    message = "existing file checksum matches expected SHA256"
                elif status.startswith("downloaded"):
                    message = "downloaded file checksum matches expected SHA256"

        status_rows.append(
            {
                "dataset": dataset,
                "species": species,
                "assembly": assembly,
                "accession_or_url": url,
                "local_path": local_path_raw,
                "expected_sha256": expected,
                "observed_sha256": observed,
                "status": status,
                "message": message,
            }
        )

fieldnames = [
    "dataset",
    "species",
    "assembly",
    "accession_or_url",
    "local_path",
    "expected_sha256",
    "observed_sha256",
    "status",
    "message",
]

with out_path.open("w", newline="", encoding="utf-8") as out_handle:
    writer = csv.DictWriter(out_handle, delimiter="\t", fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(status_rows)

print(f"wrote {out_path} with {len(status_rows)} dataset status row(s)", file=sys.stderr)

raise SystemExit(1 if had_error else 0)
PY
