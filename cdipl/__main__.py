"""Command line: python -m cdipl build|lift|explain|choose|affected ..."""
import argparse
import json
import re
import sys
from pathlib import Path

from . import library, pages
from .compiler import BuildError, build_with_index, lift_app, lift_text, read_intent, target_for
from .languages import HEADERS
from .live_server import serve
from .model import IntentError
from .resolve import Resolver, empty_index, key_for
from .targets import TARGETS
from .targets.common import NotGenerated, blocks_used


def index_path(intent):
    return intent.with_suffix(".index.json")


def load_index(intent):
    path = index_path(intent)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def save_index(intent, index):
    path = index_path(intent)
    if index["statements"] or path.exists():
        path.write_text(json.dumps(index, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def fail(intent, problem):
    if isinstance(problem, IntentError):
        sys.exit(f"{intent}:{problem.line}: {problem.message}")
    sys.exit(f"{intent}: {problem}")


def command_build(args):
    intent = Path(args.intent)
    try:
        files, index = build_with_index(intent.read_text(encoding="utf-8"), args.target, load_index(intent))
    except (IntentError, BuildError) as problem:
        fail(intent, problem)
    save_index(intent, index)
    folder = Path(args.out) if args.out else intent.parent / "build" / args.target
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8")
        print(f"wrote {folder / name}")
    trace = json.loads(files["trace.json"])
    drafts = [entry["block"] for entry in trace["blocks"] if entry["status"] == "draft"]
    if drafts:
        print(f"note: {len(drafts)} block(s) used are drafts awaiting human review: {', '.join(drafts)}", file=sys.stderr)


def command_lift(args):
    path = Path(args.program)
    try:
        if path.is_dir():
            files = {item.name: item.read_text(encoding="utf-8") for item in sorted(path.iterdir())
                     if item.suffix in (".html", ".css")}
            sys.stdout.write(pages.render(lift_app(files), args.language))
        else:
            sys.stdout.write(lift_text(path.read_text(encoding="utf-8"), target_for(path.name), args.language))
    except NotGenerated as problem:
        sys.exit(f"{path}: refused: {problem}")


def statements(intent_text):
    """(line number, text) of each statement after the source declaration."""
    out, in_source = [], False
    for number, line in enumerate(intent_text.split("\n"), start=1):
        if not line.strip() or number == 1:
            continue
        if line.rstrip().endswith(":") and not line[:1].isspace() and not out:
            in_source = True
            continue
        if in_source and line[:1].isspace():
            continue
        out.append((number, line.strip()))
    return out


def command_explain(args):
    """Show, in plain words, which block each statement was read as, and how that was decided."""
    intent = Path(args.intent)
    text = intent.read_text(encoding="utf-8")
    try:
        program, resolver = read_intent(text, load_index(intent))
    except IntentError as problem:
        fail(intent, problem)
    descriptions, statuses = library.catalogue(), library.statuses()
    blocks_by_line = {}
    for step in program.steps:
        single = type(program)(source=program.source, steps=(step,))
        names = [b for b in blocks_used(single) if b != "print-message" or step.__class__.__name__ == "IfNone"]
        blocks_by_line.setdefault(step.line, []).extend(n for n in names if n not in blocks_by_line.get(step.line, []))
        if getattr(step, "skip_line", 0):
            blocks_by_line[step.skip_line] = ["drop-invalid-rows"]
            blocks_by_line[step.line] = [n for n in blocks_by_line[step.line] if n != "drop-invalid-rows"]
    for number, statement in statements(text):
        entry = resolver.entries.get(key_for(statement))
        how = "standard phrase" if entry is None else {"classifier": "chosen by the classifier",
                                                       "developer": "chosen by the developer"}[entry["by"]]
        print(f"line {number}: {statement}")
        for block in blocks_by_line.get(number, []):
            print(f"    {block} [{statuses.get(block, 'planned')}] - {descriptions[block]} ({how})")


def declared_names(intent_text):
    """The source and field names declared in an intent file, plus the field that counting adds."""
    names = {"count"}
    for line in intent_text.split("\n"):
        if (match := re.match(r"\s+([A-Za-z_][A-Za-z0-9_]*)\s*:", line)) or (match := re.match(r"\S+\s+([A-Za-z_][A-Za-z0-9_]*)\s+\S+.*:\s*$", line)) and len(names) == 1:
            names.add(match[1])
    return names


def command_choose(args):
    """List the closest blocks for a statement, or record the developer's choice in the index."""
    intent = Path(args.intent)
    text = intent.read_text(encoding="utf-8")
    found = dict(statements(text))
    if args.line not in found:
        sys.exit(f"{intent}: line {args.line} is not a statement")
    statement = found[args.line]
    index = load_index(intent) or empty_index()
    descriptions = library.catalogue()
    if args.block is None:
        language = HEADERS.get(" ".join(text.split("\n", 1)[0].split()), "en")
        ranked, _, unknown = Resolver(language, index).candidates(statement, declared_names(text))
        print(f"line {args.line}: {statement}")
        if unknown:
            print(f"  words not in the word list: {', '.join(unknown)}")
        print("  closest blocks (record one with --block NAME):")
        for block in ranked[:5]:
            print(f"    {block} - {descriptions[block]}")
        return
    if args.block not in descriptions:
        sys.exit(f"there is no block named '{args.block}'")
    index["statements"][key_for(statement)] = {"block": args.block, "by": "developer"}
    index_path(intent).write_text(json.dumps(index, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"recorded: line {args.line} means {args.block} - {descriptions[args.block]}")


def command_affected(args):
    """List the intent files under a folder whose programs use a given block."""
    if args.block not in library.catalogue():
        sys.exit(f"there is no block named '{args.block}'")
    for intent in sorted(Path(args.folder).rglob("*.intent")):
        try:
            program, _ = read_intent(intent.read_text(encoding="utf-8"), load_index(intent))
        except IntentError:
            continue
        if args.block in blocks_used(program):
            print(intent)


def main():
    parser = argparse.ArgumentParser(prog="cdipl", description="Build programs from intent files.")
    commands = parser.add_subparsers(dest="command", required=True)
    build_parser = commands.add_parser("build", help="generate a program from an intent file")
    build_parser.add_argument("intent")
    build_parser.add_argument("--target", choices=[*sorted(TARGETS), "html"], required=True)
    build_parser.add_argument("--out", help="folder to write to (default: build/<target> beside the intent file)")
    build_parser.set_defaults(run=command_build)
    lift_parser = commands.add_parser("lift", help="turn a generated program back into intent")
    lift_parser.add_argument("program", help="a generated program, or a folder of generated pages")
    lift_parser.add_argument("--language", choices=("en", "es"), default="en")
    lift_parser.set_defaults(run=command_lift)
    explain_parser = commands.add_parser("explain", help="show which block each statement was read as")
    explain_parser.add_argument("intent")
    explain_parser.set_defaults(run=command_explain)
    choose_parser = commands.add_parser("choose", help="list the closest blocks for a statement, or record a choice")
    choose_parser.add_argument("intent")
    choose_parser.add_argument("line", type=int)
    choose_parser.add_argument("--block", help="the block this statement means")
    choose_parser.set_defaults(run=command_choose)
    live_parser = commands.add_parser("live", help="open the live view for an intent file in a local browser page")
    live_parser.add_argument("intent")
    live_parser.add_argument("--port", type=int, default=8765)
    live_parser.set_defaults(run=lambda args: serve(args.intent, args.port))
    affected_parser = commands.add_parser("affected", help="list the intent files that use a block")
    affected_parser.add_argument("block")
    affected_parser.add_argument("folder")
    affected_parser.set_defaults(run=command_affected)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
