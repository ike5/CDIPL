"""Read an intent file written in standard phrases and check it."""
import re

from .languages import HEADERS, PHRASES
from .model import (
    COMPARISONS,
    MAX_INTEGER,
    Condition,
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
    Source,
    TypeMismatch,
    WriteJson,
    check_chain,
)

IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
TOKEN = re.compile(r'\s*(?:(?P<text>"(?:[^"\\]|\\["\\])*")|(?P<number>-?\d+)(?![\w.])|(?P<op>>=|<=|!=|=|<|>)|'
                   r"(?P<comma>,)|(?P<word>[^\W\d]\w*))")


def unquote(literal):
    return re.sub(r"\\(.)", r"\1", literal[1:-1])


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


def parse(text):
    """Turn intent text into a checked Program. Raises IntentError."""
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
        new_steps = _parse_statement(line.strip(), number, words, source, steps)
        for step in new_steps:
            candidate = steps + [step] if not isinstance(step, Read) or not steps else _replace_read(steps, step)
            try:
                _check_prefix(source, candidate)
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


def _check_prefix(source, steps):
    """Check a chain that may not be finished yet."""
    try:
        check_chain(source, steps)
    except TypeMismatch as problem:
        if "produces no output" not in str(problem):
            raise


def _parse_source(numbered, position, words):
    if position >= len(numbered):
        raise IntentError(numbered[-1][0], f"a source must be declared, starting with '{words['source']}'")
    number, line = numbered[position]
    pattern = re.compile(
        rf'{re.escape(words["source"])}\s+(?P<name>\S+)\s+{re.escape(words["from"])}\s+'
        rf'(?:(?P<path>"(?:[^"\\]|\\["\\])*")|{re.escape(words["argument"])}\s+(?P<argument>\d+))\s*:\s*\Z')
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
        if not IDENTIFIER.match(field_name):
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


def _parse_statement(line, number, words, source, steps):
    rest = _strip_phrase(line, words["skip"])
    if rest is not None:
        _nothing_after(rest, number)
        only_read = len(steps) >= 1 and isinstance(steps[0], Read) and all(
            isinstance(step, Filter) and step.line == steps[0].line for step in steps[1:])
        if not only_read:
            raise IntentError(number, f"'{words['skip']}' must come directly after the step that reads the source")
        if steps[0].skip_invalid:
            raise IntentError(number, f"'{words['skip']}' is written twice")
        return [Read(skip_invalid=True, line=steps[0].line, skip_line=number)]
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
    raise IntentError(number, f"'{line}' is not a statement the language knows")


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


def _conditions(found, number, words):
    conditions, index = [], 0
    while True:
        part = found[index:index + 3]
        if len(part) != 3 or part[0][0] != "word" or part[1][0] != "op" or part[2][0] not in ("number", "text"):
            raise IntentError(number, "expected a condition such as 'age >= 18' or 'city = \"Lima\"'")
        if part[2][0] == "text" and any(ord(ch) < 32 for ch in part[2][1]):
            raise IntentError(number, "the text must not contain control characters")
        assert part[1][1] in COMPARISONS
        conditions.append(Condition(field=part[0][1], op=part[1][1], value=part[2][1]))
        index += 3
        if index == len(found):
            return tuple(conditions)
        if found[index] != ("word", words["and"]):
            raise IntentError(number, f"conditions must be joined by '{words['and']}'")
        index += 1


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


def render(program, language=None):
    """Write a Program as intent text in standard phrases."""
    words = PHRASES[language or program.language]
    source = program.source
    origin = quote(source.path) if source.path is not None else f"{words['argument']} {source.argument}"
    out = [words["header"], "", f"{words['source']} {source.name} {words['from']} {origin}:"]
    out += [f"    {name}: {words[kind]}" for name, kind in source.fields]
    out.append("")
    for step in program.steps:
        if isinstance(step, Read):
            out.append(f"{words['get']} {source.name}")
            if step.skip_invalid:
                out.append(words["skip"])
        elif isinstance(step, Filter):
            joined = f" {words['and']} ".join(
                f"{c.field} {c.op} {quote(c.value) if isinstance(c.value, str) else c.value}" for c in step.conditions)
            out.append(f"{words['keep']} {joined}")
        elif isinstance(step, Sort):
            direction = words["descending"] if step.descending else words["ascending"]
            suffix = f" {words['ignoring_case']}" if step.ignore_case else ""
            out.append(f"{words['sort']} {step.field} {direction}{suffix}")
        elif isinstance(step, Limit):
            out.append(f"{words['limit']} {step.count}")
        elif isinstance(step, Group):
            out.append(f"{words['group']} {step.field}")
        elif isinstance(step, Count):
            out.append(words["count"])
        elif isinstance(step, IfNone):
            out.append(f"{words['if_none']} {quote(step.text)}")
        elif isinstance(step, Show):
            out.append(f"{words['show']} {', '.join(step.fields)}")
        elif isinstance(step, WriteJson):
            out.append(words["write_json"])
    return "\n".join(out) + "\n"
