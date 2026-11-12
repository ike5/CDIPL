"""The live view: every statement is reported, and what is shown matches what a build writes."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from cdipl.compiler import build
from cdipl.live import analyse
from cdipl.targets import TARGETS
from cdipl.live_server import PreviewServer, make_server

from .support import REPO

HEAD = "language: en\n\nsource users from argument 1:\n    name: text\n    age: integer\n\n"
FREE = HEAD + ("get users\ndrop the malformed rows\nonly keep the rows where age >= 18\nsort them by name, highest first\n"
               "frobnicate everything\nkeep just the first 10\n")
OWNERS = '''language: en

use web

app Inventory:

    data Product:
        name: text
        price: decimal
        stock: integer

    expose Product as api

    page Products:
        table Product
        searchable by name
        editable

    when Product.stock < 5:
        notify inventory_manager
'''
OWNERS_BUILT = '''language: en

use sqlite
use FastAPI

app Inventory:
    data Product:
        name: text
        price: decimal
        stock: integer

    expose Product as api

    page Products:
        table Product
        searchable by name
        sortable by price
        editable

    when Product.stock < 5:
        notify inventory_manager
'''
OWNERS_BUILT_ES = '''idioma: es

usar sqlite
usar FastAPI

aplicación Inventory:
    datos Product:
        name: texto
        price: decimal
        stock: entero

    exponer Product como api

    página Products:
        tabla Product
        editable
        notificaciones

    cuando   Product.stock<5   y Product.price >= 1.50 :
        notificar inventory_manager
'''


def text_of(result, name):
    return "\n".join(line["text"] for file in result["files"] if file["name"] == name for line in file["lines"]) + "\n"


class LiveTest(unittest.TestCase):
    def test_every_statement_is_reported_and_one_problem_does_not_hide_the_rest(self):
        result = analyse(FREE, "python")
        by_text = {statement["text"]: statement for statement in result["statements"]}
        self.assertEqual(by_text["get users"]["status"], "standard")
        self.assertEqual(by_text["drop the malformed rows"]["reading"], "skip invalid records")
        self.assertEqual(by_text["only keep the rows where age >= 18"]["reading"], "keep where age >= 18")
        self.assertEqual(by_text["sort them by name, highest first"]["reading"], "sort by name descending")
        self.assertEqual(by_text["frobnicate everything"]["status"], "error")
        self.assertIn("frobnicate", by_text["frobnicate everything"]["note"])
        self.assertTrue(by_text["frobnicate everything"]["alternatives"])
        self.assertEqual(by_text["keep just the first 10"]["reading"], "limit 10")
        self.assertFalse(result["complete"])
        self.assertIsNone(result["canonical"])
        code = text_of(result, "main.py")
        self.assertIn("rows = rows[:10]", code)  # the statement after the problem is still shown

    def test_each_statement_maps_to_its_own_lines(self):
        result = analyse(FREE, "javascript")
        lines = result["files"][0]["lines"]
        by_text = {statement["text"]: statement["line"] for statement in result["statements"]}
        mine = [line["text"].strip() for line in lines if line["origin"] == by_text["only keep the rows where age >= 18"]]
        self.assertEqual(mine, ["rows = rows.filter((row) => row.age >= 18);"])
        self.assertEqual([line for line in lines if line["origin"] == by_text["frobnicate everything"]], [])

    def test_a_complete_file_shows_exactly_what_build_writes(self):
        for example, targets in (("adult_users.intent", tuple(TARGETS)), ("inventory.intent", ("html",))):
            text = (REPO / "examples" / example).read_text(encoding="utf-8")
            for target in targets:
                with self.subTest(example=example, target=target):
                    result = analyse(text, target)
                    self.assertTrue(result["complete"])
                    self.assertEqual(result["canonical"], text)
                    built = build(text, target)
                    for file in result["files"]:
                        self.assertEqual(text_of(result, file["name"]), built[file["name"]])

    def test_unfinished_file_is_shown_but_not_complete(self):
        result = analyse(HEAD + "get users\nlimit 3\n", "python")
        self.assertFalse(result["complete"])
        self.assertIn("produces no output", result["problems"][0]["message"])
        self.assertIn("rows = rows[:3]", text_of(result, "main.py"))

    def test_the_owners_pseudocode(self):
        result = analyse(OWNERS)
        statements = {statement["text"]: statement for statement in result["statements"]}
        status = {text: statement["status"] for text, statement in statements.items()}
        self.assertEqual(status["table Product"], "standard")
        self.assertEqual(status["use web"], "unbuilt")
        self.assertEqual(status["expose Product as api"], "error")  # it needs 'use sqlite' and 'use FastAPI'
        # without an API, the table cannot be edited and the rule cannot be applied: each line says so
        for line in ("editable", "when Product.stock < 5:", "notify inventory_manager"):
            self.assertEqual(status[line], "error", line)
            self.assertIn("exposed as an API", statements[line]["note"])
        self.assertEqual(status["searchable by name"], "standard")
        self.assertEqual(result["kind"], "app")
        self.assertIn('<table data-name="Product">', text_of(result, "products.html"))
        self.assertEqual(result["preview"], "products.html")
        self.assertFalse(result["complete"])

    def test_the_owners_pseudocode_with_a_database_and_a_framework(self):
        text = OWNERS_BUILT  # exactly the owner's pseudocode, after the line that names the language
        result = analyse(text)
        self.assertTrue(result["complete"], result["problems"])
        self.assertEqual(result["canonical"], text)
        built = build(text, "html")
        self.assertEqual(sorted(file["name"] for file in result["files"]), sorted(name for name in built if name != "trace.json"))
        for file in result["files"]:
            self.assertEqual(text_of(result, file["name"]), built[file["name"]])
        statements = {statement["text"]: statement for statement in result["statements"]}
        blocks = {text: [block["block"] for block in statement["blocks"]] for text, statement in statements.items()}
        self.assertEqual(blocks["editable"], ["edit-table-rows", "add-record-form"])
        self.assertEqual(blocks["when Product.stock < 5:"], ["notify-when"])
        self.assertEqual(blocks["notify inventory_manager"], ["notify-when"])
        for line in ("editable", "when Product.stock < 5:", "notify inventory_manager"):
            self.assertEqual(statements[line]["status"], "standard", line)
            self.assertEqual(statements[line]["reading"], line)
        rule = statements["when Product.stock < 5:"]["line"]
        mine = [line["text"].strip() for file in result["files"] if file["name"] == "server.py" for line in file["lines"]
                if line["origin"] == rule]
        self.assertEqual(mine, ['def product_rules(connection, record_id, record):', 'if record["stock"] < 5:'])
        # the same in Spanish, and freely spaced: read in standard phrases
        spanish = analyse(OWNERS_BUILT_ES)
        self.assertTrue(spanish["complete"], spanish["problems"])
        readings = [statement["reading"] for statement in spanish["statements"]]
        self.assertIn("cuando Product.stock < 5 y Product.price >= 1.50:", readings)
        self.assertIn("notificar inventory_manager", readings)
        listed = next(statement for statement in spanish["statements"] if statement["text"] == "notificaciones")
        self.assertEqual(([block["block"] for block in listed["blocks"]], listed["status"]), (["render-list"], "standard"))
        self.assertIn("<ul data-notifications></ul>", text_of(spanish, "static/products.html"))

    def test_a_broken_rule_does_not_hide_the_rest(self):
        text = OWNERS_BUILT + "\n    when Product.colour < 5:\n        notify nobody\n\n    when Product.stock >> 5:\n        notify nobody\n"
        result = analyse(text)
        statements = {statement["text"]: statement for statement in result["statements"]}
        self.assertFalse(result["complete"])
        self.assertEqual(statements["when Product.stock >> 5:"]["status"], "error")
        self.assertIn("expected a condition", statements["when Product.stock >> 5:"]["note"])
        self.assertEqual(statements["when Product.colour < 5:"]["status"], "error")
        self.assertEqual(statements["when Product.stock < 5:"]["status"], "standard")
        self.assertEqual(statements["editable"]["status"], "standard")
        server = text_of(result, "server.py")
        self.assertIn('notify(connection, "inventory_manager", "Product.stock < 5", record_id)', server)
        self.assertNotIn("nobody", server)
        self.assertIn("data-editable", text_of(result, "static/products.html"))

    def test_stack_keywords_are_understood_but_not_built(self):
        text = "language: en\n\nuse sqlite\nuse FastAPI\ncreate postgres:\n    using docker\n\napp A:\n    page P:\n        heading \"Hi\"\n"
        result = analyse(text)
        status = {statement["text"]: statement["status"] for statement in result["statements"]}
        for line in ("create postgres:", "using docker"):
            self.assertEqual(status[line], "unbuilt", line)
        self.assertEqual(status["use FastAPI"], "standard")
        self.assertEqual(status["use sqlite"], "error")  # nothing is exposed, so nothing uses the database
        self.assertIn("<h1>Hi</h1>", text_of(result, "static/p.html"))
        self.assertIn("FastAPI(", text_of(result, "server.py"))

    def test_an_application_with_an_api(self):
        text = (REPO / "examples" / "inventory_server.intent").read_text(encoding="utf-8")
        result = analyse(text)
        self.assertTrue(result["complete"])
        self.assertEqual(result["canonical"], text)
        self.assertEqual(result["preview"], "static/products.html")
        self.assertIn("imitates", result["preview_note"])
        built = build(text, "html")
        for file in result["files"]:
            self.assertEqual(text_of(result, file["name"]), built[file["name"]])
        expose = next(s for s in result["statements"] if s["text"] == "expose Product as api")
        mine = [line["text"] for file in result["files"] if file["name"] == "server.py" for line in file["lines"]
                if line["origin"] == expose["line"]]
        self.assertIn('@app.get("/api/product")', mine)

    def test_resizing_a_button_shows_the_change_at_once(self):
        text = (REPO / "examples" / "inventory.intent").read_text(encoding="utf-8") + "        increase button size by 40px\n"
        result = analyse(text)
        self.assertTrue(result["complete"])
        self.assertIn('class="width-200"', text_of(result, "products.html"))
        self.assertIn('button "Add product" width 200px', result["canonical"])
        self.assertNotIn("increase", result["canonical"])
        command = result["statements"][-1]
        button = next(s for s in result["statements"] if s["text"].startswith("button"))
        self.assertEqual(command["shows"], button["line"])

    def test_free_wording_on_a_page(self):
        head = "language: en\n\napp Shop:\n    data Product:\n        name: text\n        price: decimal\n\n    page Products:\n"
        free = head + ('        add a big title that says "Products"\n        show a table of Product\n'
                       "        let people sort the table by clicking the price column\n"
                       '        put a button labelled "Add product" 160px wide\n        make the button 40px wider\n')
        result = analyse(free)
        self.assertTrue(result["complete"])
        standard = head + ('        heading "Products"\n        table Product\n        sortable by price\n'
                           '        button "Add product" width 200px\n')
        self.assertEqual(result["canonical"], standard)
        self.assertEqual(analyse(standard)["files"], [dict(file, lines=[dict(line, origin=line["origin"]) for line in file["lines"]])
                                                      for file in analyse(standard)["files"]])
        statuses = {statement["text"]: statement["status"] for statement in result["statements"]}
        self.assertIn(statuses['add a big title that says "Products"'], ("sure", "unsure"))
        spanish = ("idioma: es\n\naplicación Shop:\n    datos Product:\n        name: texto\n        price: decimal\n\n"
                   "    página Products:\n" '        pon un título grande que diga "Products"\n        muestra una tabla de Product\n'
                   '        añade un botón con el texto "Add product" de 160px de ancho\n        ensancha el botón 40px\n')
        result = analyse(spanish)
        self.assertTrue(result["complete"])
        self.assertIn('botón "Add product" ancho 200px', result["canonical"])
        unknown = analyse(head + "        add a carousel of Product\n        table Product\n")
        problem = next(s for s in unknown["statements"] if "carousel" in s["text"])
        self.assertEqual(problem["status"], "error")
        self.assertIn("carousel", problem["note"])

    def test_problems_before_anything_can_be_read(self):
        for text in ("", "get users\n", "language: en\n\nsource users\n"):
            result = analyse(text, "python")
            self.assertFalse(result["complete"])
            self.assertTrue(result["problems"])

    def test_server_serves_the_page_and_refuses_posts_without_its_token(self):
        with tempfile.TemporaryDirectory() as folder:
            intent = Path(folder) / "demo.intent"
            intent.write_text(HEAD + "get users\nshow name\n", encoding="utf-8")
            server = make_server(intent, port=0)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            try:
                page = opener.open(base + "/").read().decode("utf-8")
                token = page.split('const token = "')[1].split('"')[0]
                self.assertEqual(json.loads(opener.open(base + "/file").read())["name"], "demo.intent")

                def post(path, body, headers):
                    request = urllib.request.Request(base + path, json.dumps(body).encode(), {"Content-Type": "application/json", **headers})
                    return json.loads(opener.open(request).read())

                with self.assertRaises(urllib.error.HTTPError) as refused:
                    post("/save", {"text": "overwritten"}, {})
                self.assertEqual(refused.exception.code, 403)
                refused.exception.close()
                self.assertIn("get users", intent.read_text(encoding="utf-8"))
                free = HEAD + "get users\ndisplay name and age in aligned columns\n"
                result = post("/analyse", {"text": free, "target": "python"}, {"X-CDIPL-Token": token})
                self.assertTrue(result["complete"])
                with self.assertRaises(urllib.error.HTTPError) as missing:
                    opener.open(base + "/preview/wrong-token/main.py")
                missing.exception.close()
                shown = opener.open(f"{base}/preview/{token}/main.py").read().decode("utf-8")
                self.assertIn("show_table(rows", shown)
                saved = post("/save", {"text": free, "target": "python"}, {"X-CDIPL-Token": token})
                self.assertTrue(saved["accepted"])
                self.assertEqual(intent.read_text(encoding="utf-8"), HEAD + "get users\nshow name, age\n")
                unfinished = post("/save", {"text": HEAD + "get users\n", "target": "python"}, {"X-CDIPL-Token": token})
                self.assertFalse(unfinished["accepted"])
                self.assertEqual(intent.read_text(encoding="utf-8"), HEAD + "get users\n")
            finally:
                server.shutdown()
                server.server_close()


class LivePreviewTest(unittest.TestCase):
    @unittest.skipUnless(PreviewServer.available(), "fastapi and uvicorn are not installed")
    def test_the_preview_of_an_application_is_its_real_server(self):
        text = (REPO / "examples" / "inventory_server.intent").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as folder:
            intent = Path(folder) / "inventory.intent"
            intent.write_text(text, encoding="utf-8")
            server = make_server(intent, port=0)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            try:
                token = opener.open(base + "/").read().decode("utf-8").split('const token = "')[1].split('"')[0]

                def analyse_text(body):
                    request = urllib.request.Request(base + "/analyse", json.dumps({"text": body}).encode(),
                                                     {"Content-Type": "application/json", "X-CDIPL-Token": token})
                    return json.loads(opener.open(request).read())

                result = analyse_text(text)
                address = result["preview_url"]
                self.assertTrue(address.endswith("/products.html"))
                self.assertIn("generated server", result["preview_note"])
                root = address.rsplit("/", 1)[0]
                self.assertIn("<h1>Products</h1>", opener.open(address).read().decode("utf-8"))
                first = json.loads(opener.open(root + "/api/product").read())
                self.assertEqual(first[0]["name"], "Widget")
                # a change to a page does not restart the server; a change to the records starts it afresh
                same = analyse_text(text.replace('heading "Products"', 'heading "Stock"'))
                self.assertEqual(same["preview_url"].rsplit("/", 1)[0], root)
                self.assertIn("<h1>Stock</h1>", opener.open(same["preview_url"]).read().decode("utf-8"))
                again = analyse_text(text.replace('"Widget", 9.99, 12', '"Sprocket", 1.50, 7'))
                listed = json.loads(opener.open(again["preview_url"].rsplit("/", 1)[0] + "/api/product").read())
                self.assertEqual(listed[0]["name"], "Sprocket")
            finally:
                server.preview.stop()
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
