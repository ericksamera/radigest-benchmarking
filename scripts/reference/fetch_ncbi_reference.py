#!/usr/bin/env python3
"""Fetch one public genome reference declared in config/references.tsv.

The primary path uses the NCBI Datasets CLI because it keeps accession-based
reference acquisition explicit and avoids hard-coding changing FTP layouts.
The script extracts the genomic FASTA from the NCBI package and writes a
normalized, deterministic gzip FASTA at the requested output path.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

REQUIRED_COLUMNS = [
    "reference_id",
    "display_name",
    "accession",
    "source_type",
    "output_gzip",
    "output_plain",
    "required_for_nonempirical",
    "notes",
]

PLACEHOLDERS = {"", "NA", "N/A", "NONE", "NULL", "TO_BE_FILLED", "TBD"}


def read_manifest(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames
        if fieldnames is None:
            raise ValueError(f"{path}: missing header")
        missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(missing)}")
        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            if not any((value or "").strip() for value in row.values()):
                continue
            cleaned = {key: (row.get(key) or "").strip() for key in REQUIRED_COLUMNS}
            reference_id = cleaned["reference_id"]
            if not reference_id:
                raise ValueError(f"{path}: blank reference_id")
            if reference_id in rows:
                raise ValueError(f"{path}: duplicate reference_id {reference_id!r}")
            rows[reference_id] = cleaned
    if not rows:
        raise ValueError(f"{path}: no reference rows")
    return rows


def require_command(command: str) -> None:
    if shutil.which(command) is None:
        raise RuntimeError(
            f"required command not found: {command}. Install the Snakemake "
            "reference environment from workflow/envs/reference.yml, or install "
            "the NCBI Datasets CLI in the active environment."
        )


def is_url(value: str) -> bool:
    return value.lower().startswith(("http://", "https://", "ftp://"))


def download_url(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_name(output.name + ".tmp")
    with urllib.request.urlopen(url) as response, tmp.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    tmp.replace(output)


def find_genomic_fasta(extract_dir: Path) -> Path:
    candidates: list[Path] = []
    for pattern in (
        "*_genomic.fna",
        "*_genomic.fna.gz",
        "*.genomic.fna",
        "*.genomic.fna.gz",
        "*.fna",
        "*.fna.gz",
        "*.fa",
        "*.fa.gz",
        "*.fasta",
        "*.fasta.gz",
    ):
        candidates.extend(extract_dir.rglob(pattern))

    def usable(path: Path) -> bool:
        name = path.name.lower()
        blocked = ("protein", "cds_from_genomic", "rna_from_genomic", "rna.fna")
        return path.is_file() and not any(token in name for token in blocked)

    usable_candidates = sorted(path for path in candidates if usable(path))
    if not usable_candidates:
        raise RuntimeError(
            f"no genomic FASTA found under extracted package {extract_dir}"
        )
    return usable_candidates[0]


def copy_to_plain(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    if src.name.endswith(".gz"):
        with gzip.open(src, "rb") as inp, tmp.open("wb") as out:
            shutil.copyfileobj(inp, out)
    else:
        shutil.copyfile(src, tmp)
    tmp.replace(dst)


def gzip_plain(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    with src.open("rb") as inp, tmp.open("wb") as raw_out:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=raw_out,
            compresslevel=6,
            mtime=0,
        ) as gz_out:
            shutil.copyfileobj(inp, gz_out)
    tmp.replace(dst)


def looks_like_fasta(path: Path) -> bool:
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            return line.startswith(">")
    return False


def download_ncbi_package(
    accession: str,
    package_zip: Path,
    force: bool,
    retries: int,
    retry_wait_seconds: float,
) -> None:
    require_command("datasets")
    if package_zip.exists() and not force:
        return
    package_zip.parent.mkdir(parents=True, exist_ok=True)
    tmp_zip = package_zip.with_name(package_zip.name + ".tmp")
    cmd = [
        "datasets",
        "download",
        "genome",
        "accession",
        accession,
        "--include",
        "genome",
        "--filename",
        str(tmp_zip),
    ]
    last_error: subprocess.CalledProcessError | None = None
    for attempt in range(1, retries + 1):
        if tmp_zip.exists():
            tmp_zip.unlink()
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as exc:
            last_error = exc
            if tmp_zip.exists():
                tmp_zip.unlink()
            if attempt >= retries:
                break
            delay = retry_wait_seconds * (2 ** (attempt - 1))
            print(
                f"warning: datasets download failed for {accession} "
                f"(attempt {attempt}/{retries}, exit {exc.returncode}); "
                f"retrying in {delay:.1f}s",
                file=sys.stderr,
            )
            time.sleep(delay)
            continue
        if not tmp_zip.exists() or tmp_zip.stat().st_size == 0:
            if tmp_zip.exists():
                tmp_zip.unlink()
            raise RuntimeError(
                f"datasets download for {accession} produced an empty package"
            )
        tmp_zip.replace(package_zip)
        return
    if last_error is not None:
        raise RuntimeError(
            f"datasets download failed for {accession} after {retries} attempts"
        ) from last_error
    raise RuntimeError(f"datasets download failed for {accession}")


def copy_package_metadata(extract_dir: Path, reference_id: str) -> None:
    metadata_dir = Path("results/references/metadata") / reference_id
    metadata_dir.mkdir(parents=True, exist_ok=True)
    for name in ("assembly_data_report.jsonl", "dataset_catalog.json"):
        for candidate in extract_dir.rglob(name):
            if candidate.is_file():
                shutil.copyfile(candidate, metadata_dir / name)
                break


def fetch_ncbi(
    row: dict[str, str],
    output: Path,
    force: bool,
    retries: int,
    retry_wait_seconds: float,
) -> None:
    reference_id = row["reference_id"]
    accession = row["accession"]
    if accession.upper() in PLACEHOLDERS:
        raise ValueError(f"{reference_id}: missing NCBI accession")

    package_zip = (
        Path("data/reference/ncbi_packages") / f"{reference_id}__{accession}.zip"
    )
    download_ncbi_package(
        accession,
        package_zip,
        force=force,
        retries=retries,
        retry_wait_seconds=retry_wait_seconds,
    )

    with tempfile.TemporaryDirectory(prefix=f"{reference_id}.ncbi.") as tmp_raw:
        tmpdir = Path(tmp_raw)
        with zipfile.ZipFile(package_zip) as package:
            package.extractall(tmpdir)
        fasta = find_genomic_fasta(tmpdir)
        plain = tmpdir / f"{reference_id}.fa"
        copy_to_plain(fasta, plain)
        if not looks_like_fasta(plain):
            raise RuntimeError(f"{reference_id}: extracted file is not FASTA: {fasta}")
        gzip_plain(plain, output)
        copy_package_metadata(tmpdir, reference_id)


def fetch_url(row: dict[str, str], output: Path, force: bool) -> None:
    url = row["accession"]
    if not is_url(url):
        raise ValueError(f"{row['reference_id']}: accession is not a URL: {url}")
    if output.exists() and not force:
        return
    with tempfile.TemporaryDirectory(prefix=f"{row['reference_id']}.url.") as tmp_raw:
        tmpdir = Path(tmp_raw)
        downloaded = tmpdir / Path(url).name
        download_url(url, downloaded)
        plain = tmpdir / f"{row['reference_id']}.fa"
        copy_to_plain(downloaded, plain)
        if not looks_like_fasta(plain):
            raise RuntimeError(f"{row['reference_id']}: downloaded file is not FASTA")
        gzip_plain(plain, output)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("config/references.tsv"))
    parser.add_argument("--reference-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--download-retries",
        type=int,
        default=5,
        help="number of attempts for NCBI datasets downloads (default: 5)",
    )
    parser.add_argument(
        "--download-retry-wait-seconds",
        type=float,
        default=15.0,
        help="initial wait between NCBI datasets download retries; doubles after each failure",
    )
    args = parser.parse_args(argv)

    try:
        if args.download_retries < 1:
            raise ValueError("--download-retries must be >= 1")
        if args.download_retry_wait_seconds < 0:
            raise ValueError("--download-retry-wait-seconds must be >= 0")

        rows = read_manifest(args.manifest)
        if args.reference_id not in rows:
            raise ValueError(
                f"unknown reference_id {args.reference_id!r} in {args.manifest}"
            )
        row = rows[args.reference_id]
        expected_output = Path(row["output_gzip"])
        if expected_output != args.output:
            raise ValueError(
                f"{args.reference_id}: rule output {args.output} does not match "
                f"manifest output_gzip {expected_output}"
            )
        if args.output.exists() and not args.force:
            print(f"exists: {args.output}")
            return 0
        source_type = row["source_type"]
        if source_type == "ncbi_datasets":
            fetch_ncbi(
                row,
                args.output,
                force=args.force,
                retries=args.download_retries,
                retry_wait_seconds=args.download_retry_wait_seconds,
            )
        elif source_type == "url":
            fetch_url(row, args.output, force=args.force)
        else:
            raise ValueError(
                f"{args.reference_id}: unsupported source_type {source_type!r}"
            )
        print(f"wrote {args.output}")
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
