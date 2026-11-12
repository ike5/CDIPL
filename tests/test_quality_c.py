"""Criterion G6 for the C target: generated C compiles without warnings and the formatter makes no change.

Configuration (proposed, awaiting the owner's confirmation):
  Compiler:  gcc -std=c11 -Wall -Wextra -Werror -pedantic -O2, and the same flags with clang when it is installed.
  Formatter: clang-format with the style {BasedOnStyle: LLVM, ColumnLimit: 400, AllowShortFunctionsOnASingleLine: None}.
A column limit of 400 means the formatter does not re-wrap generated lines: C is wordier than Python and
JavaScript, and the longest line in 3,000 random programs is 341 characters (246 for Python). A longer
formula would be re-wrapped, as in the other targets.

Each test is skipped, with a message, when its tool is not installed.
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from cdipl.compiler import build, build_program
from cdipl.targets import c

from .support import programs

STYLE = "{BasedOnStyle: LLVM, ColumnLimit: 400, AllowShortFunctionsOnASingleLine: None}"
FLAGS = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic", "-O2"]
HEAD = "language: en\n\nsource people from argument 1:\n    name: text\n    age: integer\n    city: text\n\nget people\n"
# Programs that between them need every piece of support code, besides the random sample.
CRAFTED = [
    HEAD + 'add greeting = "Hello, " & name & "!"\nadd five = 5\nadd label = "x"\nkeep where name < city and greeting != "?"\n'
           'sort by age ascending\nsort by name descending ignoring case\nsort by city ascending\nlimit 3\nwrite as json\n',
    HEAD + "skip invalid records\nkeep where age * 2 - 1 >= 0 - 7 and city = \"Lima\"\ngroup by city\ncount each group\n"
           'if none say "None."\nshow city, count\n',
    'language: en\n\nsource users from "users.json":\n    name: text\n\nget users\nshow name\n',
]
SAMPLE = [build_program(program, "c")["main.c"] for program in programs(40, seed=5)]
SAMPLE += [build(text, "c")["main.c"] for text in CRAFTED]


def write_sample(folder):
    paths = []
    for index, text in enumerate(SAMPLE):
        path = Path(folder) / f"program{index}.c"
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    return paths


class CQualityTest(unittest.TestCase):
    def test_the_sample_uses_every_piece_of_support_code(self):
        for _, _, piece in c.SUPPORT:
            self.assertTrue(any(piece in text for text in SAMPLE), piece.split("\n")[0])

    def compile_all(self, compiler):
        with tempfile.TemporaryDirectory() as folder:
            for path in write_sample(folder):
                done = subprocess.run([compiler, *FLAGS, "-c", "-o", str(path.with_suffix(".o")), str(path)],
                                      capture_output=True, text=True, check=False)
                with self.subTest(compiler=compiler, program=path.name):
                    self.assertEqual(done.returncode, 0, done.stderr)
                    self.assertEqual(done.stderr, "")

    @unittest.skipUnless(shutil.which("gcc"), "gcc is not installed")
    def test_gcc_reports_no_warnings(self):
        self.compile_all("gcc")

    @unittest.skipUnless(shutil.which("clang"), "clang is not installed")
    def test_clang_reports_no_warnings(self):
        self.compile_all("clang")

    @unittest.skipUnless(shutil.which("clang-format"), "clang-format is not installed")
    def test_clang_format_makes_no_change(self):
        with tempfile.TemporaryDirectory() as folder:
            for path in write_sample(folder):
                done = subprocess.run(["clang-format", f"--style={STYLE}", str(path)], capture_output=True, text=True, check=False)
                with self.subTest(program=path.name):
                    self.assertEqual(done.returncode, 0, done.stderr)
                    self.assertEqual(done.stdout, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
