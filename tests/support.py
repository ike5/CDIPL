"""Shared helpers for the tests: build programs, run them, and make test material."""
import random
import subprocess
import sys
import tempfile
from pathlib import Path

from cdipl.compiler import build_program
from cdipl.model import Condition, Count, Filter, Group, IfNone, Limit, Program, Read, Show, Sort, Source, WriteJson
from cdipl.targets import TARGETS

REPO = Path(__file__).resolve().parent.parent
RUNNERS = {"python": [sys.executable], "javascript": ["node"]}
FIELDS = (("name", "text"), ("age", "integer"), ("city", "text"))
TEXTS = ["Lima", "m", "", "～", "😀", "Zoe", 'a"b', "back\\slash", "Ñandú", "zoe"]
NUMBERS = [18, 0, -5, 30, 9007199254740991, -9007199254740991, 2]


class Workspace:
    """A temporary folder holding built programs and data files."""

    def __init__(self):
        self._folder = tempfile.TemporaryDirectory()
        self.path = Path(self._folder.name)
        self._count = 0

    def close(self):
        self._folder.cleanup()

    def write_program(self, program, target):
        self._count += 1
        folder = self.path / f"{target}-{self._count}"
        folder.mkdir()
        for name, text in build_program(program, target).items():
            (folder / name).write_text(text, encoding="utf-8")
        return folder / TARGETS[target].FILE_NAME

    def write_data(self, name, data):
        path = self.path / name
        path.write_bytes(data)
        return path


def run(target, program_path, *arguments):
    """Run a generated program. Returns (exit status, output bytes, error category)."""
    done = subprocess.run(RUNNERS[target] + [str(program_path), *map(str, arguments)], capture_output=True, timeout=60, check=False)
    category = ""
    if done.stderr:
        first = done.stderr.decode("utf-8", "replace").split("\n")[0]
        parts = first.split(": ")
        category = parts[1] if parts[0] == "error" and len(parts) > 1 else "unexpected: " + first
    return done.returncode, done.stdout, category


def random_condition(rng, schema):
    name = rng.choice(list(schema))
    op = rng.choice(["=", "!=", "<", "<=", ">", ">="])
    value = rng.choice(TEXTS) if schema[name] == "text" else rng.choice(NUMBERS)
    return Condition(field=name, op=op, value=value)


def random_program(rng, source=None, max_steps=4):
    """A random program whose steps fit together."""
    if source is None:
        source = Source(name="people", path=None, argument=1, fields=FIELDS)
    schema = dict(source.fields)
    steps = [Read(skip_invalid=rng.random() < 0.5)]
    grouped = None
    for _ in range(rng.randint(0, max_steps)):
        if grouped is not None:
            steps.append(Count(field=grouped))
            schema = {grouped: schema[grouped], "count": "integer"}
            grouped = None
            continue
        kind = rng.choice(["filter", "filter", "sort", "sort", "limit", "group"])
        if kind == "filter":
            steps.append(Filter(conditions=tuple(random_condition(rng, schema) for _ in range(rng.randint(1, 2)))))
        elif kind == "sort":
            name = rng.choice(list(schema))
            steps.append(Sort(field=name, descending=rng.random() < 0.5,
                              ignore_case=schema[name] == "text" and rng.random() < 0.4))
        elif kind == "limit":
            steps.append(Limit(count=rng.choice([0, 1, 2, 3, 10, 1000])))
        else:
            candidates = [name for name in schema if name != "count"]
            if not candidates:
                continue
            grouped = rng.choice(candidates)
            steps.append(Group(field=grouped))
    if grouped is not None:
        steps.append(Count(field=grouped))
        schema = {grouped: schema[grouped], "count": "integer"}
    if rng.random() < 0.25:
        steps.append(IfNone(text=rng.choice(["Nothing found.", "Sin resultados", 'none "at all"', "～ 😀"])))
    if rng.random() < 0.5:
        names = list(schema)
        rng.shuffle(names)
        steps.append(Show(fields=tuple(names[: rng.randint(1, len(names))])))
    else:
        steps.append(WriteJson())
    return Program(source=source, steps=tuple(steps))


def programs(count, seed):
    rng = random.Random(seed)
    return [random_program(rng) for _ in range(count)]
