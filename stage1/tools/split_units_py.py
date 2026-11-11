"""Split Python programs into units for the Stage 1 inventory.

A unit is a top-level function, a method of a top-level class, or "<module>":
the top-level statements that are not imports, docstrings, assignments of
constants, or a `__main__` guard whose body is a single call.

Lines counted are non-blank lines that are not comments or docstrings.
Usage: python3 split_units_py.py FILE... (prints CSV rows: program,unit,start,end,lines)
"""
import ast
import io
import sys
import tokenize
from pathlib import Path


def skipped_lines(source):
    """Line numbers that are blank, comment-only, or part of a docstring."""
    skip = set()
    lines = source.splitlines()
    for number, text in enumerate(lines, 1):
        if not text.strip():
            skip.add(number)
    code_lines = set()
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
                        tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER):
            continue
        code_lines.update(range(tok.start[0], tok.end[0] + 1))
    skip.update(set(range(1, len(lines) + 1)) - code_lines)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                skip.update(range(body[0].lineno, body[0].end_lineno + 1))
    return skip


def is_constant(node):
    try:
        ast.literal_eval(node)
        return True
    except (ValueError, SyntaxError):
        return False


def is_boilerplate(stmt):
    if isinstance(stmt, (ast.Import, ast.ImportFrom)):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
        return True
    if isinstance(stmt, (ast.Assign, ast.AnnAssign)) and stmt.value is not None and is_constant(stmt.value):
        return True
    if isinstance(stmt, ast.If) and isinstance(stmt.test, ast.Compare) \
            and "__name__" in ast.dump(stmt.test) and len(stmt.body) == 1 and not stmt.orelse:
        only = stmt.body[0]
        return isinstance(only, ast.Raise) or (isinstance(only, ast.Expr) and isinstance(only.value, ast.Call))
    return False


def units(path):
    source = Path(path).read_text()
    skip = skipped_lines(source)
    tree = ast.parse(source)

    def count(start, end):
        return sum(1 for n in range(start, end + 1) if n not in skip)

    rows, module_lines = [], 0
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            rows.append((stmt.name, stmt.lineno, stmt.end_lineno, count(stmt.lineno, stmt.end_lineno)))
        elif isinstance(stmt, ast.ClassDef):
            for item in stmt.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    rows.append((f"{stmt.name}.{item.name}", item.lineno, item.end_lineno,
                                 count(item.lineno, item.end_lineno)))
        elif not is_boilerplate(stmt):
            module_lines += count(stmt.lineno, stmt.end_lineno)
    if module_lines:
        rows.append(("<module>", 0, 0, module_lines))
    return rows


if __name__ == "__main__":
    for path in sys.argv[1:]:
        program = Path(path).stem.split("_")[0].upper()
        for name, start, end, lines in units(path):
            print(f"{program},{name},{start},{end},{lines}")
