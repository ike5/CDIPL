"""Criterion G4: for a hand-edited file, lift either returns an intent that regenerates it exactly, or refuses."""
import unittest

from cdipl.compiler import build, build_program, lift
from cdipl.targets import TARGETS
from cdipl.targets.common import NotGenerated

INTENT = '''language: en

source users from "users.json":
    name: text
    age: integer
    city: text

get users
skip invalid records
keep where age >= 18 and city != "Lima"
sort by name ascending ignoring case
limit 10
if none say "Nobody."
show name, age
'''

LIFTED, REFUSED = "lifted", "refused"

# (description, text to find, replacement, expected outcome)
PYTHON_EDITS = [
    ("change a number in a condition", 'row["age"] >= 18', 'row["age"] >= 21', LIFTED),
    ("change a comparison", 'row["age"] >= 18', 'row["age"] > 18', LIFTED),
    ("change a text value", '"Lima"', '"Quito"', LIFTED),
    ("text value with an escaped accent", '"Lima"', '"S\\xe3o Paulo"', LIFTED),
    ("change the limit", "rows[:10]", "rows[:25]", LIFTED),
    ("change the message", '"Nobody.\\n"', '"No one here.\\n"', LIFTED),
    ("change the fields shown", '["name", "age"]', '["age", "name", "city"]', LIFTED),
    ("make the sort descending", 'fold_case(row["name"]))', 'fold_case(row["name"]), reverse=True)', LIFTED),
    ("change the input file", '"users.json"', '"people.json"', LIFTED),
    ("rename the source", 'SOURCE = "users"', 'SOURCE = "people"', LIFTED),
    ("delete the limit step", "    rows = rows[:10]\n", "", LIFTED),
    ("repeat the limit step", "    rows = rows[:10]\n", "    rows = rows[:10]\n    rows = rows[:10]\n", LIFTED),
    ("move the limit before the sort",
     '    rows = sorted(rows, key=lambda row: fold_case(row["name"]))\n    rows = rows[:10]\n',
     '    rows = rows[:10]\n    rows = sorted(rows, key=lambda row: fold_case(row["name"]))\n', LIFTED),
    ("switch to strict reading without its support code", "rows = keep_valid(records)", "rows = require_valid(records)", REFUSED),
    ("add a foreign statement", "    rows = rows[:10]\n", '    rows = rows[:10]\n    print("debug")\n', REFUSED),
    ("add a comment", "def main():\n", "def main():\n    # check this\n", REFUSED),
    ("change support code", "sys.exit(status)", "sys.exit(1)", REFUSED),
    ("arithmetic in a condition", 'row["age"] >= 18', 'row["age"] + 1 >= 18', REFUSED),
    ("join conditions with or", " and row[", " or row[", REFUSED),
    ("negative slice", "rows[:10]", "rows[:-1]", REFUSED),
    ("slice with a start", "rows[:10]", "rows[1:10]", REFUSED),
    ("ignore case on a number field", 'fold_case(row["name"])', 'fold_case(row["age"])', REFUSED),
    ("show a field that does not exist", '["name", "age"]', '["height"]', REFUSED),
    ("change a declared type so a condition no longer fits", '"age": "integer"', '"age": "text"', REFUSED),
    ("message without its line break", '"Nobody.\\n"', '"Nobody."', REFUSED),
    ("line break inside a text value", '"Lima"', '"Li\\nma"', REFUSED),
    ("text value with an unescaped accent", '"Lima"', '"São Paulo"', REFUSED),
    ("trailing space", "    rows = rows[:10]\n", "    rows = rows[:10] \n", REFUSED),
    ("wrap sorted in list", "rows = sorted(", "rows = list(sorted(", REFUSED),
    ("change a constant", "MAX_INTEGER = 9007199254740991", "MAX_INTEGER = 100", REFUSED),
    ("delete the call to main", 'if __name__ == "__main__":\n    main()\n', "", REFUSED),
    ("rename a variable", "    rows = rows[:10]\n", "    result = rows[:10]\n", REFUSED),
]

JAVASCRIPT_EDITS = [
    ("change a number in a condition", "row.age >= 18", "row.age >= 21", LIFTED),
    ("change a comparison", 'row.city !== "Lima"', 'row.city === "Lima"', LIFTED),
    ("change a text value", '"Lima"', '"Quito"', LIFTED),
    ("text value with an escaped accent", '"Lima"', '"S\\u00e3o Paulo"', LIFTED),
    ("change the limit", "rows.slice(0, 10)", "rows.slice(0, 3)", LIFTED),
    ("make the sort descending", "compareText(foldCase(a.name), foldCase(b.name))",
     "compareText(foldCase(b.name), foldCase(a.name))", LIFTED),
    ("sort by another text field", "compareText(foldCase(a.name), foldCase(b.name))",
     "compareText(foldCase(a.city), foldCase(b.city))", LIFTED),
    ("change the fields shown", '["name", "age"]', '["city"]', LIFTED),
    ("change the input file", '"users.json"', '"people.json"', LIFTED),
    ("change the message", '"Nobody.\\n"', '"Nadie.\\n"', LIFTED),
    ("rename the source", 'const SOURCE = "users";', 'const SOURCE = "people";', LIFTED),
    ("delete the limit step", "  rows = rows.slice(0, 10);\n", "", LIFTED),
    ("delete the sort step but leave its support code",
     "  rows = [...rows].sort((a, b) => compareText(foldCase(a.name), foldCase(b.name)));\n", "", REFUSED),
    ("sort fields that do not match", "compareText(foldCase(a.name), foldCase(b.name))",
     "compareText(foldCase(a.name), foldCase(b.city))", REFUSED),
    ("add a foreign statement", "  rows = rows.slice(0, 10);\n", '  rows = rows.slice(0, 10);\n  console.log("debug");\n', REFUSED),
    ("add a comment", "function main() {\n", "function main() {\n  // check this\n", REFUSED),
    ("change support code", "process.exitCode = error.status;", "process.exitCode = 1;", REFUSED),
    ("arithmetic in a condition", "row.age >= 18", "row.age + 1 >= 18", REFUSED),
    ("join conditions with or", " && row.", " || row.", REFUSED),
    ("slice with a start", "rows.slice(0, 10)", "rows.slice(1, 10)", REFUSED),
    ("change let to var", "let rows", "var rows", REFUSED),
    ("remove strict mode", '"use strict";\n', "", REFUSED),
    ("change a declared type so a condition no longer fits", '["age", "integer"]', '["age", "text"]', REFUSED),
    ("message without its line break", '"Nobody.\\n"', '"Nobody."', REFUSED),
    ("text value with an unescaped accent", '"Lima"', '"São Paulo"', REFUSED),
    ("loose equality", 'row.city !== "Lima"', 'row.city != "Lima"', REFUSED),
]


class EditedCodeTest(unittest.TestCase):
    def check(self, target, edits):
        generator = TARGETS[target]
        original = build(INTENT, target)[generator.FILE_NAME]
        outcomes = []
        for description, old, new, expected in edits:
            with self.subTest(target=target, edit=description):
                self.assertEqual(original.count(old), 1, f"'{old}' should occur once in the generated file")
                edited = original.replace(old, new)
                self.assertNotEqual(edited, original)
                try:
                    program = lift(edited, target)
                except NotGenerated:
                    outcome = REFUSED
                else:
                    outcome = LIFTED
                    self.assertEqual(build_program(program, target)[generator.FILE_NAME], edited)
                self.assertEqual(outcome, expected)
                outcomes.append(outcome)
        return outcomes

    def test_edits(self):
        outcomes = self.check("python", PYTHON_EDITS) + self.check("javascript", JAVASCRIPT_EDITS)
        self.assertGreaterEqual(len(outcomes), 30)
        self.assertIn(LIFTED, outcomes)
        self.assertIn(REFUSED, outcomes)

    def test_other_changes_to_the_whole_file(self):
        for target, generator in TARGETS.items():
            original = build(INTENT, target)[generator.FILE_NAME]
            for description, edited in (("no final line break", original[:-1]),
                                        ("Windows line endings", original.replace("\n", "\r\n")),
                                        ("an extra blank line at the end", original + "\n"),
                                        ("an empty file", ""),
                                        ("some other program", "print('hello')\n")):
                with self.subTest(target=target, change=description), self.assertRaises(NotGenerated):
                    lift(edited, target)


if __name__ == "__main__":
    unittest.main()
