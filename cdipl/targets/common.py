"""Pieces shared by the target code generators."""
from ..model import (
    Add,
    Arith,
    Concat,
    Condition,
    Count,
    Field,
    Filter,
    Group,
    IfNone,
    Limit,
    Number,
    Program,
    Read,
    Show,
    Sort,
    Source,
    Text,
    TypeMismatch,
    WriteJson,
    check_chain,
    formula_type,
    schema_after,
    uses_arithmetic,
)


class NotGenerated(Exception):
    """The file is not something this compiler would generate."""


def blocks_used(program):
    """The blocks a program is built from, in order of first use."""
    used = []

    def add(*names):
        for name in names:
            if name not in used:
                used.append(name)

    for step, schema in zip(program.steps, schemas(program)):
        if isinstance(step, Read):
            if program.source.argument is not None:
                add("cli-options")
            add("read-text-file", "parse-json", "check-list-of-records", "exit-on-error", "check-required-types")
            if step.skip_invalid:
                add("drop-invalid-rows")
        elif isinstance(step, Filter):
            add("filter-rows")
            sides = [side for cond in step.conditions for side in (cond.left, cond.right)]
            if any(uses_arithmetic(side) for side in sides):
                add("calculate")
            if any(cond.op in ("<", "<=", ">", ">=") and formula_type(schema, cond.left) == "text"
                   for cond in step.conditions):
                add("sort-rows")  # comparing text uses the ordering rule that belongs to sort-rows
        elif isinstance(step, Add):
            add("calculate")
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
            add("print-table", "print-message")
        elif isinstance(step, WriteJson):
            add("format-json", "print-message")
    return used


def schemas(program):
    """The field types in force before each step."""
    schema = dict(program.source.fields)
    result = []
    for step in program.steps:
        result.append(dict(schema))
        schema = schema_after(schema, step)
    return result


def has_arithmetic(formula):
    """Whether whole-number arithmetic appears anywhere in a formula."""
    if isinstance(formula, Arith):
        return True
    if isinstance(formula, Concat):
        return any(has_arithmetic(part) for part in formula.parts)
    return False


def formulas(step):
    """Every formula written in a step."""
    if isinstance(step, Filter):
        return [side for cond in step.conditions for side in (cond.left, cond.right)]
    if isinstance(step, Add):
        return [step.formula]
    return []


class Scanner:
    """Reads generated code from left to right."""

    def __init__(self, text):
        self.text = text
        self.position = 0

    def take(self, literal):
        if self.text.startswith(literal, self.position):
            self.position += len(literal)
            return True
        return False

    def match(self, pattern):
        found = pattern.match(self.text, self.position)
        if found:
            self.position = found.end()
        return found

    def expect(self, literal):
        if not self.take(literal):
            raise NotGenerated("a formula or condition is not written the way the compiler writes it")

    def done(self):
        return self.position == len(self.text)


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


__all__ = ["Add", "Arith", "Concat", "Condition", "Count", "Field", "Filter", "Group", "IfNone", "Limit", "NotGenerated",
           "Number", "Program", "Read", "Scanner", "Show", "Sort", "Source", "Text", "WriteJson", "assemble", "blocks_used",
           "formula_type", "formulas", "has_arithmetic", "schemas"]
