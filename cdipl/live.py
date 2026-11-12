"""Analyse intent text as it is being written, for the live view.

Unlike a build, the analysis does not stop at the first problem: it reports on every statement
and generates code for as much of the file as can be read.
"""
import time

from . import library, parser, words
from . import pages as pages_module
from .languages import HEADERS, PHRASES
from .model import (
    Add,
    Count,
    Filter,
    Group,
    IfNone,
    IntentError,
    Limit,
    Program,
    Read,
    Show,
    Sort,
    TypeMismatch,
    WriteJson,
    check_chain,
)
from .resolve import Resolver, empty_index, key_for
from .targets import TARGETS, html

STEP_BLOCKS = {Read: ["read-text-file", "parse-json", "check-list-of-records", "check-required-types"],
               Filter: ["filter-rows"], Add: ["calculate"], Sort: ["sort-rows"], Limit: ["take-first"],
               Group: ["group-by-key"], Count: ["count-values"], IfNone: ["print-message"], Show: ["print-table"],
               WriteJson: ["format-json"]}
ELEMENT_BLOCKS = {pages_module.Heading: "page-heading", pages_module.Paragraph: "page-text",
                  pages_module.Table: "data-table", pages_module.Button: "page-button"}


class LiveResolver(Resolver):
    """Chooses a block for every readable statement, sure or not, and notes how sure it was."""

    def __init__(self, language, index=None):
        super().__init__(language, index)
        self.notes = {}

    def resolve(self, statement, line, names):
        try:
            tokens, unknown = words.encode(statement, self.words, names)
        except words.WordError as problem:
            raise IntentError(line, str(problem)) from None
        except FileNotFoundError:
            raise IntentError(line, "this is not written in standard phrases, and there is no word list for this language") from None
        key = key_for(statement)
        entry = self.index["statements"].get(key)
        note = self.notes.setdefault(line, {})
        if entry is None:
            _, ranked, margin = self.classifier.choose(words.codes(tokens))
            note["alternatives"] = ranked[:3]
            if unknown:
                listed = ", ".join(f"'{word}'" for word in unknown)
                raise IntentError(line, f"not understood: {listed} is not in the word list")
            note["how"] = "sure" if margin >= self.classifier.threshold else "unsure"
            entry = {"block": ranked[0], "by": "classifier", "classifier": self.classifier.version}
        else:
            note["how"] = "project"
        self.entries[key] = dict(entry, version=library.version(entry["block"]))
        return entry["block"], tokens


def describe(blocks):
    catalogue, statuses = library.catalogue(), library.statuses()
    return [{"block": block, "description": catalogue.get(block, ""), "status": statuses.get(block, "planned")}
            for block in blocks]


def analyse(text, target=None, index=None):
    """Report on every statement of intent text and generate what can be generated."""
    started = time.perf_counter()
    try:
        result = _analyse_app(text) if pages_module.is_app(text) else _analyse_program(text, target, index)
    except IntentError as problem:
        result = {"kind": "program", "targets": sorted(TARGETS), "target": target or "python", "statements": [],
                  "files": [], "problems": [{"line": problem.line, "message": problem.message}], "complete": False,
                  "canonical": None, "preview": None}
    result["ms"] = round((time.perf_counter() - started) * 1000, 2)
    return result


def _analyse_program(text, target, index):
    target = target if target in TARGETS else "python"
    numbered = [(number, line) for number, line in enumerate(text.split("\n"), start=1) if line.strip()]
    if not numbered:
        raise IntentError(1, "start with a line that names the human language, such as 'language: en'")
    language = HEADERS.get(" ".join(numbered[0][1].split()))
    if language is None:
        raise IntentError(numbered[0][0], "the first line must name the human language: "
                          + " or ".join(f"'{header}'" for header in HEADERS))
    phrases = PHRASES[language]
    source, position = parser._parse_source(numbered, 1, phrases)
    resolver = LiveResolver(language, index or empty_index())
    statements = [{"line": numbered[1][0], "text": numbered[1][1].strip(), "status": "standard",
                   "reading": numbered[1][1].strip(), "blocks": [], "note": "", "alternatives": []}]
    steps, problems = [], []
    for number, raw in numbered[position:]:
        record = {"line": number, "text": raw.strip(), "status": "standard", "reading": "", "blocks": [], "note": "",
                  "alternatives": []}
        statements.append(record)
        try:
            if raw[:1].isspace():
                raise IntentError(number, "a statement must not be indented")
            new_steps = parser._parse_statement(raw.strip(), number, phrases, source, steps, resolver)
            candidate = steps
            for step in new_steps:
                candidate = [step, *candidate[1:]] if isinstance(step, Read) and candidate else [*candidate, step]
                check_chain(source, candidate, complete=False)
            steps = candidate
        except (IntentError, TypeMismatch) as problem:
            record["status"] = "error"
            record["note"] = getattr(problem, "message", str(problem))
            record["alternatives"] = describe(resolver.notes.get(number, {}).get("alternatives", []))
            continue
        how = resolver.notes.get(number, {}).get("how")
        if how:
            record["status"] = how
            if how == "unsure":
                record["alternatives"] = describe(resolver.notes[number].get("alternatives", [])[1:])
        if isinstance(new_steps[0], Read) and new_steps[0].skip_invalid:
            record["reading"], names = phrases["skip"], ["drop-invalid-rows"]
        else:
            lines = [line for step in new_steps for line in parser.step_text(step, phrases, source)]
            record["reading"] = "\n".join(lines)
            names = [block for step in new_steps for block in STEP_BLOCKS[type(step)]]
        record["blocks"] = describe(dict.fromkeys(names))
    complete = not any(record["status"] == "error" for record in statements)
    canonical = None
    if complete:
        try:
            check_chain(source, steps)
            canonical = parser.render(Program(source, tuple(steps), language))
        except TypeMismatch as problem:
            complete = False
            problems.append({"line": numbered[-1][0], "message": str(problem)})
    files = []
    if steps:
        generator = TARGETS[target]
        generated = generator.generate(Program(source, tuple(steps), language))
        files.append({"name": generator.FILE_NAME, "lines": [{"text": line, "origin": origin} for line, origin in generated]})
    return {"kind": "program", "targets": sorted(TARGETS), "target": target, "statements": statements, "files": files,
            "problems": problems, "complete": complete, "canonical": canonical, "preview": None,
            "index": resolver.new_index()}


def _analyse_app(text):
    found = []
    app = pages_module.read_lines(text, on_problem=found.append)
    by_line = {problem.line: problem for problem in found}
    statements = []
    lines = text.split("\n")
    elements = {element.line: element for page in app.pages for element in page.elements}
    for number, raw in enumerate(lines, start=1):
        if not raw.strip() or number == 1:
            continue
        record = {"line": number, "text": raw.strip(), "status": "standard", "reading": raw.strip(), "blocks": [],
                  "note": "", "alternatives": []}
        if number in by_line:
            problem = by_line[number]
            record["status"] = "unbuilt" if isinstance(problem, pages_module.NotBuilt) else "error"
            record["note"] = problem.message
        elif number in elements:
            record["reading"] = pages_module.element_text(elements[number], app.language)
            record["blocks"] = describe([ELEMENT_BLOCKS[type(elements[number])]])
        elif any(page.line == number for page in app.pages):
            record["blocks"] = describe(["html-page"])
        statements.append(record)
    problems = []
    complete = not found
    usable = _usable(app)
    try:
        pages_module.check(app)
    except IntentError as problem:
        complete = False
        if problem.line not in by_line:
            problems.append({"line": problem.line, "message": problem.message})
    files, preview = [], None
    if usable.pages:
        generated = html.generate(usable)
        files = [{"name": name, "lines": [{"text": line, "origin": origin} for line, origin in generated[name]]}
                 for name in generated]
        first = html.file_name(usable.pages[0])
        styles = "\n".join(line for line, _ in generated[html.STYLES])
        preview = "\n".join(f"<style>\n{styles}\n</style>" if "rel=\"stylesheet\"" in line else line
                            for line, _ in generated[first])
    canonical = pages_module.render(app) if complete else None
    return {"kind": "app", "targets": ["html"], "target": "html", "statements": statements, "files": files,
            "problems": problems, "complete": complete, "canonical": canonical, "preview": preview,
            "index": empty_index()}


def _usable(app):
    """The part of an application that can be generated: pages with content, tables whose data exists."""
    names = {item.name for item in app.data if item.fields}
    usable_pages, seen = [], set()
    for page in app.pages:
        kept = tuple(element for element in page.elements
                     if not isinstance(element, pages_module.Table) or element.data in names)
        if kept and page.name.lower() not in seen:
            seen.add(page.name.lower())
            usable_pages.append(pages_module.Page(page.name, kept, page.line))
    return pages_module.App(app.name, app.data, tuple(usable_pages), app.language, app.line)
