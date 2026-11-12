# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

`PLAN.md` is the current plan for the project and records the product owner's decisions; read it before doing any work. The proposal under review is in `outputs/`.

- **Stage 1 (complete, accepted):** `stage1/inventory.md` is the result. `stage1/` also holds the approved briefs, the 20 sample programs, their test inputs, the classification files and the tools that produce the figures. The programs under `stage1/programs/` are study material, not part of the product.
- **Stage 2 (built and measured):** `cdipl/` is the compiler. The compiler criteria pass. The classifier missed the marks set for choosing unseen (`stage2/classifier_result.md`).
- **Stage 3 (built):** programs build in Python, JavaScript, C and Java and behave identically on every test. The cost of each target is in `docs/target-c.md`, `docs/target-java.md` and "Stage 3 result" in `PLAN.md`.
- **Live view and applications (built):** the owner redirected the product toward pseudocode written in a live view. `python -m cdipl live FILE` serves a local page with the intent on the left and the exact generated files on the right; saving rewrites the file in standard phrases. An `app` description builds pages (HTML, CSS, JavaScript), records as JSON, tables that fill, search, sort and can be edited, buttons with actions, rules that store notifications and, with `use sqlite` and `use FastAPI`, a server with an API over a SQLite table. `use authentication` adds signing in. The authentication code is a draft that no person has reviewed; say so whenever it comes up. Postgres, Docker, Django and React are not built.
- **Revision 13 of `PLAN.md`** records an instruction from the owner to do the work without asking questions, and lists the choices the assistant made ("Decisions made by the assistant"). See "Open decisions" there for what is next.

Layout:

- `cdipl/model.py`, `parser.py`, `languages.py`: the intent language, in English and Spanish standard phrases.
- `cdipl/targets/`: one generator per target language (`python.py`, `javascript.py`, `c.py`, `java.py`), each with the reverse step that lifts generated code back to intent. A target is registered in `cdipl/targets/__init__.py` and is then covered by the shared tests.
- `cdipl/library/`: the catalogue of 108 blocks (90 from Stage 1, the rest for pages and applications) and the review status of the 37 implemented ones. Every block is a draft until a person reviews it; do not mark a block verified yourself.
- `docs/meaning.md`: what each block means, independently of any target. Change it together with the generators.
- `cdipl/words.py`, `classifier.py`, `resolve.py`, `slots.py`: free wording. Word lists turn words into concept codes, the classifier chooses a block or declines, the choice is recorded in an index beside the intent file, and parameters are read by fixed rules.
- `stage2/wordings/`: training wordings (`train_*.tsv`), concept codes, and the held-out test wordings (`test_*.tsv`). Both test sets (`test_*.tsv` and `test_pages_*.tsv`) have been used. Do not tune word lists, training wordings or the classifier against it; any change to them must be tested on newly written wordings. Blocks added since (editable tables, rules, authentication) are read in fixed form only and are listed as untaught in `tests/test_real_wording.py`.
- `stage2/train_classifier.py` rebuilds `cdipl/library/classifier.json`; `stage2/evaluate_classifier.py` runs the held-out test.
- `cdipl/pages.py` and `cdipl/targets/html.py`: descriptions of an application, and the generator for its pages, scripts, records and FastAPI server (including authentication), with the reverse step. An application that does not use a feature must generate exactly what it did before the feature existed. `cdipl/page_wording.py` reads freely worded lines of a page.
- `cdipl/live.py`, `live_server.py`, `live_page.html`: the live view. The analysis reports on every statement and does not stop at the first problem. The preview of an application with a server runs the generated server itself in a temporary folder.
- `cdipl/starters.py` and `cdipl/__main__.py`: the commands (`new`, `run`, `build`, `lift`, `explain`, `choose`, `affected`, `live`).
- `main.py` is PyCharm's default sample and is unused.

## Environment

- `pyproject.toml` declares Python `>=3.13`, the project name `cdipl` and the console command `cdipl`. The tests have been run with 3.14 only.
- A local virtualenv lives at `.venv/` (Python 3.14, git-ignored). Use `.venv/bin/python` rather than a system interpreter. In a fresh checkout, create it with `uv venv --python 3.14 .venv`.
- The package itself has no dependencies. `fastapi` and `uvicorn` (extra `server`) are needed only to run a generated server, and `ruff` and `httpx` (extra `dev`) for the tests. Generated servers pin the versions of `fastapi` and `uvicorn` they were tested with.

## Commands

- Build: `.venv/bin/python -m cdipl build examples/adult_users.intent --target python` (or `--target javascript`, `c`, `java`)
- Live view: `.venv/bin/python -m cdipl live examples/adult_users.intent` (or `examples/inventory.intent`, `examples/inventory_auth.intent`), then open the address it prints
- Build an application: `.venv/bin/python -m cdipl build examples/inventory_server.intent --target html --out OUT`, then in `OUT`: `python -m uvicorn server:app` (needs `fastapi` and `uvicorn`, which are installed in `.venv` for the tests but are not project dependencies)
- Lift a generated program back to intent: `.venv/bin/python -m cdipl lift PATH [--language es]`
- Start a file and run it: `.venv/bin/python -m cdipl new FILE --kind program|pages|app`, then `.venv/bin/python -m cdipl run [--target python|javascript|c|java] FILE [ARGUMENTS]`
- Add a user to a built application that uses authentication: in its folder, `python server.py add-user NAME`
- Tests: `.venv/bin/python -m unittest discover -s tests -t .` (needs `node`, `gcc`, `javac` and `java`; takes two to three minutes; see `tests/README.md` for the optional formatter and linter tools)
