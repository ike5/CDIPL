"""Intent files that describe an application's pages: the checked form, the reader and the writer."""
import re
from dataclasses import dataclass, field, replace

from .model import IntentError

IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
STRING = r'"(?:[^"\\]|\\.)*"'
FIELD_TYPES = ("text", "integer", "decimal")
MAX_WIDTH = 2000
PARTS = {"sqlite": "sqlite", "fastapi": "FastAPI", "authentication": "authentication"}  # the parts that can be built
SERVER_PARTS = {"sqlite", "fastapi"}  # what an API, and authentication, need
OPERATORS = ("=", "!=", "<", "<=", ">", ">=")
NOTIFICATIONS_TABLE = "notification"  # the table, and the address under /api/, that keeps the notifications
AUTH_TABLES = ("auth_user", "auth_session")  # the tables that keep the users and their sessions

PHRASES = {
    "en": {"header": "language: en", "app": "app", "data": "data", "records": "records", "page": "page",
           "heading": "heading", "text": "text", "table": "table", "button": "button", "width": "width",
           "searchable": "searchable by", "sortable": "sortable by", "use": "use", "expose": r"expose (\S+) as api",
           "expose_text": "expose {} as api", "adds": "adds", "opens": "opens",
           "increase": r"increase button(?: (STRING))? size by (\d+)px", "decrease": r"decrease button(?: (STRING))? size by (\d+)px",
           "editable": "editable", "when": "when", "notify": "notify", "and": "and", "notifications": "notifications",
           "authentication": "authentication", "sign_in": "sign in", "signs_out": "signs out",
           "types": {"text": "text", "integer": "integer", "decimal": "decimal"}},
    "es": {"header": "idioma: es", "app": "aplicación", "data": "datos", "records": "registros", "page": "página",
           "heading": "encabezado", "text": "texto", "table": "tabla", "button": "botón", "width": "ancho",
           "searchable": "buscable por", "sortable": "ordenable por", "use": "usar", "expose": r"exponer (\S+) como api",
           "expose_text": "exponer {} como api", "adds": "añade", "opens": "abre",
           "increase": r"aumentar tamaño del botón(?: (STRING))? en (\d+)px",
           "decrease": r"reducir tamaño del botón(?: (STRING))? en (\d+)px",
           "editable": "editable", "when": "cuando", "notify": "notificar", "and": "y", "notifications": "notificaciones",
           "authentication": "autenticación", "sign_in": "iniciar sesión", "signs_out": "cierra sesión",
           "types": {"text": "texto", "integer": "entero", "decimal": "decimal"}},
}
HEADERS = {phrases["header"]: code for code, phrases in PHRASES.items()}

# Statements the reader recognises but the library cannot build yet: (pattern, what it would need).
NOT_BUILT = {
    "en": [
        (r"use\s+\S+", "choosing the parts of an application, such as SQLite, Postgres or FastAPI"),
        (r"create\s+\S+\s*:", "creating a service, such as a Postgres database"),
        (r"using\s+\S+", "choosing how a service is run, such as Docker"),
    ],
    "es": [
        (r"usar\s+\S+", "choosing the parts of an application, such as SQLite, Postgres or FastAPI"),
        (r"crear\s+\S+\s*:", "creating a service, such as a Postgres database"),
        (r"usando\s+\S+", "choosing how a service is run, such as Docker"),
    ],
}


@dataclass(frozen=True)
class Element:
    line: int = field(default=0, compare=False, kw_only=True)


@dataclass(frozen=True)
class Heading(Element):
    text: str = ""


@dataclass(frozen=True)
class Paragraph(Element):
    text: str = ""


@dataclass(frozen=True)
class Table(Element):
    data: str = ""
    search: str | None = None  # the field a search box looks in
    sort: tuple[str, ...] = ()  # the fields whose column headings sort the table
    editable: bool = False  # each row has controls that change or delete its record
    search_line: int = field(default=0, compare=False, kw_only=True)
    sort_lines: tuple[int, ...] = field(default=(), compare=False, kw_only=True)
    editable_line: int = field(default=0, compare=False, kw_only=True)


@dataclass(frozen=True)
class Button(Element):
    text: str = ""
    width: int | None = None
    action: tuple[str, str] | None = None  # ("adds", a data name), ("opens", a page name) or SIGNS_OUT


SIGNS_OUT = ("signs out", "")  # the action of a button that ends the session


@dataclass(frozen=True)
class SignIn(Element):
    """The form for signing in: the labels of the name and password boxes, the button, and the message on failure."""
    name_label: str = ""
    password_label: str = ""
    button: str = ""
    failure: str = ""


@dataclass(frozen=True)
class Notifications(Element):
    """The list of notifications stored by the rules of the application."""


@dataclass(frozen=True)
class Rule:
    """When a record of a data type, as stored, meets every comparison, someone is notified.

    Each comparison is (field, operator, value); values are kept as in records: Quoted, int or Decimal.
    """
    data: str
    conditions: tuple[tuple[str, str, object], ...]
    recipient: str
    line: int = field(default=0, compare=False)
    notify_line: int = field(default=0, compare=False)


@dataclass(frozen=True)
class Data:
    name: str
    fields: tuple[tuple[str, str], ...]
    line: int = field(default=0, compare=False)


@dataclass(frozen=True)
class Records:
    """Records of a data type, written out in the intent file. Decimals are kept as written, as text."""
    name: str
    rows: tuple[tuple, ...]
    line: int = field(default=0, compare=False)
    row_lines: tuple[int, ...] = field(default=(), compare=False)


@dataclass(frozen=True)
class Page:
    name: str
    elements: tuple[Element, ...]
    line: int = field(default=0, compare=False)


@dataclass(frozen=True)
class App:
    name: str
    data: tuple[Data, ...]
    pages: tuple[Page, ...]
    records: tuple[Records, ...] = ()
    uses: tuple[str, ...] = ()  # the parts chosen with 'use': sqlite, fastapi, authentication
    exposed: tuple[str, ...] = ()  # the data types that have an API
    language: str = field(default="en", compare=False)
    line: int = field(default=0, compare=False)
    changes: tuple[tuple[int, int], ...] = field(default=(), compare=False)  # (line of a change, line it changes)
    use_lines: tuple[int, ...] = field(default=(), compare=False)
    expose_lines: tuple[int, ...] = field(default=(), compare=False)
    rules: tuple[Rule, ...] = ()  # rules that notify, in the order of their data, then as written


class NotBuilt(IntentError):
    """A statement the reader recognises but the library cannot build yet."""


def part_of(written, words):
    """The part of an application that a word after 'use' names, or None."""
    written = written.lower()
    if written == words["authentication"]:
        return "authentication"
    return written if written in SERVER_PARTS else None


def part_text(part, language):
    """A part of an application as written after 'use' in standard phrases."""
    return PHRASES[language]["authentication"] if part == "authentication" else PARTS[part]


def sign_in_page(app):
    """The page that holds the sign-in form, or None if there is none."""
    return next((page for page in app.pages if any(isinstance(element, SignIn) for element in page.elements)), None)


def unquote(literal):
    return re.sub(r'\\(["\\])', r"\1", literal[1:-1])


def quote(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def is_app(intent_text):
    """Whether intent text describes an application's pages (as opposed to a program over a source)."""
    for line in intent_text.split("\n")[1:]:
        if line.strip():
            first = line.split()[0]
            return any(first == phrases["app"] or re.fullmatch(pattern, line.strip())
                       for code, phrases in PHRASES.items() for pattern, _ in NOT_BUILT[code][:2])
    return False


def check(app):
    """Check an application as a whole. Raises IntentError at the line of the problem."""
    names = {}
    for item in app.data:
        if item.name in names:
            raise IntentError(item.line, f"'{item.name}' is declared twice")
        names[item.name] = item
        if not item.fields:
            raise IntentError(item.line, f"'{item.name}' must declare at least one field on the lines beneath it")
    files = {}
    for page in app.pages:
        if page.name.lower() in files:
            raise IntentError(page.line, f"two pages would be written to the same file: '{page.name}' and "
                                         f"'{files[page.name.lower()]}'")
        files[page.name.lower()] = page.name
        if not page.elements:
            raise IntentError(page.line, f"page '{page.name}' is empty")
        for element in page.elements:
            if not isinstance(element, Table):
                continue
            if element.data not in names:
                raise IntentError(element.line, f"there is no data named '{element.data}'")
            known = [name for name, _ in names[element.data].fields]
            for name, line in [(element.search, element.search_line), *zip(element.sort, element.sort_lines)]:
                if name is not None and name not in known:
                    raise IntentError(line or element.line, f"'{element.data}' has no field named '{name}'")
    seen = {}
    for item in app.records:
        if item.name not in names:
            raise IntentError(item.line, f"there is no data named '{item.name}'")
        if item.name.lower() in seen:
            raise IntentError(item.line, f"the records of '{item.name}' and '{seen[item.name.lower()]}' would be written "
                                         f"to the same file")
        seen[item.name.lower()] = item.name
        kinds = [kind for _, kind in names[item.name].fields]
        if not item.rows:
            raise IntentError(item.line, f"the records of '{item.name}' are empty")
        for index, row in enumerate(item.rows):
            line = item.row_lines[index] if index < len(item.row_lines) else item.line
            if len(row) != len(kinds):
                raise IntentError(line, f"a record of '{item.name}' needs {len(kinds)} values, one for each field")
            for value, kind, (name, _) in zip(row, kinds, names[item.name].fields):
                if not fits(value, kind):
                    raise IntentError(line, f"the value for '{name}' must be {VALUE_HELP[kind]}")
    if not app.pages:
        raise IntentError(app.line, "the application has no page")
    lines = dict(zip(app.exposed, app.expose_lines)) if app.expose_lines else {}
    for name in app.exposed:
        line = lines.get(name, app.line)
        if name not in names:
            raise IntentError(line, f"there is no data named '{name}'")
        if not SERVER_PARTS <= set(app.uses):
            raise IntentError(line, "an API needs a database and a web framework: add 'use sqlite' and 'use FastAPI'")
        if any(field_name == "id" for field_name, _ in names[name].fields):
            raise IntentError(line, f"'{name}' has a field named 'id', which the database keeps for itself")
    if len({name.lower() for name in app.exposed}) != len(app.exposed):
        raise IntentError(app.line, "two data types with an API would share one table name")
    if "sqlite" in app.uses and not app.exposed and "authentication" not in app.uses:
        raise IntentError((app.use_lines or (app.line,))[0], "nothing uses the database: expose a data type as an API, "
                                                             "or remove 'use sqlite'")
    check_authentication(app)
    page_names = {page.name for page in app.pages}
    for page in app.pages:
        for element in page.elements:
            if isinstance(element, Button) and element.action is not None:
                verb, target = element.action
                if verb == "adds" and target not in app.exposed:
                    raise IntentError(element.line, f"a button can add a '{target}' only if '{target}' is exposed as an API")
                if verb == "opens" and target not in page_names:
                    raise IntentError(element.line, f"there is no page named '{target}'")
            if isinstance(element, Table) and element.editable and element.data not in app.exposed:
                raise IntentError(element.editable_line or element.line,
                                  f"a table can be editable only if '{element.data}' is exposed as an API")
            if isinstance(element, Notifications) and not app.rules:
                raise IntentError(element.line, "there are no notifications to show: no rule notifies anyone")
    check_rules(app, names, lines)
    shown = {element.data for page in app.pages for element in page.elements if isinstance(element, Table)}
    for item in app.data:
        if item.name not in shown:
            raise IntentError(item.line, f"'{item.name}' is declared but no page shows it")


def check_authentication(app):
    """Check signing in and out. Raises IntentError at the line of the problem."""
    use_line = dict(zip(app.uses, app.use_lines)).get("authentication", app.line)
    forms = sorted([(page, element) for page in app.pages for element in page.elements if isinstance(element, SignIn)],
                   key=lambda pair: pair[1].line)
    leaving = [element for page in app.pages for element in page.elements
               if isinstance(element, Button) and element.action == SIGNS_OUT]
    if "authentication" not in app.uses:
        if forms or leaving:
            first = min([element for _, element in forms] + leaving, key=lambda element: element.line)
            raise IntentError(first.line, "signing in and out needs 'use authentication' before the application")
        return
    if not SERVER_PARTS <= set(app.uses):
        raise IntentError(use_line, "authentication needs a database and a web framework: add 'use sqlite' and 'use FastAPI'")
    for item in app.data:
        if item.name.lower() in AUTH_TABLES:
            raise IntentError(item.line, f"'{item.name}' cannot be declared with authentication: its table would be named "
                                         f"'{item.name.lower()}', where the users and their sessions are kept")
    if not forms:
        raise IntentError(use_line, "authentication needs one page with a sign-in form, such as "
                                    "'sign in \"Name\" \"Password\" \"Sign in\" \"Wrong name or password\"'")
    if len(forms) > 1:
        raise IntentError(forms[1][1].line, "there is already a sign-in form; an application has exactly one")
    page = forms[0][0]
    for element in page.elements:
        if not isinstance(element, (Heading, Paragraph, SignIn)):
            raise IntentError(element.line, "the sign-in page may hold only headings, text and the sign-in form")
    if len(app.pages) < 2:
        raise IntentError(page.line, "there must be at least one page besides the sign-in page")


def check_rules(app, names, expose_lines):
    """Check the rules that notify. Raises IntentError at the line of the problem."""
    seen = set()
    for rule in app.rules:
        if rule.data not in names:
            raise IntentError(rule.line, f"there is no data named '{rule.data}'")
        if rule.data not in app.exposed:
            raise IntentError(rule.line, f"a rule about '{rule.data}' needs '{rule.data}' to be exposed as an API")
        kinds = dict(names[rule.data].fields)
        for name, _, value in rule.conditions:
            if name not in kinds:
                raise IntentError(rule.line, f"'{rule.data}' has no field named '{name}'")
            if not fits(value, kinds[name]):
                raise IntentError(rule.line, f"the value compared with '{name}' must be {VALUE_HELP[kinds[name]]}")
        if not IDENTIFIER.match(rule.recipient):
            raise IntentError(rule.notify_line or rule.line, f"'{rule.recipient}' is not a valid name")
        if rule in seen:
            raise IntentError(rule.line, "this rule is written twice")
        seen.add(rule)
    if app.rules:
        for name in app.exposed:
            if name.lower() == NOTIFICATIONS_TABLE:
                raise IntentError(expose_lines.get(name, app.line),
                                  f"'{name}' cannot have an API: its table would be named '{NOTIFICATIONS_TABLE}', "
                                  f"where the notifications are kept")


DECIMAL = re.compile(r"-?\d+(?:\.\d+)?\Z")
VALUE_HELP = {"text": "text in double quotes", "integer": "a whole number", "decimal": "a number such as 9.99"}


class Quoted(str):
    """Text that was written in double quotes."""


class Decimal(str):
    """A number with a decimal point, kept exactly as written."""


def fits(value, kind):
    """Whether a value written in a record fits a field type."""
    if kind == "text":
        return isinstance(value, Quoted)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool) and abs(value) <= 9007199254740991
    return isinstance(value, Decimal) and bool(DECIMAL.match(value)) and len(value.replace("-", "").replace(".", "")) <= 15


def first_use_order(data, pages):
    """Data declarations in the order in which pages first show them; the rest keep their order."""
    order = []
    for page in pages:
        for element in page.elements:
            if isinstance(element, Table) and element.data not in order:
                order.append(element.data)
    position = {name: index for index, name in enumerate(order)}
    return tuple(sorted(data, key=lambda item: position.get(item.name, len(order))))


def read_lines(text, on_problem=None, resolver=None):
    """Read an application description.

    Raises IntentError at the first problem. If on_problem is given, it is called with each
    problem instead and reading carries on, so that the rest of the file can still be shown.
    Returns an App that has not yet been checked as a whole.
    """
    def problem(error):
        if on_problem is None:
            raise error
        on_problem(error)

    numbered = [(number, line) for number, line in enumerate(text.split("\n"), start=1) if line.strip()]
    if not numbered:
        raise IntentError(1, "the file is empty; it must start with a line such as 'language: en'")
    language = HEADERS.get(" ".join(numbered[0][1].split()))
    if language is None:
        raise IntentError(numbered[0][0], "the first line must name the human language: "
                          + " or ".join(f"'{header}'" for header in HEADERS))
    words = PHRASES[language]
    types = {word: kind for kind, word in words["types"].items()}
    app_name, app_line, data, records, pages, changes = None, numbered[0][0], [], [], [], []
    uses, use_lines, exposed, expose_lines = [], [], [], []
    rules = []
    current = None  # [kind, name, line, indent, items, lines of the items]

    def close():
        nonlocal current
        if current is not None:
            kind, name, line, _, items, lines = current
            current = None
            if kind == "data":
                data.append(Data(name, tuple(items), line))
            elif kind == "records":
                records.append(Records(name, tuple(items), line, tuple(lines)))
            elif kind == "rule":
                if not items:
                    problem(IntentError(line, f"a rule needs one line beneath it naming who is notified, such as "
                                              f"'{words['notify']} manager'"))
                elif name is not None:
                    rules.append(Rule(name[0], name[1], items[0], line, lines[0]))
            else:
                pages.append(Page(name, tuple(items), line))

    kinds = {words["data"]: "data", words["records"]: "records", words["page"]: "page"}
    opener = re.compile(rf"({'|'.join(re.escape(word) for word in kinds)})\s+(\S+)\s*:")
    for number, raw in numbered[1:]:
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if (match := re.fullmatch(rf"{words['use']}\s+(\S+)", line)) and part_of(match[1], words) is not None:
            part = part_of(match[1], words)
            if app_name is not None or indent:
                problem(IntentError(number, "the parts of an application are chosen before the application, at the "
                                            "start of a line"))
            elif part in uses:
                problem(IntentError(number, f"'{PARTS[part]}' is chosen twice"))
            else:
                uses.append(part)
                use_lines.append(number)
            continue
        if match := re.fullmatch(words["expose"].replace(" ", r"\s+"), line):
            close()
            if app_name is None or not indent:
                problem(IntentError(number, "this belongs inside the application, so it must be indented"))
            elif not IDENTIFIER.match(match[1]):
                problem(IntentError(number, f"'{match[1]}' is not a valid name"))
            elif match[1] in exposed:
                problem(IntentError(number, f"'{match[1]}' is exposed twice"))
            else:
                exposed.append(match[1])
                expose_lines.append(number)
            continue
        unbuilt = next((needs for pattern, needs in NOT_BUILT[language] if re.fullmatch(pattern, line)), None)
        if unbuilt is not None:
            problem(NotBuilt(number, f"this is understood, but it is not built yet: it needs {unbuilt}"))
            continue
        if match := re.fullmatch(rf"{words['app']}\s+(\S+)\s*:", line):
            if app_name is not None or indent:
                problem(IntentError(number, "an application is declared once, at the start of a line"))
                continue
            if not IDENTIFIER.match(match[1]):
                problem(IntentError(number, f"'{match[1]}' is not a valid name"))
                continue
            app_name, app_line = match[1], number
            continue
        if app_name is None:
            problem(IntentError(number, f"expected the application, written as '{words['app']} Name:'"))
            continue
        if match := re.fullmatch(rf"{words['when']}\s+(.*?)\s*:", line):
            close()
            if not indent:
                problem(IntentError(number, "this belongs inside the application, so it must be indented"))
                continue
            try:
                condition = read_condition(match[1], number, words)
            except IntentError as error:
                problem(error)
                condition = None
            current = ["rule", condition, number, indent, [], []]
            continue
        if match := opener.fullmatch(line):
            close()
            if not indent:
                problem(IntentError(number, "this belongs inside the application, so it must be indented"))
                continue
            if not IDENTIFIER.match(match[2]):
                problem(IntentError(number, f"'{match[2]}' is not a valid name"))
                continue
            current = [kinds[match[1]], match[2], number, indent, [], []]
            continue
        if current is None or indent <= current[3]:
            close()
            problem(IntentError(number, f"expected '{words['data']} Name:', '{words['records']} Name:' "
                                        f"or '{words['page']} Name:'"))
            continue
        kind, name, _, _, items, lines = current
        notify = re.fullmatch(rf"{words['notify']}\s+(\S+)", line)
        try:
            if kind == "rule":
                if notify is None:
                    raise IntentError(number, f"expected '{words['notify']} name' beneath the rule")
                if not IDENTIFIER.match(notify[1]):
                    raise IntentError(number, f"'{notify[1]}' is not a valid name")
                if items:
                    raise IntentError(number, f"a rule has exactly one '{words['notify']}' line")
                items.append(notify[1])
                lines.append(number)
            elif notify is not None:
                raise IntentError(number, f"'{words['notify']}' belongs beneath a rule written as "
                                          f"'{words['when']} Data.field < 5:'")
            elif kind == "data":
                items.append(_field(line, number, types, items))
            elif kind == "records":
                declared = next((item for item in data if item.name == name), None)
                items.append(_record(line, number, declared))
                lines.append(number)
            else:
                known = {item.name: item for item in data}
                changed = _page_line(line, number, words, items, known, resolver)
                if changed is not None:
                    changes.append((number, changed))
        except IntentError as error:
            problem(error)
    close()
    if app_name is None:
        raise IntentError(numbered[-1][0], f"expected the application, written as '{words['app']} Name:'")
    ordered = first_use_order(data, pages)
    position = {item.name: index for index, item in enumerate(ordered)}
    records.sort(key=lambda item: position.get(item.name, len(position)))
    pairs = sorted(zip(exposed, expose_lines), key=lambda pair: position.get(pair[0], len(position)))
    parts = sorted(zip(uses, use_lines), key=lambda pair: list(PARTS).index(pair[0]))
    rules.sort(key=lambda rule: position.get(rule.data, len(position)))
    pages.sort(key=lambda page: not any(isinstance(element, SignIn) for element in page.elements))  # the sign-in page first
    known = {item.name: dict(item.fields) for item in data}
    rules = [replace(rule, conditions=tuple((name, operator, as_kind(value, known.get(rule.data, {}).get(name)))
                                            for name, operator, value in rule.conditions)) for rule in rules]
    return App(app_name, ordered, tuple(pages), tuple(records), tuple(part for part, _ in parts),
               tuple(name for name, _ in pairs), language, app_line, tuple(changes),
               tuple(line for _, line in parts), tuple(line for _, line in pairs), tuple(rules))


def as_kind(value, kind):
    """A whole number written for a decimal field is that decimal, as in records."""
    if kind == "decimal" and isinstance(value, int) and not isinstance(value, bool):
        return Decimal(str(value))
    return value


def read_condition(text, number, words):
    """The condition of a rule: comparisons of fields of one data type with fixed values, joined by 'and'.

    Returns (data name, ((field, operator, value), ...)). Raises IntentError.
    """
    comparison = re.compile(rf"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\s*(!=|<=|>=|=|<|>)\s*"
                            rf"(?:({STRING})|(-?\d+\.\d+)|(-?\d+))")
    joiner = re.compile(rf"\s+{words['and']}\s+")
    data_name, conditions, position = None, [], 0
    while True:
        match = comparison.match(text, position)
        if match is None:
            raise IntentError(number, f"expected a condition such as 'Product.stock < 5', comparing a field with a value "
                                      f"using {' '.join(OPERATORS)}, joined by '{words['and']}'")
        if data_name is not None and match[1] != data_name:
            raise IntentError(number, "the comparisons of a rule must all be about the same data type")
        data_name = match[1]
        if match[4]:
            value = Quoted(unquote(match[4]))
            if any(ord(ch) < 32 for ch in value):
                raise IntentError(number, "text must not contain control characters")
        elif match[5]:
            value = Decimal(match[5])
        else:
            value = int(match[6])
        conditions.append((match[2], match[3], value))
        position = match.end()
        if position == len(text):
            return data_name, tuple(conditions)
        joined = joiner.match(text, position)
        if joined is None:
            raise IntentError(number, f"comparisons must be joined by '{words['and']}'")
        position = joined.end()


def condition_text(rule, language="en"):
    """The condition of a rule in standard phrases, such as 'Product.stock < 5'."""
    joiner = f" {PHRASES[language]['and']} "
    return joiner.join(f"{rule.data}.{name} {operator} {value_text(value)}" for name, operator, value in rule.conditions)


def _record(line, number, declared):
    """One record: values separated by commas, in the order of the fields."""
    values, position = [], 0
    pattern = re.compile(rf"\s*(?:({STRING})|(-?\d+\.\d+)|(-?\d+))\s*(,|\Z)")
    while position < len(line):
        match = pattern.match(line, position)
        if match is None:
            raise IntentError(number, "expected values separated by commas: text in double quotes, or numbers")
        if match[1]:
            value = Quoted(unquote(match[1]))
            if any(ord(ch) < 32 for ch in value):
                raise IntentError(number, "text must not contain control characters")
        elif match[2]:
            value = Decimal(match[2])
        else:
            value = int(match[3])
        values.append(value)
        position = match.end()
        if match[4] == "," and position == len(line):
            raise IntentError(number, "a value is missing after the last comma")
    if declared is not None:
        kinds = [kind for _, kind in declared.fields]
        values = [Decimal(str(value)) if kind == "decimal" and isinstance(value, int) and not isinstance(value, bool)
                  else value for value, kind in zip(values, kinds)] + values[len(kinds):]
    return tuple(values)


def _field(line, number, types, items):
    match = re.fullmatch(r"(\S+)\s*:\s*(\S+)", line)
    if match is None:
        raise IntentError(number, f"expected a field such as 'name: {next(iter(types))}'")
    name, kind = match.groups()
    if not IDENTIFIER.match(name) or name == "__proto__":
        raise IntentError(number, f"'{name}' is not a valid field name")
    if kind not in types:
        raise IntentError(number, f"unknown type '{kind}'; use {', '.join(types)}")
    if any(name == existing for existing, _ in items):
        raise IntentError(number, f"field '{name}' is declared twice")
    return name, types[kind]


def _text(literal, number):
    value = unquote(literal)
    if not value.strip() or any(ord(ch) < 32 for ch in value) or value != value.strip() or "  " in value:
        raise IntentError(number, "the text must not be empty, start or end with a space, hold two spaces in a row, "
                                  "or contain control characters")
    return value


def _element(line, number, words):
    if match := re.fullmatch(rf"{words['heading']}\s+({STRING})", line):
        return Heading(text=_text(match[1], number), line=number)
    if match := re.fullmatch(rf"{words['text']}\s+({STRING})", line):
        return Paragraph(text=_text(match[1], number), line=number)
    if match := re.fullmatch(rf"{words['table']}\s+(\S+)", line):
        if not IDENTIFIER.match(match[1]):
            raise IntentError(number, f"'{match[1]}' is not a valid name")
        return Table(data=match[1], line=number)
    if re.fullmatch(words["notifications"], line):
        return Notifications(line=number)
    sign_in = words["sign_in"].replace(" ", r"\s+")
    if match := re.fullmatch(rf"{sign_in}\s+({STRING})\s+({STRING})\s+({STRING})\s+({STRING})", line):
        texts = [_text(match[index], number) for index in range(1, 5)]
        return SignIn(name_label=texts[0], password_label=texts[1], button=texts[2], failure=texts[3], line=number)
    if re.match(rf"{sign_in}(\s|\Z)", line):
        raise IntentError(number, f"expected '{words['sign_in']}' and four texts in double quotes: the labels of the name "
                                  f"and the password, the text of the button, and the message when signing in fails")
    signs_out = words["signs_out"].replace(" ", r"\s+")
    if match := re.fullmatch(rf"{words['button']}\s+({STRING})(?:\s+{words['width']}\s+(\d+)px)?"
                             rf"(?:\s+({words['adds']}|{words['opens']})\s+(\S+)|\s+({signs_out}))?", line):
        width = int(match[2]) if match[2] else None
        if width is not None and not 1 <= width <= MAX_WIDTH:
            raise IntentError(number, f"the width must be between 1px and {MAX_WIDTH}px")
        action = SIGNS_OUT if match[5] else None
        if match[3]:
            if not IDENTIFIER.match(match[4]):
                raise IntentError(number, f"'{match[4]}' is not a valid name")
            action = ("adds" if match[3] == words["adds"] else "opens", match[4])
        return Button(text=_text(match[1], number), width=width, action=action, line=number)
    return None


def _page_line(line, number, words, items, data, resolver):
    """Read one line of a page: add an element, or change one already there.

    Returns the line number of the element that was changed, or None when an element was added.
    """
    element = _element(line, number, words)
    if element is not None:
        items.append(element)
        return None
    for key in ("searchable", "sortable"):
        if match := re.fullmatch(rf"{words[key]}\s+(\S+)", line):
            return _table_feature(key, match[1], number, items)
    if line == words["editable"]:
        return _table_feature("editable", None, number, items)
    for key, sign in (("increase", 1), ("decrease", -1)):
        if match := re.fullmatch(words[key].replace("STRING", STRING), line):
            return resize(items, number, sign * int(match[2]), unquote(match[1]) if match[1] else None)
    if resolver is not None:
        return resolver(line, number, items, data)
    raise IntentError(number, f"'{line}' is not something a page can hold; use {words['heading']}, {words['text']}, "
                              f"{words['table']}, {words['button']} or {words['notifications']}")


def _table_feature(key, name, number, items):
    if not items or not isinstance(items[-1], Table):
        raise IntentError(number, "this must come directly after the table it applies to")
    table = items[-1]
    if key == "searchable":
        if table.search is not None:
            raise IntentError(number, "the table already has a search box")
        items[-1] = replace(table, search=name, search_line=number)
    elif key == "sortable":
        if name in table.sort:
            raise IntentError(number, f"the table can already be sorted by '{name}'")
        items[-1] = replace(table, sort=(*table.sort, name), sort_lines=(*table.sort_lines, number))
    else:
        if table.editable:
            raise IntentError(number, "the table is already editable")
        items[-1] = replace(table, editable=True, editable_line=number)
    return table.line


def resize(items, number, amount, label):
    """Make a button already on the page wider or narrower. Returns the line of that button."""
    buttons = [(index, item) for index, item in enumerate(items) if isinstance(item, Button)]
    if label is not None:
        buttons = [(index, item) for index, item in buttons if item.text == label]
        if not buttons:
            raise IntentError(number, f"there is no button labelled {quote(label)} above this line")
    if not buttons:
        raise IntentError(number, "there is no button above this line to resize")
    if len(buttons) > 1:
        raise IntentError(number, "there is more than one button; say which one by giving its label in double quotes")
    index, button = buttons[0]
    if button.width is None:
        raise IntentError(number, "that button has no width yet; give it one first, such as 'width 120px'")
    width = button.width + amount
    if not 1 <= width <= MAX_WIDTH:
        raise IntentError(number, f"the width would be {width}px; it must be between 1px and {MAX_WIDTH}px")
    items[index] = Button(text=button.text, width=width, action=button.action, line=button.line)
    return button.line


def parse(text, resolver=None):
    """Turn an application description into a checked App. Raises IntentError.

    resolver, if given, is asked about lines of a page that are not standard phrases.
    """
    app = read_lines(text, resolver=resolver)
    check(app)
    return app


def element_text(element, language):
    """One element of a page, in standard phrases. Returns a list of lines."""
    words = PHRASES[language]
    if isinstance(element, Heading):
        return [f"{words['heading']} {quote(element.text)}"]
    if isinstance(element, Paragraph):
        return [f"{words['text']} {quote(element.text)}"]
    if isinstance(element, Table):
        lines = [f"{words['table']} {element.data}"]
        if element.search is not None:
            lines.append(f"{words['searchable']} {element.search}")
        lines += [f"{words['sortable']} {name}" for name in element.sort]
        return lines + ([words["editable"]] if element.editable else [])
    if isinstance(element, Notifications):
        return [words["notifications"]]
    if isinstance(element, SignIn):
        texts = (element.name_label, element.password_label, element.button, element.failure)
        return [f"{words['sign_in']} " + " ".join(quote(text) for text in texts)]
    suffix = f" {words['width']} {element.width}px" if element.width is not None else ""
    if element.action == SIGNS_OUT:
        suffix += f" {words['signs_out']}"
    elif element.action is not None:
        suffix += f" {words[element.action[0]]} {element.action[1]}"
    return [f"{words['button']} {quote(element.text)}{suffix}"]


def value_text(value):
    return quote(value) if isinstance(value, Quoted) else str(value)


def render(app, language=None):
    """Write an App as intent text in standard phrases."""
    language = language or app.language
    words = PHRASES[language]
    out = [words["header"], ""]
    if app.uses:
        out += [f"{words['use']} {part_text(part, language)}" for part in app.uses] + [""]
    out.append(f"{words['app']} {app.name}:")
    for item in app.data:
        out.append(f"    {words['data']} {item.name}:")
        out += [f"        {name}: {words['types'][kind]}" for name, kind in item.fields]
        out.append("")
    for item in app.records:
        out.append(f"    {words['records']} {item.name}:")
        out += ["        " + ", ".join(value_text(value) for value in row) for row in item.rows]
        out.append("")
    if app.exposed:
        out += [f"    {words['expose_text'].format(name)}" for name in app.exposed] + [""]
    for index, page in enumerate(app.pages):
        out.append(f"    {words['page']} {page.name}:")
        out += [f"        {line}" for element in page.elements for line in element_text(element, language)]
        if index < len(app.pages) - 1:
            out.append("")
    for rule in app.rules:
        out += ["", f"    {words['when']} {condition_text(rule, language)}:", f"        {words['notify']} {rule.recipient}"]
    return "\n".join(out) + "\n"
