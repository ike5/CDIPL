"""Generate Python programs, and recognise programs this generator wrote."""
import re

from .common import (Condition, Count, Filter, Group, IfNone, Limit, NotGenerated, Read, Show, Sort, Source,
                     WriteJson, assemble, blocks_used, schemas)

FILE_NAME = "main.py"

# Fixed support code. Each piece belongs to one block and is included only when needed.
SUPPORT = [
    ("exit-on-error", "always", '''\
def fail(status, category, detail):
    print(f"error: {category}: {SOURCE}: {detail}", file=sys.stderr)
    sys.exit(status)
'''),
    ("cli-options", "argument", '''\
def read_argument(position):
    if len(sys.argv) <= position:
        fail(2, "usage", f"argument {position} is required")
    return sys.argv[position]
'''),
    ("read-text-file", "always", '''\
def read_text_file(path):
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError as error:
        fail(3, "cannot-read", f"{path}: {error.strerror}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        fail(4, "bad-json", "the input is not valid UTF-8")
'''),
    ("parse-json", "always", '''\
def reject_constant(name):
    raise ValueError(name)
'''),
    ("parse-json", "always", '''\
def parse_whole_number(digits):
    return int(digits) if len(digits) < 19 else float(digits)
'''),
    ("parse-json", "always", '''\
def parse_json(text):
    try:
        return json.loads(text, parse_constant=reject_constant, parse_int=parse_whole_number)
    except (ValueError, RecursionError):
        fail(4, "bad-json", "the input is not valid JSON")
'''),
    ("check-list-of-records", "always", '''\
def check_list(data):
    if not isinstance(data, list):
        fail(5, "not-a-list", "the input must be a list of records")
    return data
'''),
    ("check-required-types", "always", '''\
def to_text(value):
    if not isinstance(value, str):
        return None
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return None
    return value
'''),
    ("check-required-types", "always", '''\
def to_integer(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    if abs(value) > MAX_INTEGER:
        return None
    return int(value)
'''),
    ("check-required-types", "always", '''\
def to_row(record):
    if not isinstance(record, dict):
        return None
    row = {}
    for name, kind in FIELDS.items():
        value = to_text(record.get(name)) if kind == "text" else to_integer(record.get(name))
        if value is None:
            return None
        row[name] = value
    return row
'''),
    ("check-required-types", "strict", '''\
def require_valid(records):
    rows = []
    for position, record in enumerate(records, start=1):
        row = to_row(record)
        if row is None:
            fail(6, "invalid-record", f"record {position} does not match the declared fields")
        rows.append(row)
    return rows
'''),
    ("drop-invalid-rows", "skip", '''\
def keep_valid(records):
    return [row for row in map(to_row, records) if row is not None]
'''),
    ("sort-rows", "fold", '''\
def fold_case(text):
    return "".join(chr(ord(ch) + 32) if "A" <= ch <= "Z" else ch for ch in text)
'''),
    ("group-by-key", "group", '''\
def group_rows(rows, name):
    groups = {}
    for row in rows:
        groups.setdefault(row[name], []).append(row)
    return groups
'''),
    ("count-values", "count", '''\
def count_groups(groups, name):
    return [{name: key, "count": len(members)} for key, members in groups.items()]
'''),
    ("print-message", "always", '''\
def emit(text):
    sys.stdout.buffer.write(text.encode("utf-8"))
'''),
    ("print-table", "show", '''\
def show_table(rows, names):
    table = [[str(row[name]) for name in names] for row in rows]
    widths = [max((len(line[index]) for line in table), default=0) for index in range(len(names))]
    for line in table:
        cells = [cell.ljust(width) for cell, width in zip(line[:-1], widths)]
        emit("  ".join(cells + [line[-1]]) + "\\n")
'''),
    ("format-json", "json", '''\
def write_json(rows):
    emit(json.dumps(rows, separators=(",", ":")) + "\\n")
'''),
]

OPERATORS = {"=": "==", "!=": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
FROM_OPERATORS = {code: op for op, code in OPERATORS.items()}


# The shape of the line each block adds to main(). Part of the block's version.
FORMS = {
    "read-text-file": "text = read_text_file(PATH)",
    "cli-options": "read_argument(N)",
    "parse-json": "records = check_list(parse_json(text))",
    "check-required-types": "rows = require_valid(records)",
    "drop-invalid-rows": "rows = keep_valid(records)",
    "filter-rows": "rows = [row for row in rows if CONDITIONS]",
    "sort-rows": "rows = sorted(rows, key=lambda row: KEY, reverse=True)",
    "take-first": "rows = rows[:N]",
    "group-by-key": "groups = group_rows(rows, FIELD)",
    "count-values": "rows = count_groups(groups, FIELD)",
    "print-message": "if not rows: emit(TEXT); return",
    "print-table": "show_table(rows, FIELDS)",
    "format-json": "write_json(rows)",
}


def quote(text):
    out = []
    for ch in text:
        code = ord(ch)
        if ch in '\\"':
            out.append("\\" + ch)
        elif ch == "\n":
            out.append("\\n")
        elif 32 <= code < 127:
            out.append(ch)
        elif code < 256:
            out.append(f"\\x{code:02x}")
        elif code < 65536:
            out.append(f"\\u{code:04x}")
        else:
            out.append(f"\\U{code:08x}")
    return '"' + "".join(out) + '"'


STRING = r'"(?:[^"\\]|\\.)*"'


def unquote(literal):
    def replace(match):
        body = match.group(1)
        if body[0] in '\\"':
            return body
        if body == "n":
            return "\n"
        return chr(int(body[1:], 16))

    inner = literal[1:-1]
    if re.fullmatch(r'(?:[ -!#-\[\]-~]|\\[\\"n]|\\x[0-9a-f]{2}|\\u[0-9a-f]{4}|\\U[0-9a-f]{8})*', inner) is None:
        raise NotGenerated("a text value is not written the way the compiler writes it")
    try:
        return re.sub(r'\\([\\"n]|x[0-9a-f]{2}|u[0-9a-f]{4}|U[0-9a-f]{8})', replace, inner)
    except (ValueError, OverflowError):
        raise NotGenerated("a text value cannot be read") from None


def needs(program):
    flags = {"always"}
    for step in program.steps:
        if isinstance(step, Read):
            flags.add("skip" if step.skip_invalid else "strict")
            if program.source.argument is not None:
                flags.add("argument")
        elif isinstance(step, Sort) and step.ignore_case:
            flags.add("fold")
        elif isinstance(step, Group):
            flags.add("group")
        elif isinstance(step, Count):
            flags.add("count")
        elif isinstance(step, Show):
            flags.add("show")
        elif isinstance(step, WriteJson):
            flags.add("json")
    return flags


def condition(cond):
    value = quote(cond.value) if isinstance(cond.value, str) else str(cond.value)
    return f'row[{quote(cond.field)}] {OPERATORS[cond.op]} {value}'


def main_lines(program):
    """The body of main(), as (text, intent line) pairs."""
    source = program.source
    out = []
    for step in program.steps:
        if isinstance(step, Read):
            origin = quote(source.path) if source.path is not None else f"read_argument({source.argument})"
            out.append((f"    text = read_text_file({origin})", step.line))
            out.append(("    records = check_list(parse_json(text))", step.line))
            if step.skip_invalid:
                out.append(("    rows = keep_valid(records)", step.skip_line))
            else:
                out.append(("    rows = require_valid(records)", step.line))
        elif isinstance(step, Filter):
            joined = " and ".join(condition(cond) for cond in step.conditions)
            out.append((f"    rows = [row for row in rows if {joined}]", step.line))
        elif isinstance(step, Sort):
            key = f"row[{quote(step.field)}]"
            if step.ignore_case:
                key = f"fold_case({key})"
            reverse = ", reverse=True" if step.descending else ""
            out.append((f"    rows = sorted(rows, key=lambda row: {key}{reverse})", step.line))
        elif isinstance(step, Limit):
            out.append((f"    rows = rows[:{step.count}]", step.line))
        elif isinstance(step, Group):
            out.append((f"    groups = group_rows(rows, {quote(step.field)})", step.line))
        elif isinstance(step, Count):
            out.append((f"    rows = count_groups(groups, {quote(step.field)})", step.line))
        elif isinstance(step, IfNone):
            out.append(("    if not rows:", step.line))
            out.append((f"        emit({quote(step.text + chr(10))})", step.line))
            out.append(("        return", step.line))
        elif isinstance(step, Show):
            names = ", ".join(quote(name) for name in step.fields)
            out.append((f"    show_table(rows, [{names}])", step.line))
        elif isinstance(step, WriteJson):
            out.append(("    write_json(rows)", step.line))
    return out


def generate(program):
    """Return the program text as a list of (line, origin) pairs.

    origin is an intent line number, or the name of the block a support line belongs to.
    """
    fields = ", ".join(f"{quote(name)}: {quote(kind)}" for name, kind in program.source.fields)
    lines = [("import json", "support"), ("import sys", "support"), ("", "support"),
             (f"SOURCE = {quote(program.source.name)}", "support"),
             ("FIELDS = {" + fields + "}", "support"),
             ("MAX_INTEGER = 9007199254740991", "support")]
    flags = needs(program)
    for block, flag, text in SUPPORT:
        if flag in flags:
            lines += [("", "support"), ("", "support")]
            lines += [(line, block) for line in text.rstrip("\n").split("\n")]
    lines += [("", "support"), ("", "support"), ("def main():", "support")]
    lines += main_lines(program)
    lines += [("", "support"), ("", "support"), ('if __name__ == "__main__":', "support"), ("    main()", "support")]
    return lines


FIELD_NAME = r'"([A-Za-z_][A-Za-z0-9_]*)"'
CONDITION = re.compile(rf'row\[{FIELD_NAME}\] (==|!=|<=|>=|<|>) ({STRING}|-?\d+)')


def lift(text):
    """Recover the Program from generated text. Raises NotGenerated."""
    lines = text.split("\n")
    name = _only(re.fullmatch(rf"SOURCE = {FIELD_NAME}", line) for line in lines)
    fields_line = _only(re.fullmatch(r"FIELDS = \{(.*)\}", line) for line in lines)
    pairs = re.findall(rf'{FIELD_NAME}: "(text|integer)"', fields_line.group(1))
    if not pairs or len({field for field, _ in pairs}) != len(pairs):
        raise NotGenerated("the declared fields cannot be read")
    try:
        start = lines.index("def main():") + 1
    except ValueError:
        raise NotGenerated("there is no main function") from None
    body = []
    for line in lines[start:]:
        if not line.startswith("    "):
            break
        body.append(line)
    steps, path, argument = [], None, None
    index = 0
    while index < len(body):
        line = body[index]
        index += 1
        if match := re.fullmatch(rf"    text = read_text_file\((?:({STRING})|read_argument\((\d+)\))\)", line):
            path = unquote(match[1]) if match[1] else None
            argument = int(match[2]) if match[2] else None
            if body[index:index + 1] != ["    records = check_list(parse_json(text))"]:
                raise NotGenerated("the lines that read the source are not as generated")
            mode = body[index + 1] if index + 1 < len(body) else ""
            if mode not in ("    rows = require_valid(records)", "    rows = keep_valid(records)"):
                raise NotGenerated("the lines that read the source are not as generated")
            steps.append(Read(skip_invalid="keep_valid" in mode))
            index += 2
        elif match := re.fullmatch(r"    rows = \[row for row in rows if (.*)\]", line):
            steps.append(Filter(conditions=_conditions(match[1])))
        elif match := re.fullmatch(rf"    rows = sorted\(rows, key=lambda row: (fold_case\()?row\[{FIELD_NAME}\]\)?(, reverse=True)?\)", line):
            steps.append(Sort(field=match[2], descending=bool(match[3]), ignore_case=bool(match[1])))
        elif match := re.fullmatch(r"    rows = rows\[:(\d+)\]", line):
            steps.append(Limit(count=int(match[1])))
        elif match := re.fullmatch(rf"    groups = group_rows\(rows, {FIELD_NAME}\)", line):
            steps.append(Group(field=match[1]))
        elif match := re.fullmatch(rf"    rows = count_groups\(groups, {FIELD_NAME}\)", line):
            steps.append(Count(field=match[1]))
        elif line == "    if not rows:":
            match = re.fullmatch(rf"        emit\(({STRING})\)", body[index] if index < len(body) else "")
            if match is None or body[index + 1:index + 2] != ["        return"]:
                raise NotGenerated("the lines that print a message are not as generated")
            message = unquote(match[1])
            if not message.endswith("\n"):
                raise NotGenerated("the message does not end with a line break")
            steps.append(IfNone(text=message[:-1]))
            index += 2
        elif match := re.fullmatch(r"    show_table\(rows, \[(.*)\]\)", line):
            names = re.findall(FIELD_NAME, match[1])
            if ", ".join(f'"{n}"' for n in names) != match[1] or not names:
                raise NotGenerated("the list of fields to show cannot be read")
            steps.append(Show(fields=tuple(names)))
        elif line == "    write_json(rows)":
            steps.append(WriteJson())
        else:
            raise NotGenerated(f"this line is not one the compiler generates: {line.strip()}")
    source = Source(name=name.group(1), path=path, argument=argument, fields=tuple(pairs))
    return assemble(source, steps)


def _only(matches):
    found = [match for match in matches if match]
    if len(found) != 1:
        raise NotGenerated("the header of the program is not as generated")
    return found[0]


def _conditions(text):
    conditions, position = [], 0
    while True:
        match = CONDITION.match(text, position)
        if match is None:
            raise NotGenerated("a condition cannot be read")
        raw = match[3]
        value = unquote(raw) if raw.startswith('"') else int(raw)
        conditions.append(Condition(field=match[1], op=FROM_OPERATORS[match[2]], value=value))
        position = match.end()
        if position == len(text):
            return tuple(conditions)
        if not text.startswith(" and ", position):
            raise NotGenerated("conditions are not joined as generated")
        position += 5


__all__ = ["FILE_NAME", "SUPPORT", "blocks_used", "generate", "lift", "schemas"]
