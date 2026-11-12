"""Criterion G4 for the C target: a hand-edited C file is either lifted to an intent that regenerates it exactly, or refused."""
import unittest

from cdipl.compiler import build, build_program, lift
from cdipl.targets.common import NotGenerated

from .test_edited import INTENT, LIFTED, REFUSED

SORT = "rows = sort_rows(rows, F_name, compare_folded, ASCENDING);"
LIMIT = "  rows = first_rows(rows, 10);\n"

# (description, text to find, replacement, expected outcome)
C_EDITS = [
    ("change a number in a condition", "row[F_age].number >= 18", "row[F_age].number >= 21", LIFTED),
    ("change a comparison", "row[F_age].number >= 18", "row[F_age].number > 18", LIFTED),
    ("change a text value", 'literal("Lima")', 'literal("Quito")', LIFTED),
    ("text value with an escaped accent", 'literal("Lima")', 'literal("S\\303\\243o Paulo")', LIFTED),
    ("text equality instead of inequality", '!same_text(row[F_city], literal("Lima"))', 'same_text(row[F_city], literal("Lima"))', LIFTED),
    ("swap the two conditions", 'row[F_age].number >= 18 && !same_text(row[F_city], literal("Lima"))',
     '!same_text(row[F_city], literal("Lima")) && row[F_age].number >= 18', LIFTED),
    ("change the limit", "first_rows(rows, 10)", "first_rows(rows, 25)", LIFTED),
    ("change the message", 'literal("Nobody.\\n")', 'literal("No one here.\\n")', LIFTED),
    ("change the fields shown", "2, (const int[]){F_name, F_age}", "3, (const int[]){F_age, F_name, F_city}", LIFTED),
    ("make the sort descending", SORT, SORT.replace("ASCENDING", "DESCENDING"), LIFTED),
    ("sort by another text field", SORT, SORT.replace("F_name", "F_city"), LIFTED),
    ("change the input file", '"users.json"', '"people.json"', LIFTED),
    ("rename the source", 'SOURCE[] = "users"', 'SOURCE[] = "people"', LIFTED),
    ("repeat the limit step", LIMIT, LIMIT + LIMIT, LIFTED),
    ("move the limit before the sort", f"  {SORT}\n{LIMIT}", f"{LIMIT}  {SORT}\n", LIFTED),
    ("change a number in a formula", "row[F_age].number, '*', 2)", "row[F_age].number, '*', 3)", LIFTED),
    ("change an operator in a formula", "'*', 2), '+', 1)", "'*', 2), '-', 1)", LIFTED),
    ("remove the range check from a formula", "calculate(row[F_age].number, '*', 2)", "row[F_age].number * 2", REFUSED),
    ("use division in a formula", "row[F_age].number, '*', 2)", "row[F_age].number, '/', 2)", REFUSED),
    ("add a field that already exists", "add_field(rows, F_double,", "add_field(rows, F_age,", REFUSED),
    ("rename the added field in one place only", "add_field(rows, F_double,", "add_field(rows, F_twice,", REFUSED),
    ("switch to strict reading without its support code", "keep_valid(records);", "require_valid(records);", REFUSED),
    ("delete the limit step but leave its support code", LIMIT, "", REFUSED),
    ("delete the filter step but leave its function", "  rows = filter_rows(rows, keep_1);\n", "", REFUSED),
    ("add a foreign statement", LIMIT, LIMIT + '  puts("debug");\n', REFUSED),
    ("add a line comment", "int main(void) {\n", "int main(void) {\n  // check this\n", REFUSED),
    ("add a block comment", "  return row[F_age]", "  /* adults */ return row[F_age]", REFUSED),
    ("change support code", "  exit(status);", "  exit(1);", REFUSED),
    ("change a constant", "MAX_INTEGER = 9007199254740991;", "MAX_INTEGER = 100;", REFUSED),
    ("write the includes with #", "%:include <stdio.h>", "#include <stdio.h>", REFUSED),
    ("arithmetic in a condition", "row[F_age].number >= 18", "row[F_age].number + 1 >= 18", REFUSED),
    ("join conditions with or", " && !same_text", " || !same_text", REFUSED),
    ("compare text by order instead of sameness", '!same_text(row[F_city], literal("Lima"))',
     'compare_text(row[F_city], literal("Lima")) != 0', REFUSED),
    ("negative limit", "first_rows(rows, 10)", "first_rows(rows, -1)", REFUSED),
    ("ignore case on a number field", SORT, SORT.replace("F_name", "F_age"), REFUSED),
    ("compare text as numbers", SORT, SORT.replace("compare_folded", "compare_numbers"), REFUSED),
    ("show a field that does not exist", "2, (const int[]){F_name, F_age}", "1, (const int[]){F_height}", REFUSED),
    ("wrong number of fields shown", "show_table(rows, 2,", "show_table(rows, 3,", REFUSED),
    ("change a declared type so a condition no longer fits", "{IS_TEXT, IS_INTEGER, IS_TEXT}", "{IS_TEXT, IS_TEXT, IS_TEXT}", REFUSED),
    ("message without its line break", 'literal("Nobody.\\n")', 'literal("Nobody.")', REFUSED),
    ("line break inside a text value", 'literal("Lima")', 'literal("Li\\nma")', REFUSED),
    ("text value with an unescaped accent", 'literal("Lima")', 'literal("São Paulo")', REFUSED),
    ("text value with a hexadecimal escape", 'literal("Lima")', 'literal("\\x4cima")', REFUSED),
    ("trailing space", LIMIT, "  rows = first_rows(rows, 10); \n", REFUSED),
    ("rename a variable", LIMIT, "  Rows result = first_rows(rows, 10);\n", REFUSED),
    ("delete the final return", "  return 0;\n}\n", "}\n", REFUSED),
    ("return a failure status", "  return 0;\n}\n", "  return 1;\n}\n", REFUSED),
]


class EditedCTest(unittest.TestCase):
    def test_edits(self):
        original = build(INTENT, "c")["main.c"]
        outcomes = []
        for description, old, new, expected in C_EDITS:
            with self.subTest(edit=description):
                self.assertEqual(original.count(old), 1, f"'{old}' should occur once in the generated file")
                edited = original.replace(old, new)
                self.assertNotEqual(edited, original)
                try:
                    program = lift(edited, "c")
                except NotGenerated:
                    outcome = REFUSED
                else:
                    outcome = LIFTED
                    self.assertEqual(build_program(program, "c")["main.c"], edited)
                self.assertEqual(outcome, expected)
                outcomes.append(outcome)
        self.assertGreaterEqual(len(outcomes), 25)
        self.assertGreaterEqual(outcomes.count(LIFTED), 10)
        self.assertGreaterEqual(outcomes.count(REFUSED), 15)


if __name__ == "__main__":
    unittest.main()
