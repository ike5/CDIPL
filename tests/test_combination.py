"""Criterion G2: every chain of up to four blocks either builds and agrees, or is rejected."""
import itertools
import unittest

from cdipl.model import IntentError
from cdipl.parser import parse

from .support import Workspace, run
from .test_equivalence import DATASETS

HEADER = "language: en\n\nsource people from argument 1:\n    name: text\n    age: integer\n    city: text\n\nget people\n"
KINDS = ("filter", "sort", "limit", "group", "count", "add")


def chain_text(kinds):
    """Write a chain as intent, choosing fields that exist wherever the chain is well formed.

    Returns (text, fits): whether the block types fit together.
    """
    fields = {"name": "text", "age": "integer", "city": "text"}
    lines, state, fits, grouped, added = [], "rows", True, "city", 0
    for kind in kinds:
        if kind == "count":
            lines.append("count each group")
            if state != "groups":
                fits = False
            else:
                fields = {grouped: fields[grouped], "count": "integer"}
            state = "rows"
            continue
        if state == "groups":
            fits = False
        number_field = "count" if "count" in fields else "age"
        text_field = next((name for name, kind_ in fields.items() if kind_ == "text"), None)
        if kind == "add":
            added += 1
            lines.append(f"add extra{added} = {number_field} * 2 - 1")
            if state != "groups":
                fields[f"extra{added}"] = "integer"
        elif kind == "filter":
            lines.append(f"keep where {number_field} + 1 >= 2")
        elif kind == "sort":
            lines.append(f"sort by {number_field} descending")
        elif kind == "limit":
            lines.append("limit 4")
        elif kind == "group":
            grouped = text_field or next(name for name in fields if name != "count")
            lines.append(f"group by {grouped}")
            state = "groups"
    if state == "groups":
        fits = False
    return HEADER + "\n".join(lines + ["write as json"]) + "\n", fits


class CombinationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = Workspace()
        cls.data = cls.work.write_data("many.json", DATASETS["many"])

    @classmethod
    def tearDownClass(cls):
        cls.work.close()

    def test_every_chain_of_up_to_four_blocks(self):
        fitting = rejected = 0
        for length in range(5):
            for kinds in itertools.product(KINDS, repeat=length):
                text, fits = chain_text(kinds)
                with self.subTest(chain=" > ".join(kinds)):
                    if not fits:
                        with self.assertRaises(IntentError) as caught:
                            parse(text)
                        message = caught.exception.message
                        self.assertTrue("takes rows" in message or "takes groups" in message
                                        or "produces no output" in message, message)
                        rejected += 1
                        continue
                    program = parse(text)
                    results = [run(target, self.work.write_program(program, target), self.data)
                               for target in ("python", "javascript")]
                    self.assertEqual(results[0], results[1])
                    self.assertEqual(results[0][0], 0, results[0])
                    fitting += 1
        self.assertEqual(fitting + rejected, sum(len(KINDS) ** length for length in range(5)))
        self.assertEqual(fitting, 399)  # chains that end in rows: 1 + 4 + 17 + 72 + 305


if __name__ == "__main__":
    unittest.main()
