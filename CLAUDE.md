# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

This repository is currently an empty scaffold: the only code is PyCharm's default sample `main.py` (a `print_hi` function). There is no application code, test suite, linter config, or dependencies yet. Update this file as real structure is added.

## Environment

- Python `>=3.14` (declared in `pyproject.toml`; project name `pythonproject`).
- A local virtualenv lives at `.venv/` (Python 3.14, git-ignored). Use `.venv/bin/python` rather than a system interpreter.
- `pyproject.toml` has no `[build-system]` or tool config; dependencies go in `[project].dependencies`.

## Commands

- Run: `.venv/bin/python main.py`
- No test runner or linter is configured yet.
