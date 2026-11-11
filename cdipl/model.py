"""The checked form of an intent file: one source and a chain of steps."""
from dataclasses import dataclass, field

MAX_INTEGER = 9007199254740991  # largest integer every target can hold exactly
TYPES = ("text", "integer")
COMPARISONS = ("=", "!=", "<", "<=", ">", ">=")


@dataclass(frozen=True)
class Source:
    name: str
    path: str | None  # a file path, or None when the path is a command-line argument
    argument: int | None
    fields: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Condition:
    field: str
    op: str
    value: int | str


@dataclass(frozen=True)
class Step:
    line: int = field(default=0, compare=False, kw_only=True)  # intent line it came from


@dataclass(frozen=True)
class Read(Step):
    skip_invalid: bool = False
    skip_line: int = field(default=0, compare=False, kw_only=True)


@dataclass(frozen=True)
class Filter(Step):
    conditions: tuple[Condition, ...] = ()


@dataclass(frozen=True)
class Sort(Step):
    field: str = ""
    descending: bool = False
    ignore_case: bool = False


@dataclass(frozen=True)
class Limit(Step):
    count: int = 0


@dataclass(frozen=True)
class Group(Step):
    field: str = ""


@dataclass(frozen=True)
class Count(Step):
    field: str = ""  # the field the groups were formed on


@dataclass(frozen=True)
class IfNone(Step):
    text: str = ""


@dataclass(frozen=True)
class Show(Step):
    fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class WriteJson(Step):
    pass


@dataclass(frozen=True)
class Program:
    source: Source
    steps: tuple[Step, ...]
    language: str = field(default="en", compare=False)


class IntentError(Exception):
    """A problem in an intent file, tied to a line."""

    def __init__(self, line, message):
        super().__init__(f"line {line}: {message}")
        self.line = line
        self.message = message


class TypeMismatch(Exception):
    """A step cannot follow the steps before it."""


def check_chain(source, steps, complete=True):
    """Check that each step fits the one before it. Returns the final field types.

    Raises TypeMismatch with a message that names what was expected and found.
    With complete=False the chain may stop before the step that produces output.
    """
    schema = dict(source.fields)
    state = "start"  # start -> rows <-> groups -> done
    group_field = None
    for position, step in enumerate(steps):
        if state == "done":
            raise TypeMismatch("nothing can follow the step that produces the output")
        if isinstance(step, Read):
            if position != 0:
                raise TypeMismatch("the source can only be read once, at the start")
            state = "rows"
            continue
        if state == "start":
            raise TypeMismatch("the first step must read the source")
        if isinstance(step, Count):
            if state != "groups":
                raise TypeMismatch("this step takes groups, but the step before it gives rows")
            schema = {group_field: schema[group_field], "count": "integer"}
            state = "rows"
            continue
        if state == "groups":
            raise TypeMismatch("this step takes rows, but the step before it gives groups")
        if isinstance(step, Filter):
            for cond in step.conditions:
                kind = _field_type(schema, cond.field)
                found = "integer" if isinstance(cond.value, int) else "text"
                if kind != found:
                    raise TypeMismatch(f"field '{cond.field}' is {kind}, but it is compared with {found}")
        elif isinstance(step, Sort):
            kind = _field_type(schema, step.field)
            if step.ignore_case and kind != "text":
                raise TypeMismatch(f"field '{step.field}' is {kind}; only text can be sorted ignoring case")
        elif isinstance(step, Group):
            _field_type(schema, step.field)
            if step.field == "count":
                raise TypeMismatch("cannot group by a field named 'count', because counting adds a field of that name")
            group_field = step.field
            state = "groups"
        elif isinstance(step, Show):
            for name in step.fields:
                _field_type(schema, name)
            state = "done"
        elif isinstance(step, WriteJson):
            state = "done"
    if state != "done" and complete:
        found = "groups" if state == "groups" else "rows"
        raise TypeMismatch(f"the program ends with {found} and produces no output")
    return schema


def _field_type(schema, name):
    if name not in schema:
        known = ", ".join(schema)
        raise TypeMismatch(f"there is no field '{name}' at this point (fields: {known})")
    return schema[name]
