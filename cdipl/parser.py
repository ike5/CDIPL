"""Read an intent file written in standard phrases and check it."""
import re

from . import slots
from .languages import HEADERS, PHRASES
from .model import (
    COMPARISONS,
    MAX_INTEGER,
    Add,
    Arith,
    Concat,
    Condition,
    Count,
    Field,
    Filter,
    Group,
    IfNone,
    IntentError,
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
)

IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
TOKEN = re.compile(r'\s*(?:(?P<text>"(?:[^"\\]|\\.)*")|(?P<number>-?\d+)(?![\w.])|(?P<op>>=|<=|!=|=|<|>)|'
                   r"(?P<sym>[-+*&()])|(?P<comma>,)|(?P<word>[^\W\d]\w*))")


def unquote(literal):
    """Only \\" and \\\\ are escapes; any other backslash stands for itself."""
    return re.sub(r'\\(["\\])', r"\1", literal[1:-1])


def quote(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def tokens(text, line):
    """Split a statement into (kind, value) pairs."""
    found, position = [], 0
    text = text.rstrip()
    while position < len(text):
        match = TOKEN.match(text, position)
        if match is None:
            raise IntentError(line, f"cannot read '{text[position:].strip()}'")
        kind = match.lastgroup
        value = match.group(kind)
        if kind == "text":
            value = unquote(value)
        elif kind == "number":
            value = int(value)
            if abs(value) > MAX_INTEGER:
                raise IntentError(line, f"the number {value} is outside the range of whole numbers the language supports")
        found.append((kind, value))
        position = match.end()
    return found


def parse(text, resolver=None):
    """Turn intent text into a checked Program. Raises IntentError.

    Statements written in standard phrases are read by fixed rules. Any other statement is
    passed to the resolver, if one is given, which chooses the block it means.
    """
    lines = text.split("\n")
    numbered = [(number, line) for number, line in enumerate(lines, start=1) if line.strip()]
    if not numbered:
        raise IntentError(1, "the file is empty; it must start with a line such as 'language: en'")
    first_number, first = numbered[0]
    language = HEADERS.get(" ".join(first.split()))
    if language is None or first[:1].isspace():
        raise IntentError(first_number, "the first line must name the human language: " + " or ".join(f"'{h}'" for h in HEADERS))
    words = PHRASES[language]
    position = 1
    source, position = _parse_source(numbered, position, words)
    steps = []
    for number, line in numbered[position:]:
        if line[:1].isspace():
            raise IntentError(number, "a statement must not be indented")
        new_steps = _parse_statement(line.strip(), number, words, source, steps, resolver)
        for step in new_steps:
            candidate = steps + [step] if not isinstance(step, Read) or not steps else _replace_read(steps, step)
            try:
                check_chain(source, candidate, complete=False)
            except TypeMismatch as problem:
                raise IntentError(number, str(problem)) from None
            steps = candidate
    last_line = numbered[-1][0]
    try:
        check_chain(source, steps)
    except TypeMismatch as problem:
        raise IntentError(last_line, str(problem)) from None
    return Program(source=source, steps=tuple(steps), language=language)


def _replace_read(steps, read):
    return [read] + steps[1:]


def _parse_source(numbered, position, words):
    if position >= len(numbered):
        raise IntentError(numbered[-1][0], f"a source must be declared, starting with '{words['source']}'")
    number, line = numbered[position]
    pattern = re.compile(
        rf'{re.escape(words["source"])}\s+(?P<name>\S+)\s+{re.escape(words["from"])}\s+'
        rf'(?:(?P<path>"(?:[^"\\]|\\.)*")|{re.escape(words["argument"])}\s+(?P<argument>\d+))\s*:\s*\Z')
    match = pattern.match(line)
    if match is None or line[:1].isspace():
        raise IntentError(number, f"expected a source declaration such as '{words['source']} users {words['from']} "
                                  f"\"users.json\":' or '{words['source']} users {words['from']} {words['argument']} 1:'")
    name = match["name"]
    if not IDENTIFIER.match(name):
        raise IntentError(number, f"'{name}' is not a valid source name")
    path = unquote(match["path"]) if match["path"] else None
    argument = int(match["argument"]) if match["argument"] else None
    if path is not None and (path == "" or any(ord(ch) < 32 for ch in path)):
        raise IntentError(number, "the file path must not be empty or contain control characters")
    if argument is not None and not 1 <= argument <= 99:
        raise IntentError(number, "the argument number must be between 1 and 99")
    types = {words["text"]: "text", words["integer"]: "integer"}
    fields = []
    position += 1
    while position < len(numbered) and numbered[position][1][:1].isspace():
        field_number, field_line = numbered[position]
        match = re.match(r"\s+(\S+)\s*:\s*(\S+)\s*\Z", field_line)
        if match is None:
            raise IntentError(field_number, f"expected a field such as 'name: {words['text']}'")
        field_name, kind = match.groups()
        if not IDENTIFIER.match(field_name) or field_name == "__proto__":
            raise IntentError(field_number, f"'{field_name}' is not a valid field name")
        if kind not in types:
            raise IntentError(field_number, f"unknown type '{kind}'; use {' or '.join(types)}")
        if any(field_name == existing for existing, _ in fields):
            raise IntentError(field_number, f"field '{field_name}' is declared twice")
        fields.append((field_name, types[kind]))
        position += 1
    if not fields:
        raise IntentError(number, "the source must declare at least one field on the lines beneath it")
    return Source(name=name, path=path, argument=argument, fields=tuple(fields)), position


def _strip_phrase(line, phrase):
    """Return the rest of the line if it starts with the phrase as whole words, else None."""
    parts, wanted = line.split(), phrase.split()
    if parts[: len(wanted)] != wanted:
        return None
    return " ".join(parts[len(wanted):])


def _skip(number, words, steps):
    only_read = len(steps) >= 1 and isinstance(steps[0], Read) and all(
        isinstance(step, Filter) and step.line == steps[0].line for step in steps[1:])
    if not only_read:
        raise IntentError(number, f"'{words['skip']}' must come directly after the step that reads the source")
    if steps[0].skip_invalid:
        raise IntentError(number, f"'{words['skip']}' is written twice")
    return [Read(skip_invalid=True, line=steps[0].line, skip_line=number)]


def _parse_statement(line, number, words, source, steps, resolver=None):
    """Read one statement: by the fixed rules if it is a standard phrase, otherwise through the resolver."""
    reads_source = _strip_phrase(line, words["get"]) is not None
    try:
        result = _parse_standard(line, number, words, source, steps)
    except IntentError:
        if resolver is None or reads_source:
            raise
        result = None
    if result is not None:
        return result
    if resolver is None:
        raise IntentError(number, f"'{line}' is not a statement the language knows")
    if not steps:
        raise IntentError(number, f"the first statement must read the source, written as '{words['get']} {source.name}'")
    try:
        names = set(check_chain(source, steps, complete=False)) | {source.name}
    except TypeMismatch as problem:
        raise IntentError(number, str(problem)) from None
    block, found = resolver.resolve(line, number, names)
    step = slots.fill(block, found, number, source.name, steps)
    if isinstance(step, Read):
        return _skip(number, words, steps)
    return [step]


def _parse_standard(line, number, words, source, steps):
    """Read a statement written in standard phrases. Returns None if it does not start with one."""
    rest = _strip_phrase(line, words["skip"])
    if rest is not None:
        _nothing_after(rest, number)
        return _skip(number, words, steps)
    rest = _strip_phrase(line, words["keep"])
    if rest is not None:
        return [Filter(conditions=_conditions(tokens(rest, number), number, words), line=number)]
    rest = _strip_phrase(line, words["sort"])
    if rest is not None:
        return [_sort(rest, number, words)]
    rest = _strip_phrase(line, words["group"])
    if rest is not None:
        return [Group(field=_one_field(tokens(rest, number), number), line=number)]
    rest = _strip_phrase(line, words["count"])
    if rest is not None:
        _nothing_after(rest, number)
        group_field = next((step.field for step in reversed(steps) if isinstance(step, Group)), "")
        return [Count(field=group_field, line=number)]
    rest = _strip_phrase(line, words["if_none"])
    if rest is not None:
        found = tokens(rest, number)
        if len(found) != 1 or found[0][0] != "text":
            raise IntentError(number, f"'{words['if_none']}' must be followed by one piece of text in double quotes")
        if any(ord(ch) < 32 for ch in found[0][1]):
            raise IntentError(number, "the text must not contain control characters")
        return [IfNone(text=found[0][1], line=number)]
    rest = _strip_phrase(line, words["write_json"])
    if rest is not None:
        _nothing_after(rest, number)
        return [WriteJson(line=number)]
    rest = _strip_phrase(line, words["add"])
    if rest is not None:
        return [_added_field(tokens(rest, number), number, words)]
    rest = _strip_phrase(line, words["limit"])
    if rest is not None:
        found = tokens(rest, number)
        if len(found) != 1 or found[0][0] != "number" or found[0][1] < 0:
            raise IntentError(number, f"'{words['limit']}' must be followed by a whole number that is not negative")
        return [Limit(count=found[0][1], line=number)]
    rest = _strip_phrase(line, words["show"])
    if rest is not None:
        return [Show(fields=_field_list(tokens(rest, number), number), line=number)]
    rest = _strip_phrase(line, words["get"])
    if rest is not None:
        found = tokens(rest, number)
        if not found or found[0][0] != "word":
            raise IntentError(number, f"'{words['get']}' must be followed by the name of the source")
        if found[0][1] != source.name:
            raise IntentError(number, f"there is no source named '{found[0][1]}' (the declared source is '{source.name}')")
        if steps:
            raise IntentError(number, "the source can only be read once, at the start")
        result = [Read(line=number)]
        if len(found) > 1:
            if found[1] != ("word", words["where"]):
                raise IntentError(number, f"after the source name, expected '{words['where']}' or nothing")
            result.append(Filter(conditions=_conditions(found[2:], number, words), line=number))
        return result
    return None


def _nothing_after(rest, number):
    if rest:
        raise IntentError(number, f"unexpected '{rest}' at the end of the statement")


def _one_field(found, number):
    if len(found) != 1 or found[0][0] != "word":
        raise IntentError(number, "expected the name of one field")
    return found[0][1]


def _field_list(found, number):
    names = []
    for index, (kind, value) in enumerate(found):
        if index % 2 == 0:
            if kind != "word":
                raise IntentError(number, "expected field names separated by commas")
            names.append(value)
        elif kind != "comma":
            raise IntentError(number, "expected field names separated by commas")
    if not names or len(found) % 2 == 0:
        raise IntentError(number, "expected field names separated by commas")
    if len(set(names)) != len(names):
        raise IntentError(number, "a field is listed twice")
    return tuple(names)


class Formula:
    """Reads formulas from a list of tokens: fields, numbers, text, + - * & and brackets."""

    def __init__(self, found, number, start=0):
        self.found = found
        self.number = number
        self.index = start

    def peek(self):
        return self.found[self.index] if self.index < len(self.found) else (None, None)

    def formula(self):
        left = self.term()
        while True:
            kind, value = self.peek()
            if kind == "sym" and value in ("+", "-", "&"):
                self.index += 1
                right = self.term()
                left = _join(left, right) if value == "&" else Arith(value, left, right)
            elif kind == "number" and value < 0:  # "a -5" written without a space after the minus sign
                self.index += 1
                left = Arith("-", left, Number(-value))
            else:
                return left

    def term(self):
        left = self.atom()
        while self.peek() == ("sym", "*"):
            self.index += 1
            left = Arith("*", left, self.atom())
        return left

    def atom(self):
        kind, value = self.peek()
        self.index += 1
        if kind == "number":
            return Number(value)
        if kind == "text":
            if any(ord(ch) < 32 for ch in value):
                raise IntentError(self.number, "the text must not contain control characters")
            return Text(value)
        if kind == "word":
            return Field(value)
        if (kind, value) == ("sym", "("):
            inner = self.formula()
            if self.peek() != ("sym", ")"):
                raise IntentError(self.number, "a bracket is opened but not closed")
            self.index += 1
            return inner
        raise IntentError(self.number, "expected a field, a number, text in double quotes or a formula")


def _join(left, right):
    parts = (left.parts if isinstance(left, Concat) else (left,)) + (right.parts if isinstance(right, Concat) else (right,))
    return Concat(parts)


def _conditions(found, number, words, joiner=None):
    """Read conditions joined by the word for 'and'. joiner is the token that stands for it."""
    joiner = joiner or ("word", words["and"])
    conditions, reader = [], Formula(found, number)
    example = "expected a condition such as 'age >= 18' or 'city = \"Lima\"'"
    while True:
        if reader.peek() == (None, None):
            raise IntentError(number, example)
        left = reader.formula()
        kind, op = reader.peek()
        if kind != "op":
            raise IntentError(number, example)
        reader.index += 1
        right = reader.formula()
        assert op in COMPARISONS
        conditions.append(Condition(left, op, right))
        if reader.peek() == (None, None):
            return tuple(conditions)
        if reader.peek() != joiner:
            raise IntentError(number, f"conditions must be joined by '{words['and']}'")
        reader.index += 1


def _added_field(found, number, words):
    """Read 'name = formula'."""
    if len(found) < 3 or found[0][0] != "word" or found[1] != ("op", "="):
        raise IntentError(number, f"expected a new field and a formula, such as '{words['add']} total = price * 2'")
    if not IDENTIFIER.match(found[0][1]) or found[0][1] == "__proto__":
        raise IntentError(number, f"'{found[0][1]}' is not a valid field name")
    reader = Formula(found, number, start=2)
    formula = reader.formula()
    if reader.peek() != (None, None):
        raise IntentError(number, "unexpected text after the formula")
    return Add(name=found[0][1], formula=formula, line=number)


def formula_text(formula, parent=0, on_right=False):
    """Write a formula with as few brackets as its meaning allows."""
    if isinstance(formula, Field):
        return formula.name
    if isinstance(formula, Number):
        return str(formula.value)
    if isinstance(formula, Text):
        return quote(formula.value)
    if isinstance(formula, Concat):
        level = 1
        body = " & ".join(formula_text(part, level, index > 0) for index, part in enumerate(formula.parts))
    else:
        level = 2 if formula.op == "*" else 1
        body = f"{formula_text(formula.left, level)} {formula.op} {formula_text(formula.right, level, True)}"
    return f"({body})" if level < parent or (level == parent and on_right) else body


def _sort(rest, number, words):
    parts = rest.split()
    if not parts:
        raise IntentError(number, "expected the name of the field to sort by")
    name, remainder = parts[0], " ".join(parts[1:])
    if not IDENTIFIER.match(name):
        raise IntentError(number, f"'{name}' is not a valid field name")
    ignore_case = False
    if remainder.endswith(words["ignoring_case"]):
        ignore_case = True
        remainder = remainder[: -len(words["ignoring_case"])].strip()
    if remainder == words["ascending"]:
        descending = False
    elif remainder == words["descending"]:
        descending = True
    else:
        raise IntentError(number, f"after the field name, expected '{words['ascending']}' or '{words['descending']}'"
                                  f", optionally followed by '{words['ignoring_case']}'")
    return Sort(field=name, descending=descending, ignore_case=ignore_case, line=number)


def step_text(step, words, source):
    """The statements a step stands for, in standard phrases. Returns a list of lines."""
    if isinstance(step, Read):
        return [f"{words['get']} {source.name}"] + ([words["skip"]] if step.skip_invalid else [])
    if isinstance(step, Filter):
        joined = f" {words['and']} ".join(
            f"{formula_text(c.left)} {c.op} {formula_text(c.right)}" for c in step.conditions)
        return [f"{words['keep']} {joined}"]
    if isinstance(step, Add):
        return [f"{words['add']} {step.name} = {formula_text(step.formula)}"]
    if isinstance(step, Sort):
        direction = words["descending"] if step.descending else words["ascending"]
        suffix = f" {words['ignoring_case']}" if step.ignore_case else ""
        return [f"{words['sort']} {step.field} {direction}{suffix}"]
    if isinstance(step, Limit):
        return [f"{words['limit']} {step.count}"]
    if isinstance(step, Group):
        return [f"{words['group']} {step.field}"]
    if isinstance(step, Count):
        return [words["count"]]
    if isinstance(step, IfNone):
        return [f"{words['if_none']} {quote(step.text)}"]
    if isinstance(step, Show):
        return [f"{words['show']} {', '.join(step.fields)}"]
    return [words["write_json"]]


def render(program, language=None):
    """Write a Program as intent text in standard phrases."""
    words = PHRASES[language or program.language]
    source = program.source
    origin = quote(source.path) if source.path is not None else f"{words['argument']} {source.argument}"
    out = [words["header"], "", f"{words['source']} {source.name} {words['from']} {origin}:"]
    out += [f"    {name}: {words[kind]}" for name, kind in source.fields]
    out.append("")
    for step in program.steps:
        out += step_text(step, words, source)
    return "\n".join(out) + "\n"
