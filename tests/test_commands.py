"""The commands `new` and `run`, and the starter files `new` writes."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from cdipl import __main__ as cli
from cdipl import pages, starters
from cdipl.compiler import build
from cdipl.parser import parse
from cdipl.targets import TARGETS

from .support import REPO


def cdipl(*args, cwd=None):
    return subprocess.run([sys.executable, "-m", "cdipl", *args], capture_output=True, text=True, cwd=cwd,
                          env={"PYTHONPATH": str(REPO), "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "TMPDIR": tempfile.gettempdir()})


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class NewTest(unittest.TestCase):
    def test_every_starter_builds_in_both_languages(self):
        for kind in starters.KINDS:
            for language in ("en", "es"):
                with self.subTest(kind=kind, language=language), tempfile.TemporaryDirectory() as folder:
                    path = Path(folder) / "start.intent"
                    result = cdipl("new", str(path), "--kind", kind, "--language", language)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(path.read_text(encoding="utf-8").startswith("language: " if language == "en" else "idioma: "))
                    self.assertIn("cdipl run", result.stdout)
                    target = "python" if kind == "program" else "html"
                    out = Path(folder) / "out"
                    built = cdipl("build", str(path), "--target", target, "--out", str(out))
                    self.assertEqual(built.returncode, 0, built.stderr)
                    self.assertTrue(any(out.rglob("trace.json")))

    def test_starters_build_the_same_program_in_both_languages(self):
        self.assertEqual(build(starters.starter("program", "en"), "python"), build(starters.starter("program", "es"), "python"))
        for kind in ("pages", "app"):
            self.assertEqual(pages.parse(starters.starter(kind, "en")).pages, pages.parse(starters.starter(kind, "es")).pages)

    def test_app_starter_has_a_server_and_an_add_button(self):
        files = build(starters.starter("app", "en"), "html")
        self.assertIn("server.py", files)
        self.assertIn("adds Person", starters.starter("app"))

    def test_default_kind_is_program(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "x.intent"
            self.assertEqual(cdipl("new", str(path)).returncode, 0)
            parse(path.read_text(encoding="utf-8"))

    def test_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mine.intent"
            path.write_text("my own work\n", encoding="utf-8")
            result = cdipl("new", str(path))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already exists", result.stderr)
            self.assertEqual(path.read_text(encoding="utf-8"), "my own work\n")

    def test_unknown_kind_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            result = cdipl("new", str(Path(folder) / "x.intent"), "--kind", "game")
            self.assertNotEqual(result.returncode, 0)


class RunTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.dir = Path(self.folder.name)

    def intent(self, kind, name="start.intent"):
        path = self.dir / name
        path.write_text(starters.starter(kind), encoding="utf-8")
        return str(path)

    def test_program_runs_with_its_arguments(self):
        data = self.dir / "people.json"
        data.write_text(json.dumps([{"name": "Zoe", "age": 30}, {"name": "Al", "age": 9}, {"name": "Bo", "age": 20}]), encoding="utf-8")
        result = cdipl("run", self.intent("program"), str(data), cwd=self.dir)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split(), ["Bo", "20", "Zoe", "30"])
        self.assertFalse(list(self.dir.glob("*.py")), "nothing is written beside the intent file")

    def test_program_runs_in_every_target_language(self):
        data = self.dir / "people.json"
        data.write_text(json.dumps([{"name": "Zoe", "age": 30}, {"name": "Al", "age": 9}, {"name": "Bo", "age": 20}]), encoding="utf-8")
        for target in sorted(TARGETS):
            with self.subTest(target=target):
                result = cdipl("run", "--target", target, self.intent("program"), str(data), cwd=self.dir)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.split(), ["Bo", "20", "Zoe", "30"])

    def test_program_exits_with_the_programs_status(self):
        missing = cdipl("run", self.intent("program"), str(self.dir / "absent.json"), cwd=self.dir)
        direct = subprocess.run([sys.executable, "-m", "cdipl", "build", self.intent("program"), "--target", "python", "--out", str(self.dir / "o")],
                                capture_output=True, text=True, env={"PYTHONPATH": str(REPO), "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "TMPDIR": tempfile.gettempdir()})
        expected = subprocess.run([sys.executable, str(self.dir / "o" / "main.py"), str(self.dir / "absent.json")], capture_output=True).returncode
        self.assertEqual(direct.returncode, 0, direct.stderr)
        self.assertNotEqual(expected, 0)
        self.assertEqual(missing.returncode, expected)
        self.assertIn("absent.json", missing.stderr)

    def test_invalid_intent_is_reported_with_its_line(self):
        path = self.dir / "bad.intent"
        path.write_text(starters.starter("program") + "frobnicate\n", encoding="utf-8")
        result = cdipl("run", str(path))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("bad.intent:", result.stderr)

    def test_missing_file_is_reported(self):
        result = cdipl("run", str(self.dir / "nothing.intent"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nothing.intent", result.stderr)

    def run_in_process(self, *argv):
        """Run the command line in this process. Returns (exit status, the message sys.exit was given)."""
        with mock.patch.object(sys, "argv", ["cdipl", *argv]), self.assertRaises(SystemExit) as caught:
            cli.main()
        code = caught.exception.code
        return (1, code) if isinstance(code, str) else (code, "")

    def test_server_application_without_fastapi_explains_how_to_install(self):
        with mock.patch.object(cli, "server_installed", return_value=False), mock.patch.object(cli.subprocess, "run") as started:
            code, message = self.run_in_process("run", self.intent("app"))
        self.assertNotEqual(code, 0)
        self.assertIn('pip install "cdipl[server]"', message)
        started.assert_not_called()

    def test_arguments_are_refused_for_pages(self):
        with mock.patch.object(cli.subprocess, "run") as started:
            code, message = self.run_in_process("run", self.intent("pages"), "extra")
        self.assertNotEqual(code, 0)
        self.assertIn("only to programs", message)
        started.assert_not_called()

    def test_port_is_refused_for_programs(self):
        code, message = self.run_in_process("run", "--port", "9000", self.intent("program"))
        self.assertNotEqual(code, 0)
        self.assertIn("--port", message)

    def test_pages_are_served_on_localhost(self):
        port = free_port()
        process = subprocess.Popen([sys.executable, "-m", "cdipl", "run", self.intent("pages"), "--port", str(port)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   env={"PYTHONPATH": str(REPO), "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "TMPDIR": tempfile.gettempdir()})
        try:
            body = None
            for _ in range(50):
                try:
                    body = urllib.request.urlopen(f"http://127.0.0.1:{port}/people.html", timeout=2).read().decode("utf-8")
                    break
                except (urllib.error.URLError, ConnectionError):
                    time.sleep(0.1)
            self.assertIsNotNone(body, "the page was not served")
            self.assertIn("People", body)
        finally:
            process.terminate()
            process.communicate(timeout=10)


if __name__ == "__main__":
    unittest.main()
