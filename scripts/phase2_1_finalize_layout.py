#!/usr/bin/env python3
"""Finalize Phase 2 script-layout migration.

This is a conservative cleanup after moving script implementations into
category subdirectories while leaving top-level compatibility wrappers.

It fixes common follow-on issues:
  1. rewrites top-level Python wrappers so Ruff line-length checks pass;
  2. adds __init__.py files so Mypy sees distinct module names;
  3. ignores .phase2_backups/ and .phase2_1_backups/ in .gitignore;
  4. patches audit_reproducibility.py so .PHONY is not treated as a duplicate
     Makefile target.

Default mode is dry-run. Use --apply to modify files.
"""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
from pathlib import Path

SCRIPT_SUBDIRS = [
    "core",
    "reference",
    "validation",
    "comparators",
    "benchmarks",
    "empirical",
    "manuscript",
]


WRAPPER_TEMPLATE = """#!/usr/bin/env python3
\"\"\"Compatibility wrapper for ``{target}``.

The implementation was moved during repository layout cleanup. This wrapper is
kept so existing Makefile, Snakemake, and documentation paths continue to work.
\"\"\"

from __future__ import annotations

import runpy
from pathlib import Path


TARGET = Path(__file__).resolve().parent / "{subdir}" / "{name}"


if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
"""


def repo_root_check() -> None:
    required = ["Makefile", "scripts", ".gitignore"]
    missing = [item for item in required if not Path(item).exists()]
    if missing:
        raise SystemExit("Run from the repository root. Missing: " + ", ".join(missing))


def backup(path: Path, backup_root: Path) -> Path | None:
    if not path.exists():
        return None
    dst = backup_root / path
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)
    return dst


def write_if_changed(
    path: Path,
    text: str,
    *,
    apply: bool,
    backup_root: Path,
    messages: list[str],
) -> None:
    old = path.read_text() if path.exists() else None
    if old == text:
        messages.append(f"unchanged {path}")
        return

    if apply:
        old_backup = backup(path, backup_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        if old_backup is None:
            messages.append(f"created {path}")
        else:
            messages.append(f"updated {path}; backup {old_backup}")
    else:
        verb = "would update" if path.exists() else "would create"
        messages.append(f"{verb} {path}")


def find_moved_implementation(root_script: Path) -> Path | None:
    matches = []
    for subdir in SCRIPT_SUBDIRS:
        candidate = root_script.parent / subdir / root_script.name
        if candidate.exists():
            matches.append(candidate)

    if len(matches) == 1:
        return matches[0]

    return None


def rewrite_python_wrappers(
    *,
    apply: bool,
    backup_root: Path,
    messages: list[str],
) -> None:
    scripts_dir = Path("scripts")

    for root_script in sorted(scripts_dir.glob("*.py")):
        implementation = find_moved_implementation(root_script)
        if implementation is None:
            continue

        subdir = implementation.parent.name
        target = f"scripts/{subdir}/{root_script.name}"

        wrapper = WRAPPER_TEMPLATE.format(
            target=target,
            subdir=subdir,
            name=root_script.name,
        )

        write_if_changed(
            root_script,
            wrapper,
            apply=apply,
            backup_root=backup_root,
            messages=messages,
        )


def add_init_files(
    *,
    apply: bool,
    backup_root: Path,
    messages: list[str],
) -> None:
    for path in [Path("scripts")] + [Path("scripts") / d for d in SCRIPT_SUBDIRS]:
        if not path.exists():
            continue
        init = path / "__init__.py"
        write_if_changed(
            init,
            '"""Script namespace for type checking only."""\n',
            apply=apply,
            backup_root=backup_root,
            messages=messages,
        )


def patch_gitignore(
    *,
    apply: bool,
    backup_root: Path,
    messages: list[str],
) -> None:
    path = Path(".gitignore")
    text = path.read_text()

    additions = []
    for item in [".phase1_backups/", ".phase2_backups/", ".phase2_1_backups/"]:
        if item not in text:
            additions.append(item)

    if additions:
        text = text.rstrip() + "\n\n# Temporary backups written by polish scripts.\n"
        text += "\n".join(additions) + "\n"

    write_if_changed(
        path,
        text,
        apply=apply,
        backup_root=backup_root,
        messages=messages,
    )


def patch_audit_phony(
    *,
    apply: bool,
    backup_root: Path,
    messages: list[str],
) -> None:
    candidates = [
        Path("scripts/core/audit_reproducibility.py"),
        Path("scripts/audit_reproducibility.py"),
    ]

    for path in candidates:
        if not path.exists():
            continue

        text = path.read_text()

        if "duplicate_make_target" not in text:
            continue

        if 'line.startswith(".")' in text or 'line.startswith(".PHONY")' in text:
            messages.append(f"audit .PHONY handling already present in {path}")
            continue

        old = '    if line.startswith((" ", "\\t", "#")):\n        return False\n'
        new = (
            '    if line.startswith((" ", "\\t", "#")):\n'
            "        return False\n"
            '    if line.startswith("."):\n'
            "        return False\n"
        )

        if old not in text:
            messages.append(
                f"warning: could not patch .PHONY handling automatically in {path}"
            )
            continue

        patched = text.replace(old, new, 1)

        write_if_changed(
            path,
            patched,
            apply=apply,
            backup_root=backup_root,
            messages=messages,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Modify files. Default is dry-run.",
    )
    args = parser.parse_args()

    repo_root_check()

    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = Path(".phase2_1_backups") / timestamp

    messages: list[str] = []
    messages.append("mode=" + ("APPLY" if args.apply else "DRY-RUN"))

    rewrite_python_wrappers(
        apply=args.apply,
        backup_root=backup_root,
        messages=messages,
    )
    add_init_files(
        apply=args.apply,
        backup_root=backup_root,
        messages=messages,
    )
    patch_gitignore(
        apply=args.apply,
        backup_root=backup_root,
        messages=messages,
    )
    patch_audit_phony(
        apply=args.apply,
        backup_root=backup_root,
        messages=messages,
    )

    print("\n".join(messages))

    if not args.apply:
        print("\nNo files were modified. Re-run with --apply to write changes.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
