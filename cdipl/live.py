"""Analyse intent text as it is being written, for the live view.

Unlike a build, the analysis does not stop at the first problem: it reports on every statement
and generates code for as much of the file as can be read.
"""
import time

from . import library, page_wording, parser, words
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
ELEMENT_BLOCKS = html.ELEMENT_BLOCKS


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
    found, notes = [], {}
    language = pages_module.HEADERS.get(" ".join(text.lstrip("\n").split("\n", 1)[0].split()), "en")
    resolver = page_wording.make_resolver(language, notes, accept_unsure=True)
    app = pages_module.read_lines(text, on_problem=found.append, resolver=resolver)
    by_line = {problem.line: problem for problem in found}
    language = app.language
    words = pages_module.PHRASES[language]
    filled = {item.name for item in app.records} | set(app.exposed)
    readings = {}  # line -> (reading, blocks, line whose code to show)
    for page in app.pages:
        readings[page.line] = (None, ["html-page"], None)
        for element in page.elements:
            lines = pages_module.element_text(element, language)
            blocks = [ELEMENT_BLOCKS[type(element)]]
            if isinstance(element, pages_module.Button) and element.action is not None:
                blocks.append("add-record-form" if element.action[0] == "adds" else "button-opens-page")
            if isinstance(element, pages_module.Table):
                if element.data in filled:
                    blocks.append("render-table")
                if element.search is not None:
                    readings[element.search_line] = (f"{words['searchable']} {element.search}", ["filter-elements-by-text"], None)
                for name, line in zip(element.sort, element.sort_lines):
                    readings[line] = (f"{words['sortable']} {name}", ["table-sort"], None)
                if element.editable:
                    readings[element.editable_line] = (words["editable"], ["edit-table-rows", "add-record-form"], None)
            readings[element.line] = (lines[0], blocks, None)
    for rule in app.rules:
        readings[rule.line] = (f"{words['when']} {pages_module.condition_text(rule, language)}:", ["notify-when"], None)
        readings[rule.notify_line] = (f"{words['notify']} {rule.recipient}", ["notify-when"], None)
    for part, line in zip(app.uses, app.use_lines):
        readings[line] = (f"{words['use']} {pages_module.PARTS[part]}", ["sqlite-table" if part == "sqlite" else "fastapi-app"], None)
    for name, line in zip(app.exposed, app.expose_lines):
        readings[line] = (words["expose_text"].format(name), ["rest-api", "sqlite-table"], None)
    for item in app.records:
        readings[item.line] = (None, ["data-records"], None)
        for row, line in zip(item.rows, item.row_lines):
            readings[line] = (", ".join(pages_module.value_text(value) for value in row), ["data-records"], None)
    for line, target in app.changes:
        if line not in readings:
            readings[line] = (readings.get(target, (None,))[0], ["page-button-resize"], target)
    statements = []
    for number, raw in enumerate(text.split("\n"), start=1):
        if not raw.strip() or number == 1:
            continue
        record = {"line": number, "text": raw.strip(), "status": "standard", "reading": raw.strip(), "blocks": [],
                  "note": "", "alternatives": []}
        if number in by_line:
            problem = by_line[number]
            record["status"] = "unbuilt" if isinstance(problem, pages_module.NotBuilt) else "error"
            record["note"] = problem.message
            record["alternatives"] = describe(notes.get(number, {}).get("alternatives", []))
        elif number in readings:
            reading, blocks, shows = readings[number]
            record["reading"] = reading or raw.strip()
            record["blocks"] = describe(blocks)
            if number in notes:
                record["status"] = notes[number]["how"]
                if notes[number]["how"] == "unsure":
                    record["alternatives"] = describe(notes[number]["alternatives"][1:])
            if shows is not None:
                record["shows"] = shows
                record["note"] = "this changes the button declared above; saving writes the new width into that line"
        statements.append(record)
    problems = []
    complete = not found
    try:
        pages_module.check(app)
    except IntentError as problem:
        complete = False
        if problem.line not in by_line:
            problems.append({"line": problem.line, "message": problem.message})
            for record in statements:
                if record["line"] == problem.line:
                    record["status"], record["note"] = "error", problem.message
    usable, dropped = _usable(app)
    for record in statements:  # a statement that is left out of what is generated is reported, with the reason
        if record["line"] in dropped and record["status"] not in ("error", "unbuilt"):
            record["status"], record["note"] = "error", dropped[record["line"]]
            complete = False
    files, preview = [], None
    if usable.pages:
        generated = html.generate(usable)
        files = [{"name": name, "lines": [{"text": line, "origin": origin} for line, origin in generated[name]]}
                 for name in generated]
        served = "fastapi" in usable.uses
        preview = ("static/" if served else "") + html.file_name(usable.pages[0])
    canonical = pages_module.render(app) if complete else None
    note = ("The preview imitates the API: it lists the records written in the file, and nothing added is saved."
            if usable.exposed else "")
    return {"kind": "app", "targets": ["html"], "target": "html", "statements": statements, "files": files,
            "problems": problems, "complete": complete, "canonical": canonical, "preview": preview,
            "preview_note": note, "index": empty_index()}


def _usable(app):
    """The part of an application that can be generated: what is left after dropping whatever does not fit.

    Returns that application and, for the new statements of an application that are left out, line -> reason.
    """
    fields = {item.name: [name for name, _ in item.fields] for item in app.data if item.fields}
    kinds = {item.name: [kind for _, kind in item.fields] for item in app.data if item.fields}
    exposed, tables, dropped = [], set(), {}
    if set(app.uses) == set(pages_module.PARTS):
        for name in app.exposed:
            if app.rules and name.lower() == pages_module.NOTIFICATIONS_TABLE:
                line = dict(zip(app.exposed, app.expose_lines)).get(name, app.line)
                dropped[line] = f"'{name}' cannot have an API: its table would be named 'notification', where the notifications are kept"
                continue
            if name in fields and "id" not in fields[name] and name.lower() not in tables:
                tables.add(name.lower())
                exposed.append(name)
    rules, seen = [], set()
    for rule in app.rules:
        known = dict(zip(fields.get(rule.data, []), kinds.get(rule.data, [])))
        if rule.data not in exposed:
            dropped[rule.line] = dropped[rule.notify_line] = f"a rule about '{rule.data}' needs '{rule.data}' to be exposed as an API"
        elif not all(name in known and pages_module.fits(value, known[name]) for name, _, value in rule.conditions):
            dropped[rule.line] = dropped[rule.notify_line] = f"the condition does not fit the fields of '{rule.data}'"
        elif rule not in seen:
            seen.add(rule)
            rules.append(rule)
    uses = tuple(part for part in app.uses if part != "sqlite" or exposed)
    page_names = {page.name for page in app.pages if page.elements}
    usable_pages, seen = [], set()
    for page in app.pages:
        kept = []
        for element in page.elements:
            if isinstance(element, pages_module.Button) and element.action is not None:
                verb, target = element.action
                if (verb == "adds" and target not in exposed) or (verb == "opens" and target not in page_names):
                    element = pages_module.Button(text=element.text, width=element.width, line=element.line)
            if isinstance(element, pages_module.Notifications) and not rules:
                dropped[element.line] = "there are no notifications to show: no rule that can be built notifies anyone"
                continue
            if isinstance(element, pages_module.Table):
                if element.data not in fields:
                    continue
                known = fields[element.data]
                pairs = [(name, line) for name, line in zip(element.sort, element.sort_lines) if name in known]
                editable = element.editable and element.data in exposed
                if element.editable and not editable:
                    dropped[element.editable_line] = f"a table can be editable only if '{element.data}' is exposed as an API"
                element = pages_module.Table(
                    data=element.data, search=element.search if element.search in known else None,
                    sort=tuple(name for name, _ in pairs), editable=editable, line=element.line,
                    search_line=element.search_line, sort_lines=tuple(line for _, line in pairs),
                    editable_line=element.editable_line)
            kept.append(element)
        if kept and page.name.lower() not in seen:
            seen.add(page.name.lower())
            usable_pages.append(pages_module.Page(page.name, tuple(kept), page.line))
    records, names = [], set()
    for item in app.records:
        if item.name not in kinds or item.name.lower() in names or not item.rows:
            continue
        good = all(len(row) == len(kinds[item.name]) and all(pages_module.fits(value, kind)
                   for value, kind in zip(row, kinds[item.name])) for row in item.rows)
        if good:
            names.add(item.name.lower())
            records.append(item)
    lines = dict(zip(app.exposed, app.expose_lines))
    use = dict(zip(app.uses, app.use_lines))
    usable = pages_module.App(app.name, app.data, tuple(usable_pages), tuple(records), uses, tuple(exposed), app.language,
                              app.line, (), tuple(use[part] for part in uses), tuple(lines[name] for name in exposed),
                              tuple(rules))
    return usable, dropped
