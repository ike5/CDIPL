"""Command line: python -m cdipl build|lift|explain ..."""
import argparse
import sys
from pathlib import Path

from . import library
from .compiler import BuildError, build, lift_text, target_for
from .model import IntentError
from .parser import parse
from .targets import TARGETS
from .targets.common import NotGenerated, blocks_used


def command_build(args):
    intent = Path(args.intent)
    try:
        files = build(intent.read_text(encoding="utf-8"), args.target)
    except IntentError as problem:
        sys.exit(f"{intent}:{problem.line}: {problem.message}")
    except BuildError as problem:
        sys.exit(f"{intent}: {problem}")
    folder = Path(args.out) if args.out else intent.with_suffix("").parent / "build" / args.target
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8")
        print(f"wrote {folder / name}")
    drafts = [b for b in blocks_used(parse(intent.read_text(encoding="utf-8"))) if library.statuses()[b] == "draft"]
    if drafts:
        print(f"note: {len(drafts)} block(s) used are drafts awaiting human review: {', '.join(drafts)}", file=sys.stderr)


def command_lift(args):
    path = Path(args.program)
    try:
        sys.stdout.write(lift_text(path.read_text(encoding="utf-8"), target_for(path.name), args.language))
    except NotGenerated as problem:
        sys.exit(f"{path}: refused: {problem}")


def command_explain(args):
    intent = Path(args.intent)
    try:
        program = parse(intent.read_text(encoding="utf-8"))
    except IntentError as problem:
        sys.exit(f"{intent}:{problem.line}: {problem.message}")
    descriptions, statuses = library.catalogue(), library.statuses()
    for block in blocks_used(program):
        print(f"{block}  [{statuses[block]}, version {library.version(block)}]  {descriptions[block]}")


def main():
    parser = argparse.ArgumentParser(prog="cdipl", description="Build programs from intent files.")
    commands = parser.add_subparsers(dest="command", required=True)
    build_parser = commands.add_parser("build", help="generate a program from an intent file")
    build_parser.add_argument("intent")
    build_parser.add_argument("--target", choices=sorted(TARGETS), required=True)
    build_parser.add_argument("--out", help="folder to write to (default: build/<target> beside the intent file)")
    build_parser.set_defaults(run=command_build)
    lift_parser = commands.add_parser("lift", help="turn a generated program back into intent")
    lift_parser.add_argument("program")
    lift_parser.add_argument("--language", choices=("en", "es"), default="en")
    lift_parser.set_defaults(run=command_lift)
    explain_parser = commands.add_parser("explain", help="list the blocks an intent file is built from")
    explain_parser.add_argument("intent")
    explain_parser.set_defaults(run=command_explain)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
