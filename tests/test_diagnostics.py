"""Criterion G7: invalid intent files are rejected with a message naming the line."""
import unittest

from cdipl.model import IntentError
from cdipl.parser import parse

HEAD = "language: en\n\nsource users from \"users.json\":\n    name: text\n    age: integer\n\n"

# (description, intent text, line the message must name)
INVALID = [
    ("empty file", "", 1),
    ("no language line", "source users from \"u.json\":\n    name: text\n\nget users\nshow name\n", 1),
    ("unknown language", "language: fr\n", 1),
    ("no source", "language: en\n\nget users\nshow name\n", 3),
    ("source without fields", "language: en\n\nsource users from \"u.json\":\n\nget users\nshow name\n", 3),
    ("unknown type", "language: en\n\nsource users from \"u.json\":\n    name: string\n\nget users\nshow name\n", 4),
    ("field declared twice", "language: en\n\nsource users from \"u.json\":\n    name: text\n    name: text\n\nget users\nshow name\n", 5),
    ("bad field name", "language: en\n\nsource users from \"u.json\":\n    first-name: text\n\nget users\nshow name\n", 4),
    ("empty path", "language: en\n\nsource users from \"\":\n    name: text\n\nget users\nshow name\n", 3),
    ("argument zero", "language: en\n\nsource users from argument 0:\n    name: text\n\nget users\nshow name\n", 3),
    ("unknown statement", HEAD + "get users\nfrobnicate the rows\nshow name\n", 8),
    ("wrong source name", HEAD + "get people\nshow name\n", 7),
    ("statement before get", HEAD + "limit 3\nget users\nshow name\n", 7),
    ("unknown field in filter", HEAD + "get users\nkeep where height > 3\nshow name\n", 8),
    ("text compared with number", HEAD + "get users\nkeep where name > 3\nshow name\n", 8),
    ("number compared with text", HEAD + "get users\nkeep where age = \"18\"\nshow name\n", 8),
    ("unknown field in sort", HEAD + "get users\nsort by height ascending\nshow name\n", 8),
    ("sort without direction", HEAD + "get users\nsort by name\nshow name\n", 8),
    ("ignoring case on a number", HEAD + "get users\nsort by age ascending ignoring case\nshow name\n", 8),
    ("negative limit", HEAD + "get users\nlimit -1\nshow name\n", 8),
    ("limit not a number", HEAD + "get users\nlimit ten\nshow name\n", 8),
    ("number too large", HEAD + "get users\nkeep where age < 9007199254740992\nshow name\n", 8),
    ("count without group", HEAD + "get users\ncount each group\nshow name\n", 8),
    ("show after group", HEAD + "get users\ngroup by name\nshow name\n", 9),
    ("field gone after count", HEAD + "get users\ngroup by name\ncount each group\nshow age\n", 10),
    ("no output", HEAD + "get users\nlimit 3\n", 8),
    ("statement after output", HEAD + "get users\nshow name\nlimit 3\n", 9),
    ("skip in the wrong place", HEAD + "get users\nlimit 3\nskip invalid records\nshow name\n", 9),
    ("show with no fields", HEAD + "get users\nshow\n", 8),
    ("unterminated text", HEAD + "get users\nif none say \"nothing\nshow name\n", 8),
    ("indented statement", HEAD + "get users\n    limit 3\nshow name\n", 8),
    ("Spanish words in an English file", HEAD + "get users\nlimitar 3\nshow name\n", 8),
    ("English words in a Spanish file", "idioma: es\n\nfuente users desde \"u.json\":\n    name: texto\n\nobtener users\nlimit 3\nmostrar name\n", 7),
]


class DiagnosticsTest(unittest.TestCase):
    def test_every_invalid_file_is_rejected_with_its_line(self):
        self.assertGreaterEqual(len(INVALID), 20)
        for description, text, line in INVALID:
            with self.subTest(description):
                with self.assertRaises(IntentError) as caught:
                    parse(text)
                self.assertEqual(caught.exception.line, line, caught.exception.message)
                self.assertTrue(caught.exception.message)


if __name__ == "__main__":
    unittest.main()
