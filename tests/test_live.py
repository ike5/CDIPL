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
from cdipl.live_server import make_server

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
        for example, targets in (("adult_users.intent", ("python", "javascript")), ("inventory.intent", ("html",))):
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
        status = {statement["text"]: statement["status"] for statement in result["statements"]}
        self.assertEqual(status["table Product"], "standard")
        for line in ("use web", "expose Product as api", "editable", "when Product.stock < 5:",
                     "notify inventory_manager"):
            self.assertEqual(status[line], "unbuilt", line)
        self.assertEqual(status["searchable by name"], "standard")
        self.assertEqual(result["kind"], "app")
        self.assertIn('<table data-name="Product">', text_of(result, "products.html"))
        self.assertEqual(result["preview"], "products.html")
        self.assertFalse(result["complete"])

    def test_stack_keywords_are_understood_but_not_built(self):
        text = "language: en\n\nuse sqlite\nuse FastAPI\ncreate postgres:\n    using docker\n\napp A:\n    page P:\n        heading \"Hi\"\n"
        result = analyse(text)
        status = {statement["text"]: statement["status"] for statement in result["statements"]}
        for line in ("use sqlite", "use FastAPI", "create postgres:", "using docker"):
            self.assertEqual(status[line], "unbuilt", line)
        self.assertIn("<h1>Hi</h1>", text_of(result, "p.html"))

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


if __name__ == "__main__":
    unittest.main()
