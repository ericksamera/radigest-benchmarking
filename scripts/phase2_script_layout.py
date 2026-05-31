#!/usr/bin/env python3
"""Phase 2 script-layout polish for radigest comparison workflows.

Conservative goals:
  1. Create category subdirectories under scripts/.
  2. Move selected implementation scripts into category subdirectories.
  3. Leave compatibility wrappers at the original scripts/<name> paths.
  4. Add scripts/README.md and docs/script_inventory.md.
  5. Optionally patch Makefile's Python compile check to recurse into subdirs.

Default mode is dry-run. Use --apply to modify files.

This script intentionally does not rewrite Snakefiles or Makefile targets to use
new script paths. Compatibility wrappers keep existing commands working.
"""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MoveSpec:
    source: str
    category: str


MOVE_SPECS = [
    MoveSpec("capture_environment.sh", "core"),
    MoveSpec("ensure_radigest.sh", "core"),
    MoveSpec("audit_reproducibility.py", "core"),
    MoveSpec("phase1_polish_repository.py", "core"),
    MoveSpec("download_reference_data.sh", "reference"),
    MoveSpec("summarize_fasta.py", "reference"),
    MoveSpec("update_dataset_sha256.py", "reference"),
    MoveSpec("prepare_plain_reference.sh", "reference"),
    MoveSpec("validate_synthetic.py", "validation"),
    MoveSpec("normalize_radigest_tsv.py", "validation"),
    MoveSpec("compare_interval_sets.py", "validation"),
    MoveSpec("diagnose_interval_mismatch.py", "validation"),
    # Comparator R scripts are intentionally left at top level for now.
    MoveSpec("install_ddgrader.sh", "comparators"),
    MoveSpec("install_ddradseqtools.sh", "comparators"),
    MoveSpec("install_digital_rads.sh", "comparators"),
    MoveSpec("run_digital_rads.sh", "comparators"),
    MoveSpec("run_ddradseqtools_rsitesearch.sh", "comparators"),
    MoveSpec("run_ddgrader_backend.py", "comparators"),
    MoveSpec("probe_ddradseqtools.sh", "comparators"),
    MoveSpec("normalize_digital_rads.py", "comparators"),
    MoveSpec("normalize_ddradseqtools_fragments.py", "comparators"),
    MoveSpec("compare_radigest_simrad_counts.py", "comparators"),
    MoveSpec("compare_radigest_ddradseqtools_counts.py", "comparators"),
    MoveSpec("compare_binned_fragment_tables.py", "comparators"),
    MoveSpec("summarize_ddradseqtools_fragments.py", "comparators"),
    MoveSpec("summarize_ddradseqtools_timing.py", "comparators"),
    MoveSpec("add_ddradseqtools_timing.py", "comparators"),
    MoveSpec("run_matched_tool_benchmarks.sh", "benchmarks"),
    MoveSpec("run_radigest_thread_scaling.sh", "benchmarks"),
    MoveSpec("run_screening_speed_benchmark.sh", "benchmarks"),
    MoveSpec("build_benchmark_table.py", "benchmarks"),
    MoveSpec("build_tool_timing_interpretation_table.py", "benchmarks"),
    MoveSpec("check_benchmark_completeness.py", "benchmarks"),
    MoveSpec("compare_input_format_benchmark.py", "benchmarks"),
    MoveSpec("summarize_matched_tool_benchmarks.py", "benchmarks"),
    MoveSpec("summarize_screening_speed.py", "benchmarks"),
    MoveSpec("summarize_radigest_json.py", "benchmarks"),
    MoveSpec("summarize_radigest_thread_scaling.py", "benchmarks"),
    MoveSpec("summarize_pair_screen.py", "benchmarks"),
    MoveSpec("summarize_pair_screen_scaling.py", "benchmarks"),
    MoveSpec("summarize_time_v.py", "benchmarks"),
    MoveSpec("bin_radigest_fragments.py", "benchmarks"),
    MoveSpec("make_enzyme_pair_list.py", "benchmarks"),
    MoveSpec("extract_bam_recovery_inputs.sh", "empirical"),
    MoveSpec("downsample_tlens_per_sample.py", "empirical"),
    MoveSpec("summarize_empirical_recovery.py", "empirical"),
    MoveSpec("model_args_from_fit.py", "empirical"),
    MoveSpec("check_bam_reference_compatibility.sh", "empirical"),
    MoveSpec("build_empirical_bam_manifest.py", "empirical"),
    MoveSpec("check_empirical_inputs.py", "empirical"),
    MoveSpec("make_manuscript_tables.py", "manuscript"),
    MoveSpec("make_figures.py", "manuscript"),
    MoveSpec("make_input_format_figures.py", "manuscript"),
    MoveSpec("make_pair_screen_figures.py", "manuscript"),
    MoveSpec("make_pair_screen_scaling_figures.py", "manuscript"),
    MoveSpec("make_screening_speed_figures.py", "manuscript"),
    MoveSpec("make_tool_comparison_figures.py", "manuscript"),
    MoveSpec("make_empirical_recovery_figures.py", "manuscript"),
]

CATEGORY_DESCRIPTIONS = {
    "core": "repository, environment, local radigest build, and audit helpers",
    "reference": "reference-data download, preparation, and summary helpers",
    "validation": "synthetic validation and interval comparison helpers",
    "comparators": "external tool installation, execution, and comparison helpers",
    "benchmarks": "benchmark execution and summary helpers",
    "empirical": "empirical TLEN recovery modelling helpers",
    "manuscript": "manuscript table and figure generation helpers",
}

COMPILE_PYTHON_TREE = r'''#!/usr/bin/env python3
"""Recursively compile Python scripts under one or more directories."""

from __future__ import annotations

import py_compile
import sys
from pathlib import Path


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    return bool(
        parts.intersection(
            {
                ".git",
                ".snakemake",
                ".mypy_cache",
                ".pytest_cache",
                ".ruff_cache",
                "__pycache__",
                ".phase1_backups",
                ".phase2_backups",
            }
        )
    )


def main(argv: list[str]) -> int:
    roots = [Path(arg) for arg in argv] if argv else [Path("scripts")]
    files: list[Path] = []

    for root in roots:
        if root.is_file() and root.suffix == ".py":
            files.append(root)
        elif root.exists():
            files.extend(sorted(root.rglob("*.py")))

    files = [path for path in files if not should_skip(path)]

    failed = False
    for path in files:
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            print(exc.msg, file=sys.stderr)
            failed = True

    if failed:
        return 1

    print(f"compiled {len(files)} Python file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''

SCRIPTS_README = """# Scripts layout

Scripts are grouped by workflow role.

The top-level `scripts/<name>` files may be compatibility wrappers that forward
to implementation scripts in subdirectories. Existing commands and Snakefiles can
continue to use the old paths while the codebase transitions to the new layout.

## Categories

| Directory | Purpose |
|---|---|
| `scripts/core/` | Repository, environment, local radigest build, and audit helpers |
| `scripts/reference/` | Reference download, preparation, checksum, and FASTA summary helpers |
| `scripts/validation/` | Synthetic validation and interval normalization/comparison helpers |
| `scripts/comparators/` | External comparator installation, execution, normalization, and comparison helpers |
| `scripts/benchmarks/` | Benchmark execution and summary helpers |
| `scripts/empirical/` | Empirical TLEN extraction, recovery fitting, and input checks |
| `scripts/manuscript/` | Manuscript table and figure generation |

## Compatibility wrappers

During the transition, compatibility wrappers are kept at the original
`scripts/<name>` paths. This avoids breaking Makefile targets, Snakefiles, and
documentation while keeping implementation code organized.

A later cleanup can patch workflows to call implementation paths directly and
remove wrappers once tests pass.
"""


def script_inventory_content(move_specs: list[MoveSpec]) -> str:
    rows = [
        "# Script inventory",
        "",
        "This file is generated by `scripts/phase2_script_layout.py`.",
        "",
        "| Original path | Implementation path | Category |",
        "|---|---|---|",
    ]
    for spec in sorted(move_specs, key=lambda s: (s.category, s.source)):
        rows.append(
            f"| `scripts/{spec.source}` | "
            f"`scripts/{spec.category}/{spec.source}` | "
            f"{spec.category} |"
        )
    rows.extend(
        [
            "",
            "Top-level script paths are kept as compatibility wrappers during the",
            "transition. Workflows can be updated to direct implementation paths in a",
            "later cleanup.",
            "",
        ]
    )
    return "\n".join(rows)


def require_repo_root() -> None:
    required = [Path("Makefile"), Path("scripts"), Path("workflow"), Path("config")]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(
            "This does not look like the radigest comparison repo root. "
            f"Missing: {', '.join(missing)}"
        )


def is_tracked(path: Path) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def git_mv_or_move(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if is_tracked(src):
        subprocess.run(["git", "mv", str(src), str(dst)], check=True)
    else:
        shutil.move(str(src), str(dst))


def make_wrapper(source: str, category: str) -> str:
    target = f"{category}/{source}"
    if source.endswith(".py"):
        return f'''#!/usr/bin/env python3
"""Compatibility wrapper for scripts/{target}."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

target = Path(__file__).resolve().parent / {category!r} / {source!r}
sys.argv[0] = str(target)
runpy.run_path(str(target), run_name="__main__")
'''
    if source.endswith(".sh"):
        return f"""#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "${{BASH_SOURCE[0]}}")/{target}" "$@"
"""
    return f"""#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "${{BASH_SOURCE[0]}}")/{target}" "$@"
"""


def chmod_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def backup(path: Path, backup_root: Path) -> None:
    if not path.exists():
        return
    dst = backup_root / path
    dst.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        shutil.copy2(path, dst)


def write_file(
    path: Path, content: str, apply: bool, backup_root: Path, messages: list[str]
) -> None:
    old = path.read_text() if path.exists() else None
    if old == content:
        messages.append(f"unchanged {path}")
        return
    if not apply:
        messages.append(
            ("would update " if path.exists() else "would create ") + str(path)
        )
        return
    backup(path, backup_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    messages.append(("updated " if old is not None else "created ") + str(path))


def patch_makefile(
    makefile: Path, apply: bool, backup_root: Path, messages: list[str]
) -> None:
    if not makefile.exists():
        messages.append("skip Makefile patch: Makefile missing")
        return
    text = makefile.read_text()
    original = text
    text = text.replace(
        "python3 -m py_compile scripts/*.py",
        "python3 scripts/core/compile_python_tree.py scripts",
    )
    text = text.replace(
        "python3 -m py_compile scripts/*.py\\",
        "python3 scripts/core/compile_python_tree.py scripts \\",
    )
    if text == original:
        messages.append("Makefile compile check unchanged")
        return
    if not apply:
        messages.append("would patch Makefile recursive Python compile check")
        return
    backup(makefile, backup_root)
    makefile.write_text(text)
    messages.append("patched Makefile recursive Python compile check")


def fix_bam_glob_shellcheck(
    path: Path, apply: bool, backup_root: Path, messages: list[str]
) -> None:
    if not path.exists():
        messages.append(f"skip SC2206 patch: {path} missing")
        return
    text = path.read_text()
    old = """shopt -s nullglob
bams=( $BAM_GLOB )
shopt -u nullglob
"""
    new = """mapfile -t bams < <(compgen -G "$BAM_GLOB" | sort)
"""
    if old not in text:
        messages.append(f"SC2206 pattern not found in {path}; no change")
        return
    text = text.replace(old, new)
    if not apply:
        messages.append(f"would patch SC2206 glob handling in {path}")
        return
    backup(path, backup_root)
    path.write_text(text)
    messages.append(f"patched SC2206 glob handling in {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--no-move",
        action="store_true",
        help="Write docs/helpers and patches, but do not move scripts.",
    )
    args = parser.parse_args(argv)
    require_repo_root()
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = Path(".phase2_backups") / timestamp
    messages: list[str] = [f"mode={'APPLY' if args.apply else 'DRY-RUN'}"]

    write_file(
        Path("scripts/README.md"), SCRIPTS_README, args.apply, backup_root, messages
    )
    write_file(
        Path("docs/script_inventory.md"),
        script_inventory_content(MOVE_SPECS),
        args.apply,
        backup_root,
        messages,
    )
    write_file(
        Path("scripts/core/compile_python_tree.py"),
        COMPILE_PYTHON_TREE,
        args.apply,
        backup_root,
        messages,
    )
    if args.apply and Path("scripts/core/compile_python_tree.py").exists():
        chmod_executable(Path("scripts/core/compile_python_tree.py"))
    fix_bam_glob_shellcheck(
        Path("scripts/check_bam_reference_compatibility.sh"),
        args.apply,
        backup_root,
        messages,
    )
    patch_makefile(Path("Makefile"), args.apply, backup_root, messages)
    for category in sorted(CATEGORY_DESCRIPTIONS):
        path = Path("scripts") / category
        if args.apply:
            path.mkdir(parents=True, exist_ok=True)
        messages.append(("ensure " if args.apply else "would ensure ") + str(path))
    if not args.no_move:
        for spec in MOVE_SPECS:
            src = Path("scripts") / spec.source
            dst = Path("scripts") / spec.category / spec.source
            if dst.exists() and src.exists():
                messages.append(f"skip {src}: both wrapper/source and {dst} exist")
                continue
            if dst.exists() and not src.exists():
                wrapper = make_wrapper(spec.source, spec.category)
                if args.apply:
                    src.write_text(wrapper)
                    chmod_executable(src)
                    messages.append(f"created missing wrapper {src}")
                else:
                    messages.append(f"would create missing wrapper {src}")
                continue
            if not src.exists():
                messages.append(f"skip missing {src}")
                continue
            if args.apply:
                backup(src, backup_root)
                git_mv_or_move(src, dst)
                src.write_text(make_wrapper(spec.source, spec.category))
                chmod_executable(src)
                chmod_executable(dst)
                messages.append(f"moved {src} -> {dst}; wrote compatibility wrapper")
            else:
                messages.append(f"would move {src} -> {dst}; write wrapper")
    print("\n".join(messages))
    if not args.apply:
        print("\nNo files were modified. Re-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
