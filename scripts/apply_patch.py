#!/usr/bin/env python3
"""Safely install a ZIP patch using paths relative to the repository root.

A single extra wrapper folder is automatically stripped. For example,
PokeDropWatch_Update/docs/app.js installs as docs/app.js.
"""
from __future__ import annotations

import argparse
import stat
import zipfile
from pathlib import Path, PurePosixPath

MAX_FILES = 1000
MAX_UNCOMPRESSED = 50 * 1024 * 1024
BLOCKED_TOP_LEVEL = {".git", "updates"}
REPOSITORY_ROOT_NAMES = {
    "docs", "monitor", "config", "scripts", "tests", "firebase",
    "README.md", ".gitignore", ".nojekyll",
}


def _clean_name(raw: str) -> PurePosixPath:
    normalized = raw.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    rel = PurePosixPath(normalized)
    if (
        rel.is_absolute()
        or not rel.parts
        or any(part in {"", ".", ".."} for part in rel.parts)
    ):
        raise ValueError(f"Unsafe path in ZIP: {raw}")
    return rel


def _select_prefix(entries: list[zipfile.ZipInfo]) -> str:
    """Strip one obvious project-folder wrapper, but retain real repo paths."""
    files = [entry for entry in entries if not entry.is_dir()]
    if not files:
        return ""

    paths = [_clean_name(entry.filename) for entry in files]
    first_parts = {path.parts[0] for path in paths}
    if len(first_parts) != 1:
        return ""

    first = next(iter(first_parts))
    if first in REPOSITORY_ROOT_NAMES or first in BLOCKED_TOP_LEVEL or first == ".github":
        return ""

    # A wrapper is only stripped when the next path component is a known
    # repository root. This avoids turning a legitimate folder into a wrapper.
    has_known_child = any(
        len(path.parts) >= 2 and path.parts[1] in REPOSITORY_ROOT_NAMES
        for path in paths
    )
    if has_known_child and all(len(path.parts) >= 2 for path in paths):
        return first + "/"
    return ""


def apply_patch(archive: Path, root: Path) -> int:
    if not archive.is_file() or not zipfile.is_zipfile(archive):
        raise SystemExit(f"Not a valid ZIP file: {archive}")

    root = root.resolve()
    with zipfile.ZipFile(archive) as zf:
        entries = [entry for entry in zf.infolist() if not entry.is_dir()]
        if len(entries) > MAX_FILES:
            raise SystemExit(f"Patch rejected: more than {MAX_FILES} files.")
        if sum(entry.file_size for entry in entries) > MAX_UNCOMPRESSED:
            raise SystemExit("Patch rejected: expanded size exceeds 50 MB.")

        try:
            prefix = _select_prefix(entries)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        plan: list[tuple[zipfile.ZipInfo, Path]] = []
        for entry in entries:
            rel = _clean_name(entry.filename)
            raw_path = rel.as_posix()
            if prefix:
                if not raw_path.startswith(prefix):
                    continue
                raw_path = raw_path[len(prefix):]
                rel = _clean_name(raw_path)

            if rel.parts[0] in BLOCKED_TOP_LEVEL:
                raise SystemExit(f"Patch may not write into {rel.parts[0]}/")
            if len(rel.parts) >= 3 and rel.parts[:2] == (".github", "workflows"):
                raise SystemExit(
                    "Patch may not modify .github/workflows; edit the workflow directly in GitHub."
                )

            mode = (entry.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                raise SystemExit(f"Symlinks are not accepted in ZIP patches: {entry.filename}")

            destination = (root / Path(*rel.parts)).resolve()
            if root not in destination.parents:
                raise SystemExit(f"Unsafe destination: {entry.filename}")
            plan.append((entry, destination))

        if not plan:
            raise SystemExit("Patch ZIP did not contain any installable files.")

        for entry, destination in plan:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(entry, "r") as source, destination.open("wb") as target:
                while chunk := source.read(1024 * 1024):
                    target.write(chunk)
            print(f"Installed {destination.relative_to(root)}")

    print(f"Applied {len(plan)} file(s) from {archive.name}.")
    if prefix:
        print(f"Automatically removed ZIP wrapper folder: {prefix}")
    return len(plan)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    args = parser.parse_args()
    apply_patch(Path(args.archive), Path.cwd())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
