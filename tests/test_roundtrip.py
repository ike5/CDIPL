"""Criteria G3, G5 and C5: round trip, trace, and the same program from English and Spanish."""
import json
import unittest

from cdipl.compiler import build, build_program, lift, lift_text
from cdipl.parser import parse, render
from cdipl.targets import TARGETS

from .support import programs

SAMPLE = programs(120, seed=4242)


class RoundTripTest(unittest.TestCase):
    def test_lift_of_build_is_the_intent_in_standard_phrases(self):
        for index, program in enumerate(SAMPLE):
            for language in ("en", "es"):
                intent = render(program, language)
                for target, generator in TARGETS.items():
                    with self.subTest(program=index, language=language, target=target):
                        text = build(intent, target)[generator.FILE_NAME]
                        self.assertEqual(lift_text(text, target, language), intent)

    def test_build_of_lift_reproduces_the_file(self):
        for index, program in enumerate(SAMPLE):
            for target, generator in TARGETS.items():
                with self.subTest(program=index, target=target):
                    text = build_program(program, target)[generator.FILE_NAME]
                    again = build_program(lift(text, target), target)[generator.FILE_NAME]
                    self.assertEqual(again, text)

    def test_generated_code_holds_no_comments_and_no_copy_of_the_intent(self):
        for index, program in enumerate(SAMPLE[:40]):
            for target, generator in TARGETS.items():
                text = build_program(program, target)[generator.FILE_NAME]
                with self.subTest(program=index, target=target):
                    for line in text.split("\n"):
                        self.assertFalse(line.strip().startswith(("#", "//", "/*", "*")), line)
                    for phrase in ("keep where", "sort by", "group by", "count each group", "write as json",
                                   "conservar donde", "ordenar por"):
                        self.assertNotIn(phrase, text)

    def test_english_and_spanish_build_the_same_program(self):
        pairs = 0
        for index, program in enumerate(SAMPLE):
            english, spanish = render(program, "en"), render(program, "es")
            self.assertNotEqual(english, spanish)
            self.assertEqual(parse(english), parse(spanish))
            for target in TARGETS:
                with self.subTest(program=index, target=target):
                    self.assertEqual(build(english, target), build(spanish, target))
            pairs += 1
        self.assertGreaterEqual(pairs, 100)

    def test_trace_covers_every_line(self):
        for index, program in enumerate(SAMPLE[:60]):
            intent = render(program, "en")
            intent_lines = intent.split("\n")
            for target, generator in TARGETS.items():
                files = build(intent, target)
                lines = files[generator.FILE_NAME].split("\n")[:-1]
                trace = json.loads(files["trace.json"])
                with self.subTest(program=index, target=target):
                    self.assertEqual(len(trace["lines"]), len(lines))
                    known = {entry["block"] for entry in trace["blocks"]} | {"support"}
                    statement_lines = set()
                    for line, origin in zip(lines, trace["lines"]):
                        if isinstance(origin, int):
                            self.assertTrue(intent_lines[origin - 1].strip(), "maps to a blank intent line")
                            statement_lines.add(origin)
                        else:
                            self.assertIn(origin, known, line)
                    statements = {number for number, line in enumerate(intent_lines, start=1)
                                  if line.strip() and number > 2 + len(program.source.fields) + 1}
                    self.assertEqual(statement_lines, statements)


if __name__ == "__main__":
    unittest.main()
