"""Pieces shared by the target code generators."""
from ..model import (Condition, Count, Filter, Group, IfNone, Limit, Program, Read, Show, Sort, Source, TypeMismatch,
                     WriteJson, check_chain)


class NotGenerated(Exception):
    """The file is not something this compiler would generate."""


def blocks_used(program):
    """The blocks a program is built from, in order of first use."""
    used = []

    def add(*names):
        for name in names:
            if name not in used:
                used.append(name)

    for step in program.steps:
        if isinstance(step, Read):
            if program.source.argument is not None:
                add("cli-options")
            add("read-text-file", "parse-json", "check-list-of-records", "exit-on-error")
            add("drop-invalid-rows" if step.skip_invalid else "check-required-types")
        elif isinstance(step, Filter):
            add("filter-rows")
        elif isinstance(step, Sort):
            add("sort-rows")
        elif isinstance(step, Limit):
            add("take-first")
        elif isinstance(step, Group):
            add("group-by-key")
        elif isinstance(step, Count):
            add("count-values")
        elif isinstance(step, IfNone):
            add("print-message")
        elif isinstance(step, Show):
            add("print-table")
        elif isinstance(step, WriteJson):
            add("format-json")
    return used


def schemas(program):
    """The field types in force before each step."""
    schema = dict(program.source.fields)
    result = []
    for step in program.steps:
        result.append(dict(schema))
        if isinstance(step, Count):
            schema = {step.field: schema[step.field], "count": "integer"}
    return result


def assemble(source, steps):
    """Build a Program from lifted parts, refusing chains whose types do not fit."""
    fixed, group_field = [], ""
    for step in steps:
        if isinstance(step, Group):
            group_field = step.field
        if isinstance(step, Count) and step.field != group_field:
            raise NotGenerated("a count does not match the grouping before it")
        fixed.append(step)
    try:
        check_chain(source, fixed)
    except TypeMismatch as problem:
        raise NotGenerated(str(problem)) from None
    return Program(source=source, steps=tuple(fixed))


__all__ = ["Condition", "Count", "Filter", "Group", "IfNone", "Limit", "NotGenerated", "Program", "Read", "Show",
           "Sort", "Source", "WriteJson", "assemble", "blocks_used", "schemas"]
