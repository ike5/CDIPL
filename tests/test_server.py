"""An application with a database and an API: the generated FastAPI server is run for real."""
import importlib.util
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
        self.assertIn('<table data-name="Product" data-source="/api/product">', products)
        self.assertIn('<button type="button" class="width-160" data-add="Product">Add product</button>', products)
        self.assertIn('<label>stock <input name="stock" type="number" step="1" required /></label>', products)
        self.assertIn('<a class="button" href="suppliers.html">Suppliers</a>', products)
        self.assertIn('<table data-name="Supplier" data-source="supplier.json">', files["static/suppliers.html"])
        self.assertIn('@app.post("/api/product", status_code=201)', files["server.py"])
        self.assertNotIn("supplier", files["server.py"])
        self.assertNotIn("sqlite3", build(PAGES_ONLY, "html")["server.py"])

    def test_round_trip_in_both_human_languages(self):
        for text in (EXAMPLE, PAGES_ONLY):
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
            for index, text in enumerate((EXAMPLE, PAGES_ONLY)):
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
