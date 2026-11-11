# Tests

Run everything from the repository root:

```bash
.venv/bin/python -m unittest discover -s tests -t .
```

Requirements:

- Python 3.14 in `.venv` (the generated Python programs are run with the same interpreter).
- `node` on the path, to run the generated JavaScript programs.
- For `test_quality.py`: `ruff` installed in `.venv`, and the environment variable `CDIPL_JS_TOOLS` naming a `node_modules` folder that holds `prettier`, `eslint`, `@eslint/js` and `globals`. Each quality test is skipped, and reported as skipped, when its tool is missing.

| File | Criterion in `PLAN.md` | What it checks |
|---|---|---|
| `test_equivalence.py` | G1 | 240 pairs of intent and dataset give identical results in every target; known results on known data; the Stage 1 sample J1 |
| `test_combination.py` | G2 | All 1,555 chains of up to four blocks: 399 fit, build and agree; 1,156 are rejected |
| `test_roundtrip.py` | G3, G5, C5 | Round trip in both directions; trace covers every line; English and Spanish build the same program |
| `test_edited.py` | G4 | 69 hand edits to generated files are each lifted exactly or refused |
| `test_quality.py` | G6 | Formatter and linter report nothing |
| `test_diagnostics.py` | G7 | 42 invalid intent files are rejected with the right line |
| `test_free_wording.py` | C3, C4 | With a small made-up word list: free wording builds the same program as standard phrases; the index is reused without the classifier; unknown words and close calls are reported |
| `test_library.py` | G8 | Flagged blocks stop a build; ten builds are byte-identical |
