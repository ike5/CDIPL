"""Criterion G6 for Java: the generated code compiles with every javac warning turned on, and none is reported.

No formatter for Java is installed, so formatting is not checked; the generator writes one fixed style
(four spaces, braces on the same line, one statement per line). The test is skipped when javac is absent.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from cdipl.compiler import build_program
from cdipl.parser import parse
from cdipl.targets import TARGETS

from .support import REPO, programs

SAMPLE = programs(40, seed=5)
HEADER = "language: en\n\nsource people from argument 1:\n    name: text\n    age: integer\n    city: text\n\nget people\n"
FIXED = [
    'keep where name < "m" and age * 2 - 1 > age + 3\nadd label = name & ", " & city\nsort by label descending ignoring case\nwrite as json\n',
    "skip invalid records\ngroup by city\ncount each group\nsort by count ascending\nlimit 3\nif none say \"None.\"\nshow city, count\n",
]


@unittest.skipUnless(shutil.which("javac"), "javac is not installed")
class JavaQualityTest(unittest.TestCase):
    def test_javac_reports_nothing_with_every_warning_on(self):
        generator = TARGETS["java"]
        sample = SAMPLE + [parse(HEADER + text) for text in FIXED]
        sample.append(parse((REPO / "examples" / "adult_users.intent").read_text(encoding="utf-8")))
        texts = [build_program(program, "java")[generator.FILE_NAME] for program in sample]
        for block, _, piece in generator.SUPPORT:
            self.assertTrue(any(piece.strip() in text for text in texts), f"a piece of {block} is never compiled")
        environment = {name: value for name, value in os.environ.items() if name != "JAVA_TOOL_OPTIONS"}
        with tempfile.TemporaryDirectory() as folder:
            sources = []
            for index, program in enumerate(sample):
                # every program declares the class Main, so each goes in a folder of its own
                path = Path(folder) / f"program{index}" / generator.FILE_NAME
                path.parent.mkdir()
                path.write_text(texts[index], encoding="utf-8")
                sources.append(path)

            def compile_one(path):
                return subprocess.run(["javac", "-Xlint:all", "-Werror", "-encoding", "UTF-8",
                                       "-d", str(path.parent / "classes"), str(path)],
                                      capture_output=True, text=True, env=environment, check=False)

            with ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as pool:
                results = list(pool.map(compile_one, sources))
            for path, done in zip(sources, results):
                with self.subTest(program=path.parent.name):
                    self.assertEqual((done.returncode, done.stdout + done.stderr), (0, ""))


if __name__ == "__main__":
    unittest.main()
