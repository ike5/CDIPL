"""Generate JavaScript (Node) programs, and recognise programs this generator wrote."""
import re

from .common import (
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
    NotGenerated,
    Number,
    Read,
    Scanner,
    Show,
    Sort,
    Source,
    Text,
    WriteJson,
    assemble,
    blocks_used,
    formula_type,
    formulas,
    has_arithmetic,
    schemas,
)

FILE_NAME = "main.js"
SUPPORTED = None  # the blocks this target can build; None means every block


def run_command(program_path):
    """The command that runs a generated program."""
    return ["node", str(program_path)]


SUPPORT = [
    ("exit-on-error", "always", '''\
class Failure extends Error {
  constructor(status, category, detail) {
    super(detail);
    this.status = status;
    this.category = category;
    this.detail = detail;
  }
}
'''),
    ("exit-on-error", "always", '''\
function fail(status, category, detail) {
  throw new Failure(status, category, detail);
}
'''),
    ("cli-options", "argument", '''\
function readArgument(position) {
  const value = process.argv[position + 1];
  if (value === undefined) {
    fail(2, "usage", `argument ${position} is required`);
  }
  return value;
}
'''),
    ("read-text-file", "always", '''\
function readTextFile(path) {
  let data;
  try {
    data = fs.readFileSync(path);
  } catch (error) {
    fail(3, "cannot-read", `${path}: ${error.code}`);
  }
  try {
    return new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(data);
  } catch {
    return fail(4, "bad-json", "the input is not valid UTF-8");
  }
}
'''),
    ("parse-json", "always", '''\
function parseJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    return fail(4, "bad-json", "the input is not valid JSON");
  }
}
'''),
    ("check-list-of-records", "always", '''\
function checkList(data) {
  if (!Array.isArray(data)) {
    fail(5, "not-a-list", "the input must be a list of records");
  }
  return data;
}
'''),
    ("check-required-types", "always", '''\
function isValid(value, kind) {
  if (kind === "text") {
    return typeof value === "string" && value.isWellFormed();
  }
  return Number.isSafeInteger(value);
}
'''),
    ("check-required-types", "always", '''\
function toRow(record) {
  if (record === null || typeof record !== "object" || Array.isArray(record)) {
    return null;
  }
  const entries = [];
  for (const [name, kind] of FIELDS) {
    const value = Object.hasOwn(record, name) ? record[name] : undefined;
    if (!isValid(value, kind)) {
      return null;
    }
    entries.push([name, value === 0 ? 0 : value]);
  }
  return Object.fromEntries(entries);
}
'''),
    ("check-required-types", "strict", '''\
function requireValid(records) {
  return records.map((record, index) => {
    const row = toRow(record);
    if (row === null) {
      fail(6, "invalid-record", `record ${index + 1} does not match the declared fields`);
    }
    return row;
  });
}
'''),
    ("drop-invalid-rows", "skip", '''\
function keepValid(records) {
  return records.map(toRow).filter((row) => row !== null);
}
'''),
    ("calculate", "whole", '''\
function whole(value) {
  if (!Number.isSafeInteger(value)) {
    fail(7, "out-of-range", "a calculation gave a number outside the supported range");
  }
  return value === 0 ? 0 : value;
}
'''),
    ("sort-rows", "compare", '''\
function compareText(left, right) {
  const a = Array.from(left, (ch) => ch.codePointAt(0));
  const b = Array.from(right, (ch) => ch.codePointAt(0));
  for (let index = 0; index < a.length && index < b.length; index += 1) {
    if (a[index] !== b[index]) {
      return a[index] - b[index];
    }
  }
  return a.length - b.length;
}
'''),
    ("sort-rows", "fold", '''\
function foldCase(text) {
  return text.replace(/[A-Z]/g, (ch) => ch.toLowerCase());
}
'''),
    ("group-by-key", "group", '''\
function groupRows(rows, name) {
  const groups = new Map();
  for (const row of rows) {
    if (!groups.has(row[name])) {
      groups.set(row[name], []);
    }
    groups.get(row[name]).push(row);
  }
  return groups;
}
'''),
    ("count-values", "count", '''\
function countGroups(groups, name) {
  return Array.from(groups, ([key, members]) => ({ [name]: key, count: members.length }));
}
'''),
    ("print-message", "always", '''\
function emit(text) {
  process.stdout.write(text);
}
'''),
    ("print-table", "show", '''\
function showTable(rows, names) {
  const table = rows.map((row) => names.map((name) => String(row[name])));
  const widths = names.map((_, index) => table.reduce((widest, line) => Math.max(widest, Array.from(line[index]).length), 0));
  for (const line of table) {
    const cells = line.slice(0, -1).map((cell, index) => cell + " ".repeat(widths[index] - Array.from(cell).length));
    emit(`${[...cells, line.at(-1)].join("  ")}\\n`);
  }
}
'''),
    ("format-json", "json", '''\
function writeJson(rows) {
  const text = JSON.stringify(rows).replace(/[\\u007f-\\uffff]/g, (ch) => `\\\\u${ch.charCodeAt(0).toString(16).padStart(4, "0")}`);
  emit(`${text}\\n`);
}
'''),
]

TAIL = '''\
try {
  main();
} catch (error) {
  if (!(error instanceof Failure)) {
    throw error;
  }
  process.stderr.write(`error: ${error.category}: ${SOURCE}: ${error.detail}\\n`);
  process.exitCode = error.status;
}
'''

ORDER = {"<": "< 0", "<=": "<= 0", ">": "> 0", ">=": ">= 0"}
NUMBER_OPERATORS = {"=": "===", "!=": "!==", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
FROM_NUMBER = {code: op for op, code in NUMBER_OPERATORS.items()}
FROM_ORDER = {code: op for op, code in ORDER.items()}


# The shape of the line each block adds to main(). Part of the block's version.
FORMS = {
    "read-text-file": "const text = readTextFile(PATH);",
    "cli-options": "readArgument(N)",
    "parse-json": "const records = checkList(parseJson(text));",
    "check-required-types": "let rows = requireValid(records);",
    "drop-invalid-rows": "let rows = keepValid(records);",
    "filter-rows": "rows = rows.filter((row) => CONDITIONS);",
    "calculate": "rows = rows.map((row) => ({ ...row, NAME: FORMULA })); whole(A + B); A + B",
    "sort-rows": "rows = [...rows].sort((a, b) => COMPARE);",
    "take-first": "rows = rows.slice(0, N);",
    "group-by-key": "let groups = groupRows(rows, FIELD);",
    "count-values": "rows = countGroups(groups, FIELD);",
    "print-message": "if (rows.length === 0) { emit(TEXT); return; }",
    "print-table": "showTable(rows, FIELDS);",
    "format-json": "writeJson(rows);",
}


def quote(text):
    out = []
    for ch in text:
        if ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif 32 <= ord(ch) < 127 and ch != '"':
            out.append(ch)
        else:
            units = ch.encode("utf-16-be")
            out += [f"\\u{int.from_bytes(units[i:i + 2], 'big'):04x}" for i in range(0, len(units), 2)]
    return '"' + "".join(out) + '"'


STRING = r'"(?:[^"\\]|\\.)*"'


def unquote(literal):
    inner = literal[1:-1]
    if re.fullmatch(r'(?:[ -!#-\[\]-~]|\\[\\n]|\\u[0-9a-f]{4})*', inner) is None:
        raise NotGenerated("a text value is not written the way the compiler writes it")
    units = bytearray()
    for match in re.finditer(r'\\([\\n]|u[0-9a-f]{4})|.', inner):
        body = match.group(1)
        if body is None:
            code = ord(match.group(0))
        elif body == "n":
            code = 10
        elif body == "\\":
            code = ord(body)
        else:
            code = int(body[1:], 16)
        units += code.to_bytes(2, "big")
    try:
        return units.decode("utf-16-be")
    except UnicodeDecodeError:
        raise NotGenerated("a text value cannot be read") from None


def needs(program):
    flags = {"always"}
    kinds = schemas(program)
    for step, schema in zip(program.steps, kinds):
        if isinstance(step, Read):
            flags.add("skip" if step.skip_invalid else "strict")
            if program.source.argument is not None:
                flags.add("argument")
        elif isinstance(step, Filter):
            if any(cond.op in ORDER and formula_type(schema, cond.left) == "text" for cond in step.conditions):
                flags.add("compare")
        elif isinstance(step, Sort):
            if schema[step.field] == "text":
                flags.add("compare")
            if step.ignore_case:
                flags.add("fold")
        elif isinstance(step, Group):
            flags.add("group")
        elif isinstance(step, Count):
            flags.add("count")
        elif isinstance(step, Show):
            flags.add("show")
        elif isinstance(step, WriteJson):
            flags.add("json")
        if any(has_arithmetic(value) for value in formulas(step)):
            flags.add("whole")
    return flags


def formula(value):
    """Write a formula as JavaScript."""
    if isinstance(value, Field):
        return f"row.{value.name}"
    if isinstance(value, Number):
        return str(value.value)
    if isinstance(value, Text):
        return quote(value.value)
    if isinstance(value, Arith):
        return f"whole({formula(value.left)} {value.op} {formula(value.right)})"
    return " + ".join(formula(part) for part in value.parts)


def condition(cond, schema):
    left, right = formula(cond.left), formula(cond.right)
    if cond.op in ORDER and formula_type(schema, cond.left) == "text":
        return f"compareText({left}, {right}) {ORDER[cond.op]}"
    return f"{left} {NUMBER_OPERATORS[cond.op]} {right}"


def main_lines(program):
    source = program.source
    out = []
    grouped = False
    for step, schema in zip(program.steps, schemas(program)):
        if isinstance(step, Read):
            origin = quote(source.path) if source.path is not None else f"readArgument({source.argument})"
            out.append((f"  const text = readTextFile({origin});", step.line))
            out.append(("  const records = checkList(parseJson(text));", step.line))
            if step.skip_invalid:
                out.append(("  let rows = keepValid(records);", step.skip_line))
            else:
                out.append(("  let rows = requireValid(records);", step.line))
        elif isinstance(step, Filter):
            joined = " && ".join(condition(cond, schema) for cond in step.conditions)
            out.append((f"  rows = rows.filter((row) => {joined});", step.line))
        elif isinstance(step, Add):
            out.append((f"  rows = rows.map((row) => ({{ ...row, {step.name}: {formula(step.formula)} }}));", step.line))
        elif isinstance(step, Sort):
            first, second = ("b", "a") if step.descending else ("a", "b")
            if schema[step.field] == "integer":
                compare = f"{first}.{step.field} - {second}.{step.field}"
            elif step.ignore_case:
                compare = f"compareText(foldCase({first}.{step.field}), foldCase({second}.{step.field}))"
            else:
                compare = f"compareText({first}.{step.field}, {second}.{step.field})"
            out.append((f"  rows = [...rows].sort((a, b) => {compare});", step.line))
        elif isinstance(step, Limit):
            out.append((f"  rows = rows.slice(0, {step.count});", step.line))
        elif isinstance(step, Group):
            keyword = "" if grouped else "let "
            grouped = True
            out.append((f"  {keyword}groups = groupRows(rows, {quote(step.field)});", step.line))
        elif isinstance(step, Count):
            out.append((f"  rows = countGroups(groups, {quote(step.field)});", step.line))
        elif isinstance(step, IfNone):
            out.append(("  if (rows.length === 0) {", step.line))
            out.append((f"    emit({quote(step.text + chr(10))});", step.line))
            out.append(("    return;", step.line))
            out.append(("  }", step.line))
        elif isinstance(step, Show):
            names = ", ".join(quote(name) for name in step.fields)
            out.append((f"  showTable(rows, [{names}]);", step.line))
        elif isinstance(step, WriteJson):
            out.append(("  writeJson(rows);", step.line))
    return out


def generate(program):
    fields = program.source.fields
    lines = [('"use strict";', "support"), ("", "support"), ('const fs = require("node:fs");', "support"),
             ("", "support"), (f"const SOURCE = {quote(program.source.name)};", "support")]
    if len(fields) == 1:
        lines.append((f'const FIELDS = [[{quote(fields[0][0])}, {quote(fields[0][1])}]];', "support"))
    else:
        lines.append(("const FIELDS = [", "support"))
        lines += [(f"  [{quote(name)}, {quote(kind)}],", "support") for name, kind in fields]
        lines.append(("];", "support"))
    flags = needs(program)
    for block, flag, text in SUPPORT:
        if flag in flags:
            lines.append(("", "support"))
            lines += [(line, block) for line in text.rstrip("\n").split("\n")]
    lines += [("", "support"), ("function main() {", "support")]
    lines += main_lines(program)
    lines += [("}", "support"), ("", "support")]
    lines += [(line, "exit-on-error") for line in TAIL.rstrip("\n").split("\n")]
    return lines


NAME = r"([A-Za-z_][A-Za-z0-9_]*)"
FIELD_NAME = rf'"{NAME}"'


def lift(text):
    lines = text.split("\n")
    name = _only(re.fullmatch(rf"const SOURCE = {FIELD_NAME};", line) for line in lines)
    pairs = []
    for line in lines:
        if (match := re.fullmatch(rf'const FIELDS = \[\[{FIELD_NAME}, "(text|integer)"\]\];', line)) or (match := re.fullmatch(rf'  \[{FIELD_NAME}, "(text|integer)"\],', line)):
            pairs.append((match[1], match[2]))
    if not pairs or len({field for field, _ in pairs}) != len(pairs):
        raise NotGenerated("the declared fields cannot be read")
    try:
        start = lines.index("function main() {") + 1
        end = lines.index("}", start)
    except ValueError:
        raise NotGenerated("there is no main function") from None
    body = lines[start:end]
    steps, path, argument = [], None, None
    index = 0
    while index < len(body):
        line = body[index]
        index += 1
        if match := re.fullmatch(rf"  const text = readTextFile\((?:({STRING})|readArgument\((\d+)\))\);", line):
            path = unquote(match[1]) if match[1] else None
            argument = int(match[2]) if match[2] else None
            if body[index:index + 1] != ["  const records = checkList(parseJson(text));"]:
                raise NotGenerated("the lines that read the source are not as generated")
            mode = body[index + 1] if index + 1 < len(body) else ""
            if mode not in ("  let rows = requireValid(records);", "  let rows = keepValid(records);"):
                raise NotGenerated("the lines that read the source are not as generated")
            steps.append(Read(skip_invalid="keepValid" in mode))
            index += 2
        elif match := re.fullmatch(r"  rows = rows\.filter\(\(row\) => (.*)\);", line):
            steps.append(Filter(conditions=_conditions(match[1])))
        elif match := re.fullmatch(rf"  rows = rows\.map\(\(row\) => \(\{{ \.\.\.row, {NAME}: (.*) \}}\)\);", line):
            scanner = Scanner(match[2])
            value = _formula(scanner)
            if not scanner.done():
                raise NotGenerated("a formula cannot be read")
            steps.append(Add(name=match[1], formula=value))
        elif match := re.fullmatch(r"  rows = \[\.\.\.rows\]\.sort\(\(a, b\) => (.*)\);", line):
            steps.append(_sort(match[1]))
        elif match := re.fullmatch(r"  rows = rows\.slice\(0, (\d+)\);", line):
            steps.append(Limit(count=int(match[1])))
        elif match := re.fullmatch(rf"  (?:let )?groups = groupRows\(rows, {FIELD_NAME}\);", line):
            steps.append(Group(field=match[1]))
        elif match := re.fullmatch(rf"  rows = countGroups\(groups, {FIELD_NAME}\);", line):
            steps.append(Count(field=match[1]))
        elif line == "  if (rows.length === 0) {":
            match = re.fullmatch(rf"    emit\(({STRING})\);", body[index] if index < len(body) else "")
            if match is None or body[index + 1:index + 3] != ["    return;", "  }"]:
                raise NotGenerated("the lines that print a message are not as generated")
            message = unquote(match[1])
            if not message.endswith("\n"):
                raise NotGenerated("the message does not end with a line break")
            steps.append(IfNone(text=message[:-1]))
            index += 3
        elif match := re.fullmatch(r"  showTable\(rows, \[(.*)\]\);", line):
            names = re.findall(FIELD_NAME, match[1])
            if ", ".join(f'"{n}"' for n in names) != match[1] or not names:
                raise NotGenerated("the list of fields to show cannot be read")
            steps.append(Show(fields=tuple(names)))
        elif line == "  writeJson(rows);":
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


def _sort(text):
    for descending, first, second in ((False, "a", "b"), (True, "b", "a")):
        if (match := re.fullmatch(rf"{first}\.{NAME} - {second}\.{NAME}", text)) and match[1] == match[2]:
            return Sort(field=match[1], descending=descending)
        if (match := re.fullmatch(rf"compareText\({first}\.{NAME}, {second}\.{NAME}\)", text)) and match[1] == match[2]:
            return Sort(field=match[1], descending=descending)
        if (match := re.fullmatch(rf"compareText\(foldCase\({first}\.{NAME}\), foldCase\({second}\.{NAME}\)\)", text)) and match[1] == match[2]:
            return Sort(field=match[1], descending=descending, ignore_case=True)
    raise NotGenerated("a sort cannot be read")


FIELD_VALUE = re.compile(rf"row\.{NAME}")
STRING_VALUE = re.compile(STRING)
NUMBER_VALUE = re.compile(r"-?\d+")
ARITHMETIC = re.compile(r" ([-+*]) ")
COMPARISON = re.compile(r" (===|!==|<=|>=|<|>) ")
ORDER_TEST = re.compile(r" (<= 0|>= 0|< 0|> 0)")


def _atom(scanner):
    if match := scanner.match(FIELD_VALUE):
        return Field(match[1])
    if match := scanner.match(STRING_VALUE):
        return Text(unquote(match[0]))
    if match := scanner.match(NUMBER_VALUE):
        return Number(int(match[0]))
    if scanner.take("whole("):
        left = _atom(scanner)
        op = scanner.match(ARITHMETIC)
        if op is None:
            raise NotGenerated("a calculation cannot be read")
        right = _atom(scanner)
        scanner.expect(")")
        return Arith(op[1], left, right)
    raise NotGenerated("a formula cannot be read")


def _formula(scanner):
    parts = [_atom(scanner)]
    while scanner.take(" + "):
        parts.append(_atom(scanner))
    return parts[0] if len(parts) == 1 else Concat(tuple(parts))


def _conditions(text):
    scanner, conditions = Scanner(text), []
    while True:
        if scanner.take("compareText("):
            left = _formula(scanner)
            scanner.expect(", ")
            right = _formula(scanner)
            scanner.expect(")")
            test = scanner.match(ORDER_TEST)
            if test is None:
                raise NotGenerated("a comparison of text cannot be read")
            conditions.append(Condition(left, FROM_ORDER[test[1]], right))
        else:
            left = _formula(scanner)
            op = scanner.match(COMPARISON)
            if op is None:
                raise NotGenerated("a condition cannot be read")
            conditions.append(Condition(left, FROM_NUMBER[op[1]], _formula(scanner)))
        if scanner.done():
            return tuple(conditions)
        scanner.expect(" && ")


__all__ = ["FILE_NAME", "SUPPORT", "blocks_used", "generate", "lift", "schemas"]
