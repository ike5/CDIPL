"""Build programs from intent, and lift generated programs back to intent."""
import json

from . import library
from .model import IntentError
from .parser import parse, render
from .targets import TARGETS
from .targets.common import NotGenerated, blocks_used


class BuildError(Exception):
    """The intent is valid but the program cannot be built."""


def build(intent_text, target, statuses=None):
    """Compile intent text for one target.

    Returns a dict of file name -> file text: the program and its trace file.
    Raises IntentError for a problem in the intent, BuildError for a flagged block.
    """
    program = parse(intent_text)
    return build_program(program, target, statuses)


def build_program(program, target, statuses=None):
    generator = TARGETS[target]
    statuses = library.statuses() if statuses is None else statuses
    used = blocks_used(program)
    for block in used:
        status = statuses.get(block)
        if status is None:
            raise BuildError(f"block '{block}' is not in the library")
        if status == "flagged":
            raise BuildError(f"block '{block}' has been flagged as faulty and cannot be used until it is fixed")
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
