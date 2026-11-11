#!/usr/bin/env python3
"""Write the rows of one CSV file whose key is absent from a second CSV file.

Both files must have a header row containing the key column. The output keeps
the first file's columns and row order.

Example:
    p07_csv_difference.py customers.csv unsubscribed.csv --key email -o keep.csv
"""

import argparse
import csv
import os
import sys


class CsvError(Exception):
    """A problem with an input file that the user should be told about."""


def open_csv(path):
    """Open a CSV file for reading (newline='' as the csv module requires)."""
    try:
        # utf-8-sig quietly drops the byte-order mark that Excel adds.
        return open(path, newline="", encoding="utf-8-sig")
    except OSError as exc:
        raise CsvError(f"cannot read {path}: {exc.strerror}") from exc


def require_key(reader, key, path):
    """Check that the file has a header and that it contains the key column."""
    if reader.fieldnames is None:
        raise CsvError(f"{path} is empty (no header row)")
    if key not in reader.fieldnames:
        columns = ", ".join(reader.fieldnames)
        raise CsvError(f"{path} has no column named {key!r} (columns: {columns})")


def read_keys(path, key):
    """Return the set of key values found in a CSV file."""
    with open_csv(path) as handle:
        reader = csv.DictReader(handle)
        require_key(reader, key, path)
        return {row[key].strip() for row in reader if row[key] is not None}


def write_difference(first_path, exclude, key, out_path):
    """Copy rows from first_path whose key is not in `exclude`.

    Returns (rows_read, rows_written).
    """
    with open_csv(first_path) as source:
        reader = csv.DictReader(source)
        require_key(reader, key, first_path)
        # Opening the output truncates it, so it must not be the input.
        if os.path.exists(out_path) and os.path.samefile(first_path, out_path):
            raise CsvError("the output file must not be the same as the first file")
        try:
            target = open(out_path, "w", newline="", encoding="utf-8")
        except OSError as exc:
            raise CsvError(f"cannot write {out_path}: {exc.strerror}") from exc

        with target:
            # extrasaction="ignore" drops surplus cells from over-long rows.
            writer = csv.DictWriter(
                target, fieldnames=reader.fieldnames, extrasaction="ignore"
            )
            writer.writeheader()
            rows_read = rows_written = 0
            for row in reader:
                rows_read += 1
                if (row[key] or "").strip() not in exclude:
                    writer.writerow(row)
                    rows_written += 1
    return rows_read, rows_written


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Write rows whose key is in the first CSV but not the second."
    )
    parser.add_argument("first", help="CSV file to take rows from")
    parser.add_argument("second", help="CSV file whose keys are excluded")
    parser.add_argument("-k", "--key", required=True, help="name of the shared key column")
    parser.add_argument("-o", "--output", required=True, help="CSV file to write")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        exclude = read_keys(args.second, args.key)
        rows_read, rows_written = write_difference(
            args.first, exclude, args.key, args.output
        )
    except (CsvError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"{rows_written} of {rows_read} rows written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
