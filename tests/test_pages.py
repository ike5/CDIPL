"""Web pages in HTML and CSS: building, converting back, the two human languages, and problems reported."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from cdipl import pages
from cdipl.compiler import BuildError, build, lift_app
from cdipl.model import IntentError
from cdipl.targets.common import NotGenerated

from .support import REPO

JS_TOOLS = os.environ.get("CDIPL_JS_TOOLS", "")
INVENTORY = (REPO / "examples" / "inventory.intent").read_text(encoding="utf-8")
TWO_PAGES = '''language: en

app Shop:
    data Product:
        name: text
        price: decimal

    data Customer:
        email: text
        orders: integer

    records Product:
        "Widget", 9.99
        "Tom & Jerry <set>", 24.50
        "Bolt", 5

    page Products:
        heading "Products & prices"
        table Product
        searchable by name
        sortable by price
        heading "More"
        text "Prices are <not> final."
        button "Add product" width 160px
        button "Export"

    page Customers:
        table Customer
        button "Invite" width 90px
'''
HEAD = "language: en\n\napp Shop:\n    data Product:\n        name: text\n\n    page Products:\n"

INVALID = [
    ("no page", "language: en\n\napp Shop:\n    data Product:\n        name: text\n", 3),
    ("empty page", HEAD, 7),
    ("table of unknown data", HEAD + "        table Customer\n", 8),
    ("data never shown", HEAD + '        heading "Hi"\n', 4),
    ("unknown element", HEAD + "        table Product\n        carousel Product\n", 9),
    ("unknown type", "language: en\n\napp Shop:\n    data Product:\n        name: money\n\n    page P:\n        table Product\n", 5),
    ("empty text", HEAD + '        table Product\n        heading ""\n', 9),
    ("width too large", HEAD + '        table Product\n        button "Go" width 5000px\n', 9),
    ("two pages with one file name", HEAD + "        table Product\n\n    page products:\n        table Product\n", 10),
    ("understood but not built", HEAD + "        table Product\n        editable\n", 9),
    ("search in a field that does not exist", HEAD + "        table Product\n        searchable by colour\n", 9),
    ("sort by a field that does not exist", HEAD + "        table Product\n        sortable by colour\n", 9),
    ("search without a table", HEAD + '        heading "Hi"\n        searchable by name\n', 9),
    ("two search boxes", HEAD + "        table Product\n        searchable by name\n        searchable by name\n", 10),
    ("records of unknown data", HEAD + "        table Product\n\n    records Customer:\n        \"a\"\n", 10),
    ("record with too few values", "language: en\n\napp S:\n    data P:\n        n: text\n        q: integer\n\n    records P:\n        \"a\"\n\n    page X:\n        table P\n", 9),
    ("record with the wrong kind of value", "language: en\n\napp S:\n    data P:\n        n: text\n        q: integer\n\n    records P:\n        \"a\", \"b\"\n\n    page X:\n        table P\n", 9),
    ("resize with no button", HEAD + "        table Product\n        increase button size by 40px\n", 9),
    ("resize a button that has no width", HEAD + '        table Product\n        button "Go"\n        increase button size by 40px\n', 10),
    ("resize with two buttons and no label", HEAD + '        table Product\n        button "A" width 50px\n        button "B" width 50px\n        increase button size by 40px\n', 11),
    ("resize below one pixel", HEAD + '        table Product\n        button "A" width 50px\n        decrease button size by 50px\n', 10),
    ("no application", "language: en\n\n    page P:\n", 3),
]


def pages_only(files):
    return {name: text for name, text in files.items() if name != "trace.json"}


class PagesTest(unittest.TestCase):
    def test_round_trip_in_both_human_languages(self):
        for text in (INVENTORY, TWO_PAGES):
            app = pages.parse(text)
            files = build(text, "html")
            lifted = lift_app(files)
            self.assertEqual(lifted, app)
            for language in ("en", "es"):
                with self.subTest(language=language):
                    self.assertEqual(pages.parse(pages.render(lifted, language)), app)
                    self.assertEqual(build(pages.render(app, language), "html"), files)
        self.assertEqual(pages.render(pages.parse(INVENTORY)), INVENTORY)

    def test_what_is_generated(self):
        files = build(TWO_PAGES, "html")
        self.assertEqual(sorted(files), ["customers.html", "product.json", "products.html", "scripts.js", "styles.css",
                                         "trace.json"])
        self.assertEqual(files["product.json"], '[\n  { "name": "Widget", "price": "9.99" },\n'
                         '  { "name": "Tom & Jerry <set>", "price": "24.50" },\n  { "name": "Bolt", "price": "5" }\n]\n')
        self.assertIn('<table data-name="Product" data-source="product.json">', files["products.html"])
        self.assertIn('<table data-name="Customer">', files["customers.html"])
        self.assertIn('<label>name <input type="search" data-search="Product" data-field="name" /></label>', files["products.html"])
        self.assertIn('<th scope="col" class="decimal"><button type="button" data-sort="price">price</button></th>',
                      files["products.html"])
        self.assertIn('<script src="scripts.js" defer></script>', files["customers.html"])
        inventory = build(INVENTORY, "html")
        self.assertIn("scripts.js", inventory)
        products = files["products.html"]
        self.assertIn("<h1>Products &amp; prices</h1>", products)
        self.assertIn("<h2>More</h2>", products)
        self.assertIn("<p>Prices are &lt;not&gt; final.</p>", products)
        self.assertIn('<a href="customers.html">Customers</a>', products)
        self.assertIn(".width-90 {\n  width: 90px;\n}\n\n.width-160 {\n  width: 160px;\n}", files["styles.css"])
        self.assertNotIn("<nav>", build(INVENTORY, "html")["products.html"])

    def test_edited_pages_are_lifted_exactly_or_refused(self):
        files = pages_only(build(TWO_PAGES, "html"))
        edits = [("products.html", "<h2>More</h2>", "<h2>Extras</h2>", True),
                 ("products.html", 'class="width-160"', 'class="width-90"', False),  # the stylesheet no longer matches
                 ("products.html", "<p>Prices are &lt;not&gt; final.</p>", "<p>Prices are <b>not</b> final.</p>", False),
                 ("products.html", '<th scope="col">name</th>', '<th scope="col">title</th>', False),  # the records still say name
                 ("customers.html", '<th scope="col">email</th>', '<th scope="col">mail</th>', True),
                 ("products.html", "<h2>More</h2>", "<h3>More</h3>", False),
                 ("products.html", "      <h2>More</h2>\n", "      <h2>More</h2>\n      <script>alert(1)</script>\n", False),
                 ("styles.css", "color: #ffffff;", "color: #ff0000;", False),
                 ("styles.css", "width: 90px;", "width: 95px;", False),
                 ("customers.html", '<a href="products.html">Products</a>', '<a href="products.html">Catalogue</a>', False),
                 ("product.json", '"price": "9.99"', '"price": "10.49"', True),
                 ("product.json", '"price": "9.99"', '"price": 9.99', False),
                 ("product.json", '"name": "Widget"', '"title": "Widget"', False),
                 ("scripts.js", "row.hidden = !", "row.hidden = ", False),
                 ("products.html", 'data-sort="price"', 'data-sort="name"', False),
                 ("products.html", ' data-source="product.json"', "", False)]
        for name, old, new, lifted in edits:
            with self.subTest(edit=new):
                self.assertEqual(files[name].count(old), 1)
                edited = dict(files, **{name: files[name].replace(old, new)})
                try:
                    app = lift_app(edited)
                except NotGenerated:
                    self.assertFalse(lifted)
                else:
                    self.assertTrue(lifted)
                    self.assertEqual(pages_only(build(pages.render(app), "html")), edited)

    def test_invalid_descriptions_are_rejected_with_their_line(self):
        for description, text, line in INVALID:
            with self.subTest(description):
                with self.assertRaises(IntentError) as caught:
                    pages.parse(text)
                self.assertEqual(caught.exception.line, line, caught.exception.message)

    def test_resizing_a_button_changes_its_declaration(self):
        base = HEAD + '        table Product\n        button "Go" width 120px\n        button "Stop" width 80px\n'
        for command, expected in (('increase button "Go" size by 40px', 'button "Go" width 160px'),
                                  ('decrease button "Stop" size by 30px', 'button "Stop" width 50px')):
            with self.subTest(command):
                app = pages.parse(base + "        " + command + "\n")
                canonical = pages.render(app)
                self.assertIn(expected, canonical)
                self.assertNotIn("size by", canonical)
                self.assertEqual(pages.parse(canonical), app)
        spanish = pages.render(pages.parse(base)).replace("language: en", "idioma: es")
        app = pages.parse(pages.render(pages.parse(base), "es") + '        aumentar tamaño del botón "Go" en 40px\n')
        self.assertIn('botón "Go" ancho 160px', pages.render(app))
        del spanish

    def test_targets_do_not_mix(self):
        with self.assertRaises(BuildError):
            build(INVENTORY, "python")
        with self.assertRaises(BuildError):
            build((REPO / "examples" / "adult_users.intent").read_text(encoding="utf-8"), "html")

    def test_trace_covers_every_line(self):
        import json
        files = build(TWO_PAGES, "html")
        trace = json.loads(files["trace.json"])
        known = {entry["block"] for entry in trace["blocks"]} | {"support"}
        for name, origins in trace["files"].items():
            self.assertEqual(len(origins), len(files[name].split("\n")) - 1)
            for origin in origins:
                self.assertTrue(isinstance(origin, int) or origin in known, origin)

    @unittest.skipUnless(JS_TOOLS and Path(JS_TOOLS, ".bin", "prettier").exists(), "CDIPL_JS_TOOLS does not hold prettier")
    def test_formatter_makes_no_change(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = []
            for index, text in enumerate((INVENTORY, TWO_PAGES)):
                for name, content in pages_only(build(text, "html")).items():
                    path = Path(folder) / f"{index}-{name}"
                    path.write_text(content, encoding="utf-8")
                    paths.append(str(path))
            done = subprocess.run([str(Path(JS_TOOLS, ".bin", "prettier")), "--print-width", "320", "--check", *paths],
                                  capture_output=True, text=True, cwd=folder, check=False)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    @unittest.skipUnless(JS_TOOLS and Path(JS_TOOLS, ".bin", "eslint").exists(), "CDIPL_JS_TOOLS does not hold eslint")
    def test_linter_reports_nothing_on_the_script(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "scripts.js").write_text(build(TWO_PAGES, "html")["scripts.js"], encoding="utf-8")
            Path(folder, "eslint.config.js").write_text(
                f'const js = require("{JS_TOOLS}/@eslint/js");\nconst globals = require("{JS_TOOLS}/globals");\n'
                'module.exports = [js.configs.recommended, { languageOptions: { sourceType: "script", '
                "ecmaVersion: 2024, globals: globals.browser } }];\n", encoding="utf-8")
            done = subprocess.run([str(Path(JS_TOOLS, ".bin", "eslint")), "-c", "eslint.config.js", "scripts.js"],
                                  capture_output=True, text=True, cwd=folder, check=False)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
