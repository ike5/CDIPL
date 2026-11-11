#!/usr/bin/env python3
"""Print the largest files under a folder, with human-readable sizes.

Usage: p02_largest_files.py [folder] [-n COUNT]
"""

import argparse
import heapq
import os
import sys

DEFAULT_COUNT = 10
UNITS = ("KB", "MB", "GB", "TB", "PB")


def iter_file_sizes(root):
    """Yield (size_in_bytes, path) for every regular file beneath `root`.

    Symbolic links are not followed, so nothing is counted twice and link
    loops cannot trap us. Unreadable entries are reported and skipped.
    """
    def report(error):
        print(f"warning: {error}", file=sys.stderr)

    for folder, _subfolders, filenames in os.walk(root, onerror=report):
        for name in filenames:
            path = os.path.join(folder, name)
            try:
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                yield os.path.getsize(path), path
            except OSError as exc:
                report(exc)


def format_size(size):
    """Format a byte count using 1024-based units, e.g. 1536 -> '1.5 KB'."""
    if size < 1024:
        return f"{size} B"
    value = float(size)
    for unit in UNITS:
        value /= 1024
        # Compare the rounded value so we never print "1024.0 KB".
        if round(value, 1) < 1024 or unit == UNITS[-1]:
            return f"{value:.1f} {unit}"


def positive_int(text):
    """argparse type: an integer greater than zero."""
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Print the largest files under a folder.")
    parser.add_argument("folder", nargs="?", default=".",
                        help="folder to search (default: current folder)")
    parser.add_argument("-n", "--count", type=positive_int,
                        default=DEFAULT_COUNT,
                        help=f"how many files to show (default: {DEFAULT_COUNT})")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.folder):
        print(f"error: not a folder: {args.folder}", file=sys.stderr)
        return 1

    # nlargest keeps only `count` entries in memory, however big the tree is.
    largest = heapq.nlargest(args.count, iter_file_sizes(args.folder))
    if not largest:
        print(f"No files found under {args.folder}")
        return 0

    sizes = [format_size(size) for size, _path in largest]
    width = max(len(text) for text in sizes)
    for text, (_size, path) in zip(sizes, largest):
        print(f"{text:>{width}}  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
