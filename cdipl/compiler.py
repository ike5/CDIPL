"""Build programs from intent, and lift generated programs back to intent."""
import json

from . import library
from . import pages as pages_module
from .languages import HEADERS
from .model import IntentError
from .parser import parse, render
from .resolve import Resolver
from .targets import TARGETS, html
from .targets.common import NotGenerated, blocks_used


class BuildError(Exception):
    """The intent is valid but the program cannot be built."""


def build(intent_text, target, statuses=None):
    """Compile intent text for one target.

    Returns a dict of file name -> file text: the program and its trace file.
    Raises IntentError for a problem in the intent, BuildError for a flagged block.
    """
    return build_with_index(intent_text, target, None, statuses)[0]


def check_blocks(used, statuses):
    for block in used:
        status = statuses.get(block)
        if status is None:
            raise BuildError(f"block '{block}' is not in the library")
        if status == "flagged":
            raise BuildError(f"block '{block}' has been flagged as faulty and cannot be used until it is fixed")


def build_app(app, statuses=None):
    """Generate the pages of an application. Returns file name -> text, including the trace file."""
    statuses = library.statuses() if statuses is None else statuses
    used = html.blocks_used(app)
    check_blocks(used, statuses)
    generated = html.generate(app)
    files = {name: "\n".join(line for line, _ in lines) + "\n" for name, lines in generated.items()}
    trace = {
        "target": "html",
        "blocks": [{"block": block, "version": library.version(block), "status": statuses[block]} for block in used],
        "files": {name: [origin for _, origin in lines] for name, lines in generated.items()},
    }
    files["trace.json"] = json.dumps(trace, indent=2) + "\n"
    return files


def lift_app(files):
    """Recover the App from generated pages. Raises NotGenerated unless rebuilding it reproduces every file."""
    pages = {name: text for name, text in files.items() if name != "trace.json"}
    app = html.lift(pages)
    rebuilt = {name: text for name, text in build_app(app).items() if name != "trace.json"}
    if rebuilt != pages:
        raise NotGenerated("the files differ from what the compiler would generate for the application they appear to describe")
    try:
        if pages_module.parse(pages_module.render(app, "en")) != app:
            raise NotGenerated("the application cannot be written back in standard phrases")
    except IntentError as problem:
        raise NotGenerated(f"the application cannot be written back in standard phrases: {problem.message}") from None
    return app


def read_intent(intent_text, index=None, classifier=None, word_list=None):
    """Parse intent text, resolving freely worded statements. Returns (program, resolver)."""
    language = HEADERS.get(" ".join(intent_text.lstrip("\n").split("\n", 1)[0].split()), "en")
    resolver = Resolver(language, index, classifier, word_list)
    return parse(intent_text, resolver), resolver


def build_with_index(intent_text, target, index, statuses=None, classifier=None, word_list=None):
    """Like build, but reuses and returns the index of block choices. Returns (files, new index)."""
    if pages_module.is_app(intent_text):
        if target != "html":
            raise BuildError("an application's pages are built with the target 'html'")
        return build_app(pages_module.parse(intent_text), statuses), index or {"classifier": "", "statements": {}}
    if target == "html":
        raise BuildError("the target 'html' builds an application's pages; this file is a program over a source")
    program, resolver = read_intent(intent_text, index, classifier, word_list)
    return build_program(program, target, statuses), resolver.new_index()


def build_program(program, target, statuses=None):
    generator = TARGETS[target]
    statuses = library.statuses() if statuses is None else statuses
    used = blocks_used(program)
    check_blocks(used, statuses)
    lines = generator.generate(program)
    text = "\n".join(line for line, _ in lines) + "\n"
    trace = {
        "program": generator.FILE_NAME,
        "target": target,
        "blocks": [{"block": block, "version": library.version(block), "status": statuses[block]} for block in used],
        "lines": [origin for _, origin in lines],
    }
    return {generator.FILE_NAME: text, "trace.json": json.dumps(trace, indent=2) + "\n"}


def lift(program_text, target):
    """Recover the Program a generated file came from.

    Raises NotGenerated unless rebuilding that Program reproduces the file exactly.
    """
    generator = TARGETS[target]
    program = generator.lift(program_text)
    rebuilt = "\n".join(line for line, _ in generator.generate(program)) + "\n"
    if rebuilt != program_text:
        raise NotGenerated("the file differs from what the compiler would generate for the intent it appears to express")
    try:
        if parse(render(program, "en")) != program:
            raise NotGenerated("the intent cannot be written back in standard phrases")
    except IntentError as problem:
        raise NotGenerated(f"the intent cannot be written back in standard phrases: {problem.message}") from None
    return program


def lift_text(program_text, target, language="en"):
    """Lift a generated file and return the intent in standard phrases."""
    return render(lift(program_text, target), language)


def target_for(file_name):
    for name, generator in TARGETS.items():
        if file_name.endswith(generator.FILE_NAME.rsplit(".", 1)[1]):
            return name
    raise NotGenerated(f"cannot tell which target language {file_name} is written in")
