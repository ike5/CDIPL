"""An application with a database and an API: the generated FastAPI server is run for real."""
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

from cdipl import pages
from cdipl.compiler import build, lift_app
from cdipl.model import IntentError
from cdipl.targets.common import NotGenerated

from .support import REPO

EXAMPLE = (REPO / "examples" / "inventory_server.intent").read_text(encoding="utf-8")
PAGES_ONLY = 'language: en\n\nuse FastAPI\n\napp Site:\n    page Home:\n        heading "Welcome"\n'
HAVE_FASTAPI = importlib.util.find_spec("fastapi") is not None and importlib.util.find_spec("httpx") is not None
HEAD = ("language: en\n\nuse sqlite\nuse FastAPI\n\napp Shop:\n    data Product:\n        name: text\n\n"
        "    expose Product as api\n\n    page Products:\n        table Product\n")
HEAD_ES = ("idioma: es\n\nusar sqlite\nusar FastAPI\n\naplicación Shop:\n    datos Product:\n        name: texto\n\n"
           "    exponer Product como api\n\n    página Products:\n        tabla Product\n")
RULES = '''language: en

use sqlite
use FastAPI

app Shop:
    data Product:
        name: text
        price: decimal
        stock: integer

    records Product:
        "cheap", 1.00, 1

    expose Product as api

    page Products:
        heading "Products"
        table Product
        sortable by price
        editable
        button "Add" adds Product
        notifications

    when Product.price < 9.99:
        notify buyer

    when Product.name = "bolt" and Product.stock >= 10:
        notify clerk

    when Product.name < "b":
        notify sorter
'''
# Rules whose values the generated Python must write with care: quotes, a backslash, a character that is not
# printable, whole numbers for a decimal field, negative numbers and leading zeros.
ODD_RULES = RULES + '''
    when Product.name = "it's \\"odd\\" \\\\ a​b" and Product.price >= 100:
        notify buyer

    when Product.price != -0.50 and Product.price > 004.5 and Product.stock != -3 and Product.price = 5:
        notify clerk
'''
JS_TOOLS = os.environ.get("CDIPL_JS_TOOLS", "")

INVALID = [
    ("an API without a database or framework", "language: en\n\napp Shop:\n    data Product:\n        name: text\n\n"
     "    expose Product as api\n\n    page Products:\n        table Product\n", 7),
    ("a database nothing uses", "language: en\n\nuse sqlite\nuse FastAPI\n\napp Shop:\n    page P:\n        heading \"Hi\"\n", 3),
    ("exposing unknown data", HEAD + "\n    expose Customer as api\n", 15),
    ("exposing twice", HEAD.replace("    expose Product as api\n", "    expose Product as api\n    expose Product as api\n"), 11),
    ("a field named id", HEAD.replace("        name: text\n", "        id: integer\n"), 10),
    ("choosing a part twice", HEAD.replace("use sqlite\n", "use sqlite\nuse sqlite\n"), 4),
    ("choosing a part inside the application", HEAD + "    use sqlite\n", 14),
    ("adding data that has no API", "language: en\n\napp Shop:\n    data Product:\n        name: text\n\n    page P:\n"
     "        table Product\n        button \"Add\" adds Product\n", 9),
    ("opening a page that does not exist", HEAD + '        button "Go" opens Nowhere\n', 14),
    ("a rule about unknown data", HEAD + '\n    when Customer.name = "a":\n        notify manager\n', 15),
    ("a rule about a field that does not exist", HEAD + '\n    when Product.colour = "a":\n        notify manager\n', 15),
    ("a rule comparing text with a number", HEAD + "\n    when Product.name < 5:\n        notify manager\n", 15),
    ("a rule about two data types", HEAD + '\n    when Product.name = "a" and Customer.name = "b":\n        notify manager\n', 15),
    ("a rule with an unknown comparison", HEAD + '\n    when Product.name == "a":\n        notify manager\n', 15),
    ("a rule joined by 'or'", HEAD + '\n    when Product.name = "a" or Product.name = "b":\n        notify manager\n', 15),
    ("a rule with no one to notify", HEAD + '\n    when Product.name = "a":\n', 15),
    ("a rule that notifies twice", HEAD + '\n    when Product.name = "a":\n        notify manager\n        notify clerk\n', 17),
    ("a rule with something else beneath it", HEAD + '\n    when Product.name = "a":\n        heading "Hi"\n', 16),
    ("notifying an invalid name", HEAD + '\n    when Product.name = "a":\n        notify 9lives\n', 16),
    ("a rule written twice", HEAD + '\n    when Product.name = "a":\n        notify manager\n\n    when Product.name = "a":\n        notify manager\n', 18),
    ("a rule that is not indented", HEAD + '\nwhen Product.name = "a":\n    notify manager\n', 15),
    ("a rule about data that has no API", HEAD.replace("    page Products:\n", "    data Customer:\n        name: text\n\n    page Products:\n")
     + '        table Customer\n\n    when Customer.name = "a":\n        notify manager\n', 19),
    ("an API named like the notifications", HEAD.replace("Product", "Notification") + '\n    when Notification.name = "a":\n        notify manager\n', 10),
    ("a decimal compared with text", HEAD.replace("name: text", "price: decimal").replace("table Product", "table Product\n        editable")
     + '\n    when Product.price < "9.99":\n        notify manager\n', 16),
    ("a whole number compared with a decimal", HEAD.replace("name: text", "stock: integer") + "\n    when Product.stock < 4.5:\n        notify manager\n", 15),
    ("a rule in Spanish joined by 'and'", HEAD_ES + '\n    cuando Product.name = "a" and Product.name = "b":\n        notificar manager\n', 15),
]


def load_server(folder, name):
    """Import the generated server from a folder, as a fresh module."""
    spec = importlib.util.spec_from_file_location(name, Path(folder) / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(folder, files):
    for name, text in files.items():
        path = Path(folder) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def without_trace(files):
    return {name: text for name, text in files.items() if name != "trace.json"}


class ServerTest(unittest.TestCase):
    def test_what_is_generated(self):
        files = build(EXAMPLE, "html")
        self.assertEqual(sorted(files), ["product.json", "requirements.txt", "server.py", "static/products.html",
                                         "static/scripts.js", "static/styles.css", "static/supplier.json",
                                         "static/suppliers.html", "trace.json"])
        products = files["static/products.html"]
        self.assertIn('<table data-name="Product" data-source="/api/product" data-editable>', products)
        self.assertIn('            <td></td>\n          </tr>', products)
        self.assertIn('      </table>\n      <dialog data-change="Product">\n        <form method="dialog">', products)
        self.assertIn('<button type="submit">✓</button>', products)
        self.assertIn("<ul data-notifications></ul>", products)
        self.assertIn('        notify(connection, "inventory_manager", "Product.stock < 5", record_id)', files["server.py"])
        self.assertIn('@app.get("/api/notification")', files["server.py"])
        self.assertNotIn("@app.post(\"/api/notification", files["server.py"])
        self.assertNotIn("notification", build(EXAMPLE.replace("    when Product.stock < 5:\n        notify inventory_manager\n", "")
                                                       .replace("        notifications\n", ""), "html")["server.py"])
        self.assertIn('<button type="button" class="width-160" data-add="Product">Add product</button>', products)
        self.assertIn('<label>stock <input name="stock" type="number" step="1" required /></label>', products)
        self.assertIn('<a class="button" href="suppliers.html">Suppliers</a>', products)
        self.assertIn('<table data-name="Supplier" data-source="supplier.json">', files["static/suppliers.html"])
        self.assertIn('@app.post("/api/product", status_code=201)', files["server.py"])
        self.assertNotIn("supplier", files["server.py"])
        self.assertNotIn("sqlite3", build(PAGES_ONLY, "html")["server.py"])

    def test_round_trip_in_both_human_languages(self):
        for text in (EXAMPLE, PAGES_ONLY, RULES):
            app = pages.parse(text)
            files = build(text, "html")
            self.assertEqual(lift_app(files), app)
            self.assertEqual(pages.render(app), text)
            self.assertEqual(build(pages.render(app, "es"), "html"), files)

    def test_edited_server_is_refused(self):
        files = without_trace(build(EXAMPLE, "html"))
        for old, new in (("status_code=201", "status_code=200"), ("abs(value) <= MAX_INTEGER", "True"),
                         ('HERE / "static"', "HERE"), ("fastapi==", "fastapi>=")):
            name = "requirements.txt" if "fastapi=" in old else "server.py"
            with self.subTest(edit=new):
                self.assertEqual(files[name].count(old), 1)
                with self.assertRaises(NotGenerated):
                    lift_app(dict(files, **{name: files[name].replace(old, new)}))

    def test_edited_rules_and_editable_tables_are_lifted_exactly_or_refused(self):
        files = without_trace(build(RULES, "html"))
        edits = [("server.py", ['if Decimal(record["price"]) < Decimal("9.99"):'], ['if Decimal(record["price"]) < Decimal("9.95"):'], False),
                 ("server.py", ['if Decimal(record["price"]) < Decimal("9.99"):', '"Product.price < 9.99"'],
                  ['if Decimal(record["price"]) <= Decimal("9.95"):', '"Product.price <= 9.95"'], True),
                 ("server.py", ['notify(connection, "buyer"'], ['notify(connection, "seller"'], True),
                 ("server.py", ['"Product.price < 9.99"'], ['"Product.price < 9.99 or 1"'], False),
                 ("server.py", ["create_notifications()\n"], [""], False),
                 ("server.py", ["record, product_rules)\n"], ["record)\n"], False),
                 ("static/products.html", [" data-editable>"], [">"], False),
                 ("static/products.html", ["<button type=\"submit\">✓</button>"], ["<button type=\"submit\">Save</button>"], False),
                 ("static/products.html", ["      <ul data-notifications></ul>\n"], [""], False),
                 ("static/scripts.js", ['change.textContent = "✎";'], ['change.textContent = "Edit";'], False),
                 ("static/scripts.js", ["/api/notification"], ["/api/notifications"], False)]
        for name, olds, news, lifted in edits:
            with self.subTest(edit=news):
                edited = files[name]
                for old, new in zip(olds, news):
                    self.assertGreaterEqual(edited.count(old), 1, old)
                    edited = edited.replace(old, new, 1)
                edited = dict(files, **{name: edited})
                try:
                    app = lift_app(edited)
                except NotGenerated:
                    self.assertFalse(lifted)
                else:
                    self.assertTrue(lifted)
                    self.assertEqual(without_trace(build(pages.render(app), "html")), edited)

    def test_invalid_descriptions_are_rejected_with_their_line(self):
        for description, text, line in INVALID:
            with self.subTest(description):
                with self.assertRaises(IntentError) as caught:
                    pages.parse(text)
                self.assertEqual(caught.exception.line, line, caught.exception.message)

    @unittest.skipUnless(importlib.util.find_spec("ruff"), "ruff is not installed")
    def test_server_passes_the_formatter_and_linter(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = []
            for index, text in enumerate((EXAMPLE, PAGES_ONLY, RULES, ODD_RULES)):
                path = Path(folder) / f"server{index}.py"
                path.write_text(build(text, "html")["server.py"], encoding="utf-8")
                paths.append(str(path))
            for command in (["format", "--check"], ["check"]):
                done = subprocess.run([sys.executable, "-m", "ruff", *command, "--isolated", "--line-length", "320", *paths],
                                      capture_output=True, text=True, check=False)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    @unittest.skipUnless(HAVE_FASTAPI, "fastapi and httpx are not installed")
    def test_the_generated_server_works(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from fastapi.testclient import TestClient
        with tempfile.TemporaryDirectory() as folder:
            write(folder, without_trace(build(EXAMPLE, "html")))
            client = TestClient(load_server(folder, "generated_server_a").app, follow_redirects=False)
            listed = client.get("/api/product")
            self.assertEqual(listed.status_code, 200)
            self.assertEqual(listed.json(), [{"id": 1, "name": "Widget", "price": "9.99", "stock": 12},
                                             {"id": 2, "name": "Gadget", "price": "24.50", "stock": 3},
                                             {"id": 3, "name": "bolt", "price": "0.35", "stock": 400}])
            added = client.post("/api/product", json={"name": "Anvil", "price": "120.00", "stock": 1})
            self.assertEqual((added.status_code, added.json()), (201, {"id": 4, "name": "Anvil", "price": "120.00", "stock": 1}))
            refused = [{"name": "x", "price": 0.35, "stock": 1}, {"name": "x", "price": "1", "stock": "1"},
                       {"name": "x", "price": "1", "stock": True}, {"name": "x", "price": "1", "stock": 9007199254740992},
                       {"name": "x", "price": "1"}, {"name": "x", "price": "1", "stock": 1, "id": 9},
                       {"name": 5, "price": "1", "stock": 1}, {"name": "x", "price": "1.", "stock": 1}, [1]]
            for body in refused:
                with self.subTest(body=body):
                    self.assertEqual(client.post("/api/product", json=body).status_code, 422)
            odd = client.post("/api/product", json={"name": "x'); DROP TABLE product;--", "price": "1", "stock": 1})
            self.assertEqual(odd.status_code, 201)
            changed = client.put("/api/product/1", json={"name": "Widget", "price": "10.49", "stock": 11})
            self.assertEqual((changed.status_code, changed.json()["price"]), (200, "10.49"))
            self.assertEqual(client.put("/api/product/999", json={"name": "W", "price": "1", "stock": 1}).status_code, 404)
            self.assertEqual(client.put("/api/product/abc", json={"name": "W", "price": "1", "stock": 1}).status_code, 422)
            self.assertEqual(client.delete("/api/product/2").status_code, 204)
            self.assertEqual(client.delete("/api/product/2").status_code, 404)
            self.assertEqual([record["id"] for record in client.get("/api/product").json()], [1, 3, 4, 5])
            self.assertEqual(client.get("/api/supplier").status_code, 404)  # not exposed
            root = client.get("/")
            self.assertEqual((root.status_code, root.headers["location"]), (307, "/products.html"))
            self.assertIn("<h1>Products</h1>", client.get("/products.html").text)
            self.assertEqual(client.get("/supplier.json").json()[0], {"name": "Acme", "city": "Lima"})
            for hidden in ("/server.py", "/inventory.db", "/product.json", "/requirements.txt", "/../server.py"):
                self.assertEqual(client.get(hidden).status_code, 404, hidden)
            # starting again keeps what was stored and does not add the first records a second time
            again = TestClient(load_server(folder, "generated_server_b").app)
            self.assertEqual([record["id"] for record in again.get("/api/product").json()], [1, 3, 4, 5])

    @unittest.skipUnless(HAVE_FASTAPI, "fastapi and httpx are not installed")
    def test_rules_store_notifications_exactly_when_their_condition_holds(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from fastapi.testclient import TestClient
        with tempfile.TemporaryDirectory() as folder:
            write(folder, without_trace(build(RULES, "html")))
            client = TestClient(load_server(folder, "generated_server_rules_a").app)

            def notes():
                listed = client.get("/api/notification")
                self.assertEqual(listed.status_code, 200)
                return listed.json()

            self.assertEqual(notes(), [])  # the records written in the intent file do not trigger the rules
            # 10.5 is not below 9.99 when compared as a number, though it is when compared as text
            self.assertEqual(client.post("/api/product", json={"name": "lamp", "price": "10.5", "stock": 2}).status_code, 201)
            self.assertEqual(notes(), [])
            self.assertEqual(client.post("/api/product", json={"name": "lamp", "price": "9.9", "stock": 2}).status_code, 201)
            self.assertEqual(client.post("/api/product", json={"name": "bolt", "price": "9.99", "stock": 10}).status_code, 201)
            self.assertEqual(client.post("/api/product", json={"name": "bolt", "price": "9.990", "stock": 9}).status_code, 201)
            # text is compared by code point: capital letters come before small ones
            self.assertEqual(client.post("/api/product", json={"name": "Zinc", "price": "20", "stock": 1}).status_code, 201)
            self.assertEqual(client.post("/api/product", json={"name": "zinc", "price": "20", "stock": 1}).status_code, 201)
            # nothing is stored for a refused record, a change to a record that does not exist, or a deletion
            self.assertEqual(client.post("/api/product", json={"name": "bolt", "price": 1, "stock": 10}).status_code, 422)
            self.assertEqual(client.put("/api/product/99", json={"name": "bolt", "price": "1", "stock": 10}).status_code, 404)
            self.assertEqual(client.delete("/api/product/3").status_code, 204)
            found = notes()
            for note in found:
                self.assertRegex(note.pop("time"), r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
            self.assertEqual(found, [{"id": 1, "recipient": "buyer", "condition": "Product.price < 9.99", "record": 3},
                                     {"id": 2, "recipient": "clerk", "condition": 'Product.name = "bolt" and Product.stock >= 10', "record": 4},
                                     {"id": 3, "recipient": "sorter", "condition": 'Product.name < "b"', "record": 6}])
            # a change is checked against the record as stored after the change
            changed = client.put("/api/product/2", json={"name": "lamp", "price": "-0.01", "stock": 2})
            self.assertEqual(changed.status_code, 200)
            self.assertEqual(client.put("/api/product/2", json={"name": "lamp", "price": "9.99", "stock": 2}).status_code, 200)
            self.assertEqual(client.put("/api/product/4", json={"name": "bolt", "price": "10", "stock": 11}).status_code, 200)
            found = notes()
            self.assertEqual([(note["id"], note["recipient"], note["record"]) for note in found],
                             [(1, "buyer", 3), (2, "clerk", 4), (3, "sorter", 6), (4, "buyer", 2), (5, "clerk", 4)])
            # notifications cannot be added, changed or deleted through the API
            for method, address in (("post", "/api/notification"), ("put", "/api/notification/1"), ("delete", "/api/notification/1"),
                                    ("put", "/api/notification"), ("delete", "/api/notification"), ("patch", "/api/notification/1")):
                with self.subTest(method=method, address=address):
                    reply = getattr(client, method)(address, **({} if method == "delete" else {"json": {"recipient": "x"}}))
                    self.assertIn(reply.status_code, (404, 405))
            self.assertEqual(notes(), found)
            # starting again keeps the notifications, and goes on numbering them
            again = TestClient(load_server(folder, "generated_server_rules_b").app)
            self.assertEqual(again.get("/api/notification").json(), found)
            self.assertEqual(again.post("/api/product", json={"name": "a", "price": "1", "stock": 1}).status_code, 201)
            self.assertEqual([(note["id"], note["recipient"]) for note in again.get("/api/notification").json()[-2:]],
                             [(6, "buyer"), (7, "sorter")])

    @unittest.skipUnless(HAVE_FASTAPI, "fastapi and httpx are not installed")
    def test_values_that_need_care_in_rules(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from fastapi.testclient import TestClient
        with tempfile.TemporaryDirectory() as folder:
            write(folder, without_trace(build(ODD_RULES, "html")))
            client = TestClient(load_server(folder, "generated_server_odd").app)
            odd = 'it\'s "odd" \\ a\u200bb'
            for body in ({"name": odd, "price": "100.00", "stock": 50}, {"name": odd + " ", "price": "100", "stock": 50},
                         {"name": "c", "price": "5.0", "stock": -2}, {"name": "c", "price": "5.0", "stock": -3}):
                self.assertEqual(client.post("/api/product", json=body).status_code, 201)
            found = [(note["recipient"], note["condition"], note["record"]) for note in client.get("/api/notification").json()]
            self.assertEqual(found, [("buyer", 'Product.name = "it\'s \\"odd\\" \\\\ a\u200bb" and Product.price >= 100', 2),
                                     ("buyer", "Product.price < 9.99", 4),
                                     ("clerk", "Product.price != -0.50 and Product.price > 004.5 and Product.stock != -3 and Product.price = 5", 4),
                                     ("buyer", "Product.price < 9.99", 5)])

    @unittest.skipUnless(JS_TOOLS and Path(JS_TOOLS, ".bin", "prettier").exists(), "CDIPL_JS_TOOLS does not hold prettier")
    def test_formatter_makes_no_change_to_the_pages(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = []
            for index, text in enumerate((EXAMPLE, RULES)):
                for name, content in without_trace(build(text, "html")).items():
                    if name.endswith((".html", ".css", ".js", ".json")):
                        path = Path(folder) / f"{index}-{name.replace('/', '-')}"
                        path.write_text(content, encoding="utf-8")
                        paths.append(str(path))
            done = subprocess.run([str(Path(JS_TOOLS, ".bin", "prettier")), "--print-width", "320", "--check", *paths],
                                  capture_output=True, text=True, cwd=folder, check=False)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    @unittest.skipUnless(JS_TOOLS and Path(JS_TOOLS, ".bin", "eslint").exists(), "CDIPL_JS_TOOLS does not hold eslint")
    def test_linter_reports_nothing_on_the_script(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "scripts.js").write_text(build(EXAMPLE, "html")["static/scripts.js"], encoding="utf-8")
            Path(folder, "eslint.config.js").write_text(
                f'const js = require("{JS_TOOLS}/@eslint/js");\nconst globals = require("{JS_TOOLS}/globals");\n'
                'module.exports = [js.configs.recommended, { languageOptions: { sourceType: "script", '
                "ecmaVersion: 2024, globals: globals.browser } }];\n", encoding="utf-8")
            done = subprocess.run([str(Path(JS_TOOLS, ".bin", "eslint")), "-c", "eslint.config.js", "scripts.js"],
                                  capture_output=True, text=True, cwd=folder, check=False)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_the_pages_show_no_words_the_developer_did_not_write(self):
        built = without_trace(build(RULES, "html"))
        words = set(re.findall(r"[A-Za-z]+", "".join(re.sub(r"<[^>]*>", " ", line) for line in built["static/products.html"].split("\n")
                                                     if "<title>" not in line)))
        self.assertEqual(words, {"Products", "Add", "name", "price", "stock"})
        script = built["static/scripts.js"]
        for text in re.findall(r'textContent = "([^"]*)"', script):
            self.assertIn(text, ("✎", "×"))

    @unittest.skipUnless(HAVE_FASTAPI, "fastapi and httpx are not installed")
    def test_a_server_without_a_database_serves_the_pages(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from fastapi.testclient import TestClient
        with tempfile.TemporaryDirectory() as folder:
            write(folder, without_trace(build(PAGES_ONLY, "html")))
            client = TestClient(load_server(folder, "generated_server_c").app)
            self.assertIn("<h1>Welcome</h1>", client.get("/home.html").text)
            self.assertFalse(list(Path(folder).glob("*.db")))


if __name__ == "__main__":
    unittest.main()
