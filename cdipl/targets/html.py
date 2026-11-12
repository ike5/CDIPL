"""Generate web pages in HTML, CSS and JavaScript, and recognise pages this generator wrote."""
import json
import re

from ..model import IntentError
from ..pages import (App, Button, Data, Decimal, Heading, Page, Paragraph, Quoted, Records, Table, check,
                     first_use_order)
from .common import NotGenerated

STYLES = "styles.css"
SCRIPTS = "scripts.js"

# Fixed style rules. Each piece belongs to one block and is included only when that block is used.
SUPPORT = [
    ("html-page", "always", '''\
body {
  margin: 0;
  font-family: system-ui, sans-serif;
  line-height: 1.5;
  color: #1f2933;
  background: #ffffff;
}
'''),
    ("html-page", "always", '''\
main {
  max-width: 60rem;
  margin: 0 auto;
  padding: 1.5rem;
}
'''),
    ("html-page", "nav", '''\
nav {
  display: flex;
  gap: 1rem;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid #d5dbe1;
}
'''),
    ("page-heading", "heading", '''\
h1,
h2 {
  margin: 0 0 0.75rem;
  line-height: 1.2;
}
'''),
    ("page-text", "text", '''\
p {
  margin: 0 0 1rem;
}
'''),
    ("data-table", "table", '''\
table {
  width: 100%;
  margin: 0 0 1rem;
  border-collapse: collapse;
}
'''),
    ("data-table", "table", '''\
th,
td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #d5dbe1;
  text-align: left;
}
'''),
    ("data-table", "table", '''\
th.integer,
th.decimal,
td.integer,
td.decimal {
  text-align: right;
}
'''),
    ("filter-elements-by-text", "search", '''\
label {
  display: block;
  margin: 0 0 0.75rem;
}
'''),
    ("filter-elements-by-text", "search", '''\
input[type="search"] {
  margin-left: 0.5rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid #9aa5b1;
  border-radius: 0.25rem;
  font: inherit;
}
'''),
    ("table-sort", "sort", '''\
th button {
  margin: 0;
  padding: 0;
  border: 0;
  font: inherit;
  font-weight: bold;
  color: inherit;
  background: none;
  cursor: pointer;
  text-decoration: underline;
}
'''),
    ("page-button", "button", '''\
main > button {
  margin: 0 0.5rem 1rem 0;
  padding: 0.5rem 1rem;
  border: 1px solid #1f2933;
  border-radius: 0.25rem;
  font: inherit;
  color: #ffffff;
  background: #1f2933;
  cursor: pointer;
}
'''),
]

# Fixed script. Each piece belongs to one block and is included only when that block is used.
SCRIPT = [
    ("render-table", "always", '''\
function columnOf(table, field) {
  const headings = Array.from(table.querySelectorAll("thead th"));
  return headings.findIndex((heading) => heading.textContent.trim() === field);
}
'''),
    ("render-table", "fill", '''\
async function fillTable(table) {
  const reply = await fetch(table.dataset.source);
  if (!reply.ok) {
    throw new Error(`${table.dataset.source}: ${reply.status}`);
  }
  const records = await reply.json();
  const headings = Array.from(table.querySelectorAll("thead th"));
  const rows = records.map((record) => {
    const row = document.createElement("tr");
    for (const heading of headings) {
      const cell = document.createElement("td");
      cell.className = heading.className;
      cell.textContent = String(record[heading.textContent.trim()]);
      row.append(cell);
    }
    return row;
  });
  table.tBodies[0].replaceChildren(...rows);
}
'''),
    ("filter-elements-by-text", "search", '''\
function foldCase(text) {
  return text.replace(/[A-Z]/g, (letter) => letter.toLowerCase());
}
'''),
    ("filter-elements-by-text", "search", '''\
function searchTable(box) {
  const table = document.querySelector(`table[data-name="${box.dataset.search}"]`);
  const column = columnOf(table, box.dataset.field);
  const wanted = foldCase(box.value);
  for (const row of table.tBodies[0].rows) {
    row.hidden = !foldCase(row.cells[column].textContent).includes(wanted);
  }
}
'''),
    ("table-sort", "sort", '''\
function compareText(left, right) {
  const a = Array.from(left, (letter) => letter.codePointAt(0));
  const b = Array.from(right, (letter) => letter.codePointAt(0));
  for (let index = 0; index < a.length && index < b.length; index += 1) {
    if (a[index] !== b[index]) {
      return a[index] - b[index];
    }
  }
  return a.length - b.length;
}
'''),
    ("table-sort", "sort", '''\
function sortTable(button) {
  const heading = button.closest("th");
  const table = button.closest("table");
  const column = columnOf(table, button.dataset.sort);
  const descending = heading.getAttribute("aria-sort") === "ascending";
  const numeric = heading.classList.contains("integer") || heading.classList.contains("decimal");
  const rows = Array.from(table.tBodies[0].rows);
  rows.sort((first, second) => {
    const a = first.cells[column].textContent;
    const b = second.cells[column].textContent;
    const order = numeric ? Number(a) - Number(b) : compareText(a, b);
    return descending ? -order : order;
  });
  for (const other of table.querySelectorAll("thead th")) {
    other.removeAttribute("aria-sort");
  }
  heading.setAttribute("aria-sort", descending ? "descending" : "ascending");
  table.tBodies[0].append(...rows);
}
'''),
]

# The shape of the markup each block adds. Part of the block's version.
FORMS = {
    "html-page": "<!doctype html><html><head><title>PAGE - APP</title></head><body><nav></nav><main></main></body></html>",
    "page-heading": "<h1>TEXT</h1> for the first heading on a page, <h2>TEXT</h2> for the rest",
    "page-text": "<p>TEXT</p>",
    "data-table": '<table data-name="DATA"><thead><tr><th scope="col" class="TYPE">FIELD</th></tr></thead><tbody></tbody></table>',
    "page-button": '<button type="button" class="width-N">TEXT</button>; .width-N { width: Npx; }',
    "data-records": 'DATA.json: [{ "FIELD": VALUE }]; decimals are written as text',
    "render-table": '<table data-name="DATA" data-source="DATA.json">; document.querySelectorAll("table[data-source]")',
    "filter-elements-by-text": '<label>FIELD <input type="search" data-search="DATA" data-field="FIELD" /></label>',
    "table-sort": '<th scope="col"><button type="button" data-sort="FIELD">FIELD</button></th>',
}


def file_name(page):
    return page.name.lower() + ".html"


def records_file(name):
    return name.lower() + ".json"


def escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def unescape(text):
    if re.search(r"[<>]|&(?!amp;|lt;|gt;)", text):
        raise NotGenerated("text is not written the way the compiler writes it")
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def tables(app):
    return [element for page in app.pages for element in page.elements if isinstance(element, Table)]


def features(app):
    """Which behaviours the application uses: fill, search, sort."""
    filled = {item.name for item in app.records}
    found = set()
    for table in tables(app):
        if table.data in filled:
            found.add("fill")
        if table.search is not None:
            found.add("search")
        if table.sort:
            found.add("sort")
    return found


def blocks_used(app):
    used = ["html-page"]

    def add(*names):
        for name in names:
            if name not in used:
                used.append(name)

    filled = {item.name for item in app.records}
    for page in app.pages:
        for element in page.elements:
            add({Heading: "page-heading", Paragraph: "page-text", Table: "data-table", Button: "page-button"}[type(element)])
            if isinstance(element, Table):
                if element.data in filled or element.search is not None or element.sort:
                    add("render-table")
                if element.search is not None:
                    add("filter-elements-by-text")
                if element.sort:
                    add("table-sort")
    if app.records:
        add("data-records")
    return used


def page_lines(app, page):
    """One page as (text, origin) pairs. origin is an intent line number or the name of a block."""
    data = {item.name: item for item in app.data}
    filled = {item.name for item in app.records}
    out = [("<!doctype html>", "html-page"), ("<html>", "html-page"), ("  <head>", "html-page"),
           ('    <meta charset="utf-8" />', "html-page"),
           ('    <meta name="viewport" content="width=device-width, initial-scale=1" />', "html-page"),
           (f"    <title>{page.name} - {app.name}</title>", page.line),
           (f'    <link rel="stylesheet" href="{STYLES}" />', "html-page")]
    if features(app):
        out.append((f'    <script src="{SCRIPTS}" defer></script>', "render-table"))
    out += [("  </head>", "html-page"), ("  <body>", "html-page")]
    if len(app.pages) > 1:
        out.append(("    <nav>", "html-page"))
        out += [(f'      <a href="{file_name(other)}">{other.name}</a>', other.line) for other in app.pages]
        out.append(("    </nav>", "html-page"))
    out.append(("    <main>", "html-page"))
    headings = 0
    for element in page.elements:
        if isinstance(element, Heading):
            headings += 1
            tag = "h1" if headings == 1 else "h2"
            out.append((f"      <{tag}>{escape(element.text)}</{tag}>", element.line))
        elif isinstance(element, Paragraph):
            out.append((f"      <p>{escape(element.text)}</p>", element.line))
        elif isinstance(element, Table):
            if element.search is not None:
                out.append((f'      <label>{element.search} <input type="search" data-search="{element.data}" '
                            f'data-field="{element.search}" /></label>', element.search_line or element.line))
            source = f' data-source="{records_file(element.data)}"' if element.data in filled else ""
            out += [(f'      <table data-name="{element.data}"{source}>', element.line), ("        <thead>", element.line),
                    ("          <tr>", element.line)]
            sort_lines = dict(zip(element.sort, element.sort_lines or (element.line,) * len(element.sort)))
            for name, kind in data[element.data].fields:
                kind_class = "" if kind == "text" else f' class="{kind}"'
                if name in sort_lines:
                    out.append((f'            <th scope="col"{kind_class}><button type="button" data-sort="{name}">'
                                f"{name}</button></th>", sort_lines[name]))
                else:
                    out.append((f'            <th scope="col"{kind_class}>{name}</th>', element.line))
            out += [("          </tr>", element.line), ("        </thead>", element.line),
                    ("        <tbody></tbody>", element.line), ("      </table>", element.line)]
        else:
            width_class = "" if element.width is None else f' class="width-{element.width}"'
            out.append((f'      <button type="button"{width_class}>{escape(element.text)}</button>', element.line))
    out += [("    </main>", "html-page"), ("  </body>", "html-page"), ("</html>", "html-page")]
    return out


def style_lines(app):
    flags = {"always"} | features(app)
    widths = {}
    for page in app.pages:
        for element in page.elements:
            flags.add({Heading: "heading", Paragraph: "text", Table: "table", Button: "button"}[type(element)])
            if isinstance(element, Button) and element.width is not None:
                widths.setdefault(element.width, element.line)
    if len(app.pages) > 1:
        flags.add("nav")
    out = []
    for block, flag, text in SUPPORT:
        if flag in flags:
            if out:
                out.append(("", "support"))
            out += [(line, block) for line in text.rstrip("\n").split("\n")]
    for width in sorted(widths):
        out += [("", "support"), (f".width-{width} {{", widths[width]), (f"  width: {width}px;", widths[width]),
                ("}", widths[width])]
    return out


def script_lines(app):
    flags = {"always"} | features(app)
    out = []
    for block, flag, text in SCRIPT:
        if flag in flags:
            out += [(line, block) for line in text.rstrip("\n").split("\n")] + [("", "support")]
    out.append(('document.addEventListener("DOMContentLoaded", () => {', "render-table"))
    if "fill" in flags:
        out += [('  for (const table of document.querySelectorAll("table[data-source]")) {', "render-table"),
                ("    fillTable(table).catch((problem) => console.error(problem));", "render-table"), ("  }", "render-table")]
    if "search" in flags:
        out += [('  for (const box of document.querySelectorAll("input[data-search]")) {', "filter-elements-by-text"),
                ('    box.addEventListener("input", () => searchTable(box));', "filter-elements-by-text"),
                ("  }", "filter-elements-by-text")]
    if "sort" in flags:
        out += [('  for (const button of document.querySelectorAll("button[data-sort]")) {', "table-sort"),
                ('    button.addEventListener("click", () => sortTable(button));', "table-sort"), ("  }", "table-sort")]
    out.append(("});", "render-table"))
    return out


def record_lines(app, records):
    """The JSON file for the records of one data type."""
    fields = next(item.fields for item in app.data if item.name == records.name)
    rows = []
    for row in records.rows:
        pairs = ", ".join(f"{json.dumps(name)}: {json.dumps(value, ensure_ascii=False)}" for (name, _), value in zip(fields, row))
        rows.append("{ " + pairs + " }")
    lines = records.row_lines or (records.line,) * len(rows)
    if len(rows) == 1:
        return [(f"[{rows[0]}]", lines[0])]
    out = [("[", records.line)]
    out += [(f"  {row}{',' if index < len(rows) - 1 else ''}", lines[index]) for index, row in enumerate(rows)]
    out.append(("]", records.line))
    return out


def generate(app):
    """Every file of the application: file name -> list of (line, origin)."""
    files = {file_name(page): page_lines(app, page) for page in app.pages}
    files[STYLES] = style_lines(app)
    if features(app):
        files[SCRIPTS] = script_lines(app)
    for records in app.records:
        files[records_file(records.name)] = record_lines(app, records)
    return files


NAME = r"([A-Za-z_][A-Za-z0-9_]*)"
HEADING_CELL = re.compile(rf'            <th scope="col"(?: class="(integer|decimal)")?>(?:<button type="button" data-sort="{NAME}">{NAME}</button>|{NAME})</th>')


def lift(files):
    """Recover the App from generated files (file name -> text). Raises NotGenerated."""
    pages, order, fields, app_names = {}, None, {}, set()
    for name, text in files.items():
        if not name.endswith(".html"):
            continue
        lines = text.split("\n")
        title = [match for match in (re.fullmatch(rf"    <title>{NAME} - {NAME}</title>", line) for line in lines) if match]
        if len(title) != 1:
            raise NotGenerated(f"{name}: the title is not as generated")
        page_name, app_name = title[0][1], title[0][2]
        app_names.add(app_name)
        links = [match[1] for match in (re.fullmatch(rf'      <a href="[a-z0-9_]+\.html">{NAME}</a>', line)
                                         for line in lines) if match]
        if links:
            if order is not None and order != links:
                raise NotGenerated("the pages do not list the same pages in the same order")
            order = links
        try:
            body = lines[lines.index("    <main>") + 1:lines.index("    </main>")]
        except ValueError:
            raise NotGenerated(f"{name}: there is no main section") from None
        elements, index, search = [], 0, None
        while index < len(body):
            line = body[index]
            index += 1
            if match := re.fullmatch(r"      <(h1|h2)>(.*)</\1>", line):
                elements.append(Heading(text=unescape(match[2])))
            elif match := re.fullmatch(r"      <p>(.*)</p>", line):
                elements.append(Paragraph(text=unescape(match[1])))
            elif match := re.fullmatch(rf'      <label>{NAME} <input type="search" data-search="{NAME}" data-field="{NAME}" /></label>', line):
                if match[1] != match[3] or search is not None:
                    raise NotGenerated(f"{name}: a search box is not as generated")
                search = (match[2], match[1])
                continue
            elif match := re.fullmatch(rf'      <table data-name="{NAME}"(?: data-source="[a-z0-9_]+\.json")?>', line):
                found, sortable = [], []
                while index < len(body) and body[index] != "      </table>":
                    if cell := HEADING_CELL.fullmatch(body[index]):
                        if cell[2] and cell[2] != cell[3]:
                            raise NotGenerated(f"{name}: a column heading is not as generated")
                        field = cell[2] or cell[4]
                        found.append((field, cell[1] or "text"))
                        if cell[2]:
                            sortable.append(field)
                    index += 1
                index += 1
                if fields.setdefault(match[1], tuple(found)) != tuple(found):
                    raise NotGenerated(f"tables of '{match[1]}' do not agree on its fields")
                if search is not None and search[0] != match[1]:
                    raise NotGenerated(f"{name}: a search box does not belong to the table after it")
                elements.append(Table(data=match[1], search=search[1] if search else None, sort=tuple(sortable)))
                search = None
            elif match := re.fullmatch(r'      <button type="button"(?: class="width-(\d+)")?>(.*)</button>', line):
                elements.append(Button(text=unescape(match[2]), width=int(match[1]) if match[1] else None))
            else:
                raise NotGenerated(f"{name}: this line is not one the compiler generates: {line.strip()}")
            if search is not None:
                raise NotGenerated(f"{name}: a search box is not followed by its table")
        if search is not None:
            raise NotGenerated(f"{name}: a search box is not followed by its table")
        pages[page_name] = Page(page_name, tuple(elements))
    if len(app_names) != 1 or not pages:
        raise NotGenerated("the files do not belong to one application")
    if order is None:
        order = list(pages)
    if sorted(order) != sorted(pages) or (len(pages) > 1 and len(order) != len(pages)):
        raise NotGenerated("the pages listed do not match the files")
    ordered = tuple(pages[name] for name in order)
    data = first_use_order([Data(name, found) for name, found in fields.items()], ordered)
    records = []
    for item in data:
        text = files.get(records_file(item.name))
        if text is not None:
            records.append(Records(item.name, _rows(text, item)))
    app = App(app_names.pop(), data, ordered, tuple(records))
    try:
        check(app)
    except IntentError as problem:
        raise NotGenerated(problem.message) from None
    return app


def _rows(text, data):
    """Read a generated JSON file of records back into values."""
    try:
        found = json.loads(text)
    except ValueError:
        raise NotGenerated(f"the records of '{data.name}' are not valid JSON") from None
    if not isinstance(found, list):
        raise NotGenerated(f"the records of '{data.name}' are not a list")
    rows = []
    for record in found:
        if not isinstance(record, dict) or list(record) != [name for name, _ in data.fields]:
            raise NotGenerated(f"a record of '{data.name}' does not have exactly the declared fields, in order")
        row = []
        for name, kind in data.fields:
            value = record[name]
            if kind == "text" and isinstance(value, str):
                row.append(Quoted(value))
            elif kind == "decimal" and isinstance(value, str):
                row.append(Decimal(value))
            elif kind == "integer" and isinstance(value, int) and not isinstance(value, bool):
                row.append(value)
            else:
                raise NotGenerated(f"a value of '{name}' in the records of '{data.name}' is not as generated")
        rows.append(tuple(row))
    return tuple(rows)
