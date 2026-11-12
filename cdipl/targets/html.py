"""Generate web pages in HTML and CSS, and recognise pages this generator wrote."""
import re

from ..model import IntentError
from ..pages import App, Button, Data, Heading, Page, Paragraph, Table, check, first_use_order
from .common import NotGenerated

STYLES = "styles.css"

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
    ("page-button", "button", '''\
button {
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

# The shape of the markup each block adds. Part of the block's version.
FORMS = {
    "html-page": "<!doctype html><html><head><title>PAGE - APP</title></head><body><nav></nav><main></main></body></html>",
    "page-heading": "<h1>TEXT</h1> for the first heading on a page, <h2>TEXT</h2> for the rest",
    "page-text": "<p>TEXT</p>",
    "data-table": '<table data-name="DATA"><thead><tr><th scope="col" class="TYPE">FIELD</th></tr></thead><tbody></tbody></table>',
    "page-button": '<button type="button" class="width-N">TEXT</button>; .width-N { width: Npx; }',
}


def file_name(page):
    return page.name.lower() + ".html"


def escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def unescape(text):
    if re.search(r"[<>]|&(?!amp;|lt;|gt;)", text):
        raise NotGenerated("text is not written the way the compiler writes it")
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def blocks_used(app):
    used = ["html-page"]
    for page in app.pages:
        for element in page.elements:
            name = {Heading: "page-heading", Paragraph: "page-text", Table: "data-table", Button: "page-button"}[type(element)]
            if name not in used:
                used.append(name)
    return used


def page_lines(app, page):
    """One page as (text, origin) pairs. origin is an intent line number or the name of a block."""
    data = {item.name: item for item in app.data}
    out = [("<!doctype html>", "html-page"), ("<html>", "html-page"), ("  <head>", "html-page"),
           ('    <meta charset="utf-8" />', "html-page"),
           ('    <meta name="viewport" content="width=device-width, initial-scale=1" />', "html-page"),
           (f"    <title>{page.name} - {app.name}</title>", page.line),
           (f'    <link rel="stylesheet" href="{STYLES}" />', "html-page"),
           ("  </head>", "html-page"), ("  <body>", "html-page")]
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
            out += [(f'      <table data-name="{element.data}">', element.line), ("        <thead>", element.line),
                    ("          <tr>", element.line)]
            for name, kind in data[element.data].fields:
                kind_class = "" if kind == "text" else f' class="{kind}"'
                out.append((f'            <th scope="col"{kind_class}>{name}</th>', element.line))
            out += [("          </tr>", element.line), ("        </thead>", element.line),
                    ("        <tbody></tbody>", element.line), ("      </table>", element.line)]
        else:
            width_class = "" if element.width is None else f' class="width-{element.width}"'
            out.append((f'      <button type="button"{width_class}>{escape(element.text)}</button>', element.line))
    out += [("    </main>", "html-page"), ("  </body>", "html-page"), ("</html>", "html-page")]
    return out


def style_lines(app):
    flags = {"always"}
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


def generate(app):
    """Every file of the application: file name -> list of (line, origin)."""
    files = {file_name(page): page_lines(app, page) for page in app.pages}
    files[STYLES] = style_lines(app)
    return files


NAME = r"([A-Za-z_][A-Za-z0-9_]*)"


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
        elements, index = [], 0
        while index < len(body):
            line = body[index]
            index += 1
            if match := re.fullmatch(r"      <(h1|h2)>(.*)</\1>", line):
                elements.append(Heading(text=unescape(match[2])))
            elif match := re.fullmatch(r"      <p>(.*)</p>", line):
                elements.append(Paragraph(text=unescape(match[1])))
            elif match := re.fullmatch(rf'      <table data-name="{NAME}">', line):
                found = []
                while index < len(body) and body[index] != "      </table>":
                    if cell := re.fullmatch(rf'            <th scope="col"(?: class="(integer|decimal)")?>{NAME}</th>', body[index]):
                        found.append((cell[2], cell[1] or "text"))
                    index += 1
                index += 1
                if fields.setdefault(match[1], tuple(found)) != tuple(found):
                    raise NotGenerated(f"tables of '{match[1]}' do not agree on its fields")
                elements.append(Table(data=match[1]))
            elif match := re.fullmatch(r'      <button type="button"(?: class="width-(\d+)")?>(.*)</button>', line):
                elements.append(Button(text=unescape(match[2]), width=int(match[1]) if match[1] else None))
            else:
                raise NotGenerated(f"{name}: this line is not one the compiler generates: {line.strip()}")
        pages[page_name] = Page(page_name, tuple(elements))
    if len(app_names) != 1 or not pages:
        raise NotGenerated("the files do not belong to one application")
    if order is None:
        order = list(pages)
    if sorted(order) != sorted(pages) or (len(pages) > 1 and len(order) != len(pages)):
        raise NotGenerated("the pages listed do not match the files")
    ordered = tuple(pages[name] for name in order)
    data = first_use_order([Data(name, found) for name, found in fields.items()], ordered)
    app = App(app_names.pop(), data, ordered)
    try:
        check(app)
    except IntentError as problem:
        raise NotGenerated(problem.message) from None
    return app
