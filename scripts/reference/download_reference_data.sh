#!/usr/bin/env bash
set -euo pipefail

DATASETS="config/datasets.tsv"
OUT="results/processed/reference_checksums.tsv"
DATASET_FILTER=""
FORCE="0"
PREPARE_PLAIN="0"
NCBI_PACKAGE_DIR="data/reference/ncbi_packages"

usage() {
  cat <<'USAGE'
Usage:
  scripts/reference/download_reference_data.sh [options]

Options:
  --datasets PATH       Dataset TSV. Default: config/datasets.tsv
  --out PATH            Output status/checksum TSV.
                        Default: results/processed/reference_checksums.tsv
  --dataset IDS         Optional dataset ID or comma-separated IDs to process.
  --force               Overwrite existing files.
  --prepare-plain       For .gz FASTA outputs, also write uncompressed .fa.
  --ncbi-package-dir D  Directory for NCBI ZIP packages.
                        Default: data/reference/ncbi_packages
  -h, --help            Show this help.

Input TSV requirements:
  Must contain either dataset_id or dataset, plus:
    species
    assembly
    accession_or_url
    local_path
    expected_sha256 or sha256

Supported accession_or_url values:
  - GCA_* or GCF_*: downloaded with NCBI Datasets CLI
  - http(s)/ftp URL: downloaded directly
  - MANUAL_LOCAL_DATA, TO_BE_FILLED, NA, blank: checked/skipped

Outputs:
  - local FASTA at local_path
  - optional uncompressed FASTA if --prepare-plain and local_path ends .gz
  - checksum/status table at --out
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --datasets) DATASETS="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --dataset) DATASET_FILTER="$2"; shift 2 ;;
    --force) FORCE="1"; shift ;;
    --prepare-plain) PREPARE_PLAIN="1"; shift ;;
    --ncbi-package-dir) NCBI_PACKAGE_DIR="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

mkdir -p data/reference results/processed "$NCBI_PACKAGE_DIR"

python3 - \
  "$DATASETS" \
  "$OUT" \
  "$DATASET_FILTER" \
  "$FORCE" \
  "$PREPARE_PLAIN" \
  "$NCBI_PACKAGE_DIR" <<'PY'
from __future__ import annotations

import csv
import gzip
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

datasets_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
dataset_filter_raw = sys.argv[3].strip()
force = sys.argv[4] == "1"
prepare_plain = sys.argv[5] == "1"
ncbi_package_dir = Path(sys.argv[6])

PLACEHOLDERS = {
    "",
    "NA",
    "N/A",
    "TO_BE_FILLED",
    "TBD",
    "NONE",
    "NULL",
    "MANUAL_LOCAL_DATA",
}

if dataset_filter_raw:
    dataset_filter = {x.strip() for x in dataset_filter_raw.split(",") if x.strip()}
else:
    dataset_filter = None


def is_url(value: str) -> bool:
    return value.lower().startswith(("http://", "https://", "ftp://"))


def is_ncbi_accession(value: str) -> bool:
    return value.startswith(("GCA_", "GCF_"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def plain_path_for(path: Path) -> Path:
    if path.name.endswith(".gz"):
        return path.with_name(path.name[:-3])
    return path


def write_plain_from_gzip(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    with gzip.open(src, "rb") as inp, tmp.open("wb") as out:
        shutil.copyfileobj(inp, out)
    tmp.replace(dst)


def gzip_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    with src.open("rb") as inp, gzip.open(tmp, "wb", compresslevel=6) as out:
        shutil.copyfileobj(inp, out)
    tmp.replace(dst)


def copy_or_compress_fasta(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.name.endswith(".gz"):
        gzip_copy(src, dst)
    else:
        tmp = dst.with_name(dst.name + ".tmp")
        shutil.copyfile(src, tmp)
        tmp.replace(dst)


def download_url(url: str, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    with urllib.request.urlopen(url) as response, tmp.open("wb") as out:
        shutil.copyfileobj(response, out)
    tmp.replace(dst)


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(
            f"required command not found: {name}. "
            "Install it with envs/benchmark.yml or conda-forge ncbi-datasets-cli."
        )


def find_genomic_fasta(extract_dir: Path) -> Path:
    candidates = []
    for pattern in (
        "*_genomic.fna",
        "*_genomic.fna.gz",
        "*.fna",
        "*.fna.gz",
        "*.fa",
        "*.fa.gz",
        "*.fasta",
        "*.fasta.gz",
    ):
        candidates.extend(extract_dir.rglob(pattern))

    candidates = sorted(
        path
        for path in candidates
        if path.is_file() and "protein" not in path.name.lower()
    )

    if not candidates:
        raise RuntimeError(f"no genomic FASTA found under {extract_dir}")

    return candidates[0]


def normalize_fasta_to_plain(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")

    if src.name.endswith(".gz"):
        opener = gzip.open
    else:
        opener = open

    with opener(src, "rt", encoding="utf-8", errors="replace") as inp, tmp.open(
        "w",
        encoding="utf-8",
    ) as out:
        for line in inp:
            out.write(line)

    tmp.replace(dst)


def download_ncbi_genome(accession: str, dataset_id: str, dst: Path) -> Path:
    require_command("datasets")

    zip_path = ncbi_package_dir / f"{dataset_id}__{accession}.zip"
    if force or not zip_path.exists():
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "datasets",
            "download",
            "genome",
            "accession",
            accession,
            "--include",
            "genome",
            "--filename",
            str(zip_path),
        ]
        subprocess.run(cmd, check=True)

    with tempfile.TemporaryDirectory(prefix=f"{dataset_id}.ncbi.") as tmpdir_raw:
        tmpdir = Path(tmpdir_raw)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmpdir)

        fasta = find_genomic_fasta(tmpdir)
        if fasta.name.endswith(".gz"):
            plain = tmpdir / "genomic.fna"
            normalize_fasta_to_plain(fasta, plain)
            fasta = plain

        copy_or_compress_fasta(fasta, dst)

        # Keep small package metadata for provenance if present.
        metadata_dir = Path("results/processed/reference_metadata") / dataset_id
        metadata_dir.mkdir(parents=True, exist_ok=True)
        for meta_name in ("assembly_data_report.jsonl", "dataset_catalog.json"):
            for meta in tmpdir.rglob(meta_name):
                shutil.copyfile(meta, metadata_dir / meta_name)
                break

    return zip_path


def row_get(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value.strip()
    return ""


def process_row(row: dict[str, str]) -> dict[str, str]:
    dataset_id = row_get(row, "dataset_id", "dataset")
    species = row_get(row, "species")
    assembly = row_get(row, "assembly")
    accession = row_get(row, "accession_or_url")
    local_raw = row_get(row, "local_path")
    expected = row_get(row, "expected_sha256", "sha256")

    result = {
        "dataset": dataset_id,
        "species": species,
        "assembly": assembly,
        "accession_or_url": accession,
        "source_type": "",
        "local_path": local_raw,
        "plain_path": "",
        "expected_sha256": expected,
        "observed_sha256": "",
        "plain_sha256": "",
        "status": "",
        "message": "",
        "package_zip": "",
    }

    if not dataset_id:
        result["status"] = "skipped"
        result["message"] = "blank dataset id"
        return result

    if not local_raw:
        result["status"] = "missing_local_path"
        result["message"] = "local_path is blank"
        return result

    local_path = Path(local_raw)

    if local_raw.endswith("/"):
        result["status"] = "skipped_directory"
        result["message"] = "local_path is a directory placeholder"
        return result

    accession_upper = accession.upper()

    try:
        if accession_upper in PLACEHOLDERS:
            result["source_type"] = "manual_or_placeholder"
            if local_path.exists():
                result["observed_sha256"] = sha256_file(local_path)
                result["status"] = "exists"
                result["message"] = "existing local file; no accession/URL download"
            else:
                result["status"] = "missing_no_download_source"
                result["message"] = "no URL or NCBI accession provided"
            return result

        if local_path.exists() and not force:
            result["observed_sha256"] = sha256_file(local_path)
            result["status"] = "exists"
            result["message"] = "existing file not overwritten"
        elif is_ncbi_accession(accession):
            result["source_type"] = "ncbi_datasets_accession"
            package_zip = download_ncbi_genome(accession, dataset_id, local_path)
            result["package_zip"] = str(package_zip)
            result["observed_sha256"] = sha256_file(local_path)
            result["status"] = "downloaded"
            result["message"] = "downloaded with NCBI Datasets CLI"
        elif is_url(accession):
            result["source_type"] = "url"
            download_url(accession, local_path)
            result["observed_sha256"] = sha256_file(local_path)
            result["status"] = "downloaded"
            result["message"] = "downloaded direct URL"
        else:
            result["source_type"] = "unknown"
            if local_path.exists():
                result["observed_sha256"] = sha256_file(local_path)
                result["status"] = "exists"
                result["message"] = "existing local file; accession_or_url not recognized"
            else:
                result["status"] = "missing_unrecognized_source"
                result["message"] = f"unrecognized accession_or_url: {accession}"
            return result

        if prepare_plain and local_path.name.endswith(".gz"):
            plain = plain_path_for(local_path)
            if force or not plain.exists():
                write_plain_from_gzip(local_path, plain)
            result["plain_path"] = str(plain)
            result["plain_sha256"] = sha256_file(plain)

        if expected and expected.upper() not in PLACEHOLDERS:
            if result["observed_sha256"] != expected:
                result["status"] = "checksum_mismatch"
                result["message"] = (
                    f"expected {expected}, observed {result['observed_sha256']}"
                )

    except Exception as exc:
        result["status"] = "error"
        result["message"] = str(exc)

    return result


if not datasets_path.exists():
    raise SystemExit(f"dataset table not found: {datasets_path}")

with datasets_path.open(newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    rows = list(reader)

out_rows = []
for row in rows:
    dataset_id = row_get(row, "dataset_id", "dataset")
    if dataset_filter is not None and dataset_id not in dataset_filter:
        continue
    out_rows.append(process_row(row))

fields = [
    "dataset",
    "species",
    "assembly",
    "accession_or_url",
    "source_type",
    "local_path",
    "plain_path",
    "expected_sha256",
    "observed_sha256",
    "plain_sha256",
    "status",
    "message",
    "package_zip",
]

out_path.parent.mkdir(parents=True, exist_ok=True)
with out_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
    writer.writeheader()
    writer.writerows(out_rows)

bad = [row for row in out_rows if row["status"] in {"error", "checksum_mismatch"}]

print(f"wrote {out_path} with {len(out_rows)} dataset status row(s)", file=sys.stderr)

if bad:
    for row in bad:
        print(
            f"ERROR {row['dataset']}: {row['status']}: {row['message']}",
            file=sys.stderr,
        )
    raise SystemExit(1)
PY
