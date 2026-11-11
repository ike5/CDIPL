#!/usr/bin/env python3
"""Find files with identical contents in a folder (and its subfolders).

Files are compared by SHA-256 hash. To avoid reading every file, only files
that share a size with at least one other file are hashed.

Each set of duplicates is printed as a group, largest files first. The exit
status is 0 whether or not duplicates were found, and 1 on error.
"""

import argparse
import hashlib
import os
import sys
from collections import defaultdict
from pathlib import Path

CHUNK_SIZE = 1024 * 1024  # read files 1 MiB at a time


def warn(message):
    print(f"warning: {message}", file=sys.stderr)


def iter_files(folder, recursive):
    """Yield regular files under `folder`, skipping symbolic links."""
    if recursive:
        for dirpath, _dirnames, filenames in os.walk(folder, onerror=_walk_error):
            for name in filenames:
                path = Path(dirpath, name)
                if path.is_file() and not path.is_symlink():
                    yield path
    else:
        for path in folder.iterdir():
            if path.is_file() and not path.is_symlink():
                yield path


def _walk_error(exc):
    warn(f"cannot list {exc.filename}: {exc.strerror}")


def file_hash(path):
    """Return the SHA-256 hex digest of a file's contents."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def group_by_size(paths):
    """Map file size -> list of paths with that size."""
    by_size = defaultdict(list)
    for path in paths:
        try:
            by_size[path.stat().st_size].append(path)
        except OSError as exc:
            warn(f"skipping {path}: {exc.strerror}")
    return by_size


def find_duplicates(folder, recursive=True):
    """Return a list of (size, [paths]) groups whose contents are identical."""
    groups = []
    for size, same_size in group_by_size(iter_files(folder, recursive)).items():
        if len(same_size) < 2:
            continue  # a unique size cannot have a duplicate
        by_hash = defaultdict(list)
        for path in same_size:
            try:
                by_hash[file_hash(path)].append(path)
            except OSError as exc:
                warn(f"skipping {path}: {exc.strerror}")
        groups.extend(
            (size, sorted(paths)) for paths in by_hash.values() if len(paths) > 1
        )
    # Biggest files first, then by name so the output is stable.
    groups.sort(key=lambda group: (-group[0], group[1][0]))
    return groups


def print_groups(groups):
    """Print each duplicate group, then a one-line summary."""
    if not groups:
        print("No duplicate files found.")
        return
    for number, (size, paths) in enumerate(groups, start=1):
        print(f"Group {number}: {len(paths)} files, {size:,} bytes each")
        for path in paths:
            print(f"  {path}")
        print()
    wasted = sum(size * (len(paths) - 1) for size, paths in groups)
    print(f"{len(groups)} group(s) of duplicates; {wasted:,} bytes could be freed.")


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Find files with identical contents in a folder."
    )
    parser.add_argument("folder", type=Path, help="folder to search")
    parser.add_argument(
        "--no-recursive",
        dest="recursive",
        action="store_false",
        help="do not look inside subfolders",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not args.folder.is_dir():
        print(f"error: {args.folder} is not a folder", file=sys.stderr)
        return 1
    try:
        groups = find_duplicates(args.folder, args.recursive)
    except OSError as exc:
        print(f"error: cannot read {args.folder}: {exc.strerror}", file=sys.stderr)
        return 1
    print_groups(groups)
    return 0


if __name__ == "__main__":
    sys.exit(main())
