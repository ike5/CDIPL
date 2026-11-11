#!/usr/bin/env python3
"""Rename the files in a folder to PREFIX + zero-padded number + extension.

Files are numbered in name order, e.g. with prefix "trip_":
    beach.jpg -> trip_001.jpg,  notes.txt -> trip_002.txt

Only regular files directly inside the folder are renamed; sub-folders and
hidden files (names starting with ".") are left alone.

Usage: p04_rename_files.py folder prefix [--dry-run] [--start N] [--width N]
"""

import argparse
import os
import sys

MIN_WIDTH = 3


def list_files(folder):
    """Return the names of the visible regular files in `folder`, sorted."""
    with os.scandir(folder) as entries:
        names = [entry.name for entry in entries
                 if entry.is_file() and not entry.name.startswith(".")]
    return sorted(names, key=lambda name: (name.lower(), name))


def build_plan(names, prefix, start, width):
    """Return a list of (old_name, new_name) pairs, one per file."""
    last_number = start + len(names) - 1
    width = max(width, len(str(last_number)))  # never truncate a number
    plan = []
    for number, old_name in enumerate(names, start=start):
        extension = os.path.splitext(old_name)[1]
        plan.append((old_name, f"{prefix}{number:0{width}d}{extension}"))
    return plan


def find_conflicts(folder, plan):
    """Return new names that already belong to something we are not renaming."""
    being_renamed = {old for old, _new in plan}
    return [new for _old, new in plan
            if new not in being_renamed
            and os.path.lexists(os.path.join(folder, new))]


def apply_plan(folder, plan):
    """Carry out the renames in `plan`."""
    changes = [(old, new) for old, new in plan if old != new]
    old_names = {old for old, _new in changes}

    # If a new name is currently used by another file in the batch (e.g. the
    # tool is re-run on its own output with a different start number), move
    # everything to temporary names first so nothing gets overwritten.
    if any(new in old_names for _old, new in changes):
        staged = []
        for index, (old, new) in enumerate(changes):
            temp = f".rename-{os.getpid()}-{index}.tmp"
            os.rename(os.path.join(folder, old), os.path.join(folder, temp))
            staged.append((temp, new))
        changes = staged

    for old, new in changes:
        os.rename(os.path.join(folder, old), os.path.join(folder, new))


def non_negative_int(text):
    """argparse type: an integer of zero or more."""
    value = int(text)
    if value < 0:
        raise argparse.ArgumentTypeError("must not be negative")
    return value


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Rename files in a folder to PREFIX plus a zero-padded "
                    "number, keeping each file's extension.")
    parser.add_argument("folder", help="folder whose files will be renamed")
    parser.add_argument("prefix", help="start of each new name, e.g. 'trip_'")
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help="print the changes without making them")
    parser.add_argument("--start", type=non_negative_int, default=1,
                        help="first number to use (default: %(default)s)")
    parser.add_argument("--width", type=non_negative_int, default=MIN_WIDTH,
                        help="minimum number of digits (default: %(default)s)")
    args = parser.parse_args(argv)

    if not args.prefix or args.prefix in (".", ".."):
        parser.error("prefix must not be empty, '.' or '..'")
    if os.sep in args.prefix or (os.altsep and os.altsep in args.prefix):
        parser.error("prefix must not contain a path separator")
    return args


def main(argv=None):
    args = parse_args(argv)

    try:
        names = list_files(args.folder)
    except OSError as exc:
        print(f"error: cannot read folder {args.folder}: {exc}", file=sys.stderr)
        return 1
    if not names:
        print(f"No files to rename in {args.folder}")
        return 0

    plan = build_plan(names, args.prefix, args.start, args.width)
    conflicts = find_conflicts(args.folder, plan)
    if conflicts:
        print(f"error: these names already exist in {args.folder}: "
              f"{', '.join(conflicts)}", file=sys.stderr)
        return 1

    for old, new in plan:
        note = "  (unchanged)" if old == new else ""
        print(f"{old} -> {new}{note}")

    changed = sum(old != new for old, new in plan)
    if args.dry_run:
        print(f"Dry run: {changed} file(s) would be renamed; nothing changed.")
        return 0

    try:
        apply_plan(args.folder, plan)
    except OSError as exc:
        print(f"error: rename failed part-way: {exc}", file=sys.stderr)
        return 1
    print(f"Renamed {changed} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
