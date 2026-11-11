# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

There is no application code yet: `main.py` is PyCharm's default sample (a `print_hi` function), and there is no test suite, linter config, or dependencies. The programs under `stage1/programs/` are study material, not part of the product. Update this file as real structure is added.

`PLAN.md` is the current plan for the project and records the product owner's decisions; read it before doing any work. Stage 1 of that plan is complete: `stage1/inventory.md` is the result, and `stage1/` also holds the approved briefs, the 20 sample programs, their test inputs, the classification files and the tools that produce the figures. Stage 2 (the compiler, blocks and classifier) must not start until the owner has reviewed the Stage 1 result. The proposal under review is in `outputs/`.

## Environment

- Python `>=3.14` (declared in `pyproject.toml`; project name `pythonproject`).
- A local virtualenv lives at `.venv/` (Python 3.14, git-ignored). Use `.venv/bin/python` rather than a system interpreter.
- `pyproject.toml` has no `[build-system]` or tool config; dependencies go in `[project].dependencies`.

## Commands

- Run: `.venv/bin/python main.py`
- No test runner or linter is configured yet.
