# Stage 1 result: block inventory

**Status:** complete, 2026-11-11. Awaiting the product owner's review before Stage 2 starts.

This is the result of Stage 1 of `PLAN.md`. The question was: how much of a set of small sample programs could be built entirely from reusable, general-purpose blocks, and which blocks would that take?

## Result in brief

- **Between 13 and 16 of the 20 sample programs could be built entirely from blocks**, depending on which of two classifiers is believed. That is above the pass mark of 30% proposed in `PLAN.md`.
- **That holds only if blocks can take formulas as parameters.** If every parameter must be a simple value, the figure falls to between 4 and 9 of 20.
- **It would take about 90 different blocks, and 55 of them are used by only one program.** Only one program, J1, could be built from blocks that some other program also uses. J1 is the example from the proposal.
- **The most reused blocks are plumbing, not data operations:** printing a message, stopping with an error, and reading command-line options.
- **Four programs contain logic that no block library would hold:** the file renaming tool (P4), text to HTML (P8), the loan table (P9) and tic-tac-toe (J10).

These figures describe programs written by an AI assistant and classified by AI assistants. They are a favourable case. See [Limits](#limits).

## What was done

1. **Briefs.** The assistant drafted 20 briefs, ten for Python and ten for JavaScript, and the owner approved them (`stage1/briefs.md`).
2. **Programs.** Four separate assistant sessions wrote the programs from the briefs alone. They were not told what the programs were for, so the code was not shaped to suit a block library. Each program was run once on a small sample input and behaved correctly; the inputs are in `stage1/samples/`. The four browser programs were run in headless Chromium.
3. **Units.** Two small tools split every program mechanically into units: each top-level function, plus the remaining top-level code of the file. This gave 129 units and 1,321 counted lines (`stage1/units.csv`).
4. **Rubric.** Each unit is given a level (`stage1/rubric.md`):
   - **A:** a sequence of general-purpose operations whose parameters are simple values.
   - **B:** as A, but at least one parameter must be a formula, of the kind typed into a spreadsheet cell.
   - **C:** logic particular to this program.

   A and B are called closed; C is called open. When in doubt, the rubric says to choose the less favourable level.
5. **First classification.** The assistant that wrote the plan classified every unit and named the blocks each closed unit would need (`stage1/classification.csv`).
6. **Second classification.** A separate assistant session classified every unit from the rubric and the code alone, without seeing the first classification (`stage1/classification_second.csv`).
7. **Figures.** `stage1/tools/report.py` computes everything below from those files.

## Results

### By program

Unit counts are shown as A / B / C. A program is *closed* if it has no C unit, and *needs formulas* if it has at least one B unit.

| ID | Program | Units | First: A / B / C | First: verdict | Second: A / B / C | Second: verdict |
|---|---|---|---|---|---|---|
| P1 | Sales totals by region | 3 | 3 / 0 / 0 | closed | 2 / 1 / 0 | closed, needs formulas |
| P2 | Ten largest files | 4 | 4 / 0 / 0 | closed | 3 / 0 / 1 | open |
| P3 | Web log summary | 4 | 4 / 0 / 0 | closed | 3 / 1 / 0 | closed, needs formulas |
| P4 | File renaming tool | 7 | 3 / 3 / 1 | open | 3 / 3 / 1 | open |
| P5 | Download with retry | 8 | 7 / 1 / 0 | closed, needs formulas | 7 / 1 / 0 | closed, needs formulas |
| P6 | Configuration check | 9 | 7 / 2 / 0 | closed, needs formulas | 5 / 3 / 1 | open |
| P7 | Rows in one CSV but not another | 6 | 6 / 0 / 0 | closed | 6 / 0 / 0 | closed |
| P8 | Text to HTML | 7 | 5 / 0 / 2 | open | 5 / 0 / 2 | open |
| P9 | Loan repayment table | 8 | 5 / 2 / 1 | open | 6 / 1 / 1 | open |
| P10 | Duplicate file finder | 10 | 8 / 2 / 0 | closed, needs formulas | 8 / 2 / 0 | closed, needs formulas |
| J1 | Adult users, sorted, first ten | 5 | 5 / 0 / 0 | closed | 4 / 1 / 0 | closed, needs formulas |
| J2 | Word count | 6 | 6 / 0 / 0 | closed | 6 / 0 / 0 | closed |
| J3 | Form checking (browser) | 6 | 5 / 1 / 0 | closed, needs formulas | 5 / 1 / 0 | closed, needs formulas |
| J4 | Table with search (browser) | 6 | 6 / 0 / 0 | closed | 6 / 0 / 0 | closed |
| J5 | Small web server | 8 | 8 / 0 / 0 | closed | 8 / 0 / 0 | closed |
| J6 | Countdown (browser) | 6 | 5 / 1 / 0 | closed, needs formulas | 4 / 2 / 0 | closed, needs formulas |
| J7 | Combine JSON files | 4 | 3 / 1 / 0 | closed, needs formulas | 2 / 2 / 0 | closed, needs formulas |
| J8 | To-do list (browser) | 10 | 8 / 2 / 0 | closed, needs formulas | 8 / 2 / 0 | closed, needs formulas |
| J9 | CSV and JSON conversion | 6 | 6 / 0 / 0 | closed | 4 / 1 / 1 | open |
| J10 | Tic-tac-toe | 6 | 2 / 2 / 2 | open | 2 / 2 / 2 | open |

### Totals

| Measure | First classification | Second classification |
|---|---|---|
| Programs closed with simple parameters only | 9 of 20 | 4 of 20 |
| Programs closed if formulas are allowed | 16 of 20 | 13 of 20 |
| Programs with at least one open unit | 4 of 20 | 7 of 20 |
| Units at level A | 106 of 129 (82%) | 97 of 129 (75%) |
| Units at level A or B | 123 of 129 (95%) | 120 of 129 (93%) |
| Counted lines in units at level A or B | 1,215 of 1,321 (92%) | 1,165 of 1,321 (88%) |

### Agreement between the two classifications

The two agreed on the level of 118 of 129 units (91%), and on closed versus open for 126 of 129 (98%).

Three units decide the difference at program level: `format_size` in P2, `lookup` in P6 and `parseCsv` in J9. Each is a general-purpose operation written out by hand: formatting a file size, following a dotted path into nested data, and parsing CSV text. The first classifier counted each as one block. The second counted each as open, because the rubric lists a custom algorithm or parser under level C. For a block library the first reading is the relevant one, since each of these would simply be a block. The disagreement shows that the rubric is ambiguous on this point, so both sets of figures are reported.

The other eight differences are between levels A and B.

### The blocks

Block names and their granularity come from the first classification and are one person's judgment. A coarser or finer naming would change the counts.

| Measure | Value |
|---|---|
| Distinct blocks needed for all closed units | 90 |
| Blocks used by two or more programs | 35 |
| Blocks used by one program only | 55 |
| Blocks per program, on average | 10.7 |
| Of those, used by no other program, on average | 2.8 |
| Blocks needed to cover 50% of closed units | 32 |
| Blocks needed to cover 80% of closed units | 62 |
| Programs that need only blocks shared with another program | 1 of 20 (J1) |

Blocks used by three or more programs, with the number of programs:

| Block | Programs | Block | Programs |
|---|---|---|---|
| `print-message` | 16 | `filter-rows` | 4 |
| `exit-on-error` | 15 | `check-path-exists` | 4 |
| `cli-options` | 15 | `format-json` | 4 |
| `read-text-file` | 9 | `select-elements` | 4 |
| `sort-rows` | 8 | `parse-csv` | 3 |
| `calculate` (evaluate a formula) | 7 | `match-pattern` | 3 |
| `parse-json` | 7 | `check-list-of-records` | 3 |
| `check-number-range` | 6 | `on-event` | 3 |
| `write-text-file` | 6 | `read-element-data` | 3 |
| `print-table` | 5 | `take-first` | 3 |

Used by two programs: `require-columns`, `format-csv`, `set-text`, `check-pattern`, `count-rows`, `count-values`, `current-time`, `drop-invalid-rows`, `file-size`, `focus-element`, `format-number`, `http-get`, `list-folder`, `total`, `walk-folder`.

Used by one program: `send-json-response`, `choose-by-value`, `get-by-path`, `group-by-key`, `hash-file`, `json-type-of`, `read-request-body`, `render-list`, `render-table`, `retry-with-backoff`, `route-request`, `all-match`, `append-record`, `block-submit-if-invalid`, `build-record`, `check-allowed-values`, `check-min-length`, `check-required`, `check-required-types`, `check-text-rule`, `check-url`, `check-valid-date`, `clean-number-field`, `distinct-values`, `escape-html`, `exclude-by-key`, `fill-series`, `fill-template`, `filter-elements-by-text`, `first-match`, `flatten-lists`, `format-grid`, `format-size`, `format-text`, `group-total`, `http-server`, `load-from-storage`, `lowercase-text`, `number-items`, `on-signal-shutdown`, `print-groups`, `records-to-rows`, `remove-duplicates`, `remove-where`, `reset-form`, `round-number`, `rows-to-records`, `save-to-storage`, `show-field-message`, `show-hide`, `split-duration`, `split-extension`, `stop-timer`, `timer-every`, `update-where`.

### The open units

Both classifiers marked these six units as open. They total 106 counted lines, 8% of the whole.

| Program | Unit | What it does |
|---|---|---|
| P4 | `apply_plan` | Renames files in two passes through temporary names, so that a new name never overwrites a file still waiting to be renamed |
| P8 | `parse_blocks` | Reads lines and groups them into headings, lists and paragraphs |
| P8 | `render_block` | Turns each of those groups into HTML |
| P9 | `schedule` | Carries the loan balance from month to month and adjusts the last payment |
| J10 | `findWinner` | Decides whether a player has won |
| J10 | `play` | Runs the game loop |

P8, P9 and J10 were expected to be hard when the briefs were drafted. P4 was not.

## Findings

1. **The idea is not ruled out.** On this material, most programs consist of units that could each be stated as a chain of named operations.
2. **Formulas are needed.** Half the programs (10 of 20 by the first classification, 14 of 20 by the second) have at least one unit that needs an arithmetic, text or true-or-false expression. An intent language limited to named operations with simple values would produce under half of these programs.
3. **The library has to grow with the programs.** Each program needs, on average, about three blocks that no other program in the sample uses. Twenty programs needed about ninety blocks, and the curve had not flattened: covering 80% of the closed units takes 62 blocks. A useful library is hundreds of blocks, not dozens.
4. **Reuse is concentrated in plumbing.** The three most used blocks are printing a message, stopping with an error and reading command-line options. A complete program cannot be generated without them, however small its real work is. J1, whose real work is filter, sort and limit, needs ten blocks in all.
5. **Many "closed" verdicts depend on large, configurable blocks.** Examples are `http-server`, `route-request`, `retry-with-backoff`, `render-table` and `block-submit-if-invalid`. Each hides a great deal of behaviour behind a few parameters. These are the blocks whose meaning will be hardest to pin down and to keep identical across target languages.
6. **A small amount of code blocks a whole program.** The open units are 8% of the lines, but they put four of twenty programs out of reach, because the first version generates complete programs and accepts no hand-written code.

## Limits

- **The programs were generated, not collected.** They are tidy and conventional. Real programs written under real constraints are likely to contain more code particular to themselves. A good result here does not show that real programs can be covered.
- **Both classifiers are AI assistants of the same kind.** The second worked without seeing the first's answers, but it is not an independent human reviewer, and both may share the same blind spots.
- **"Could be built from blocks" was judged by reading, not by building.** No block exists yet. Each verdict assumes that a block of that name could be written, would be general enough, and would join cleanly with its neighbours. Stage 2 tests that for a handful of blocks only.
- **Twenty programs is a small sample,** all of one size (40 to 100 counted lines) and all without frameworks.
- **The pass mark of 30% was proposed by the assistant** and has not been ratified by the owner.

## What this means for Stage 2

Three points need the owner's decision. They are also listed as open decisions in `PLAN.md`.

1. **Formulas.** Should the intent language allow formulas as parameters? Without them, the library covers under half of even this favourable sample. With them, the language needs an expression syntax with defined meaning in every target, which is more work and more risk of targets drifting apart. The pipeline slice in the plan has comparisons only.
2. **Plumbing blocks in Stage 2.** The six pipeline blocks in the plan cannot produce a complete program alone. Recommended: add the plumbing blocks that J1 needs (`cli-options`, `read-text-file`, `parse-json`, `check-list-of-records`, `print-table`, `print-message`, `exit-on-error`), and make "the generated program behaves like the sample J1 on its test input, in Python and in JavaScript" an acceptance test for Stage 2.
3. **Classifier test set.** The 90 block names above are the labels the classifier will be tested against in Stage 2, as the plan requires.

## Reproducing the figures

```bash
python3 stage1/tools/report.py stage1/units.csv stage1/classification.csv stage1/classification_second.csv
```

To regenerate `stage1/units.csv`, run `stage1/tools/split_units_py.py` on the Python programs and `stage1/tools/split_units_js.js` on the JavaScript programs. The JavaScript tool needs the `acorn` parser (version 8.14.0 was used) on `NODE_PATH`; it is not part of the repository.
