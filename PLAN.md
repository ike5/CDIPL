# PLAN: Evaluation of the CDIPL proposal and a first proof of concept

| | |
|---|---|
| **Reviewed** | `outputs/proposal-classifier-driven-intent-programming-language.md` (v0.2) and this repository at commit `194e44b` |
| **Revision** | 13, dated 2026-11-12. It incorporates twelve rounds of decisions from the product owner and the results of Stages 1, 2 and 3. In the twelfth round the owner asked the assistant to stop asking questions and build a CDIPL that works from the ideas given so far; the choices the assistant made to do that are listed under [Decisions made by the assistant](#decisions-made-by-the-assistant). Revision 1 (commit `d23ae96`) led with an engine for editing existing code, which the owner has since ruled out for the first version. |
| **Status** | Stage 1 is complete and accepted. Stage 2 is built and measured. Stage 3 is built: programs now build in Python, JavaScript, C and Java, with identical behaviour on every test. The live view and whole applications are built and tested: pages, records, tables that fill, search, sort and can be edited, buttons with actions, rules that notify, a FastAPI server with an API over SQLite, and authentication. CDIPL installs as a package with a `cdipl` command. See [Next step: a live view](#next-step-a-live-view) and [Stage 3 result](#stage-3-result). Not built: Postgres and Docker, Django, React. Every block is still a draft: no person has reviewed any of them, and the authentication code in particular has not been reviewed by anyone experienced in it. No developer other than the assistant has used any of it. |
| **Audience** | Engineers deciding whether to build this, and what to build first |

References such as "§8" point to sections of the proposal. Sections of this plan are referred to by name.

## Conclusion

As decided by the product owner, CDIPL works like this. A developer writes intent in a file, in their own wording and their own human language, starting with English and Spanish. A fast classifier chooses, for each statement, the matching block from a library of code blocks that were tested and reviewed in advance. The compiler records each choice in an index, joins the blocks like Lego, and writes out a complete program as folders of code in the chosen language. No LLM writes code. Generated code can be converted back to intent and traced to it. The aim is to make programming enjoyable again by leaving the developer in control.

- **Coherent?** Yes, with five conditions.
  - **Reproducible is not the same as correct.** The index makes a build repeatable: once a choice is recorded, the same intent file always produces the same program. It does not make the choice right. A classifier is a statistical tool and will sometimes choose the wrong block. How often, and how the developer finds out, become central questions.
  - **The classifier must be able to decline.** The proposal itself requires a diagnostic instead of a guess when wording is ambiguous (§4). The plan keeps that.
  - **Reversibility** holds only for code the tool generated that is still in a form the tool would generate. The owner has accepted this.
  - **Several languages** requires the same intent to mean the same thing in every target, which is not automatic (see [Probe](#probe-the-same-operation-in-two-languages)).
  - **Blocks tested one at a time are not thereby tested in combination.** Blocks need declared input and output types, and the compiler must check every join.
- **Worth pursuing?** Yes, as a staged experiment with a review after each stage. The compiler mechanics are established engineering and I expect them to work. Two things are uncertain. One is usefulness: the first version generates complete programs and allows no hand-written code, so a program can be generated only if every part of it is in the library. The other is classifier accuracy as the library grows.
- **Smallest proof of concept:**
  1. **Block inventory**, with no product code: work out, from sample programs, which blocks a library would need and how many sample programs it could produce in full.
  2. **Pipeline slice**: six blocks from the proposal's own examples, with a classifier, an index and two targets (Python and JavaScript), tested for correct choices in English and Spanish, identical behaviour, every valid combination, conversion back to intent, and tracing.
  3. **Third target**: add C, to measure what each additional language costs.

**Stage 3 is built.** C and Java were added as targets. Every program in the equivalence and combination tests behaves identically in all four languages. The cost of a target is now measured: a C program carries about 500 lines of fixed support code and a Java program about 360, against 77 for Python, and each generator is two to three times the size of the Python one. See [Stage 3 result](#stage-3-result).

**Stage 2 is built and measured.** The compiler does what the plan asked: 16 blocks, programs that behave identically in Python and JavaScript, conversion back to intent, formulas, and English and Spanish. The classifier does not meet the marks the owner set: on wording it had not seen, 1 accepted choice in 120 was wrong against a mark of 1 in 300, and it declined 32% of English statements against a mark of 25%. Its first guess is right 93% to 95% of the time, so the difficulty is knowing when a guess can be trusted without anyone looking. See [Stage 2 progress](#stage-2-progress).

**Stage 1 is done.** Between 13 and 16 of 20 sample programs could be built entirely from blocks, which is above the proposed pass mark, but only if blocks may take formulas as parameters; without formulas the figure is 4 to 9. It would take about 90 blocks, 55 of them used by a single program. The full result and its limits are under [Stage 1 result](#stage-1-result).

One caution about what Stage 2 can show. Small blocks in Python and JavaScript are the right place to prove the mechanics and the wrong place to prove value: the hand-written equivalent of the first example is one line. The value is in large blocks such as framework code, which the roadmap reaches later, and that is also where keeping targets equivalent is hardest.

The owner has asked the AI assistant that wrote this plan to build the compiler and the blocks, and to write the classifier's example wordings. By the owner's own definition, a block is verified only after a person has reviewed it, so blocks written by the assistant are drafts until then.

## Product decisions made by the owner

| Topic | Decision | Effect on this plan |
|---|---|---|
| Product claim | A deterministic generator of code. No LLM generates the code. | Fixed |
| Goal | Make programming enjoyable again by giving developers control | Recorded as the product goal; see critique point 8 |
| Building blocks | Tested, listed and formatted, with human review; easy to flag when an error is found; assembled like Lego | The library is the product; Stage 2 is built around it |
| Classifier | It chooses the blocks from the intent. It does not ask the developer to confirm. | Now part of Stage 2; accuracy becomes a success criterion |
| Index | The compiler records chosen blocks in an index for fast lookup. Entries need not be readable, so the intent file never has to name components. | Designed in Stage 2; see critique points 7 and 8 |
| Seeing and correcting a choice | The `explain` and `choose` commands are accepted | Built in Stage 2 |
| Classifier pass marks | At most 1 accepted wrong choice in 300 unseen wordings; at most 25% of statements declined | Criteria C1 and C2 are ratified |
| Human languages | Intent may be written in several human languages, English and Spanish first. Words may be mapped to language-independent codes that the classifier works with. | A word list per language is added to Stage 2 (critique point 10) |
| Who builds | The AI assistant builds the compiler and the blocks for each target, and writes the classifier's example wordings, including the wordings used to test it | Checking must not rest on the builder alone (critique point 11) |
| Who reviews blocks | The owner or another professional developer marks each block as reviewed | A block is a draft until then |
| Language of an intent file | Declared on its first line, one human language per file | Built in Stage 2 |
| Output | Complete programs, written out as folders of code | Coverage is all or nothing (critique point 1) |
| Hand edits to generated code | Allowed only if they convert back to intent | Tested in Stage 2 |
| Existing code CDIPL did not generate | Not supported | The edit engine is out of scope |
| Hand-written code inside intent files | Not in the first version | With "complete programs", makes coverage central |
| Order of targets | Python and JavaScript; then C, then Java; HTML with CSS; then FastAPI and Django; then React with CSS | See [Roadmap](#roadmap-after-the-proof-of-concept) |
| Sample material for Stage 1 | The assistant drafted 20 program briefs, the owner approved them, and the assistant generates the programs | Changes what Stage 1 can show (critique point 12) |
| Implementation language | Python is not required | The compiler is written in Python, since the repository was already set up for it |
| Stage 1 result | Accepted as a pass | Stage 2 started |
| Formulas | The intent language allows formulas as parameters | Built as part C of Stage 2, with a written meaning for each operator |
| Plumbing blocks | Stage 2 includes the blocks needed to generate a whole program, with sample J1 as an acceptance test | Done in part A |
| Formatter and linter for generated code | ruff for Python; prettier and eslint for JavaScript; default rules; line length 320, so the formatters never re-wrap a generated line | Used for criterion G6 |
| Main way of writing | Pseudocode, written quickly as intents. Short descriptions are also wanted, such as "increase button size by 40px". | The live view and the page blocks follow the shape of the owner's pseudocode |
| How choices are accepted | Automatically, in a live view: the generated code appears beside the text as it is typed, each statement is shown against the code it produced, and a change to the text changes the code at once | Replaces confirming each choice; see [Next step: a live view](#next-step-a-live-view) |
| What may be written | Any description should be accepted as input, with the tool steering the developer toward the wording it recognises best | Cannot be met in full without a generative model; see the limits in the next step |
| What happens to an accepted choice | It becomes canonical for the developer's project. Accepting is saving the file. | On saving, the live view rewrites the file in standard phrases, so the file itself is the record (see the next step) |
| Where the live view runs | A local browser page first; integration with editors later | Built |
| User-interface blocks | Start now, in HTML and CSS | Built |
| Data in pseudocode | Records are written in the intent file and built into JSON: everything is created from the file | Built: `records` |
| Table behaviour | Fill from the records first, then search and sort | Built |
| Sentences about something already declared | "Increase button size by 40px" changes the button declared above | Built |
| Free wording for pages | Teach the classifier the page blocks | Built; no wrong choice in 24 unseen wordings per language, nearly half declined |
| Choosing a stack | By keyword: `use sqlite`, `use FastAPI`, `use postgres`, `create postgres:` with `using docker` | `use sqlite`, `use FastAPI` and `use authentication` are built; Postgres and Docker are recognised and reported as not built |
| What a stack generates first | A table for each data declaration that is exposed, and an API to list, add, change and delete its records | Built |
| Buttons | Buttons have actions | Three built: add a record, open a page, sign out |
| How to proceed | The assistant does all the work without stopping to ask questions, delegating to other AI agents, and uses the owner's ideas so far to build a CDIPL that works | Done in revision 13. Choices that were the owner's to make are listed under [Decisions made by the assistant](#decisions-made-by-the-assistant) so that they can be reversed. |
| Pace | Generate a small amount, review, then generate more | Three stages with a review after each; Stage 2 is delivered in three parts |

## Basis and limits of this review

What was examined:

- **The repository.** It contains no implementation. `main.py` is the PyCharm sample script, `pyproject.toml` declares `requires-python >=3.14` with no dependencies, build system or tool configuration, and there are no tests. The only substantive file is the proposal.
- **The proposal**, read in full, and the owner's written decisions summarised above.
- **A probe** on generating for several languages: the same sort and filter written the obvious way in Python 3.13.18 and Node 22.23.4, run on five records. Inputs and method are in the [Appendix](#appendix-probe-inputs-and-method). The script was not committed.
- **An earlier probe** on editing an existing stylesheet in a browser, summarised under [Out of scope](#out-of-scope-editing-existing-code).

What was not done:

- No part of the proposed system was implemented. No classifier was trained or measured.
- Tools present in the environment used for this review: Python 3.13.18, Node 22.23.4 and GCC 13.3.0. Python 3.14, which `pyproject.toml` requires, is not installed but is offered for download by the `uv` tool that is present.
- The probe covered Python and JavaScript only. C, Java and every framework are untested.
- No search of prior art or competing tools was performed. Statements about existing tools, about classifiers in general and about the history of similar efforts come from general knowledge and are marked as assumptions.
- `main.py` was not run. This checkout has no `.venv`, and the container's Python is 3.13.18, below the declared minimum.

## Critique

### What holds up

- **A compiler, not a predictor, once choices are recorded.** With the index in place, the same intent file gives the same program, and every generated line has a known cause.
- **The index is a good idea.** It works like a lock file. It makes builds repeatable even if the classifier is later retrained, it pins the exact version of each block, and it makes it possible to find every program that uses a block flagged as faulty.
- **Tested blocks as the unit of reuse.** Quality is established once per block, not re-argued for each generated program.
- **The owner's decisions narrow the problem.** Ruling out existing code and hand-written code removes the hardest machinery in the proposal (§6.2 to §6.5) and makes the round trip between intent and code achievable.

### The product as decided

1. **Complete programs with no hand-written code means coverage is all or nothing.** If a program is 90% standard blocks and 10% logic particular to it, CDIPL cannot produce it. Usefulness therefore depends on how many real programs consist entirely of reusable blocks. This is not known.

2. **A library function is already a tested, reusable block.** `sorted(...)` in Python is one. The product needs a clear answer to "why generate code when I could call a library?" The candidate answers are: one description produces several languages; the output is plain code with no added dependency; every line traces to an intent. For small blocks the answer is weak, since the hand-written version of the proposal's first example is one expression: `sorted((u for u in users if u.age >= 18), key=lambda u: u.name)[:10]`. It becomes stronger as blocks get larger.

3. **Blocks tested one at a time are not tested in combination.** Joining blocks raises questions no single block's tests answer: whether the output of one is a valid input to the next, name clashes, duplicate imports, and how errors pass between blocks. "Optimised" also does not carry over: a full sort followed by "limit 10" is two good blocks and a wasteful pair. Blocks need declared input and output types, the compiler must check every join, and combinations must be tested as combinations.

4. **The same intent must mean the same thing in every language.** The probe wrote "sort by name" and "where age >= 18" the obvious way in Python and JavaScript. The two programs disagreed on all four checks. A written meaning for each block, independent of any target, has to exist before the second target is written.

5. **The roadmap mixes two kinds of growth, and each multiplies the work.** C and Java are new *targets* for the same intents. HTML with CSS, FastAPI, Django and React are new *kinds of intent*, each needing its own blocks. Every block has to be written, tested and kept equivalent for every target that supports it. Framework blocks also have to follow each framework's releases.

6. **Value and difficulty rise together.** Large blocks save real work, so the framework tiers are where the product is most valuable. They are also where "one intent, several targets" is hardest, because FastAPI and Django are different designs and not the same thing in two languages.

7. **A classifier that chooses can choose wrongly, and nothing downstream knows.** I recommended that the classifier only suggest; the owner has decided that it chooses, and the plan follows that decision. The consequence should be stated once, plainly: when the classifier picks the wrong block, the compiler will produce a well-formed, well-tested program that does something other than what the developer wrote, with no error. The index does not help here, because it faithfully records the wrong choice. The plan limits the damage in four ways, all compatible with the owner's decision:
   - The classifier declines when its best candidates are close, and the compiler reports a diagnostic, as §4 of the proposal requires.
   - Type checking rejects a chosen block that does not fit its neighbours.
   - The developer can see what was chosen (point 8).
   - Wrong-choice rate is measured on wording the classifier has not seen, with a pass mark set in advance.

   What remains is a residual error rate greater than zero. The owner has accepted the pass marks set out in the success criteria.

8. **Unreadable index entries and developer control pull against each other.** The owner wants developers in control and does not want them to name components. If the classifier chooses silently and the record of its choice is unreadable, the developer has two ways to find a wrong choice: read the generated code, or notice wrong behaviour. They have one way to fix it: reword the intent and try again, which is the trial and error that makes prompting an LLM frustrating. The plan therefore proposes two tool commands that keep the intent file free of component names: one that shows, in plain words, which block was chosen for each statement, and one that lets the developer pick a different block from a list when the choice was wrong, writing the result to the index. The owner has accepted both.

9. **The classifier needs example wordings, and gets harder as the library grows.** A classifier learns from labelled examples: many wordings for each block. The owner has decided that the assistant writes them. *Assumption, from general knowledge: accuracy falls as the number of blocks rises and as blocks become more alike.* Six blocks will be easy and prove little. Stage 2 therefore measures the classifier against the whole inventory from Stage 1, not only the six blocks that are implemented.

10. **Word codes are a sound way to support several human languages, with known weak spots.** The owner proposes mapping each word, in whatever language, to a language-independent code, and having the classifier work on codes. One classifier then serves every language, a new language needs only a new word list, and much of the choosing becomes a plain lookup, which is more predictable than statistics. The weak spots are:
    - one word with several meanings (`order` as an instruction and as a purchase; Spanish `por`);
    - word forms (`ordenar`, `ordena`, `ordenados`);
    - phrases that only mean something together (`at most`, `como máximo`);
    - differences in word order between languages;
    - missing accents (`más` typed as `mas`).

    The word list therefore needs entries for set phrases and word forms, and must report a word it does not know instead of ignoring it. Field names, data values and generated code are never translated.

11. **The builder should not be the only checker.** The owner has asked the assistant to write the briefs, the sample programs, the compiler, the blocks, the example wordings and the tests. A single author tends to test for the mistakes it can imagine. The owner's definition of a verified block includes human review, so a block written by the assistant is a draft until the owner or another professional developer has reviewed it. I recommended that the wordings used to test the classifier come from someone else. The owner has decided that the assistant writes those too. To limit the weakness, the test wordings are written and set aside before the word lists and training wordings exist, and the classifier result is reported as weaker evidence than an independent test would give.

12. **Generated sample programs are a favourable case, not a representative one.** The owner has decided that Stage 1 uses programs generated by the assistant, from briefs the assistant drafts and the owner approves. Such programs are regular and tutorial-like, and the same assistant that writes them would be judging how block-like they are. Stage 1 can therefore show which blocks to build first, and a poor result on this favourable material would be strong evidence against the idea. A good result would not show that real programs can be covered. That question stays open, and is carried as a risk.

13. **Reversibility returns the standard wording, not the developer's.** Many wordings lead to one block, so the original wording cannot be recovered from code. Each block therefore has one standard phrase in each human language. Converting code back gives the intent in standard phrases, and each standard phrase must always resolve to its own block. The rule is: converting a file back either returns an intent that regenerates that file exactly, or refuses. *Assumption, from general knowledge: earlier model-driven tools that promised round trips between models and code struggled once developers edited the generated code.* The owner's rule avoids that by refusing such edits.

### The proposal document

14. **No shared representation is shown.** The two examples in §5 have no fields in common. The representation is called typed, but the examples carry no types and do not say where `users` is bound. Block interfaces with declared types, as required in point 3, would supply what is missing.

15. **The proof of concept in §12 is superseded.** It tests the editing of an existing React project, which the owner has ruled out for the first version.

### Probe: the same operation in two languages

Five records, read from one JSON file. Each check is the obvious one-line implementation in each language, the kind a first version of a block would contain.

| Check | Python | JavaScript (Node) |
|---|---|---|
| Sort by name, where names include `～` (U+FF5E) and `😀` (U+1F600) | `～` before `😀` | `😀` before `～` |
| `age > 9007199254740992` for ages `…993` and `…992` | selects the first record | selects nothing |
| Output of ages written as `18` and `18.0` | `18`, `18.0` | `18`, `18` |
| `age >= 18` when one record has no `age` | raises an error | silently drops the record |

Reading: two straightforward translations of one intent are not the same program. Each difference has a known remedy, but each remedy is a decision the block's written meaning has to make and every target then has to implement. This is five records and two languages; it shows the problem exists, not how large it is.

## Recommended direction

1. **Treat the block library as the product.** Each block has an identifier, typed inputs and outputs, a written meaning, one standard phrase, code for each supported target, a way to recognise that code when converting back, tests, a record of human review, and a status of verified or flagged.
2. **Make the index a committed lock file.** For each statement it records the chosen block, the exact version of that block, the extracted parameters and the classifier version. A build reads the index and consults the classifier only for statements that are new or changed.
3. **Let the classifier choose the block and nothing else.** Field names, values and comparisons are extracted by exact rules, as §1 and §4 of the proposal require. The classifier never alters them.
4. **Let the classifier decline.** Below a set margin between its best candidates, it reports a diagnostic and chooses nothing.
5. **Write each block's meaning down before its second target,** and check every join at compile time using the declared types.
6. **State reversibility as two testable rules.** Converting generated code back gives the intent in standard phrases. Converting any file back either gives an intent that regenerates that file exactly, or refuses.
7. **Every target declares which blocks it supports.** The compiler refuses an unsupported block for that target; it never approximates.
8. **Use flags.** When a block is flagged as faulty, the compiler refuses to build with it, and the index shows which programs are affected.
9. **Review after each stage,** as the owner asked.
10. **Put a word list in front of the classifier.** For each human language, a list maps words and set phrases to language-independent codes. The classifier sees only codes. Each intent file declares its human language.
11. **Keep building and checking apart as far as the owner's decisions allow.** A person reviews each block before it is marked verified. The classifier's test wordings are written and set aside before its word lists and training wordings are written.

## Proof of concept

### The hypothesis being tested

For one family of intents: a classifier can choose the right block from freely worded statements, declining when unsure; a compiler can join the chosen blocks into complete programs in at least two languages that behave identically on the same input, in every valid combination; and those programs convert back to intent and trace line by line to it.

### Stage 1: block inventory

No product code.

1. Write short briefs for 20 small programs, half for Python and half for JavaScript: one or two sentences each on what the program should do. The assistant drafted them in `stage1/briefs.md` and the owner approved the list.
2. The assistant generates each program from its brief, as the owner decided.
3. Split each program into units: its functions, or the whole script if it has none.
4. Classify each unit:
   - **Closed:** it could be stated entirely as a chain of named operations with parameters.
   - **Open:** it contains logic particular to that program.
   - For closed units, name the block or blocks it would need.
5. Report the share of whole programs in which every unit is closed; the share of units that are closed; the list of distinct blocks, with how often each occurs; and how many blocks would cover 50% and 80% of the closed units.

The block list is the main product of this stage. It sets the order in which blocks are built and gives the classifier in Stage 2 a realistic number of blocks to choose among.

Limit: see critique point 12. The result describes generated sample programs.

#### Stage 1 result

Completed on 2026-11-11. The full write-up, method and limits are in `stage1/inventory.md`. Two classifiers judged all 129 units of the 20 programs; the second worked without seeing the first's answers.

| Measure | First classification | Second classification |
|---|---|---|
| Programs that could be built entirely from blocks with simple parameters | 9 of 20 | 4 of 20 |
| The same, if blocks may take formulas as parameters | 16 of 20 | 13 of 20 |
| Programs containing logic particular to themselves | 4 of 20 | 7 of 20 |
| Units on which the two agreed about closed or open | 126 of 129 | |

Against the proposed pass mark (30% or more of programs entirely closed), the result is a pass at 65% to 80% with formulas, and borderline to pass at 20% to 45% without.

What the result changes:

- **Formulas are needed.** At least half the programs need an arithmetic, text or true-or-false expression somewhere. The owner has since decided that the intent language will allow them; they are part C of Stage 2.
- **The library has to be large.** Twenty programs needed about 90 distinct blocks, and 55 of those were used by one program only. Only one program, the proposal's own example, could be built from blocks that another program also uses. Each new program brought about three blocks of its own.
- **Plumbing comes first.** The most reused blocks are printing a message, stopping with an error and reading command-line options. The six pipeline blocks cannot produce a complete program without them. The owner agreed to add them to Stage 2.
- **The classifier has a realistic test set.** The 90 block names are the labels it will be tested against.
- **The expected hard cases were hard.** The text converter, the loan table and tic-tac-toe each contain logic no library would hold, and so does the file renaming tool, which was not expected.

The limits in critique point 12 apply in full: these are generated programs judged by AI assistants, and "could be built from blocks" was judged by reading, not by building.

### Stage 2: pipeline slice

**Blocks.** The six operations in the proposal's examples in §2 and §3.1.

| Block | Takes | Gives |
|---|---|---|
| Read a declared source | nothing | rows |
| Filter | rows | rows |
| Sort | rows | rows |
| Limit | rows | rows |
| Group by a field | rows | groups |
| Count each group | groups | rows of key and count |

**Intent file.** The source declaration has a fixed form. Each statement after it is free wording for the operation, with exact expressions for its parameters. For example:

```text
language: en

source users from "users.json":
    name: text
    age: integer
    school: text

get users where age >= 18
sort by name ascending
limit 10
```

The second statement might equally be written "order by name ascending". The first line declares the human language of the file. In a Spanish file the same statements might read `obtener users donde age >= 18`, `ordenar por name ascendente` and `limitar 10`: the wording is Spanish, and the field names stay as declared. Fields have declared types, `integer` and `text`. Comparisons use `=`, `!=`, `<`, `<=`, `>`, `>=`, joined by `and`, and are read exactly.

**Word lists.** One per human language, English and Spanish to begin with. Each maps words and set phrases to language-independent codes, and names the filler words that may be ignored. Field names, values and comparisons pass through unchanged. Any other word the list does not know causes a diagnostic.

**Classifier.** It works on codes, not words. Start with the simplest kind that works and record what was used. It is stored as a fixed file with a version. It is trained on example wordings, written by the assistant in English and Spanish, for every block in the Stage 1 inventory, including blocks that are not implemented. It is tested on wordings that the assistant wrote and set aside before the word lists and training wordings were written.

**Index.** A file written beside the intent file and committed with it. Entries use block identifiers, not names.

**Written meanings.** One page that fixes, independently of any target: the ordering of text, the range of integers, what happens when a field is missing or has the wrong type, the order of groups, and the order of rows that tie in a sort.

**Targets.** Python and JavaScript. Each build produces a complete program that reads a data file and writes its result. Generated programs contain plain code and depend on nothing supplied by CDIPL. The input format is an open decision (D1).

**Commands.**

- `build`: reads an intent file and its index, classifies any new statements, updates the index, and writes a folder containing the program and a trace file mapping each generated line to an intent statement.
- `lift`: reads a generated program and returns the intent in the standard phrases of a chosen human language, or refuses.
- `explain`: shows, in plain words, which block was chosen for each statement.
- `choose`: lets the developer replace a wrong choice by picking from a list, and records it in the index.

**Tests.**

| Test | What is checked |
|---|---|
| Classifier | At least 300 unseen wordings in each human language, across the whole inventory. Count correct choices, wrong choices and declined statements. Record how many wrong choices the type check catches. |
| Standard phrases | Every block has one standard phrase in each human language, and each resolves to that block without declining. |
| Language parity | At least 100 intent files written in both English and Spanish. Each pair must resolve to the same blocks and build byte-identical programs. |
| Index | A build with a complete index never consults the classifier. Replacing the classifier with a different version does not change the output for indexed statements. Deleting the index and rebuilding recreates it identically. |
| Equivalence | A fixed set of at least 200 pairs of intent and dataset, including the edge cases from the probe, empty input, ties, and a limit larger than the data. Every target produces byte-identical output, or every target reports the same category of error. |
| Combination | Every chain of up to four blocks after the source is enumerated. Each chain whose types fit must build in every target and pass equivalence. Each chain whose types do not fit, such as counting groups that were never formed, must be rejected with a message naming the mismatch. |
| Round trip | For every test intent, `lift` of the built program equals the intent in standard phrases, with comments stripped from the program first, so that the intent is recovered from the code and not from an embedded copy. For every generated file, `build` of its `lift` reproduces the file exactly. |
| Edited code | At least 30 hand edits to generated files: changed literals, changes that stay within the blocks, and inserted foreign statements. `lift` either returns an intent that regenerates the edited file exactly, or refuses. |
| Trace | Every non-blank generated line maps to one intent statement or is marked as fixed support code. Checked mechanically. |
| Quality | Generated code passes, with no findings, a formatter and linter configuration agreed for each target before the stage starts. |
| Diagnostics | At least 20 invalid intent files (unknown field, type mismatch, unrecognisable statement, missing source). Each is rejected with a message naming the statement. None builds. |
| Flagging | Flagging a block makes every build that uses it fail with a message naming the block, and the index lists the affected programs. |
| Determinism | Ten builds from a clean checkout produce byte-identical folders. |

Also record, for ten test intents, the generated program beside a hand-written equivalent, with line counts. This is not a pass or fail test. It is material for the discussion of value in critique point 2.

#### Stage 2 progress

Stage 2 is being built in three parts.

**Part A, the compiler core: built and tested.** Intent is written in standard phrases, in English or Spanish. There are 16 blocks: the six pipeline blocks, the plumbing needed for a whole program, and a block for calculations (part C). The meanings are in `docs/meaning.md`, the code in `cdipl/`, the tests in `tests/`, and an example in `examples/adult_users.intent`. All blocks are marked draft, because no person has reviewed them yet.

| Criterion | Result | Evidence |
|---|---|---|
| G1 Equivalence | Pass | 240 pairs of intent and dataset give byte-identical output, status and error category in Python and JavaScript. Known results on known data are also checked, so that both targets cannot be wrong in the same way unnoticed. |
| G2 Combination | Pass | All 1,555 chains of up to four blocks, now including the block that adds a calculated field: the 399 whose types fit build in both targets and agree; the 1,156 whose types do not fit are rejected with a message naming the mismatch. |
| G3 Round trip | Pass | 120 programs, in English and Spanish, in both targets: lifting the built program gives the intent in standard phrases, and rebuilding the lifted intent reproduces the file. Generated code holds no comments and no copy of the intent. |
| G4 Edited code | Pass | 69 hand edits and 10 whole-file changes: 31 edits are lifted to an intent that regenerates the edited file exactly, and the rest are refused. |
| G5 Trace | Pass | Every generated line maps to an intent line or to the block whose support code it is. |
| G6 Quality | Pass | No findings from ruff, prettier or eslint on 40 generated programs per target, with the configuration the owner accepted (default rules, line length 320). |
| G7 Diagnostics | Pass | 42 invalid intent files are each rejected with a message naming the right line. |
| G8 Flagging and determinism | Pass | Flagging any block stops every build that uses it; ten builds are byte-identical. Listing the affected programs through the index is part B. |
| G9 Meanings written first | Not met as worded | `docs/meaning.md` was written alongside the two targets, not before the second. Every difference between targets was resolved in the generated code and the meanings, and none by changing a test. |
| C5 Language parity | Pass for standard phrases | 120 programs written in English and in Spanish build byte-identical programs. Free wording is part B. |
| Sample J1 | Pass | The program generated from `examples/adult_users.intent` gives the same output as the Stage 1 sample J1 on its test input, in both targets. |

Limits of part A: the tests were written by the same assistant that wrote the compiler; they were run on one machine (Linux, Python 3.14.6, Node 22.23.4); and `docs/meaning.md` lists cases where the targets may still differ, such as very deeply nested JSON.

**Part B, free wording: built and measured. The classifier misses the owner's marks.** The full result, method and limits are in `stage2/classifier_result.md`.

The machinery works as designed: free wording builds the same program as standard phrases; a complete index is reused without consulting the classifier; replacing the classifier does not change indexed statements; an unknown word or a close call is reported and nothing is guessed; standard phrases never reach the classifier; and `explain`, `choose` and `affected` are built.

The classifier was trained on 1,080 wordings per language and frozen, then run once on 360 unseen wordings per language, covering all 90 blocks in the catalogue.

| Criterion | English | Spanish | Result |
|---|---|---|---|
| C1 Wrong choices accepted (mark: at most 1 in 300) | 3 in 360, or 1 in 120 | 3 in 360, or 1 in 120 | Not met |
| C2 Statements declined (mark: at most 25%) | 31.7% | 23.9% | Not met in English; met in Spanish |
| C3 Standard phrases resolve to their own block | Pass | Pass | Pass: they are read by fixed rules and never reach the classifier |
| C4 Index | Pass | Pass | Pass |
| C5 English and Spanish free wording build the same program | 13 of 32 hand-written pairs were accepted in both languages, and all 13 built identical programs; the rest were declined; none was accepted as the wrong block | | Pass where both are accepted |
| Best guess correct, if the classifier never declined | 93.3% | 95.3% | For information |

Each of the six wrong choices was a close neighbour of the block meant, such as a total where a per-group total was meant, or writing CSV where reading CSV was meant. A program built from them would run and give a plausible, wrong answer. No decline threshold meets both marks in either language.

**Part C, formulas: built and tested.** A formula may be a field, a whole number, text, `+`, `-` or `*` on whole numbers, `&` to join text, or any of these in brackets. Conditions compare two formulas, and `add N = formula` gives every row a calculated field. Every step of a calculation is checked against the integer range in both targets, and a result outside it stops the program with the same error in both. There is no division, no conversion between numbers and text, and no choosing between values by a condition; these are listed in `docs/meaning.md`. The criteria in the table above were re-run with formulas included.

### Next step: a live view

Asked for by the owner in the eighth and ninth rounds of decisions. A first version is built and tested. It has not been tried by any developer other than the assistant.

**What the owner asked for.** Developers write pseudocode, or short descriptions, in one pane. The generated code, in the language they chose, appears in another pane as they type, as a set of blocks. Each statement is shown against the code it produced. The classifier's choice is applied automatically, with no confirmation step. If the result is not what was meant, the developer rewords the statement and the code changes at once. Saving the file accepts the choices, which are then fixed for the project.

**Why this changes the classifier question.** The Stage 2 marks were set for a classifier that chooses unseen. In a live view nothing is unseen: a wrong choice appears on screen the moment it is made, next to the statement that caused it. On that footing the useful figure is how often the first guess is right, which was 93% in English and 95% in Spanish on wording the classifier had not seen. The product's promise changes with this, and should be stated that way: it no longer "never guesses"; it guesses in the open, and what the developer accepts is then fixed and repeatable.

**What was built.**

- `python -m cdipl live FILE` starts a server on the developer's own machine and prints an address to open in a browser. It listens on that machine only, and it can read and write only the one file it was started with.
- The page has the text on the left and the exact generated file on the right, with line numbers: the same Python, JavaScript, HTML or CSS that the `build` command writes. This is what the owner asked for after seeing a first version that showed a card for each statement.
- Putting the cursor on a statement highlights the lines of code it produced and scrolls them into view. Selecting a line of code selects the statement that produced it.
- A mark beside each line of text shows how it was read: standard phrase, chosen, chosen but unsure, accepted earlier, not understood, or understood but not built. A strip under the text shows, for the statement the cursor is on, the same statement in standard phrases, the blocks used and their review status, and, if it was not understood, why and which blocks are closest.
- A problem in one statement does not hide the rest: the code for the other statements is still shown.
- The target language can be changed in the page: Python or JavaScript for programs, HTML for pages. For pages, each generated file has its own tab, and a further tab shows the page as a browser renders it.
- **Saving accepts.** If every statement is read and the file is complete, saving rewrites the file in standard phrases. Otherwise the file is saved as typed.

**How accepted wordings are recorded.** The owner asked whether there is a better way than a separate record. There is, and it is what the live view does: on saving, the accepted wording is replaced in the file by the standard phrase it was read as. The file is then the whole record. It is read by fixed rules from then on, the classifier is never consulted for it again, nothing has to be kept in step with it, and a colleague reading the file sees exactly what will be built. The cost is that the developer's own wording is not kept; they see the standard phrase beside their wording as they type, and it is what remains after saving. The index of choices built in Stage 2 is still used by the `build` command for files that have not been saved from the live view, but it is no longer needed for files that have.

**The first web-page blocks.** Five blocks build static pages in HTML and CSS: the page itself, headings, paragraphs, a table with a column for each field of a declared data type, and buttons with an optional width in pixels. They follow the shape of the owner's pseudocode (`app`, `data`, `page`, `table`). Their meaning is in `docs/meaning.md`, and an example is in `examples/inventory.intent`. Pages convert back to intent, build identically from English and Spanish, and pass the formatter. They have structure and style and no behaviour: a table has headings and no rows, and a button does nothing.

**What has been added since the first version.**

- **Records in the intent file.** `records Product:` with one record per line is built into a JSON file.
- **Tables that fill, search and sort.** `table Product` fills itself from the records, `searchable by name` adds a search box, and `sortable by price` makes a column heading sort the table.
- **A sentence that changes something already declared.** `increase button size by 40px` changes the width of a button declared above it. The preview follows at once, and on saving the button's own line carries the new width and the sentence is gone.
- **Free wording for pages.** The classifier now knows six page blocks. In the live view, `add a big title that says "Products"` is read as a heading, and `make the button 40px wider` as a change to the button, in English and in Spanish.
- **A server, a database and an API.** With `use sqlite` and `use FastAPI`, `expose Product as api` generates a FastAPI server with a SQLite table for Product, seeded from the records, and an API to list, add, change and delete. A table of Product on a page then fills from the API.
- **Buttons with actions.** `button "Add product" adds Product` opens a form with an input for each field and adds the record through the API. `button "Suppliers" opens Suppliers` opens another page.
- **Editable tables.** `editable` under a table gives every row a control to change it and one to delete it, through the API.
- **Rules that notify.** `when Product.stock < 5:` with `notify inventory_manager` beneath stores a notification whenever a record that is added or changed meets the condition, in the same transaction as the record. `notifications` on a page lists them. Nothing is sent to anyone: the name after `notify` is a label, and delivery (email, chat) is not built.
- **Authentication.** `use authentication` makes the server refuse everything to a visitor who has not signed in, except the sign-in page and what it needs. The developer writes the sign-in page (`sign in "Name" "Password" "Sign in" "Wrong name or password"`) and a `signs out` button. Users are added from the command line (`python server.py add-user NAME`); there is no default account and no password in the intent file. Passwords are stored as scrypt hashes, sessions as hashes of random tokens, and a name is locked for five minutes after five wrong passwords.
- **The preview is the real server.** For an application with a server, the live view runs the generated server itself in a temporary folder, so adding, changing, deleting, notifications and signing in work in the preview as they will when built. With authentication it creates a user for the preview and shows the name and password under the text.
- **A package and two more commands.** `pip install -e .` gives a `cdipl` command. `cdipl new FILE --kind program|pages|app` writes a starter file in English or Spanish, and `cdipl run FILE` builds into a temporary folder and runs the result (`--target` chooses the language of a program).

The meaning of every statement, and what the generated server does not do, is in `docs/meaning.md`. Examples are `examples/inventory.intent` (pages only), `examples/inventory_server.intent` (with a server, an editable table and a rule) and `examples/inventory_auth.intent` (with authentication).

**The owner's pseudocode, line by line.**

| Line | What happens today |
|---|---|
| `app Inventory:`, `data Product:` and its fields | Built |
| `page Products:`, `table Product` | Built; the table fills from records or from the API |
| `searchable by name`, `sortable by price` | Built |
| `use sqlite`, `use FastAPI` | Built |
| `expose Product as api` | Built |
| `use web`, `use database` | Understood, not built: they do not name a technology. The owner has since said these lines should name one. |
| `use authentication` | Built. It needs a page with a `sign in` element, which the owner's pseudocode did not have, because a page carries no words the developer did not write. |
| `create postgres:`, `using docker` | Understood, not built. Neither Postgres nor Docker can be run where this was built, so nothing generated for them could have been tested. |
| `editable` | Built |
| `when Product.stock < 5:`, `notify inventory_manager` | Built: a notification is stored and can be listed on a page. Nothing is delivered to a person. |

**What the generated server fixes in advance.** Each of these is a decision the pseudocode does not state, made once by the generator. They are listed in `docs/meaning.md` so that a developer can see them.

- **Without `use authentication`, anyone who can reach the server can read and change every record.** It is safe only where that is acceptable, such as on the developer's own machine.
- **With `use authentication`, the code that protects the server is a draft.** It was written by an AI agent to a design by the assistant and reviewed by the assistant, which also probed a running server: every file and every route refused a visitor without a session, including addresses written to slip past the check. No person experienced in authentication has read it. Its limits are listed in `docs/meaning.md`; the main ones are one kind of user with full access, no way to register or reset a password except the commands, no limit on attempts per address, and that it must be put behind HTTPS for anything beyond the developer's own machine. Have it reviewed before anyone relies on it.
- Decimals are stored as text, so that no digit is lost.
- A record must have exactly the declared fields, of exactly the declared types, or it is refused.
- The first records are put into a table when it is created and never again.
- Changing a data declaration does not change a table that already exists.
- The versions of FastAPI and uvicorn are pinned to the ones the server was tested with.

**Limits that the live view does not remove.**

- **"Any description should work" cannot be promised.** The tool accepts any text and answers at once, but it can only build what is in the library, and one statement maps to one block.
- **Free wording covers statements, not structure.** The lines that open a section (`app`, `data`, `records`, `page`), the fields and the records must be written in their fixed form, and so must `use`, `expose`, buttons with an action, `editable`, `notifications`, rules and the sign-in element. The last five were added after the classifier was trained and it has not been taught them, because both sets of test wordings are used up and teaching it would need newly written ones.
- **The preview needs FastAPI and uvicorn installed** to run the real server. Without them it imitates the API: it lists the records written in the file and saves nothing.
- **A wrong choice is caught only if the developer looks.** The view shows the reading beside what was typed, and marks unsure choices, but nothing forces a look.
- **The values still have to be exact.** Names, numbers, sizes, comparisons and formulas are read by fixed rules, however freely the rest is worded.

**Evidence so far.**

| ID | Criterion | Result |
|---|---|---|
| L1 | After each change to the text, the view shows the new code within 100 ms | Met on the one machine tried: an analysis takes 1 to 3 ms once the word lists are loaded, and in a browser the new code appeared 69 ms after the text changed, which includes a deliberate 40 ms pause after the last keystroke. The first analysis of a session takes about 20 ms. |
| L2 | A statement and its code are highlighted together, in both directions | Met: the cursor's statement highlights exactly the lines the trace gives for it, in whichever file is shown, and selecting a line of code selects its statement. |
| L3 | Every statement shows what it was read as, and whether the choice was sure | Met |
| L4 | A statement that cannot be read shows why and lists the closest blocks, without hiding the rest | Met |
| L5 | An accepted wording is fixed for the project | Met by rewriting the file in standard phrases on saving |
| L6 | What the view shows is byte-identical to what `build` writes | Met for complete files, for programs, pages and applications with a server |
| L7 | Five developers who have not seen the tool each write a small program | Not done. This remains the test that says whether the idea works. |

For applications, the same criteria as Stage 2 were applied and are in the tests: every generated file passes its formatter and linter; applications convert back to intent and build identically from English and Spanish; edited files are lifted exactly or refused; invalid descriptions are rejected with their line. In addition, the generated server is imported and exercised by the tests, and it was run with uvicorn and used from a real browser: the table filled from the API, a record was added through the form and was still there after the server was restarted, and the server did not serve its own code, its database or its seed file.

The later additions were checked the same way. Editable tables and rules: in a real browser a record was changed and deleted, a change that met the rule put a notification in the list, and one that did not put none. Authentication: 29 tests on the generated server and its commands, and by hand over a real connection, as described above. In the live view's preview, in a real browser, a wrong password showed the developer's message, the right one opened the first page, a record was changed, a notification appeared, and signing out returned to the sign-in page.

Screenshots: `docs/live-view-program.png`, `docs/live-view-pages.png` and `docs/live-view-preview.png` show the live view; `docs/live-view-c.png` shows it generating C; `docs/live-view-app.png` shows the preview of the application with authentication after signing in; `docs/generated-app.png` and `docs/generated-app-form.png` show the generated application running.

### Stage 3: third target

*The plan as written before the work; the result follows it.*

Add C, as the owner decided. Java follows later.

C will show the cost of a target more sharply than any other choice. *From general knowledge, not checked in this review:* C's standard library does not read JSON; C has no built-in growable lists or records, so memory is managed by hand; and its standard text comparison works on bytes. Since generated programs must be complete and depend on nothing from CDIPL, the C output will either carry a large amount of fixed support code or the input format must be one C can read simply. That choice (D1) should be made before Stage 2, because it affects all targets.

Record the effort relative to the second target, which written meanings needed special handling, how much of each generated C program is fixed support code, and any dependency required. The same tests apply. If C cannot meet the written meaning for a block, the target must declare it and the compiler must refuse that block for C.

#### Stage 3 result

Built in revision 13: C, and Java as well, since the owner had named it as the next target. Each was written by an AI agent working from `docs/meaning.md` and the existing targets, and then merged and checked by the assistant. The details are in `docs/target-c.md` and `docs/target-java.md`.

**The same tests pass.** Registering a target puts it through every existing test with no change to the tests' substance: all 240 equivalence pairs and all 399 fitting chains of the combination test give the same output and exit status in Python, JavaScript, C and Java. No block had to be declared unsupported in either language, so the compiler's refusal of unsupported blocks (which exists) was not needed. Round trip, exact lifting of edited files (47 hand edits in C, 48 in Java, each lifted exactly or refused) and the trace hold for both.

**Quality.** Generated C compiles with gcc and clang under `-std=c11 -Wall -Wextra -Werror -pedantic` with no warnings, is unchanged by clang-format, and uses only the C standard library. Generated Java compiles with `javac -Xlint:all -Werror` with no output and uses only `java.base`; no Java formatter was available, so none was applied.

**D1, the input format, is settled by the result:** JSON stays. Each C and Java program carries its own JSON reader, written once as a block.

**The cost of a target (criterion G10).**

| | Python | JavaScript | C | Java |
|---|---|---|---|---|
| Fixed support code in a typical generated program (non-blank lines) | 77 | 107 | 495 | 364 |
| of which the JSON reader | 9 | 7 | 226 | 195 |
| Generator source (lines) | 460 | 545 | 1,253 | 1,073 |

- A generated C program is about 520 lines for the ten-line example, and a Java one about 400, against 86 for Python. The code is fixed and written once, but it is what a reviewer has to read before the blocks can be called verified.
- Where the meanings needed special care: the integer rule (defined by double-precision reading, reproduced in C with `strtod` and range checks, and in Java with `Double.parseDouble`), surrogate escapes in JSON, a sort that keeps equal rows in order (C has none), integer overflow (Java adds small literals as `int` unless forced to `long`), and nesting depth, where the targets differ and the specification now says so.
- The Java work found two inexact statements in `docs/meaning.md` (Python's nesting limit, and that "a whole number" is tested on the nearest double). Both are corrected, and the second was confirmed to behave identically in all four languages.
- The test suite went from 45 seconds to about two and a half minutes, mostly compiling. It now needs `gcc` and `javac`.
- Effort was not measured in person-hours, because agents did the work: each target took one agent session of 35 to 45 minutes, against a specification and two existing targets to copy from. That says little about what a person would need.

**What this does not show.** Both targets cover the 16 blocks of the pipeline family only. Nothing was learned about C or Java for other kinds of intent.

### Not included

Editing of existing code, hand-written code inside intent files, IDE integration and performance measurement. Markup and framework blocks, first listed here, were later asked for by the owner and are described under [Next step: a live view](#next-step-a-live-view).

### Suggested time budget

*My estimates, not validated, and made for one engineer:* about one week for Stage 1, three to four weeks for Stage 2, and one to two weeks for Stage 3. With the assistant building, elapsed time will depend mostly on how quickly briefs, blocks and results are reviewed. Each stage ends with a review by the owner before the next begins.

## Evidence that would count as success

Fix these before any result is seen. The owner has ratified the classifier pass marks C1 and C2. The owner has accepted the Stage 1 result as a pass. The compiler criteria remain proposals. All are judgment calls with no empirical basis.

**Stage 1.**

| Share of sample programs in which every unit is closed | Reading |
|---|---|
| 30% or more | Not ruled out on favourable material. Continue. |
| Between 10% and 30% | Owner's decision. The first version would produce few complete programs. |
| Below 10% | Even favourable material is mostly out of reach. Stop, or revisit the decision on hand-written code. |

**Stage 2, classifier.**

| ID | Criterion | Pass mark |
|---|---|---|
| C1 | Wrong choices that are accepted, meaning not declined and not caught by the type check | At most 1 in 300 unseen wordings, in each human language |
| C2 | Statements declined | At most 25% |
| C3 | Standard phrases | All resolve to their own block |
| C4 | Index | All three index checks hold |
| C5 | Language parity | Every English and Spanish pair resolves to the same blocks and builds the same program |

C1 is strict because an accepted wrong choice produces a wrong program with no warning.

**Stages 2 and 3, compiler. All must hold.**

| ID | Criterion |
|---|---|
| G1 | Equivalence: no pair on which targets differ. |
| G2 | Combination: every chain whose types fit builds and passes; every chain whose types do not fit is rejected. |
| G3 | Round trip: holds for every test intent and every generated file, in every target. |
| G4 | Edited code: `lift` never returns an intent that fails to regenerate the file it was given. One such case fails the stage. |
| G5 | Trace: complete, with no unmapped lines. |
| G6 | Quality: no formatter or linter findings in any generated file. |
| G7 | Diagnostics: every invalid file rejected with its statement; none built. |
| G8 | Flagging and determinism: both tests pass. |
| G9 | The written meanings existed before the second target, and every difference found between targets was resolved by changing a meaning or a target, not a test. |
| G10 | Stage 3 only: the effort for C is recorded, and any unsupported block is refused by the compiler, not mistranslated. *Result: the cost is recorded under [Stage 3 result](#stage-3-result); no block was unsupported.* |

**What would disprove the idea.** Stage 1 below its floor disproves usefulness for the first version as scoped. Failure of C1 that cannot be fixed without declining most statements disproves "the classifier chooses" as a safe design. Failure of G1 or G2 that can be fixed only by restricting the blocks until they are no longer useful disproves the multi-target or the Lego claim for this family. Failure of G4 disproves reversibility as stated.

**What success would not show.** That real programs, as opposed to generated samples, can be covered; that the classifier stays accurate with hundreds of blocks; that developers find this more enjoyable or more controllable than the alternatives; that markup or framework blocks work; that many kinds of intent in many languages can be maintained at acceptable cost.

**What happens next.**

| Outcome | Next step |
|---|---|
| All stages pass | Start the roadmap below, one step at a time, taking the next blocks from the Stage 1 inventory. Check coverage on real programs before the framework tier. |
| C1 or C5 fails | Revisit the decision that the classifier chooses without confirmation, and the word lists, before going further |
| G1 or G2 fails | Reduce to one target language and re-examine the claim that failed |
| Stage 1 fails | Stop before writing the compiler, or revisit the decision on hand-written code |

## Roadmap after the proof of concept

This follows the owner's order. Each step adds either a target for existing blocks or a new kind of intent, and each should pass the same tests before the next begins. It is a direction, not a schedule; nothing beyond Stage 3 is planned in detail.

| Tier | Owner's item | What it adds | What is new and untested |
|---|---|---|---|
| 1 | Python, JavaScript | First two targets | Covered by Stages 1 and 2 |
| 2 | C, then Java | More targets for the same blocks | Built for the pipeline family; see [Stage 3 result](#stage-3-result). |
| 2 | HTML with CSS | A new kind of intent: pages and layout | Built, with JavaScript for behaviour. There is one target for pages, so equivalence between targets has not been tested for them. |
| 3 | FastAPI, Django | New kinds of intent: endpoints and data models | FastAPI with SQLite is built, including authentication. Django is not, so whether one intent can target two frameworks is still untested. |
| 4 | React with CSS | A new kind of intent: stateful components | State and events; equivalence across UI frameworks |

At each tier, repeat the classifier test against the enlarged library.

## Out of scope: editing existing code

The owner has decided that the first version does not work on code it did not generate. The proposal's transformation mode (§6.2 to §6.5, §8, §12) is therefore out of scope.

For the record, revision 1 of this plan examined it and ran a browser probe on nine simple cases of "make this element 10% wider". The browser reported the exact file, line and column of every matching width declaration. The proposal's rule of multiplying the declared width failed in five of the nine cases: three had nothing to edit, one produced no visible change, and one gave 7.9% in place of 10%. The full results, and a design for a proof of concept, are in revision 1 of this file at commit `d23ae96`.

## Major risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| The classifier accepts a wrong block | A wrong program is produced with no warning | Declining; type check; `explain`; criterion C1. A residual rate remains, which the owner has accepted. |
| Classifier accuracy falls as the library grows | Six blocks prove little | Test against the whole Stage 1 inventory; repeat at every tier |
| Too few real programs consist entirely of blocks | Complete programs with no hand-written code means partial coverage is no coverage | Stage 1 passed on favourable material only; test on real programs before the framework tier |
| The library must be very large to be useful | Stage 1 needed about 90 blocks for 20 small programs, most used once | Build blocks in order of reuse; track how many new blocks each new program needs |
| Developers cannot see or correct a choice | Undermines the goal of control | The `explain` and `choose` commands |
| A word means different things in different contexts | One code per word loses the distinction, in any human language | Entries for set phrases and word forms; unknown words reported; the parity test (C5) |
| The builder checks its own work | The assistant writes the briefs, sample programs, blocks, example wordings and tests | Owner approval of briefs; human review before a block is verified; test wordings set aside before training material is written; programs for Stage 1 written without knowledge of their purpose |
| Cost grows with kinds of intent multiplied by targets | Every block is written per target and must stay equivalent; every human language needs a word list and standard phrases | Stage 3 measures one added target; one roadmap step at a time |
| Targets drift apart in meaning | The probe found four differences in two operations | Written meanings; equivalence tests on every change (G1, G9) |
| Blocks interact badly when combined | Tests of single blocks do not cover joins | Typed interfaces; the combination test (G2) |
| C makes complete, dependency-free programs expensive | Large fixed support code in every program | Measured in Stage 3: about 500 lines per program, written once. It is the reviewer's burden, not the developer's. |
| Developers cannot adjust generated code | Edits that do not convert back are refused, by the owner's rule | Accepted for the first version; watch for it in early use |
| Existing tools already do this well | Not evaluated in this review | A prior-art survey before Stage 2 is recommended |
| Scope returns to "everything at once" | The proposal's breadth is its main delivery risk (§10.9) | The roadmap's one-step rule and a review after each stage |

## Decisions made by the assistant

In the twelfth round the owner asked for the work to be done without further questions. These are the choices that would otherwise have been put to the owner. Each can be reversed; none changes a decision in the table at the top.

| Topic | What the assistant chose | Why |
|---|---|---|
| What to build | Everything in the owner's pseudocode that could be tested here: editable tables, rules that notify, authentication; C and Java targets; a package with `new` and `run` commands | The owner's roadmap and pseudocode, in order |
| Postgres and Docker | Not built; the lines are still recognised and reported | Neither can be run where this was built, and generated code that has never run would break the rule that blocks are tested |
| Django, React | Not built | Each is a second target for a kind of intent, which is the roadmap's hardest untested question, and deserves its own stage |
| `use web`, `use database` | Still reported as not built, with a suggestion to name a technology | The owner said parts are chosen by naming a technology |
| What `notify` does | Stores a notification that a page can list. Nothing is delivered. | Delivery needs a mail or chat service and credentials, which the pseudocode does not name |
| How users are created | From the command line of the generated server. No default account, no password in the intent file, no self-registration. | A default account or a password in a file under version control is the commonest way such systems are broken |
| The sign-in page | Written by the developer with a `sign in` element carrying four texts | A page carries no words the developer did not write, which also keeps English and Spanish builds identical |
| Free wording for the new statements | None. `editable`, `notifications`, rules, the sign-in element and `signs out` are read in their fixed form only. | Both sets of test wordings have been used. Teaching the classifier new blocks honestly needs new wordings written by someone who has not seen the training material. |
| Input format for C and Java (D1) | JSON, with a reader carried in each program | Keeps every target's programs interchangeable; the cost is measured in [Stage 3 result](#stage-3-result) |
| Review status | Every block stays a draft | Only the owner or another professional developer can mark a block reviewed |
| Method | Five AI agents did the building in separate copies of the repository (packaging, C, Java, editable tables and rules, authentication), each to a written brief; the assistant merged, ran the whole test suite after each merge, changed what it found wrong, and probed the results by hand | The owner asked for agents to do the routine work |

What the assistant changed after the agents reported: generated C now uses ordinary `#include` lines (the agent had used the digraph `%:` to get past a test written for Python); the sign-in form is marked to post, so that a password can never be put in an address; `cdipl run` takes `--target`; a file is matched to its language by its whole extension; two statements in `docs/meaning.md` were corrected; and the live view's file tabs wrap.

## Open decisions

Each has a default that this plan assumes if nobody decides otherwise.

| ID | Decision | Default assumed here |
|---|---|---|
| D1 | Input format for generated programs | Settled by Stage 3: JSON |
| D2 | What should be built next? The candidates are: a review of the blocks by a person, starting with authentication; the five-developer test (L7); new wordings so that the classifier can be taught the newer statements; Postgres; Django as a second target for applications; delivery of notifications. | The review and the five-developer test, because everything built so far rests on the assistant's own checking |
| D3 | Which other button actions are wanted? Three are built: add a record, open a page, sign out. | Decide from real use |
| D4 | Should a generated server without authentication refuse to listen beyond the local machine? | Not enforced: uvicorn chooses the address, not the generated code. `cdipl run` listens on the local machine only, and the documentation warns. |
| D5 | What should `use web` and `use database` mean, if anything? | Nothing: report them as not built and suggest `use FastAPI` and `use sqlite` |
| D6 | Who are the five developers for criterion L7, and when? | The owner arranges it |
| D7 | Who reviews the authentication blocks, and should `use authentication` print a warning at every build until they have? | Every build already lists the draft blocks it used. A person experienced in authentication should review them before any use beyond the developer's own machine. |
| D8 | Should roles or per-record permissions be added to authentication? | No, until someone needs them |

## Assumptions

- No implementation exists beyond what is in the repository at commit `194e44b`. Verified for this checkout only.
- The proposal and the owner's answers are the only statements of intent.
- "No LLM generates the code" applies to what runs when a developer builds. The owner has confirmed that an AI assistant may build the compiler, the blocks and the example wordings.
- A classifier that is not an LLM is acceptable, including one that uses a small language model internally, provided it only selects among existing blocks.
- Statements about existing tools, classifiers, C and the history of similar efforts are general knowledge, not the result of a survey or test.
- Effort estimates are unvalidated.

## Positions on the proposal's evaluation questions (§13)

| Q | Position |
|---|---|
| 1 | By the owner's decision the classifier chooses blocks from free wording. It is useful only because wording is free; with a fixed grammar it would add nothing. Its accuracy is a success criterion. |
| 2 | A chain of blocks with declared input and output types over a declared source, plus an index recording which block each statement resolved to. |
| 3 | The classifier declines below a set margin and the compiler reports a diagnostic. Scores are never shown as evidence of correctness. |
| 4 to 8 | These concern editing existing code, which is out of scope for the first version. Findings are summarised under "Out of scope". |
| 9 | Each target declares the blocks it supports, and the compiler refuses the rest for that target. |
| 10 | Not done in this review. A prior-art survey is recommended before Stage 2. |
| 11 | Generated programs are executed during testing, so tests run in an isolated environment. |
| 12 | See "Evidence that would count as success". |
| 13 | See "What would disprove the idea". |

## Appendix: probe inputs and method

Input (`data.json`):

```json
[{"name":"～","age":9007199254740993},{"name":"😀","age":9007199254740992},{"name":"b","age":18},{"name":"B","age":18.0},{"name":"a"}]
```

| Check | Python | JavaScript |
|---|---|---|
| Sort | `sorted(d, key=lambda u: u['name'])` | `sort` with a comparator using `<` and `>` on `name` |
| Large integers | first two records, `u['age'] > 9007199254740992` | first two records, `u.age > 9007199254740992` |
| Number output | `json.dumps` of the ages of records 3 and 4 | `JSON.stringify` of the same |
| Missing field | `[u for u in d if u['age'] >= 18]` | `d.filter(u => u.age >= 18)` |

Full sort results: Python gave `B, a, b, ～, 😀`; JavaScript gave `B, a, b, 😀, ～`.
