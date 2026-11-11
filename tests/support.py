"""Shared helpers for the tests: build programs, run them, and make test material."""
import random
import subprocess
import sys
import tempfile
from pathlib import Path

from cdipl.compiler import build_program
from cdipl.model import (
    Add,
    Arith,
    Concat,
    Condition,
    Count,
    Field,
    Filter,
    Group,
    IfNone,
    Limit,
    Number,
    Program,
    Read,
    Show,
    Sort,
    Source,
    Text,
    WriteJson,
    uses_field,
)
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


def random_formula(rng, schema, kind, depth=0):
    """A random formula of the given type over the fields in force."""
    fields = [name for name, field_kind in schema.items() if field_kind == kind]
    roll = rng.random()
    if depth >= 2 or roll < 0.45 or not fields:
        if fields and rng.random() < 0.6:
            return Field(rng.choice(fields))
        return Text(rng.choice(TEXTS)) if kind == "text" else Number(rng.choice(NUMBERS))
    if kind == "text":
        return Concat(tuple(random_formula(rng, schema, "text", 2) for _ in range(rng.randint(2, 3))))
    return Arith(rng.choice("+-*"), random_formula(rng, schema, "integer", depth + 1),
                 random_formula(rng, schema, "integer", depth + 1))


def random_condition(rng, schema):
    name = rng.choice(list(schema))
    op = rng.choice(["=", "!=", "<", "<=", ">", ">="])
    if rng.random() < 0.6:  # the plain case: a field compared with a fixed value
        value = Text(rng.choice(TEXTS)) if schema[name] == "text" else Number(rng.choice(NUMBERS))
        return Condition(Field(name), op, value)
    kind = schema[name]
    left, right = random_formula(rng, schema, kind), random_formula(rng, schema, kind)
    if left == right or not (uses_field(left) or uses_field(right)):
        left, right = Field(name), Text("q") if kind == "text" else Number(7)
    return Condition(left, op, right)


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
        kind = rng.choice(["filter", "filter", "sort", "sort", "limit", "group", "add"])
        if kind == "add":
            name = next(candidate for candidate in ("extra", "more", "third", "fourth", "fifth") if candidate not in schema)
            added = rng.choice(["text", "integer"])
            steps.append(Add(name=name, formula=random_formula(rng, schema, added)))
            schema = dict(schema, **{name: added})
        elif kind == "filter":
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
