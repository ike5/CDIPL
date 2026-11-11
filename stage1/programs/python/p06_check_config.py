#!/usr/bin/env python3
"""Check a JSON configuration file against required keys and expected types.

The requirements live in a second JSON file: an object that maps a dotted
key path to a type name, for example

    {"server.host": "string", "server.port": "integer", "debug": "boolean"}

Every problem is printed with the path to the key. The exit status is 0 when
the configuration is valid, 1 when problems were found and 2 when the tool
itself could not run (bad arguments, unreadable file).
"""

import argparse
import json
import sys

# Type names accepted in the requirements file. In Python True and False are
# also ints, so the numeric checks have to exclude bool explicitly.
TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "null": lambda v: v is None,
}

_MISSING = object()


def type_name(value):
    """Return the JSON type name of a decoded value."""
    for name in ("boolean", "integer", "number", "string", "array", "object", "null"):
        if TYPE_CHECKS[name](value):
            return name
    return type(value).__name__


def fail(message):
    """Report a problem with the tool's own inputs and exit with status 2."""
    print(f"error: {message}", file=sys.stderr)
    sys.exit(2)


def load_json(path):
    """Load a JSON file, exiting with status 2 if it cannot be read."""
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except OSError as exc:
        fail(f"cannot read {path}: {exc.strerror}")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        fail(f"{path} is not valid JSON: {exc}")


def validate_requirements(requirements, path):
    """Make sure the requirements file itself is usable."""
    if not isinstance(requirements, dict):
        fail(f"{path} must contain a JSON object of key path -> type")
    for key, expected in requirements.items():
        if expected not in TYPE_CHECKS:
            known = ", ".join(sorted(TYPE_CHECKS))
            fail(f"{path}: unknown type {expected!r} for {key!r} (use: {known})")


def lookup(config, dotted_path):
    """Follow a dotted path into nested objects.

    Returns (value, None) on success, or (_MISSING, path_of_the_broken_step).
    """
    current = config
    walked = []
    for part in dotted_path.split("."):
        walked.append(part)
        if not isinstance(current, dict) or part not in current:
            return _MISSING, ".".join(walked)
        current = current[part]
    return current, None


def check_config(config, requirements):
    """Return a list of problem messages, one per failing requirement."""
    if not isinstance(config, dict):
        return [f"(top level): expected object, found {type_name(config)}"]

    problems = []
    for key_path, expected in requirements.items():
        value, broken_at = lookup(config, key_path)
        if value is _MISSING:
            detail = "" if broken_at == key_path else f" (no '{broken_at}')"
            problems.append(f"{key_path}: missing required key{detail}")
        elif not TYPE_CHECKS[expected](value):
            problems.append(f"{key_path}: expected {expected}, found {type_name(value)}")
    return problems


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Check a JSON config file against required keys and types."
    )
    parser.add_argument("config", help="JSON configuration file to check")
    parser.add_argument(
        "requirements",
        help="JSON file mapping dotted key paths to type names "
        f"({', '.join(sorted(TYPE_CHECKS))})",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    requirements = load_json(args.requirements)
    validate_requirements(requirements, args.requirements)
    config = load_json(args.config)

    problems = check_config(config, requirements)
    if problems:
        for problem in problems:
            print(problem)
        print(f"{args.config}: {len(problems)} problem(s) found", file=sys.stderr)
        return 1

    print(f"{args.config}: OK ({len(requirements)} keys checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
