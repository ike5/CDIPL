#!/usr/bin/env python3
"""Fetch JSON from a web address and save it to a file.

If the request fails, it is retried up to three more times, waiting longer
after each failure (1s, 2s, 4s by default). Errors that a retry cannot fix,
such as "404 Not Found" or a reply that is not JSON, stop the program at once.

Usage: p05_fetch_json.py URL [-o output.json] [--delay SECONDS]
"""

import argparse
import http.client
import json
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

MAX_RETRIES = 3
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class FetchError(Exception):
    """The download failed and should not (or can no longer) be retried."""


def fetch_once(url, timeout):
    """Return the response body as bytes; raises on any network/HTTP error."""
    request = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "fetch-json/1.0",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def is_retryable(error):
    """Decide whether trying again might help."""
    if isinstance(error, urllib.error.HTTPError):
        return error.code in RETRYABLE_STATUS
    return True  # connection refused, DNS failure, timeout, dropped link...


def fetch_with_retries(url, timeout, base_delay, retries=MAX_RETRIES):
    """Fetch `url`, retrying with exponential backoff. Returns bytes."""
    for attempt in range(retries + 1):
        try:
            return fetch_once(url, timeout)
        # URLError covers HTTPError; OSError covers timeouts and resets;
        # HTTPException covers replies that are cut short or garbled.
        except (urllib.error.URLError, OSError,
                http.client.HTTPException) as exc:
            reason = getattr(exc, "reason", None) or exc
            if isinstance(exc, urllib.error.HTTPError):
                reason = f"HTTP {exc.code} {exc.reason}"
            if not is_retryable(exc):
                raise FetchError(str(reason)) from exc
            if attempt == retries:
                raise FetchError(
                    f"giving up after {retries + 1} attempts: {reason}") from exc
            delay = base_delay * 2 ** attempt
            print(f"Attempt {attempt + 1} failed ({reason}); "
                  f"retrying in {delay:g}s...", file=sys.stderr)
            time.sleep(delay)


def parse_json(body):
    """Decode the response body and check that it really is JSON."""
    try:
        return json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FetchError(f"response is not valid JSON: {exc}") from exc


def save_json(data, path):
    """Write `data` to `path` as indented JSON."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def positive_float(text):
    """argparse type: a number greater than zero."""
    value = float(text)
    if not value > 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return value


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Fetch JSON from a URL and save it to a file.")
    parser.add_argument("url", help="http:// or https:// address to fetch")
    parser.add_argument("-o", "--output", default="output.json",
                        help="file to write (default: %(default)s)")
    parser.add_argument("--timeout", type=positive_float, default=10.0,
                        help="seconds to wait for each attempt "
                             "(default: %(default)s)")
    parser.add_argument("--delay", type=positive_float, default=1.0,
                        help="seconds to wait before the first retry; "
                             "doubles each time (default: %(default)s)")
    args = parser.parse_args(argv)

    parts = urlparse(args.url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        parser.error(f"not an http(s) URL: {args.url}")
    return args


def main(argv=None):
    args = parse_args(argv)

    try:
        body = fetch_with_retries(args.url, args.timeout, args.delay)
        data = parse_json(body)
    except FetchError as exc:
        print(f"error: {args.url}: {exc}", file=sys.stderr)
        return 1

    try:
        save_json(data, args.output)
    except OSError as exc:
        print(f"error: cannot write {args.output}: {exc}", file=sys.stderr)
        return 1

    print(f"Saved {len(body)} bytes of JSON from {args.url} to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
