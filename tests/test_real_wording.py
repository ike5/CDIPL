"""Checks on the real word lists and the trained classifier, and criterion C5 for free wording.

The pairs below were written by the assistant after the word lists existed. They are not a
measure of how good the classifier is (see stage2/classifier_result.md for that); they check
that whenever an English statement and its Spanish counterpart are both accepted, they build
the same program, and they record how often that happens.
"""
import csv
import json
import unittest
from pathlib import Path

from cdipl import classifier, library, slots
from cdipl.compiler import build_with_index
from cdipl.model import IntentError

from .support import REPO

HEAD = {"en": "language: en\n\nsource users from argument 1:\n    name: text\n    age: integer\n    city: text\n\nget users\n",
        "es": "idioma: es\n\nfuente users desde argumento 1:\n    name: texto\n    age: entero\n    city: texto\n\nobtener users\n"}
TAIL = {"en": "write as json\n", "es": "escribir como json\n"}
GROUP = {"en": "group by city\n", "es": "agrupar por city\n"}

# (block meant, English statement, Spanish statement, needs a group before it, is the last statement)
PAIRS = [
    ("drop-invalid-rows", "leave out the invalid records", "omite los registros inválidos", False, False),
    ("drop-invalid-rows", "drop the malformed rows", "descarta las filas mal formadas", False, False),
    ("drop-invalid-rows", "skip records that are not valid", "sáltate los registros que no sean válidos", False, False),
    ("filter-rows", "only keep the rows where age >= 18", "conserva solo las filas donde age >= 18", False, False),
    ("filter-rows", 'filter users where city = "Lima" and age < 65', 'filtra los users donde city = "Lima" y age < 65', False, False),
    ("filter-rows", "keep those with age > 30", "quédate con los que tengan age > 30", False, False),
    ("filter-rows", "keep the rows where age * 2 > 50", "conserva las filas donde age * 2 > 50", False, False),
    ("sort-rows", "order the rows by name in ascending order", "ordena las filas por name en orden ascendente", False, False),
    ("sort-rows", "sort users by age, highest first", "ordena los users por age de mayor a menor", False, False),
    ("sort-rows", "arrange them by city from a to z", "ordénalos por city de la a a la z", False, False),
    ("sort-rows", "sort the rows by name in descending order", "ordena las filas por name en orden descendente", False, False),
    ("take-first", "keep just the first 10", "quédate solo con los primeros 10", False, False),
    ("take-first", "take the top 5 rows", "toma las 5 primeras filas", False, False),
    ("take-first", "only the first 3 records", "solo los 3 primeros registros", False, False),
    ("take-first", "limit the output to 20 rows", "limita la salida a 20 filas", False, False),
    ("group-by-key", "group the rows by city", "agrupa las filas por city", False, False),
    ("group-by-key", "bucket users by age", "agrupa los users según age", False, False),
    ("group-by-key", "split the rows into groups by city", "divide las filas en grupos por city", False, False),
    ("count-values", "count how many rows are in each group", "cuenta cuántas filas hay en cada grupo", True, False),
    ("count-values", "count the members of every group", "cuenta los miembros de cada grupo", True, False),
    ("count-values", "tally each group", "haz el recuento de cada grupo", True, False),
    ("print-table", "display name and age in aligned columns", "muestra name y age en columnas alineadas", False, True),
    ("print-table", "print a table of name, city", "imprime una tabla con name, city", False, True),
    ("print-table", "show the name and age columns", "muestra las columnas name y age", False, True),
    ("print-table", "list name, age, city side by side", "lista name, age, city en columnas", False, True),
    ("format-json", "output the rows as json", "escribe las filas como json", False, True),
    ("format-json", "print the result as JSON", "imprime el resultado en JSON", False, True),
    ("format-json", "write everything out as json", "escribe todo en formato json", False, True),
    ("print-message", 'if there are none, say "Nobody."', 'si no hay ninguno, di "Nobody."', False, False),
    ("print-message", 'when the list is empty, print "Nobody."', 'cuando la lista esté vacía, imprime "Nobody."', False, False),
    ("calculate", "work out double = age * 2", "calcula double = age * 2", False, False),
    ("calculate", "add a field double = age + 1", "añade un campo double = age + 1", False, False),
]


def intent(language, statement, grouped, last):
    middle = (GROUP[language] if grouped else "") + statement + "\n"
    if grouped is False and statement.split()[0] in ("group", "bucket", "split", "agrupa", "divide"):
        middle += {"en": "count each group\n", "es": "contar cada grupo\n"}[language]
    return HEAD[language] + middle + ("" if last else TAIL[language])


def outcome(language, statement, grouped, last):
    """('built', files, block) or ('refused', message, None)."""
    try:
        files, index = build_with_index(intent(language, statement, grouped, last), "python", None)
    except IntentError as problem:
        return "refused", problem.message, None
    entry = index["statements"].get(" ".join(statement.split()))
    return "built", files, entry["block"] if entry else "standard phrase"


class RealWordingTest(unittest.TestCase):
    def test_word_lists_use_only_known_codes(self):
        with open(REPO / "stage2/wordings/codes.tsv", newline="", encoding="utf-8") as handle:
            codes = {row[0] for row in csv.reader(handle, delimiter="\t")}
        for language in ("en", "es"):
            with open(REPO / f"cdipl/library/words_{language}.tsv", newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle, delimiter="\t", quoting=csv.QUOTE_NONE))[1:]
            forms = [row[0] for row in rows]
            self.assertEqual(len(forms), len(set(forms)), f"{language}: a form is listed twice")
            self.assertTrue(all(len(row) == 2 and (row[1] == "-" or row[1] in codes) for row in rows))
        for options in slots.concepts().values():
            for option in options:
                for code in [option] if isinstance(option, str) else option:
                    if code not in ("and", "y", "e", "case-insensitive", "ignore-case"):
                        self.assertIn(code, codes)

    def test_classifier_file_is_intact(self):
        path = Path(classifier.HERE / "classifier.json")
        model = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(model["blocks"], list(library.catalogue())[:90])  # the page blocks came after training
        rebuilt = classifier.make_model(model["weights"], model["blocks"], model["threshold"])
        self.assertEqual(rebuilt["version"], model["version"])
        self.assertTrue(all(isinstance(weight, int) for row in model["weights"].values() for weight in row))

    def test_english_and_spanish_free_wording_agree_whenever_both_are_accepted(self):
        both = wrong = 0
        for block, english, spanish, grouped, last in PAIRS:
            results = {"en": outcome("en", english, grouped, last), "es": outcome("es", spanish, grouped, last)}
            for status, _, chosen in results.values():
                if status == "built" and chosen not in (block, "standard phrase"):
                    wrong += 1
            if results["en"][0] == results["es"][0] == "built":
                both += 1
                with self.subTest(english=english, spanish=spanish):
                    self.assertEqual(results["en"][1], results["es"][1])
        self.assertEqual(wrong, 0, "a statement was accepted as a block other than the one meant")
        self.assertGreater(both, 0)


if __name__ == "__main__":
    unittest.main()
