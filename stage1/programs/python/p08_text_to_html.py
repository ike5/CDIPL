#!/usr/bin/env python3
"""Convert a plain-text file with '#' headings and '-' bullets into HTML.

Supported markup:
    # Heading       one to six '#' characters give <h1> to <h6>
    - item          consecutive '-' lines form one <ul> list
    other text      consecutive lines form one <p> paragraph
    (blank line)    ends the current paragraph or list

The page is written to the file given with -o, or to the screen.
"""

import argparse
import html
import re
import sys
from pathlib import Path

HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET = re.compile(r"^-\s+(.*)$")

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
</head>
<body>
{body}
</body>
</html>
"""


def parse_blocks(lines):
    """Group lines into blocks: ("heading", level, text), ("list", items)
    or ("paragraph", lines)."""
    blocks = []
    paragraph, items = [], []

    def flush():
        # Close whichever block is currently open.
        if paragraph:
            blocks.append(("paragraph", paragraph.copy()))
            paragraph.clear()
        if items:
            blocks.append(("list", items.copy()))
            items.clear()

    for raw in lines:
        line = raw.strip()
        if not line:
            flush()
        elif match := HEADING.match(line):
            flush()
            blocks.append(("heading", len(match.group(1)), match.group(2).strip()))
        elif match := BULLET.match(line):
            if paragraph:
                flush()
            items.append(match.group(1).strip())
        else:
            if items:
                flush()
            paragraph.append(line)
    flush()
    return blocks


def render_block(block):
    """Return the HTML for one block, with all text escaped."""
    kind = block[0]
    if kind == "heading":
        _, level, text = block
        return f"<h{level}>{html.escape(text)}</h{level}>"
    if kind == "list":
        rows = "\n".join(f"  <li>{html.escape(item)}</li>" for item in block[1])
        return f"<ul>\n{rows}\n</ul>"
    return f"<p>{html.escape(' '.join(block[1]))}</p>"


def page_title(blocks, fallback):
    """Use the first heading as the page title, else the fallback."""
    for block in blocks:
        if block[0] == "heading":
            return block[2]
    return fallback


def convert(text, fallback_title):
    """Convert the whole input text into a complete HTML page."""
    blocks = parse_blocks(text.splitlines())
    body = "\n".join(render_block(block) for block in blocks)
    title = html.escape(page_title(blocks, fallback_title))
    return PAGE.format(title=title, body=body)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Convert a text file with # headings and - bullets to HTML."
    )
    parser.add_argument("input", type=Path, help="plain-text file to convert")
    parser.add_argument(
        "-o", "--output", type=Path, help="HTML file to write (default: screen)"
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        text = args.input.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: cannot read {args.input}: {exc}", file=sys.stderr)
        return 1

    page = convert(text, fallback_title=args.input.stem)

    if args.output is None:
        sys.stdout.write(page)
        return 0
    try:
        args.output.write_text(page, encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot write {args.output}: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
