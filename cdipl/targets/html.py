"""Generate web pages in HTML, CSS and JavaScript, and recognise pages this generator wrote."""
import ast
import json
import re

from ..model import IntentError
from ..pages import (
    NOTIFICATIONS_TABLE,
    PHRASES,
    App,
    Button,
    Data,
    Decimal,
    Heading,
    Notifications,
    Page,
    Paragraph,
    Quoted,
    Records,
    Rule,
    Table,
    as_kind,
    check,
    condition_text,
    first_use_order,
    read_condition,
)
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
    ("filter-elements-by-text", "label", '''\
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
    ("add-record-form", "dialog", '''\
dialog {
  padding: 1.5rem;
  border: 1px solid #9aa5b1;
  border-radius: 0.25rem;
}
'''),
    ("add-record-form", "dialog", '''\
dialog input {
  margin-left: 0.5rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid #9aa5b1;
  border-radius: 0.25rem;
  font: inherit;
}
'''),
    ("add-record-form", "dialog", '''\
dialog button {
  margin: 0.5rem 0.5rem 0 0;
  padding: 0.5rem 1rem;
  font: inherit;
}
'''),
    ("edit-table-rows", "edit", '''\
td button {
  margin: 0 0.25rem 0 0;
  padding: 0 0.5rem;
  border: 1px solid #9aa5b1;
  border-radius: 0.25rem;
  font: inherit;
  background: none;
  cursor: pointer;
}
'''),
    ("render-list", "list", '''\
ul {
  margin: 0 0 1rem;
  padding-left: 1.5rem;
}
'''),
    ("button-opens-page", "link", '''\
a.button {
  display: inline-block;
  box-sizing: border-box;
  margin: 0 0.5rem 1rem 0;
  padding: 0.5rem 1rem;
  border: 1px solid #1f2933;
  border-radius: 0.25rem;
  color: #ffffff;
  background: #1f2933;
  text-align: center;
  text-decoration: none;
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
  table.dispatchEvent(new CustomEvent("filled", { detail: records }));
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
    ("add-record-form", "form", '''\
async function addRecord(form) {
  const dialog = form.closest("dialog");
  const name = dialog.dataset.form;
  const record = {};
  for (const input of form.querySelectorAll("input")) {
    record[input.name] = input.type === "number" ? Number(input.value) : input.value;
  }
  const reply = await fetch(`/api/${name.toLowerCase()}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(record) });
  if (!reply.ok) {
    throw new Error(`${name}: ${reply.status}`);
  }
  form.reset();
  dialog.close();
  document.dispatchEvent(new Event("stored"));
  for (const table of document.querySelectorAll(`table[data-name="${name}"]`)) {
    await fillTable(table);
  }
}
'''),
    ("edit-table-rows", "edit", '''\
function addControls(table, records) {
  for (const [index, row] of Array.from(table.tBodies[0].rows).entries()) {
    row.dataset.id = String(records[index].id);
    const change = document.createElement("button");
    change.type = "button";
    change.textContent = "✎";
    change.addEventListener("click", () => openChange(table, row));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "×";
    remove.addEventListener("click", () => deleteRecord(table, row).catch((problem) => console.error(problem)));
    const cell = document.createElement("td");
    cell.append(change, remove);
    row.append(cell);
  }
}
'''),
    ("edit-table-rows", "edit", '''\
function openChange(table, row) {
  const dialog = table.nextElementSibling;
  dialog.dataset.id = row.dataset.id;
  for (const input of dialog.querySelectorAll("input")) {
    input.value = row.cells[columnOf(table, input.name)].textContent;
  }
  dialog.showModal();
}
'''),
    ("edit-table-rows", "edit", '''\
async function changeRecord(form) {
  const dialog = form.closest("dialog");
  const name = dialog.dataset.change;
  const record = {};
  for (const input of form.querySelectorAll("input")) {
    record[input.name] = input.type === "number" ? Number(input.value) : input.value;
  }
  const reply = await fetch(`/api/${name.toLowerCase()}/${dialog.dataset.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(record) });
  if (!reply.ok) {
    throw new Error(`${name}: ${reply.status}`);
  }
  dialog.close();
  document.dispatchEvent(new Event("stored"));
  for (const table of document.querySelectorAll(`table[data-name="${name}"]`)) {
    await fillTable(table);
  }
}
'''),
    ("edit-table-rows", "edit", '''\
async function deleteRecord(table, row) {
  const name = table.dataset.name;
  const reply = await fetch(`/api/${name.toLowerCase()}/${row.dataset.id}`, { method: "DELETE" });
  if (!reply.ok) {
    throw new Error(`${name}: ${reply.status}`);
  }
  for (const other of document.querySelectorAll(`table[data-name="${name}"]`)) {
    await fillTable(other);
  }
}
'''),
    ("render-list", "list", '''\
async function fillNotifications(list) {
  const reply = await fetch("/api/notification");
  if (!reply.ok) {
    throw new Error(`/api/notification: ${reply.status}`);
  }
  const notifications = await reply.json();
  const items = notifications.map((notification) => {
    const item = document.createElement("li");
    item.textContent = `${notification.recipient}: ${notification.condition} #${notification.record}`;
    return item;
  });
  list.replaceChildren(...items);
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

# Fixed server code. Each piece belongs to one block and is included only when a data type has an API.
SERVER = [
    ('sqlite-table', 'def connect():\n    connection = sqlite3.connect(DATABASE)\n    connection.row_factory = sqlite3.Row\n    return connection\n'),
    ('sqlite-table', 'def fits(value, kind):\n    if kind == "integer":\n        return isinstance(value, int) and not isinstance(value, bool) and abs(value) <= MAX_INTEGER\n    if not isinstance(value, str):\n        return False\n    if kind == "decimal":\n        return DECIMAL.fullmatch(value) is not None and sum(ch.isdigit() for ch in value) <= 15\n    try:\n        value.encode("utf-8")\n    except UnicodeEncodeError:\n        return False\n    return True\n'),
    ('sqlite-table', 'def checked(record, fields):\n    if set(record) != set(fields):\n        raise HTTPException(status_code=422, detail=f"a record needs exactly these fields: {\', \'.join(fields)}")\n    for name, kind in fields.items():\n        if not fits(record[name], kind):\n            raise HTTPException(status_code=422, detail=f"\'{name}\' must be {kind}")\n    return [record[name] for name in fields]\n'),
    ('sqlite-table', 'def columns(fields):\n    return ", ".join(f\'"{name}"\' for name in fields)\n'),
    ('sqlite-table', 'def create_table(table, fields, seed):\n    kinds = ", ".join(f\'"{name}" {"INTEGER" if kind == "integer" else "TEXT"} NOT NULL\' for name, kind in fields.items())\n    with closing(connect()) as connection, connection:\n        if connection.execute("SELECT 1 FROM sqlite_master WHERE type = \'table\' AND name = ?", (table,)).fetchone():\n            return\n        connection.execute(f\'CREATE TABLE "{table}" (id INTEGER PRIMARY KEY, {kinds})\')\n        if seed.exists():\n            marks = ", ".join("?" for _ in fields)\n            rows = [checked(record, fields) for record in json.loads(seed.read_text(encoding="utf-8"))]\n            connection.executemany(f\'INSERT INTO "{table}" ({columns(fields)}) VALUES ({marks})\', rows)\n'),
    ('rest-api', 'def list_records(table, fields):\n    with closing(connect()) as connection:\n        rows = connection.execute(f\'SELECT id, {columns(fields)} FROM "{table}" ORDER BY id\').fetchall()\n    return [dict(row) for row in rows]\n'),
    ('rest-api', 'def add_record(table, fields, record, after=None):\n    values = checked(record, fields)\n    marks = ", ".join("?" for _ in fields)\n    with closing(connect()) as connection, connection:\n        cursor = connection.execute(f\'INSERT INTO "{table}" ({columns(fields)}) VALUES ({marks})\', values)\n        if after is not None:\n            after(connection, cursor.lastrowid, dict(zip(fields, values)))\n    return {"id": cursor.lastrowid, **dict(zip(fields, values))}\n'),
    ('rest-api', 'def change_record(table, fields, record_id, record, after=None):\n    values = checked(record, fields)\n    changes = ", ".join(f\'"{name}" = ?\' for name in fields)\n    with closing(connect()) as connection, connection:\n        cursor = connection.execute(f\'UPDATE "{table}" SET {changes} WHERE id = ?\', [*values, record_id])\n        if cursor.rowcount and after is not None:\n            after(connection, record_id, dict(zip(fields, values)))\n    if cursor.rowcount == 0:\n        raise HTTPException(status_code=404, detail="there is no record with that id")\n    return {"id": record_id, **dict(zip(fields, values))}\n'),
    ('rest-api', 'def delete_record(table, record_id):\n    with closing(connect()) as connection, connection:\n        cursor = connection.execute(f\'DELETE FROM "{table}" WHERE id = ?\', [record_id])\n    if cursor.rowcount == 0:\n        raise HTTPException(status_code=404, detail="there is no record with that id")\n'),
    ('notify-when', 'def create_notifications():\n    with closing(connect()) as connection, connection:\n        connection.execute(\'CREATE TABLE IF NOT EXISTS "notification" (id INTEGER PRIMARY KEY, "recipient" TEXT NOT NULL, "condition" TEXT NOT NULL, "record" INTEGER NOT NULL, "time" TEXT NOT NULL)\')\n'),
    ('notify-when', 'def notify(connection, recipient, condition, record_id):\n    time = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")\n    connection.execute(\'INSERT INTO "notification" ("recipient", "condition", "record", "time") VALUES (?, ?, ?, ?)\', [recipient, condition, record_id, time])\n'),
    ('notify-when', 'def list_notifications():\n    with closing(connect()) as connection:\n        rows = connection.execute(\'SELECT id, "recipient", "condition", "record", "time" FROM "notification" ORDER BY id\').fetchall()\n    return [dict(row) for row in rows]\n'),
]
REQUIREMENTS = ["fastapi==0.162.5", "uvicorn==0.54.0"]  # the versions the generated server was tested with

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
    "fastapi-app": "server.py: app = FastAPI(title=APP); GET / redirects to the first page; pages served from static/",
    "sqlite-table": 'create_table(TABLE, FIELDS, HERE / "TABLE.json"); id INTEGER PRIMARY KEY; decimals stored as TEXT',
    "rest-api": "GET and POST /api/TABLE; PUT and DELETE /api/TABLE/{record_id}",
    "add-record-form": '<button data-add="DATA">; <dialog data-form="DATA"><form method="dialog"> one input per field',
    "button-opens-page": '<a class="button" href="PAGE.html">TEXT</a>',
    "edit-table-rows": '<table data-editable>; <td></td> after the headings; <dialog data-change="DATA"><form method="dialog"> one input '
                       "per field; each row: data-id, a cell with buttons ✎ (PUT /api/TABLE/ID) and × (DELETE /api/TABLE/ID)",
    "render-list": "<ul data-notifications></ul>; one <li>RECIPIENT: CONDITION #RECORD</li> per notification from /api/notification",
    "notify-when": 'def TABLE_rules(connection, record_id, record): if COMPARISONS: notify(connection, "RECIPIENT", "CONDITION", '
                   "record_id); GET /api/notification",
}


ELEMENT_BLOCKS = {Heading: "page-heading", Paragraph: "page-text", Table: "data-table", Button: "page-button",
                  Notifications: "render-list"}


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
    """Which behaviours the application uses: fill, search, sort, form, edit, list."""
    filled = {item.name for item in app.records} | set(app.exposed)
    found = set()
    for page in app.pages:
        for element in page.elements:
            if isinstance(element, Button) and element.action is not None and element.action[0] == "adds":
                found.add("form")
            if isinstance(element, Notifications):
                found.add("list")
    for table in tables(app):
        if table.editable:
            found.add("edit")
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

    filled = {item.name for item in app.records} | set(app.exposed)
    if "fastapi" in app.uses:
        add("fastapi-app")
    if app.exposed:
        add("sqlite-table", "rest-api")
    if app.rules:
        add("notify-when")
    for page in app.pages:
        for element in page.elements:
            add(ELEMENT_BLOCKS[type(element)])
            if isinstance(element, Button) and element.action is not None:
                add("add-record-form" if element.action[0] == "adds" else "button-opens-page")
            if isinstance(element, Table):
                if element.data in filled or element.search is not None or element.sort:
                    add("render-table")
                if element.search is not None:
                    add("filter-elements-by-text")
                if element.sort:
                    add("table-sort")
                if element.editable:
                    add("edit-table-rows", "add-record-form")  # the form for changing a record is the add form's
    if app.records:
        add("data-records")
    return used


def page_lines(app, page):
    """One page as (text, origin) pairs. origin is an intent line number or the name of a block."""
    data = {item.name: item for item in app.data}
    filled = {item.name for item in app.records}
    files = {other.name: file_name(other) for other in app.pages}
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
            if element.data in app.exposed:
                source = f' data-source="/api/{element.data.lower()}"'
            if element.editable:
                source += " data-editable"
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
            edit = element.editable_line or element.line
            if element.editable:
                out.append(("            <td></td>", edit))
            out += [("          </tr>", element.line), ("        </thead>", element.line),
                    ("        <tbody></tbody>", element.line), ("      </table>", element.line)]
            if element.editable:
                out += [(f'      <dialog data-change="{element.data}">', edit)] + form_lines(data[element.data], "✓", edit)
        elif isinstance(element, Notifications):
            out.append(("      <ul data-notifications></ul>", element.line))
        elif element.action is not None and element.action[0] == "opens":
            width_class = "" if element.width is None else f" width-{element.width}"
            out.append((f'      <a class="button{width_class}" href="{files[element.action[1]]}">{escape(element.text)}</a>',
                        element.line))
        else:
            width_class = "" if element.width is None else f' class="width-{element.width}"'
            adds = "" if element.action is None else f' data-add="{element.action[1]}"'
            out.append((f'      <button type="button"{width_class}{adds}>{escape(element.text)}</button>', element.line))
            if element.action is not None:
                out += [(f'      <dialog data-form="{element.action[1]}">', element.line)]
                out += form_lines(data[element.action[1]], escape(element.text), element.line)
    out += [("    </main>", "html-page"), ("  </body>", "html-page"), ("</html>", "html-page")]
    return out


def form_lines(data, send, origin):
    """The form inside a dialog, with one input for each field of a data type, and the end of the dialog."""
    out = [('        <form method="dialog">', origin)]
    for name, kind in data.fields:
        extra = {"text": "", "integer": ' type="number" step="1" required',
                 "decimal": ' inputmode="decimal" pattern="-?\\d+(\\.\\d+)?" required'}[kind]
        out.append((f'          <label>{name} <input name="{name}"{extra} /></label>', origin))
    return out + [(f'          <button type="submit">{send}</button>', origin),
                  ('          <button type="button" value="close">×</button>', origin),
                  ("        </form>", origin), ("      </dialog>", origin)]


def style_lines(app):
    flags = {"always"} | features(app)
    if flags & {"search", "form", "edit"}:
        flags.add("label")
    if flags & {"form", "edit"}:
        flags.add("dialog")
    widths = {}
    for page in app.pages:
        for element in page.elements:
            if isinstance(element, Button) and element.action is not None and element.action[0] == "opens":
                flags.add("link")
            else:
                flags.add({Heading: "heading", Paragraph: "text", Table: "table", Button: "button",
                           Notifications: "list"}[type(element)])
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
    if "edit" in flags:  # before the tables are filled, so that every row gets its controls
        block = "edit-table-rows"
        out += [('  for (const table of document.querySelectorAll("table[data-editable]")) {', block),
                ("    const dialog = table.nextElementSibling;", block),
                ('    table.addEventListener("filled", (event) => addControls(table, event.detail));', block),
                ("    dialog.querySelector('button[value=\"close\"]').addEventListener(\"click\", () => dialog.close());", block),
                ('    dialog.querySelector("form").addEventListener("submit", (event) => {', block),
                ("      event.preventDefault();", block),
                ("      changeRecord(event.target).catch((problem) => console.error(problem));", block),
                ("    });", block), ("  }", block)]
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
    if "form" in flags:
        block = "add-record-form"
        out += [('  for (const button of document.querySelectorAll("button[data-add]")) {', block),
                ("    const dialog = button.nextElementSibling;", block),
                ('    button.addEventListener("click", () => dialog.showModal());', block),
                ("    dialog.querySelector('button[value=\"close\"]').addEventListener(\"click\", () => dialog.close());", block),
                ('    dialog.querySelector("form").addEventListener("submit", (event) => {', block),
                ("      event.preventDefault();", block),
                ("      addRecord(event.target).catch((problem) => console.error(problem));", block),
                ("    });", block), ("  }", block)]
    if "list" in flags:
        block = "render-list"
        out += [('  for (const list of document.querySelectorAll("ul[data-notifications]")) {', block),
                ("    fillNotifications(list).catch((problem) => console.error(problem));", block),
                ('    document.addEventListener("stored", () => fillNotifications(list).catch((problem) => console.error(problem)));', block),
                ("  }", block)]
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


def server_lines(app):
    """The FastAPI server: serves the pages and, for each exposed data type, an API over a SQLite table."""
    data = {item.name: item for item in app.data}
    exposed = [data[name] for name in app.exposed]
    lines = dict(zip(app.exposed, app.expose_lines or (app.line,) * len(app.exposed)))
    use = dict(zip(app.uses, app.use_lines or (app.line,) * len(app.uses)))
    web, base = use.get("fastapi", app.line), use.get("sqlite", app.line)
    out = []
    if exposed:
        out += [("import json", base), ("import re", base), ("import sqlite3", base),
                ("from contextlib import closing", base)]
    if app.rules:
        out.append(("from datetime import UTC, datetime", "notify-when"))
        kinds = {item.name: dict(item.fields) for item in exposed}
        decimal = [rule for rule in app.rules if any(kinds[rule.data][name] == "decimal" for name, _, _ in rule.conditions)]
        if decimal:
            out.append(("from decimal import Decimal", decimal[0].line))
    out.append(("from pathlib import Path", web))
    if exposed:
        out.append(("from typing import Annotated", web))
    names = "Body, FastAPI, HTTPException" if exposed else "FastAPI"
    out += [("", "support"), (f"from fastapi import {names}", web),
            ("from fastapi.responses import RedirectResponse", web), ("from fastapi.staticfiles import StaticFiles", web),
            ("", "support"), ("HERE = Path(__file__).parent", web)]
    if exposed:
        out += [(f'DATABASE = HERE / "{app.name.lower()}.db"', base), ("MAX_INTEGER = 9007199254740991", "sqlite-table"),
                ('DECIMAL = re.compile(r"-?\\d+(\\.\\d+)?")', "sqlite-table")]
        for item in exposed:
            fields = ", ".join(f'"{name}": "{kind}"' for name, kind in item.fields)
            out.append((f"{item.name.upper()}_FIELDS = {{{fields}}}", item.line))
    out += [("", "support"), (f'app = FastAPI(title="{app.name}")', app.line)]
    if exposed:
        for block, text in SERVER:
            if block != "notify-when" or app.rules:
                out += [("", "support"), ("", "support")] + [(line, block) for line in text.rstrip("\n").split("\n")]
    ruled = {}
    for rule in app.rules:
        ruled.setdefault(rule.data, []).append(rule)
    for item in exposed:
        if item.name in ruled:
            out += [("", "support"), ("", "support")] + rule_lines(item, ruled[item.name])
    for item in exposed:
        table, fields, line = item.name.lower(), f"{item.name.upper()}_FIELDS", lines[item.name]
        after = f", {table}_rules" if item.name in ruled else ""
        out += [("", "support"), ("", "support"),
                (f'@app.get("/api/{table}")', line), (f"def {table}_list():", line),
                (f'    return list_records("{table}", {fields})', line),
                ("", "support"), ("", "support"),
                (f'@app.post("/api/{table}", status_code=201)', line),
                (f"def {table}_add(record: Annotated[dict, Body()]):", line),
                (f'    return add_record("{table}", {fields}, record{after})', line),
                ("", "support"), ("", "support"),
                (f'@app.put("/api/{table}/{{record_id}}")', line),
                (f"def {table}_change(record_id: int, record: Annotated[dict, Body()]):", line),
                (f'    return change_record("{table}", {fields}, record_id, record{after})', line),
                ("", "support"), ("", "support"),
                (f'@app.delete("/api/{table}/{{record_id}}", status_code=204)', line),
                (f"def {table}_delete(record_id: int):", line),
                (f'    delete_record("{table}", record_id)', line)]
    if app.rules:
        block = "notify-when"
        out += [("", "support"), ("", "support"), (f'@app.get("/api/{NOTIFICATIONS_TABLE}")', block),
                (f"def {NOTIFICATIONS_TABLE}_list():", block), ("    return list_notifications()", block)]
    first = app.pages[0]
    out += [("", "support"), ("", "support"), ('@app.get("/")', first.line), ("def first_page():", first.line),
            (f'    return RedirectResponse(url="/{file_name(first)}")', first.line), ("", "support"), ("", "support")]
    for item in exposed:
        table = item.name.lower()
        out.append((f'create_table("{table}", {item.name.upper()}_FIELDS, HERE / "{table}.json")', lines[item.name]))
    if app.rules:
        out.append(("create_notifications()", "notify-when"))
    out.append(('app.mount("/", StaticFiles(directory=HERE / "static"), name="pages")', web))
    return out


def python_string(text):
    """A Python string literal for text, written as the formatter writes it: double quotes unless single quotes
    need fewer escapes, and characters that are not printable as escapes."""
    body = "".join(ch if ch.isprintable() else (f"\\u{ord(ch):04x}" if ord(ch) < 0x10000 else f"\\U{ord(ch):08x}")
                   for ch in text.replace("\\", "\\\\"))
    if text.count('"') > text.count("'"):
        return "'" + body.replace("'", "\\'") + "'"
    return '"' + body.replace('"', '\\"') + '"'


def comparison_code(name, operator, value, kind):
    """One comparison of a rule as a Python expression over the record as stored."""
    python = "==" if operator == "=" else operator
    if kind == "decimal":  # compared exactly; a whole number needs no Decimal of its own
        return f'Decimal(record["{name}"]) {python} ' + (f'Decimal("{value}")' if "." in value else str(int(value)))
    if kind == "text":
        return f'record["{name}"] {python} {python_string(value)}'
    return f'record["{name}"] {python} {value}'


def rule_lines(data, rules):
    """The function that applies the rules of one data type to a record that has just been stored."""
    kinds = dict(data.fields)
    out = [(f"def {data.name.lower()}_rules(connection, record_id, record):", rules[0].line)]
    for rule in rules:
        test = " and ".join(comparison_code(name, operator, value, kinds[name]) for name, operator, value in rule.conditions)
        out += [(f"    if {test}:", rule.line),
                (f"        notify(connection, {python_string(rule.recipient)}, {python_string(condition_text(rule))}, record_id)",
                 rule.notify_line or rule.line)]
    return out


def generate(app):
    """Every file of the application: file name -> list of (line, origin)."""
    served = "fastapi" in app.uses
    folder = "static/" if served else ""
    files = {folder + file_name(page): page_lines(app, page) for page in app.pages}
    files[folder + STYLES] = style_lines(app)
    if features(app):
        files[folder + SCRIPTS] = script_lines(app)
    for records in app.records:
        files[("" if records.name in app.exposed else folder) + records_file(records.name)] = record_lines(app, records)
    if served:
        files["server.py"] = server_lines(app)
        line = dict(zip(app.uses, app.use_lines or (app.line,) * len(app.uses)))["fastapi"]
        files["requirements.txt"] = [(requirement, line) for requirement in REQUIREMENTS]
    return files


NAME = r"([A-Za-z_][A-Za-z0-9_]*)"
HEADING_CELL = re.compile(rf'            <th scope="col"(?: class="(integer|decimal)")?>(?:<button type="button" data-sort="{NAME}">{NAME}</button>|{NAME})</th>')


def lift(files):
    """Recover the App from generated files (file name -> text). Raises NotGenerated."""
    served = "server.py" in files
    files = {name.removeprefix("static/") if served else name: text for name, text in files.items()}
    pages, order, fields, app_names, exposed, opens = {}, None, {}, set(), [], {}
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
            elif line == "      <ul data-notifications></ul>":
                elements.append(Notifications())
            elif match := re.fullmatch(rf'      <table data-name="{NAME}"(?: data-source="(/api/)?[a-z0-9_]+(?:\.json)?")?( data-editable)?>', line):
                if match[2] and match[1] not in exposed:
                    exposed.append(match[1])
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
                editable = bool(match[3])
                if editable:  # the form for changing a record follows the table; rebuilding checks every line of it
                    if index >= len(body) or body[index] != f'      <dialog data-change="{match[1]}">':
                        raise NotGenerated(f"{name}: an editable table is not followed by its form")
                    try:
                        index = body.index("      </dialog>", index) + 1
                    except ValueError:
                        raise NotGenerated(f"{name}: a form is not as generated") from None
                elements.append(Table(data=match[1], search=search[1] if search else None, sort=tuple(sortable),
                                      editable=editable))
                search = None
            elif match := re.fullmatch(rf'      <button type="button"(?: class="width-(\d+)")?(?: data-add="{NAME}")?>(.*)</button>', line):
                action = ("adds", match[2]) if match[2] else None
                if action is not None:
                    try:
                        index = body.index("      </dialog>", index) + 1
                    except ValueError:
                        raise NotGenerated(f"{name}: a form is not as generated") from None
                elements.append(Button(text=unescape(match[3]), width=int(match[1]) if match[1] else None, action=action))
            elif match := re.fullmatch(r'      <a class="button(?: width-(\d+))?" href="([a-z0-9_]+\.html)">(.*)</a>', line):
                opens[(page_name, len(elements))] = match[2]
                elements.append(Button(text=unescape(match[3]), width=int(match[1]) if match[1] else None,
                                       action=("opens", match[2])))
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
    by_file = {file_name(page): page.name for page in pages.values()}
    for (page_name, position), target in opens.items():
        if target not in by_file:
            raise NotGenerated("a button opens a page that is not among the files")
        page = pages[page_name]
        button = page.elements[position]
        changed = Button(text=button.text, width=button.width, action=("opens", by_file[target]))
        pages[page_name] = Page(page.name, (*page.elements[:position], changed, *page.elements[position + 1:]))
    ordered = tuple(pages[name] for name in order)
    data = first_use_order([Data(name, found) for name, found in fields.items()], ordered)
    records = []
    for item in data:
        text = files.get(records_file(item.name))
        if text is not None:
            records.append(Records(item.name, _rows(text, item)))
    position = {item.name: index for index, item in enumerate(data)}
    exposed.sort(key=lambda name: position.get(name, len(position)))
    uses = (("sqlite",) if exposed else ()) + (("fastapi",) if served else ())
    rules = _rules(files.get("server.py", ""), data)
    app = App(app_names.pop(), data, ordered, tuple(records), uses, tuple(exposed), rules=rules)
    try:
        check(app)
    except IntentError as problem:
        raise NotGenerated(problem.message) from None
    return app


def _rules(server, data):
    """Read the rules back from the calls that store notifications in a generated server.

    Each call holds the rule's recipient and its condition in standard English phrases; the comparisons
    in the code are not read, because rebuilding the server checks that they are exactly as generated.
    """
    fields = {item.name: dict(item.fields) for item in data}
    rules = []
    for line in server.split("\n"):
        match = re.fullmatch(rf'        notify\(connection, "{NAME}", (.+), record_id\)', line)
        if match is None:
            continue
        try:
            condition = ast.literal_eval(match[2])
        except (ValueError, SyntaxError):
            raise NotGenerated("a rule in the server is not as generated") from None
        if not isinstance(condition, str):
            raise NotGenerated("a rule in the server is not as generated")
        try:
            name, comparisons = read_condition(condition, 0, PHRASES["en"])
        except IntentError:
            raise NotGenerated("a rule in the server is not as generated") from None
        kinds = fields.get(name, {})
        comparisons = tuple((field, operator, as_kind(value, kinds.get(field))) for field, operator, value in comparisons)
        rules.append(Rule(name, comparisons, match[1]))
    return tuple(rules)


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
