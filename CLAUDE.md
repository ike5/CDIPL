# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

`PLAN.md` is the current plan for the project and records the product owner's decisions; read it before doing any work. The proposal under review is in `outputs/`.

- **Stage 1 (complete, accepted):** `stage1/inventory.md` is the result. `stage1/` also holds the approved briefs, the 20 sample programs, their test inputs, the classification files and the tools that produce the figures. The programs under `stage1/programs/` are study material, not part of the product.
- **Stage 2 (built and measured):** `cdipl/` is the compiler. The compiler criteria pass. The classifier missed the marks set for choosing unseen (`stage2/classifier_result.md`).
- **Live view and applications (built, in progress):** the owner redirected the product toward pseudocode written in a live view. `python -m cdipl live FILE` serves a local page with the intent on the left and the exact generated files on the right; saving rewrites the file in standard phrases. An `app` description builds pages (HTML, CSS, JavaScript), records as JSON, tables that fill, search and sort, buttons that add a record or open a page, and, with `use sqlite` and `use FastAPI`, a server with an API over a SQLite table. The generated server has no authentication. See "Next step: a live view" in `PLAN.md` for what is and is not built and the open decisions. Stage 3 (a C target) has not started.

Layout:

- `cdipl/model.py`, `parser.py`, `languages.py`: the intent language, in English and Spanish standard phrases.
- `cdipl/targets/`: one generator per target language, each with the reverse step that lifts generated code back to intent.
- `cdipl/library/`: the catalogue of 90 blocks and the review status of the implemented ones. Every block is a draft until a person reviews it; do not mark a block verified yourself.
- `docs/meaning.md`: what each block means, independently of any target. Change it together with the generators.
- `cdipl/words.py`, `classifier.py`, `resolve.py`, `slots.py`: free wording. Word lists turn words into concept codes, the classifier chooses a block or declines, the choice is recorded in an index beside the intent file, and parameters are read by fixed rules.
- `stage2/wordings/`: training wordings (`train_*.tsv`), concept codes, and the held-out test wordings (`test_*.tsv`). Both test sets (`test_*.tsv` and `test_pages_*.tsv`) have been used. Do not tune word lists, training wordings or the classifier against it; any change to them must be tested on newly written wordings.
- `stage2/train_classifier.py` rebuilds `cdipl/library/classifier.json`; `stage2/evaluate_classifier.py` runs the held-out test.
- `cdipl/pages.py` and `cdipl/targets/html.py`: descriptions of an application, and the generator for its pages, scripts, records and FastAPI server, with the reverse step. `cdipl/page_wording.py` reads freely worded lines of a page.
- `cdipl/live.py`, `live_server.py`, `live_page.html`: the live view. The analysis reports on every statement and does not stop at the first problem.
- `main.py` is PyCharm's default sample and is unused.

## Environment

- Python `>=3.14` (declared in `pyproject.toml`; project name `pythonproject`).
- A local virtualenv lives at `.venv/` (Python 3.14, git-ignored). Use `.venv/bin/python` rather than a system interpreter. In a fresh checkout, create it with `uv venv --python 3.14 .venv`.
- `pyproject.toml` has no `[build-system]` or tool config; dependencies go in `[project].dependencies`.

## Commands

- Build: `.venv/bin/python -m cdipl build examples/adult_users.intent --target python` (or `--target javascript`)
- Live view: `.venv/bin/python -m cdipl live examples/adult_users.intent` (or `examples/inventory.intent`), then open the address it prints
- Build an application: `.venv/bin/python -m cdipl build examples/inventory_server.intent --target html --out OUT`, then in `OUT`: `python -m uvicorn server:app` (needs `fastapi` and `uvicorn`, which are installed in `.venv` for the tests but are not project dependencies)
- Lift a generated program back to intent: `.venv/bin/python -m cdipl lift PATH [--language es]`
- Tests: `.venv/bin/python -m unittest discover -s tests -t .` (needs `node`; see `tests/README.md` for the optional formatter and linter tools)
