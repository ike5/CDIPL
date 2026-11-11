#!/usr/bin/env python3
"""Print total sales per region from a CSV file, largest total first.

The CSV must have a header row containing at least the columns
"region" and "amount" (a "product" column is expected but not used).

Usage: p01_sales_by_region.py sales.csv
"""

import argparse
import csv
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation

REQUIRED_COLUMNS = ("region", "amount")


def read_totals(path):
    """Return ({region: total}, skipped_row_count) for the CSV at `path`."""
    totals = defaultdict(Decimal)
    skipped = 0

    # utf-8-sig quietly drops the byte-order mark that Excel likes to add.
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("file is empty")

        # Be forgiving about header case and stray spaces.
        reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
        missing = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
        if missing:
            raise ValueError(f"missing column(s): {', '.join(missing)}")

        for row in reader:
            region = (row["region"] or "").strip()
            try:
                amount = Decimal((row["amount"] or "").strip().replace(",", ""))
            except InvalidOperation:
                amount = None
            if not region or amount is None or not amount.is_finite():
                print(f"warning: line {reader.line_num}: skipping bad row",
                      file=sys.stderr)
                skipped += 1
                continue
            totals[region] += amount

    return dict(totals), skipped


def print_report(totals):
    """Print regions and totals as an aligned table, largest total first."""
    # Sort by total descending; break ties by name so output is stable.
    ranked = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    rows = [(region, f"{total:,.2f}") for region, total in ranked]

    name_width = max(len("Region"), *(len(region) for region, _ in rows))
    total_width = max(len("Total"), *(len(total) for _, total in rows))

    print(f"{'Region':<{name_width}}  {'Total':>{total_width}}")
    print(f"{'-' * name_width}  {'-' * total_width}")
    for region, total in rows:
        print(f"{region:<{name_width}}  {total:>{total_width}}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Print total sales amount per region, largest first.")
    parser.add_argument("csv_file",
                        help="CSV file with region, product, amount columns")
    args = parser.parse_args(argv)

    try:
        totals, skipped = read_totals(args.csv_file)
    except (OSError, UnicodeDecodeError, ValueError, csv.Error) as exc:
        print(f"error: {args.csv_file}: {exc}", file=sys.stderr)
        return 1

    if not totals:
        print(f"error: {args.csv_file}: no valid sales records found",
              file=sys.stderr)
        return 1

    print_report(totals)
    if skipped:
        print(f"({skipped} row(s) skipped)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
