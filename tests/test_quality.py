"""Criterion G6: generated code passes a formatter and a linter with no findings.

Configuration (proposed, awaiting the owner's confirmation):
  Python:     ruff format and ruff check, default rules, line length 320.
  JavaScript: prettier, defaults, print width 320; eslint, recommended rules.
A line length of 320 means the formatters never re-wrap a generated line.

ruff must be installed in the interpreter running the tests. The JavaScript tools are found
through the environment variable CDIPL_JS_TOOLS, which names a node_modules folder holding
prettier, eslint, @eslint/js and globals. A test is skipped when its tool is absent.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cdipl.compiler import build_program
from cdipl.targets import TARGETS

from .support import programs

JS_TOOLS = os.environ.get("CDIPL_JS_TOOLS", "")
SAMPLE = programs(40, seed=5)


def write_sample(folder, target):
    generator = TARGETS[target]
    extension = generator.FILE_NAME.rsplit(".", 1)[1]
    paths = []
    for index, program in enumerate(SAMPLE):
        path = Path(folder) / f"program{index}.{extension}"
        path.write_text(build_program(program, target)[generator.FILE_NAME], encoding="utf-8")
        paths.append(str(path))
    return paths


class QualityTest(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("ruff"), "ruff is not installed")
    def test_python_formatter_and_linter(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = write_sample(folder, "python")
            ruff = [sys.executable, "-m", "ruff"]
            done = subprocess.run(ruff + ["format", "--isolated", "--line-length", "320", "--check", *paths],
                                  capture_output=True, text=True, check=False)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            done = subprocess.run(ruff + ["check", "--isolated", "--line-length", "320", *paths],
                                  capture_output=True, text=True, check=False)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    @unittest.skipUnless(JS_TOOLS and Path(JS_TOOLS, ".bin", "prettier").exists(), "CDIPL_JS_TOOLS does not hold prettier")
    def test_javascript_formatter(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = write_sample(folder, "javascript")
            done = subprocess.run([str(Path(JS_TOOLS, ".bin", "prettier")), "--print-width", "320", "--check", *paths],
                                  capture_output=True, text=True, cwd=folder, check=False)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    @unittest.skipUnless(JS_TOOLS and Path(JS_TOOLS, ".bin", "eslint").exists(), "CDIPL_JS_TOOLS does not hold eslint")
    def test_javascript_linter(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = write_sample(folder, "javascript")
            config = Path(folder) / "eslint.config.js"
            config.write_text(
                f'const js = require("{JS_TOOLS}/@eslint/js");\nconst globals = require("{JS_TOOLS}/globals");\n'
                'module.exports = [js.configs.recommended, { languageOptions: { sourceType: "commonjs", '
                "ecmaVersion: 2024, globals: globals.node } }];\n", encoding="utf-8")
            done = subprocess.run([str(Path(JS_TOOLS, ".bin", "eslint")), "-c", str(config), *paths],
                                  capture_output=True, text=True, cwd=folder, check=False)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
