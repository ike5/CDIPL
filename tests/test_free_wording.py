"""Criteria C3 and C4, and the rules around the classifier, tested with a small made-up word list.

These tests do not use the real word lists or the real classifier, so they test the machinery
(index, declining, unknown words, the developer's own choice) and not how good the classifier is.
"""
import unittest

from cdipl import classifier
from cdipl.compiler import build_with_index
from cdipl.languages import PHRASES
from cdipl.model import IntentError, compare
from cdipl.parser import parse, render
from cdipl.resolve import Resolver, empty_index
from cdipl.words import WordList

from .support import programs

ENGLISH = WordList("en", [
    ("sort", "sort"), ("order", "sort"), ("arrange", "sort"), ("descending", "descending"), ("highest first", "descending"),
    ("ascending", "ascending"), ("a to z", "ascending"), ("by", "-"), ("the", "-"), ("please", "-"), ("them", "-"),
    ("keep", "keep"), ("only", "keep"), ("where", "-"), ("take", "take"), ("first", "take"), ("top", "take"),
    ("group", "group"), ("count", "count"), ("each", "-"), ("show", "show"), ("display", "show"), ("write", "write"),
    ("output", "write"), ("json", "json"), ("as", "-"), ("skip", "skip"), ("ignore", "skip"), ("invalid", "invalid"),
    ("broken", "invalid"), ("rows", "record"), ("if", "-"), ("there", "-"), ("are", "-"), ("none", "empty"),
    ("say", "say"), ("work out", "calculate"), ("checksum", "hash"), ("file", "file"), ("compute", "-"), ("of", "-"), ("a", "-"), ("and", "and"),
])
SPANISH = WordList("es", [
    ("ordenar", "sort"), ("ordena", "sort"), ("descendente", "descending"), ("de mayor a menor", "descending"),
    ("ascendente", "ascending"), ("por", "-"), ("los", "-"), ("las", "-"), ("conservar", "keep"), ("solo", "keep"),
    ("donde", "-"), ("tomar", "take"), ("primeros", "take"), ("agrupar", "group"), ("contar", "count"), ("cada", "-"),
    ("grupo", "group"), ("mostrar", "show"), ("muestra", "show"), ("escribir", "write"), ("json", "json"),
    ("como", "-"), ("omitir", "skip"), ("inválidas", "invalid"), ("filas", "record"), ("si", "-"), ("no", "-"),
    ("hay", "-"), ("ninguno", "empty"), ("decir", "say"),
])
BLOCKS = ["sort-rows", "filter-rows", "take-first", "group-by-key", "count-values", "print-table", "format-json",
          "drop-invalid-rows", "print-message", "hash-file", "calculate"]
TRAINING = [
    ("sort-rows", ["sort", "<name>", "descending"]), ("sort-rows", ["sort", "<name>", "ascending"]),
    ("filter-rows", ["keep", "<name>", "<comparison>", "<number>"]), ("filter-rows", ["keep", "<name>", "<comparison>", "<text>"]),
    ("take-first", ["take", "<number>"]), ("take-first", ["take", "<number>", "record"]),
    ("group-by-key", ["group", "<name>"]), ("count-values", ["count", "group"]),
    ("print-table", ["show", "<name>", "<name>"]), ("print-table", ["show", "<name>"]),
    ("format-json", ["write", "json"]), ("drop-invalid-rows", ["skip", "invalid", "record"]),
    ("print-message", ["empty", "say", "<text>"]), ("hash-file", ["hash", "file"]),
    ("calculate", ["calculate", "<newname>", "<comparison>", "<name>", "<arithmetic>", "<number>"]),
    ("filter-rows", ["keep", "<name>", "<arithmetic>", "<name>", "<comparison>", "<number>"]),
]
MODEL = classifier.Classifier(classifier.make_model(classifier.train(TRAINING, BLOCKS), BLOCKS, threshold=500))
LISTS = {"en": ENGLISH, "es": SPANISH}

HEAD = "language: en\n\nsource users from argument 1:\n    name: text\n    age: integer\n\nget users\n"
FREE = HEAD + ('ignore the broken rows\nonly keep age >= 18\nplease arrange them by name, highest first\ntop 10\n'
               'if there are none say "Nobody."\ndisplay name, age\n')
STANDARD = HEAD + ('skip invalid records\nkeep where age >= 18\nsort by name descending\nlimit 10\n'
                   'if none say "Nobody."\nshow name, age\n')
SPANISH_HEAD = "idioma: es\n\nfuente users desde argumento 1:\n    name: texto\n    age: entero\n\nobtener users\n"
SPANISH_FREE = SPANISH_HEAD + ('omitir las filas inválidas\nsolo conservar age >= 18\nordena por name de mayor a menor\n'
                               'tomar los primeros 10\nsi no hay ninguno decir "Nobody."\nmuestra name, age\n')


class Forbidden:
    """A classifier that must not be consulted."""
    version = "forbidden"

    def choose(self, features):
        raise AssertionError("the classifier was consulted although the index was complete")


def build_free(text, index=None, model=MODEL):
    language = "es" if text.startswith("idioma") else "en"
    return build_with_index(text, "python", index, classifier=model, word_list=LISTS[language])


class FreeWordingTest(unittest.TestCase):
    def test_free_wording_builds_the_same_program_as_standard_phrases(self):
        self.assertEqual(build_free(FREE)[0], build_free(STANDARD)[0])
        self.assertEqual(len(build_free(FREE)[1]["statements"]), 6)
        self.assertEqual(build_free(STANDARD)[1]["statements"], {})

    def test_english_and_spanish_free_wording_build_the_same_program(self):
        self.assertEqual(build_free(SPANISH_FREE)[0], build_free(FREE)[0])

    def test_standard_phrases_never_reach_the_classifier(self):
        for index, program in enumerate(programs(60, seed=11)):
            for language in PHRASES:
                with self.subTest(program=index, language=language):
                    resolver = Resolver(language, classifier=Forbidden(), word_list=LISTS[language])
                    self.assertEqual(parse(render(program, language), resolver), program)

    def test_a_complete_index_is_used_without_the_classifier(self):
        files, index = build_free(FREE)
        again, index_again = build_free(FREE, index, model=Forbidden())
        self.assertEqual(again, files)
        self.assertEqual(index_again["statements"], index["statements"])

    def test_a_different_classifier_does_not_change_indexed_statements(self):
        files, index = build_free(FREE)
        shuffled = [("sort-rows" if block == "print-table" else "print-table" if block == "sort-rows" else block, features)
                    for block, features in TRAINING]
        other = classifier.Classifier(classifier.make_model(classifier.train(shuffled, BLOCKS), BLOCKS, threshold=500))
        self.assertNotEqual(other.version, MODEL.version)
        with self.assertRaises(IntentError):
            build_free(FREE, None, model=other)  # without the index this classifier reads the file differently
        self.assertEqual(build_free(FREE, index, model=other)[0], files)

    def test_deleting_the_index_recreates_it_identically(self):
        first = build_free(FREE)[1]
        second = build_free(FREE, empty_index())[1]
        self.assertEqual(first, second)
        self.assertEqual(first["classifier"], MODEL.version)

    def test_unknown_word_is_reported_and_nothing_is_guessed(self):
        with self.assertRaises(IntentError) as caught:
            build_free(HEAD + "frobnicate by name descending\nshow name\n")
        self.assertEqual(caught.exception.line, 8)
        self.assertIn("frobnicate", caught.exception.message)

    def test_classifier_declines_when_candidates_are_close(self):
        with self.assertRaises(IntentError) as caught:
            build_free(HEAD + "display json\nshow name\n")
        self.assertEqual(caught.exception.line, 8)
        self.assertIn("closest", caught.exception.message)

    def test_a_block_that_is_not_built_is_reported(self):
        with self.assertRaises(IntentError) as caught:
            build_free(HEAD + "compute a checksum of the file\nshow name\n")
        self.assertIn("hash-file", caught.exception.message)
        self.assertIn("not built yet", caught.exception.message)

    def test_the_developers_choice_overrides_the_classifier_and_unknown_words(self):
        text = HEAD + "frobnicate by name descending\nshow name\n"
        index = {"classifier": "", "statements": {"frobnicate by name descending": {"block": "sort-rows", "by": "developer"}}}
        files, new_index = build_free(text, index, model=Forbidden())
        self.assertEqual(files, build_free(HEAD + "sort by name descending\nshow name\n")[0])
        self.assertEqual(new_index["statements"]["frobnicate by name descending"]["by"], "developer")

    def test_values_are_never_altered_by_wording(self):
        text = HEAD + 'only keep age >= 18 and name != "the top"\nplease arrange them by name, a to z\ndisplay name\n'
        program = parse(text, Resolver("en", classifier=MODEL, word_list=ENGLISH))
        conditions = program.steps[1].conditions
        self.assertEqual(conditions, (compare("age", ">=", 18), compare("name", "!=", "the top")))

    def test_formulas_in_free_wording(self):
        free = HEAD + 'work out double = age * 2 + 1\nonly keep double - age > 20 and name & "!" != "x!"\ndisplay name, double\n'
        standard = HEAD + 'add double = age * 2 + 1\nkeep where double - age > 20 and name & "!" != "x!"\nshow name, double\n'
        self.assertEqual(build_free(free)[0], build_free(standard)[0])

    def test_missing_or_contradictory_values_are_reported(self):
        for statement, expected in (("sort by name", "ascending or descending"),
                                    ("sort by name, ascending descending", "ascending or descending"),
                                    ("only keep age", "field, a comparison and a value"),
                                    ("top", "number of rows"),
                                    ("display", "fields to show"),
                                    ('say "hello"', "no rows")):
            with self.subTest(statement):
                with self.assertRaises(IntentError) as caught:
                    build_free(HEAD + statement + "\nshow name\n")
                self.assertIn(expected, caught.exception.message)


if __name__ == "__main__":
    unittest.main()
