# Tests

Run everything from the repository root:

```bash
.venv/bin/python -m unittest discover -s tests -t .
```

Requirements:

- Python 3.14 in `.venv` (the generated Python programs are run with the same interpreter).
- `node` on the path, to run the generated JavaScript programs.
- `gcc` on the path (or the compiler named by `CC`), to compile the generated C programs. `test_quality_c.py` also uses `clang` and `clang-format` and skips the checks whose tool is missing.
- `javac` and `java` 21 or later on the path, to compile and run the generated Java programs.
- Compiled C and Java programs are cached in the temporary folder, so a second run is faster. The whole suite takes two to three minutes.
- For `test_quality.py`: `ruff` installed in `.venv`, and the environment variable `CDIPL_JS_TOOLS` naming a `node_modules` folder that holds `prettier`, `eslint`, `@eslint/js` and `globals`. Each quality test is skipped, and reported as skipped, when its tool is missing.

| File | Criterion in `PLAN.md` | What it checks |
|---|---|---|
| `test_equivalence.py` | G1 | 240 pairs of intent and dataset give identical results in every target; known results on known data; the Stage 1 sample J1 |
| `test_combination.py` | G2 | All 1,555 chains of up to four blocks: 399 fit, build and agree; 1,156 are rejected |
| `test_roundtrip.py` | G3, G5, C5 | Round trip in both directions; trace covers every line; English and Spanish build the same program |
| `test_edited.py` | G4 | 69 hand edits to generated files are each lifted exactly or refused |
| `test_quality.py` | G6 | Formatter and linter report nothing |
| `test_quality_c.py` | G6 for C | gcc and clang compile the sample with `-std=c11 -Wall -Wextra -Werror -pedantic` and report nothing; clang-format changes nothing; the sample uses every piece of support code |
| `test_quality_java.py` | G6 for Java | `javac -Xlint:all -Werror` reports nothing for the sample |
| `test_edited_c.py`, `test_edited_java.py` | G4 for C and Java | 47 hand edits to a generated C file and 48 to a generated Java file are each lifted exactly or refused |
| `test_diagnostics.py` | G7 | 42 invalid intent files are rejected with the right line |
| `test_free_wording.py` | C3, C4 | With a small made-up word list: free wording builds the same program as standard phrases; the index is reused without the classifier; unknown words and close calls are reported |
| `test_library.py` | G8 | Flagged blocks stop a build; ten builds are byte-identical |
| `test_real_wording.py` | C5 | The real word lists and classifier file are intact; hand-written English and Spanish pairs build the same program whenever both are accepted, and none is accepted as the wrong block |
| `test_pages.py` | G3, G4, G5, G6, G7, C5 for web pages | Pages build and convert back in both human languages; edited pages are lifted exactly or refused; invalid descriptions are rejected with their line; the formatter makes no change |
| `test_live.py` | L2, L3, L4, L6 | The live view reports on every statement, a problem does not hide the rest, a complete file shows exactly what `build` writes, and the server refuses posts that lack its token |
| `test_server.py` | G1 to G7 for applications with an API | The generated FastAPI server is imported and exercised: listing, adding, changing, deleting, refusing bad records, keeping records across a restart, and not serving its own code or database; rules store a notification exactly when their condition holds, and notifications cannot be changed through the API and survive a restart; edited rules are lifted exactly or refused; the formatter, linter and ruff report nothing. Skipped, and reported as skipped, if `fastapi` and `httpx` are not installed. |
| `test_commands.py` | | The `new` and `run` commands: every starter builds in both human languages, a program runs with its arguments and returns its own exit status, and pages are served |
