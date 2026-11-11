# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

`PLAN.md` is the current plan for the project and records the product owner's decisions; read it before doing any work. The proposal under review is in `outputs/`.

- **Stage 1 (complete, accepted):** `stage1/inventory.md` is the result. `stage1/` also holds the approved briefs, the 20 sample programs, their test inputs, the classification files and the tools that produce the figures. The programs under `stage1/programs/` are study material, not part of the product.
- **Stage 2 (under way):** `cdipl/` is the compiler. Part A (the compiler core, with intent written in standard phrases) is built and tested. Part B (word lists, classifier, index) and part C (formulas) are not. See "Stage 2 progress" in `PLAN.md`.

Layout:

- `cdipl/model.py`, `parser.py`, `languages.py`: the intent language, in English and Spanish standard phrases.
- `cdipl/targets/`: one generator per target language, each with the reverse step that lifts generated code back to intent.
- `cdipl/library/`: the catalogue of 90 blocks and the review status of the implemented ones. Every block is a draft until a person reviews it; do not mark a block verified yourself.
- `docs/meaning.md`: what each block means, independently of any target. Change it together with the generators.
- `stage2/wordings/test_*.tsv`: the classifier's held-out test wordings. Do not read them, and do not use them to build word lists or training material; they exist to test the classifier once it is built.
- `main.py` is PyCharm's default sample and is unused.

## Environment

- Python `>=3.14` (declared in `pyproject.toml`; project name `pythonproject`).
- A local virtualenv lives at `.venv/` (Python 3.14, git-ignored). Use `.venv/bin/python` rather than a system interpreter. In a fresh checkout, create it with `uv venv --python 3.14 .venv`.
- `pyproject.toml` has no `[build-system]` or tool config; dependencies go in `[project].dependencies`.

## Commands

- Build: `.venv/bin/python -m cdipl build examples/adult_users.intent --target python` (or `--target javascript`)
- Lift a generated program back to intent: `.venv/bin/python -m cdipl lift PATH [--language es]`
- Tests: `.venv/bin/python -m unittest discover -s tests -t .` (needs `node`; see `tests/README.md` for the optional formatter and linter tools)
