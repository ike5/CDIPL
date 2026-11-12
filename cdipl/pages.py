"""Intent files that describe an application's pages: the checked form, the reader and the writer."""
import re
from dataclasses import dataclass, field

from .model import IntentError

IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
STRING = r'"(?:[^"\\]|\\.)*"'
FIELD_TYPES = ("text", "integer", "decimal")
MAX_WIDTH = 2000

PHRASES = {
    "en": {"header": "language: en", "app": "app", "data": "data", "page": "page", "heading": "heading", "text": "text",
           "table": "table", "button": "button", "width": "width",
           "types": {"text": "text", "integer": "integer", "decimal": "decimal"}},
    "es": {"header": "idioma: es", "app": "aplicación", "data": "datos", "page": "página", "heading": "encabezado",
           "text": "texto", "table": "tabla", "button": "botón", "width": "ancho",
           "types": {"text": "texto", "integer": "entero", "decimal": "decimal"}},
}
HEADERS = {phrases["header"]: code for code, phrases in PHRASES.items()}

# Statements the reader recognises but the library cannot build yet: (pattern, what it would need).
NOT_BUILT = {
    "en": [
        (r"use\s+\S+", "choosing the parts of an application, such as web, database or authentication"),
        (r"expose\s+\S+\s+as\s+api", "an API for a data type"),
        (r"searchable\s+by\s+\S+", "searching a table, which needs script blocks"),
        (r"sortable\s+by\s+\S+", "sorting a table, which needs script blocks"),
        (r"editable", "editing a table, which needs script blocks and somewhere to store the data"),
        (r"when\s+.+:", "rules that react to data"),
        (r"notify\s+\S+", "notifying someone"),
    ],
    "es": [
        (r"usar\s+\S+", "choosing the parts of an application, such as web, database or authentication"),
        (r"exponer\s+\S+\s+como\s+api", "an API for a data type"),
        (r"buscable\s+por\s+\S+", "searching a table, which needs script blocks"),
        (r"ordenable\s+por\s+\S+", "sorting a table, which needs script blocks"),
        (r"editable", "editing a table, which needs script blocks and somewhere to store the data"),
        (r"cuando\s+.+:", "rules that react to data"),
        (r"notificar\s+\S+", "notifying someone"),
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


@dataclass(frozen=True)
class Button(Element):
    text: str = ""
    width: int | None = None


@dataclass(frozen=True)
class Data:
    name: str
    fields: tuple[tuple[str, str], ...]
    line: int = field(default=0, compare=False)


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
    language: str = field(default="en", compare=False)
    line: int = field(default=0, compare=False)


class NotBuilt(IntentError):
    """A statement the reader recognises but the library cannot build yet."""


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
                       for code, phrases in PHRASES.items() for pattern, _ in NOT_BUILT[code][:1])
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
            if isinstance(element, Table) and element.data not in names:
                raise IntentError(element.line, f"there is no data named '{element.data}'")
    if not app.pages:
        raise IntentError(app.line, "the application has no page")
    shown = {element.data for page in app.pages for element in page.elements if isinstance(element, Table)}
    for item in app.data:
        if item.name not in shown:
            raise IntentError(item.line, f"'{item.name}' is declared but no page shows it")


def first_use_order(data, pages):
    """Data declarations in the order in which pages first show them; the rest keep their order."""
    order = []
    for page in pages:
        for element in page.elements:
            if isinstance(element, Table) and element.data not in order:
                order.append(element.data)
    position = {name: index for index, name in enumerate(order)}
    return tuple(sorted(data, key=lambda item: position.get(item.name, len(order))))


def read_lines(text, on_problem=None):
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
    app_name, app_line, data, pages = None, numbered[0][0], [], []
    current = None  # ("data" or "page", name, line, indent, items)

    def close():
        nonlocal current
        if current is not None:
            kind, name, line, _, items = current
            (data if kind == "data" else pages).append(
                Data(name, tuple(items), line) if kind == "data" else Page(name, tuple(items), line))
        current = None

    for number, raw in numbered[1:]:
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
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
        if match := re.fullmatch(rf"({words['data']}|{words['page']})\s+(\S+)\s*:", line):
            close()
            if not indent:
                problem(IntentError(number, "this belongs inside the application, so it must be indented"))
                continue
            if not IDENTIFIER.match(match[2]):
                problem(IntentError(number, f"'{match[2]}' is not a valid name"))
                continue
            current = ("data" if match[1] == words["data"] else "page", match[2], number, indent, [])
            continue
        if current is None or indent <= current[3]:
            close()
            problem(IntentError(number, f"expected '{words['data']} Name:' or '{words['page']} Name:'"))
            continue
        kind, _, _, _, items = current
        try:
            items.append(_field(line, number, types, items) if kind == "data" else _element(line, number, words))
        except IntentError as error:
            problem(error)
    close()
    if app_name is None:
        raise IntentError(numbered[-1][0], f"expected the application, written as '{words['app']} Name:'")
    return App(app_name, first_use_order(data, pages), tuple(pages), language, app_line)


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
    if match := re.fullmatch(rf"{words['button']}\s+({STRING})(?:\s+{words['width']}\s+(\d+)px)?", line):
        width = int(match[2]) if match[2] else None
        if width is not None and not 1 <= width <= MAX_WIDTH:
            raise IntentError(number, f"the width must be between 1px and {MAX_WIDTH}px")
        return Button(text=_text(match[1], number), width=width, line=number)
    raise IntentError(number, f"'{line}' is not something a page can hold; use {words['heading']}, {words['text']}, "
                              f"{words['table']} or {words['button']}")


def parse(text):
    """Turn an application description into a checked App. Raises IntentError."""
    app = read_lines(text)
    check(app)
    return app


def element_text(element, language):
    """One element of a page, in standard phrases."""
    words = PHRASES[language]
    if isinstance(element, Heading):
        return f"{words['heading']} {quote(element.text)}"
    if isinstance(element, Paragraph):
        return f"{words['text']} {quote(element.text)}"
    if isinstance(element, Table):
        return f"{words['table']} {element.data}"
    suffix = f" {words['width']} {element.width}px" if element.width is not None else ""
    return f"{words['button']} {quote(element.text)}{suffix}"


def render(app, language=None):
    """Write an App as intent text in standard phrases."""
    language = language or app.language
    words = PHRASES[language]
    out = [words["header"], "", f"{words['app']} {app.name}:"]
    for item in app.data:
        out.append(f"    {words['data']} {item.name}:")
        out += [f"        {name}: {words['types'][kind]}" for name, kind in item.fields]
        out.append("")
    for index, page in enumerate(app.pages):
        out.append(f"    {words['page']} {page.name}:")
        out += [f"        {element_text(element, language)}" for element in page.elements]
        if index < len(app.pages) - 1:
            out.append("")
    return "\n".join(out) + "\n"
