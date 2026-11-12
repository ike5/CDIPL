"""Criterion G4 for Java: a hand-edited Main.java is either lifted to an intent that regenerates it exactly, or refused."""
import unittest

from cdipl.compiler import build, build_program, lift
from cdipl.targets import TARGETS
from cdipl.targets.common import NotGenerated

from .test_edited import INTENT, LIFTED, REFUSED

SORT = 'compareText(foldCase(text(a, "name")), foldCase(text(b, "name")))'
FORMULA = 'plus(times(number(row, "age"), 2), 1)'

# (description, text to find, replacement, expected outcome)
JAVA_EDITS = [
    ("change a number in a condition", 'number(row, "age") >= 18', 'number(row, "age") >= 21', LIFTED),
    ("change a comparison", 'number(row, "age") >= 18', 'number(row, "age") > 18', LIFTED),
    ("change a text value", '"Lima"', '"Quito"', LIFTED),
    ("text value with an escaped accent", '"Lima"', '"S\\u00e3o Paulo"', LIFTED),
    ("text value with an escaped astral character", '"Lima"', '"\\ud83d\\ude00"', LIFTED),
    ("test for equal text instead of different", '!text(row, "city").equals("Lima")', 'text(row, "city").equals("Lima")', LIFTED),
    ("order text instead of testing it", '!text(row, "city").equals("Lima")', 'compareText(text(row, "city"), "Lima") < 0', LIFTED),
    ("change the limit", "limit(10)", "limit(25)", LIFTED),
    ("a limit beyond the range of int", "limit(10)", "limit(9007199254740991L)", LIFTED),
    ("change the message", '"Nobody.\\n"', '"Nadie.\\n"', LIFTED),
    ("change the fields shown", 'showTable(rows, "name", "age");', 'showTable(rows, "age", "name", "city");', LIFTED),
    ("make the sort descending", SORT, 'compareText(foldCase(text(b, "name")), foldCase(text(a, "name")))', LIFTED),
    ("sort by another text field", SORT, 'compareText(foldCase(text(a, "city")), foldCase(text(b, "city")))', LIFTED),
    ("change the input file", '"users.json"', '"people.json"', LIFTED),
    ("rename the source", 'SOURCE = "users";', 'SOURCE = "people";', LIFTED),
    ("delete the limit step", "        rows = rows.stream().limit(10).toList();\n", "", LIFTED),
    ("change a number in a formula", 'times(number(row, "age"), 2)', 'times(number(row, "age"), 3)', LIFTED),
    ("change an operator to one whose support method is absent", FORMULA, 'minus(times(number(row, "age"), 2), 1)', REFUSED),
    ("rename the added field", 'with(row, "double",', 'with(row, "twice",', LIFTED),
    ("remove the range check from a formula", FORMULA, 'times(number(row, "age"), 2) + 1', REFUSED),
    ("multiply without the range check", 'times(number(row, "age"), 2)', 'Math.multiplyExact(number(row, "age"), 2)', REFUSED),
    ("use division in a formula", 'times(number(row, "age"), 2)', 'number(row, "age") / 2', REFUSED),
    ("a large number without its L", "limit(10)", "limit(9007199254740991)", REFUSED),
    ("read a number field as text", 'number(row, "age") >= 18', 'text(row, "age") >= 18', REFUSED),
    ("compare text with !=", '!text(row, "city").equals("Lima")', 'text(row, "city") != "Lima"', REFUSED),
    ("join conditions with or", '>= 18 && !text', '>= 18 || !text', REFUSED),
    ("a field that does not exist", 'number(row, "age") >= 18', 'number(row, "height") >= 18', REFUSED),
    ("add a field that already exists", 'with(row, "double",', 'with(row, "age",', REFUSED),
    ("delete the sort step but leave its support code",
     f"        rows = rows.stream().sorted((a, b) -> {SORT}).toList();\n", "", REFUSED),
    ("sort fields that do not match", SORT, 'compareText(foldCase(text(a, "name")), foldCase(text(b, "city")))', REFUSED),
    ("sort with the reversed comparator", f"(a, b) -> {SORT})", f"(a, b) -> {SORT}).reversed()", REFUSED),
    ("add a foreign statement", "        rows = rows.stream().limit(10).toList();\n",
     '        rows = rows.stream().limit(10).toList();\n        System.out.println("debug");\n', REFUSED),
    ("add a line comment", "    private static void run(String[] args) {\n",
     "    private static void run(String[] args) {\n        // check this\n", REFUSED),
    ("add a block comment", "public final class Main {\n", "/* generated */\npublic final class Main {\n", REFUSED),
    ("change support code", "System.exit(failure.status);", "System.exit(1);", REFUSED),
    ("change a constant", "MAX_INTEGER = 9007199254740991L;", "MAX_INTEGER = 100L;", REFUSED),
    ("change a declared type so a condition no longer fits", '{"age", "integer"}', '{"age", "text"}', REFUSED),
    ("switch to strict reading without its support code", "rows = keepValid(records);", "rows = requireValid(records);", REFUSED),
    ("message without its line break", '"Nobody.\\n"', '"Nobody."', REFUSED),
    ("text value with an unescaped accent", '"Lima"', '"São Paulo"', REFUSED),
    ("a line break written as a unicode escape", '"Lima"', '"Li\\u000ama"', REFUSED),
    ("a quote written as a unicode escape", '"Lima"', '"Li\\u0022ma"', REFUSED),
    ("upper-case hexadecimal digits", '"Lima"', '"S\\u00E3o"', REFUSED),
    ("trailing space", "        rows = rows.stream().limit(10).toList();\n", "        rows = rows.stream().limit(10).toList(); \n", REFUSED),
    ("rename a variable", "        rows = rows.stream().limit(10).toList();\n", "        result = rows.stream().limit(10).toList();\n", REFUSED),
    ("collect instead of toList", "rows.stream().limit(10).toList()", "rows.stream().limit(10).collect(Collectors.toList())", REFUSED),
    ("indent with a tab", "        rows = rows.stream().limit(10).toList();\n", "\trows = rows.stream().limit(10).toList();\n", REFUSED),
    ("a different type for the records", "List<?> records =", "List<Object> records =", REFUSED),
]


class EditedJavaTest(unittest.TestCase):
    def test_edits(self):
        generator = TARGETS["java"]
        original = build(INTENT, "java")[generator.FILE_NAME]
        outcomes = []
        for description, old, new, expected in JAVA_EDITS:
            with self.subTest(edit=description):
                self.assertEqual(original.count(old), 1, f"'{old}' should occur once in the generated file")
                edited = original.replace(old, new)
                self.assertNotEqual(edited, original)
                try:
                    program = lift(edited, "java")
                except NotGenerated:
                    outcome = REFUSED
                else:
                    outcome = LIFTED
                    self.assertEqual(build_program(program, "java")[generator.FILE_NAME], edited)
                self.assertEqual(outcome, expected)
                outcomes.append(outcome)
        self.assertGreaterEqual(len(outcomes), 25)
        self.assertIn(LIFTED, outcomes)
        self.assertIn(REFUSED, outcomes)


if __name__ == "__main__":
    unittest.main()
