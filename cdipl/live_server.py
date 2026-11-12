"""A local web server for the live view: text on one side, generated files on the other."""
import hashlib
import importlib.util
import json
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .live import analyse

PAGE = Path(__file__).parent / "live_page.html"
STARTER = 'language: en\n\nsource users from argument 1:\n    name: text\n    age: integer\n\nget users\n'


def index_path(intent):
    return intent.with_suffix(".index.json")


class PreviewServer:
    """Runs the generated server of an application, so that the preview is the real thing.

    The generated files are written to a temporary folder and served by uvicorn on this machine only.
    The server is started again, with an empty database, whenever its code or its first records change.
    """

    def __init__(self):
        self.folder = None
        self.process = None
        self.port = None
        self.signature = None

    @staticmethod
    def available():
        return all(importlib.util.find_spec(name) is not None for name in ("fastapi", "uvicorn"))

    def update(self, files):
        """Bring the running server in line with the files. Returns its address, or None if there is none."""
        if "server.py" not in files or not self.available():
            self.stop()
            return None
        if self.folder is None:
            self.folder = tempfile.TemporaryDirectory(prefix="cdipl-preview-")
        root = Path(self.folder.name)
        for name, text in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                path.write_text(text, encoding="utf-8")
        for path in root.rglob("*"):
            relative = path.relative_to(root).as_posix()
            if path.is_file() and relative not in files and path.suffix != ".db" and "__pycache__" not in path.parts:
                path.unlink()
        core = sorted((name, text) for name, text in files.items() if "/" not in name)
        signature = hashlib.sha256(json.dumps(core).encode("utf-8")).hexdigest()
        if signature != self.signature or self.process is None or self.process.poll() is not None:
            self._start(root)
            self.signature = signature
        return f"http://127.0.0.1:{self.port}" if self.process is not None else None

    def _start(self, root):
        self._end_process()
        for database in root.glob("*.db"):
            database.unlink()
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            self.port = probe.getsockname()[1]
        self.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(self.port),
             "--log-level", "warning"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                break
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.2):
                    return
            except OSError:
                time.sleep(0.05)
        self._end_process()

    def _end_process(self):
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

    def stop(self):
        self._end_process()
        self.signature = None
        if self.folder is not None:
            self.folder.cleanup()
            self.folder = None


def make_server(intent_path, port=8765):
    """Create the server. intent_path is the one file the view may read and write."""
    intent = Path(intent_path)
    token = secrets.token_urlsafe(24)
    latest = {}  # the files of the most recent analysis, served to the preview
    kinds = {".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".json": "application/json"}

    preview = PreviewServer()

    def remember(result):
        latest.clear()
        latest.update({file["name"]: "\n".join(line["text"] for line in file["lines"]) + "\n" for file in result["files"]})
        if result.get("kind") == "app":
            address = preview.update(latest)
            if address is not None and result.get("preview"):
                result["preview_url"] = f"{address}/{result['preview'].removeprefix('static/')}"
                result["preview_note"] = ("The preview is the generated server, running on this machine. Its database "
                                          "starts again from the records in the file whenever the data or the API change.")
        return result

    def load_index():
        path = index_path(intent)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, body, kind="application/json", shared=False):
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", f"{kind}; charset=utf-8")
            if shared:  # the preview runs in a sandboxed frame, which counts as another origin
                self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def local(self):
            host = (self.headers.get("Host") or "").split(":")[0]
            return host in ("127.0.0.1", "localhost")

        def do_GET(self):
            if not self.local():
                return self.reply(403, "{}")
            if self.path == "/":
                page = PAGE.read_text(encoding="utf-8").replace("__TOKEN__", token)
                return self.reply(200, page, "text/html")
            prefix = f"/preview/{token}/"
            if self.path.startswith(prefix):
                name = self.path[len(prefix):].split("?")[0]
                if name in latest:
                    return self.reply(200, latest[name], kinds.get(Path(name).suffix, "text/plain"), shared=True)
                return self.reply(404, "{}")
            if self.path.startswith("/api/") and f"{self.path[5:]}.json" in latest | {"": ""}:
                # The preview of an application with an API: list the records written in the intent file.
                seed = json.loads(latest.get(f"{self.path[5:]}.json", "[]"))
                listed = [{"id": number, **record} for number, record in enumerate(seed, start=1)]
                return self.reply(200, json.dumps(listed), shared=True)
            if self.path.startswith("/api/"):
                return self.reply(200, "[]", shared=True)
            if self.path == "/file":
                text = intent.read_text(encoding="utf-8") if intent.exists() else STARTER
                return self.reply(200, json.dumps({"name": intent.name, "text": text}))
            return self.reply(404, "{}")

        def do_POST(self):
            # Only this page may post: it must come from this machine and carry the token the page was given.
            if not self.local() or self.headers.get("X-CDIPL-Token") != token:
                return self.reply(403, "{}")
            length = int(self.headers.get("Content-Length") or 0)
            if length > 2_000_000:
                return self.reply(413, "{}")
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                text = body["text"]
            except (ValueError, KeyError, UnicodeDecodeError):
                return self.reply(400, "{}")
            if self.path == "/analyse":
                return self.reply(200, json.dumps(remember(analyse(text, body.get("target"), load_index()))))
            if self.path == "/save":
                result = remember(analyse(text, body.get("target"), load_index()))
                accepted = result["complete"] and result["canonical"] is not None
                saved = result["canonical"] if accepted else text
                intent.write_text(saved, encoding="utf-8")
                return self.reply(200, json.dumps({"text": saved, "accepted": accepted}))
            return self.reply(404, "{}")

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.preview = preview
    return server


def serve(intent_path, port=8765):
    server = make_server(intent_path, port)
    print(f"Live view for {intent_path}: http://127.0.0.1:{server.server_address[1]}/  (Ctrl+C to stop)")

    def stop(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)  # so that being asked to end also ends the preview server
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.preview.stop()
        server.server_close()
