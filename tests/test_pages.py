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

    page Products:
        heading "Products & prices"
        table Product
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
    ("understood but not built", HEAD + "        table Product\n        searchable by name\n", 9),
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
        self.assertEqual(sorted(files), ["customers.html", "products.html", "styles.css", "trace.json"])
        products = files["products.html"]
        self.assertIn("<h1>Products &amp; prices</h1>", products)
        self.assertIn("<h2>More</h2>", products)
        self.assertIn("<p>Prices are &lt;not&gt; final.</p>", products)
        self.assertIn('<th scope="col" class="decimal">price</th>', products)
        self.assertIn('<a href="customers.html">Customers</a>', products)
        self.assertIn(".width-90 {\n  width: 90px;\n}\n\n.width-160 {\n  width: 160px;\n}", files["styles.css"])
        self.assertNotIn("<nav>", build(INVENTORY, "html")["products.html"])

    def test_edited_pages_are_lifted_exactly_or_refused(self):
        files = pages_only(build(TWO_PAGES, "html"))
        edits = [("products.html", "<h2>More</h2>", "<h2>Extras</h2>", True),
                 ("products.html", 'class="width-160"', 'class="width-90"', False),  # the stylesheet no longer matches
                 ("products.html", "<p>Prices are &lt;not&gt; final.</p>", "<p>Prices are <b>not</b> final.</p>", False),
                 ("products.html", '<th scope="col">name</th>', '<th scope="col">title</th>', True),
                 ("products.html", "<h2>More</h2>", "<h3>More</h3>", False),
                 ("products.html", "      <h2>More</h2>\n", "      <h2>More</h2>\n      <script>alert(1)</script>\n", False),
                 ("styles.css", "color: #ffffff;", "color: #ff0000;", False),
                 ("styles.css", "width: 90px;", "width: 95px;", False),
                 ("customers.html", '<a href="products.html">Products</a>', '<a href="products.html">Catalogue</a>', False)]
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


if __name__ == "__main__":
    unittest.main()
