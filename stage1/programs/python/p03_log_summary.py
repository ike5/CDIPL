#!/usr/bin/env python3
"""Summarise a web server access log as JSON.

Reads a log in Common or Combined Log Format (Apache, nginx) and writes
the number of requests per status code and per hour of day to a JSON file.

Usage: p03_log_summary.py access.log [-o summary.json]
"""

import argparse
import json
import re
import sys
from collections import Counter

# Example line:
# 203.0.113.9 - - [10/Oct/2024:13:55:36 +0000] "GET / HTTP/1.1" 200 2326
LOG_LINE = re.compile(
    r'^\S+ \S+ \S+ '                          # client, identity, user
    r'\[\d{2}/\w{3}/\d{4}:(?P<hour>\d{2}):\d{2}:\d{2}[^\]]*\] '
    r'"(?:[^"\\]|\\.)*" '                     # request line (may hold \")
    r'(?P<status>\d{3})\b'
)


def summarise(lines):
    """Count requests by status code and by hour.

    Returns (status_counts, hour_counts, unparsed_line_count).
    """
    by_status = Counter()
    by_hour = Counter()
    unparsed = 0

    for line in lines:
        if not line.strip():
            continue
        match = LOG_LINE.match(line)
        if match is None or int(match["hour"]) > 23:
            unparsed += 1
            continue
        by_status[match["status"]] += 1
        by_hour[match["hour"]] += 1

    return by_status, by_hour, unparsed


def build_report(by_status, by_hour, unparsed):
    """Arrange the counts as a JSON-ready dictionary."""
    return {
        "total_requests": sum(by_status.values()),
        "unparsed_lines": unparsed,
        "by_status": dict(sorted(by_status.items())),
        # List all 24 hours so quiet hours show up as 0 rather than vanish.
        # Hours are as written in the log (its own timezone).
        "by_hour": {f"{hour:02d}": by_hour.get(f"{hour:02d}", 0)
                    for hour in range(24)},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Count access-log requests by status code and hour of day.")
    parser.add_argument("log_file", help="access log to read")
    parser.add_argument("-o", "--output", default="log_summary.json",
                        help="JSON file to write (default: %(default)s)")
    args = parser.parse_args(argv)

    try:
        # Logs can contain arbitrary bytes; never fail on a bad character.
        with open(args.log_file, encoding="utf-8", errors="replace") as handle:
            by_status, by_hour, unparsed = summarise(handle)
    except OSError as exc:
        print(f"error: cannot read {args.log_file}: {exc}", file=sys.stderr)
        return 1

    report = build_report(by_status, by_hour, unparsed)
    if report["total_requests"] == 0:
        print(f"error: no valid log lines found in {args.log_file}",
              file=sys.stderr)
        return 1

    try:
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    except OSError as exc:
        print(f"error: cannot write {args.output}: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {args.output}: {report['total_requests']} requests, "
          f"{len(by_status)} status codes")
    if unparsed:
        print(f"warning: {unparsed} line(s) could not be parsed",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
