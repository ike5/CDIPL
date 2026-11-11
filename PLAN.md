# PLAN: Evaluation of the CDIPL proposal and a first proof of concept

| | |
|---|---|
| **Reviewed** | `outputs/proposal-classifier-driven-intent-programming-language.md` (v0.2) and this repository at commit `194e44b` |
| **Revision** | 4, dated 2026-11-11. It incorporates three rounds of decisions from the product owner. Revision 1 (commit `d23ae96`) led with an engine for editing existing code, which the owner has since ruled out for the first version. |
| **Status** | Recommendation for the development team. Nothing in this plan has been built. |
| **Audience** | Engineers deciding whether to build this, and what to build first |

References such as "§8" point to sections of the proposal. Sections of this plan are referred to by name.

## Conclusion

As decided by the product owner, CDIPL works like this. A developer writes intent in a file, in their own wording. A fast classifier chooses, for each statement, the matching block from a library of code blocks that were tested and reviewed in advance. The compiler records each choice in an index, joins the blocks like Lego, and writes out a complete program as folders of code in the chosen language. No LLM writes code. Generated code can be converted back to intent and traced to it. The aim is to make programming enjoyable again by leaving the developer in control.

- **Coherent?** Yes, with five conditions.
  - **Reproducible is not the same as correct.** The index makes a build repeatable: once a choice is recorded, the same intent file always produces the same program. It does not make the choice right. A classifier is a statistical tool and will sometimes choose the wrong block. How often, and how the developer finds out, become central questions.
  - **The classifier must be able to decline.** The proposal itself requires a diagnostic instead of a guess when wording is ambiguous (§4). The plan keeps that.
  - **Reversibility** holds only for code the tool generated that is still in a form the tool would generate. The owner has accepted this.
  - **Several languages** requires the same intent to mean the same thing in every target, which is not automatic (see [Probe](#probe-the-same-operation-in-two-languages)).
  - **Blocks tested one at a time are not thereby tested in combination.** Blocks need declared input and output types, and the compiler must check every join.
- **Worth pursuing?** Yes, as a staged experiment with a review after each stage. The compiler mechanics are established engineering and I expect them to work. Two things are uncertain. One is usefulness: the first version generates complete programs and allows no hand-written code, so a program can be generated only if every part of it is in the library. The other is classifier accuracy as the library grows.
- **Smallest proof of concept:**
  1. **Block inventory**, with no product code: work out, from sample programs, which blocks a library would need and how many sample programs it could produce in full.
  2. **Pipeline slice**: six blocks from the proposal's own examples, with a classifier, an index and two targets (Python and JavaScript), tested for correct choices, identical behaviour, every valid combination, conversion back to intent, and tracing.
  3. **Third target**: add C, to measure what each additional language costs.

One caution about what Stage 2 can show. Small blocks in Python and JavaScript are the right place to prove the mechanics and the wrong place to prove value: the hand-written equivalent of the first example is one line. The value is in large blocks such as framework code, which the roadmap reaches later, and that is also where keeping targets equivalent is hardest.

## Product decisions made by the owner

| Topic | Decision | Effect on this plan |
|---|---|---|
| Product claim | A deterministic generator of code. No LLM generates the code. | Fixed |
| Goal | Make programming enjoyable again by giving developers control | Recorded as the product goal; see critique point 8 |
| Building blocks | Tested, listed and formatted, with human review; easy to flag when an error is found; assembled like Lego | The library is the product; Stage 2 is built around it |
| Classifier | It chooses the blocks from the intent. It does not ask the developer to confirm. | Now part of Stage 2; accuracy becomes a success criterion |
| Index | The compiler records chosen blocks in an index for fast lookup. Entries need not be readable, so the intent file never has to name components. | Designed in Stage 2; see critique points 7 and 8 |
| Output | Complete programs, written out as folders of code | Coverage is all or nothing (critique point 1) |
| Hand edits to generated code | Allowed only if they convert back to intent | Tested in Stage 2 |
| Existing code CDIPL did not generate | Not supported | The edit engine is out of scope |
| Hand-written code inside intent files | Not in the first version | With "complete programs", makes coverage central |
| Order of targets | Python and JavaScript; then C, then Java; HTML with CSS; then FastAPI and Django; then React with CSS | See [Roadmap](#roadmap-after-the-proof-of-concept) |
| Sample material for Stage 1 | Generated by an AI assistant, not taken from real requests or open-source code | Changes what Stage 1 can show (critique point 10) |
| Implementation language | Python is not required | Open (D6) |
| Pace | Generate a small amount, review, then generate more | Three stages with a review after each |

## Basis and limits of this review

What was examined:

- **The repository.** It contains no implementation. `main.py` is the PyCharm sample script, `pyproject.toml` declares `requires-python >=3.14` with no dependencies, build system or tool configuration, and there are no tests. The only substantive file is the proposal.
- **The proposal**, read in full, and the owner's written decisions summarised above.
- **A probe** on generating for several languages: the same sort and filter written the obvious way in Python 3.13.18 and Node 22.23.4, run on five records. Inputs and method are in the [Appendix](#appendix-probe-inputs-and-method). The script was not committed.
- **An earlier probe** on editing an existing stylesheet in a browser, summarised under [Out of scope](#out-of-scope-editing-existing-code).

What was not done:

- No part of the proposed system was implemented. No classifier was trained or measured.
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

   What remains is a residual error rate greater than zero. Whether that is acceptable for a product described as deterministic is the owner's call (D2).

8. **Unreadable index entries and developer control pull against each other.** The owner wants developers in control and does not want them to name components. If the classifier chooses silently and the record of its choice is unreadable, the developer has two ways to find a wrong choice: read the generated code, or notice wrong behaviour. They have one way to fix it: reword the intent and try again, which is the trial and error that makes prompting an LLM frustrating. The plan therefore proposes two tool commands that keep the intent file free of component names: one that shows, in plain words, which block was chosen for each statement, and one that lets the developer pick a different block from a list when the choice was wrong, writing the result to the index (D1).

9. **The classifier needs example wordings, and gets harder as the library grows.** A classifier learns from labelled examples: many wordings for each block. Someone has to write them (D4). *Assumption, from general knowledge: accuracy falls as the number of blocks rises and as blocks become more alike.* Six blocks will be easy and prove little. Stage 2 therefore measures the classifier against the whole inventory from Stage 1, not only the six blocks that are implemented.

10. **Generated sample programs are a favourable case, not a representative one.** The owner has decided that Stage 1 uses programs generated by an AI assistant. Such programs are regular and tutorial-like, and the same assistant that writes them would be judging how block-like they are. Stage 1 can therefore show which blocks to build first, and a poor result on this favourable material would be strong evidence against the idea. A good result would not show that real programs can be covered. That question stays open, and is carried as a risk.

11. **Reversibility returns the standard wording, not the developer's.** Many wordings lead to one block, so the original wording cannot be recovered from code. Each block therefore has one standard phrase. Converting code back gives the intent in standard phrases, and each standard phrase must always resolve to its own block. The rule is: converting a file back either returns an intent that regenerates that file exactly, or refuses. *Assumption, from general knowledge: earlier model-driven tools that promised round trips between models and code struggled once developers edited the generated code.* The owner's rule avoids that by refusing such edits.

### The proposal document

12. **No shared representation is shown.** The two examples in §5 have no fields in common. The representation is called typed, but the examples carry no types and do not say where `users` is bound. Block interfaces with declared types, as required in point 3, would supply what is missing.

13. **The proof of concept in §12 is superseded.** It tests the editing of an existing React project, which the owner has ruled out for the first version.

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

## Proof of concept

### The hypothesis being tested

For one family of intents: a classifier can choose the right block from freely worded statements, declining when unsure; a compiler can join the chosen blocks into complete programs in at least two languages that behave identically on the same input, in every valid combination; and those programs convert back to intent and trace line by line to it.

### Stage 1: block inventory

No product code.

1. Write short briefs for at least 20 small programs, half for Python and half for JavaScript: one or two sentences each on what the program should do. The owner or the team writes or approves the list before any code is generated (D8), so that the choice of programs is theirs.
2. An AI assistant generates each program from its brief, as the owner decided.
3. Split each program into units: its functions, or the whole script if it has none.
4. Classify each unit:
   - **Closed:** it could be stated entirely as a chain of named operations with parameters.
   - **Open:** it contains logic particular to that program.
   - For closed units, name the block or blocks it would need.
5. Report the share of whole programs in which every unit is closed; the share of units that are closed; the list of distinct blocks, with how often each occurs; and how many blocks would cover 50% and 80% of the closed units.

The block list is the main product of this stage. It sets the order in which blocks are built and gives the classifier in Stage 2 a realistic number of blocks to choose among.

Limit: see critique point 10. The result describes generated sample programs.

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
source users from "users.json":
    name: text
    age: integer
    school: text

get users where age >= 18
sort by name ascending
limit 10
```

The second statement might equally be written "order by name ascending". Fields have declared types, `integer` and `text`. Comparisons use `=`, `!=`, `<`, `<=`, `>`, `>=`, joined by `and`, and are read exactly.

**Classifier.** Start with the simplest kind that works and record what was used. It is stored as a fixed file with a version. It is trained on example wordings for every block in the Stage 1 inventory, including blocks that are not implemented, and tested on wordings written by people who did not write the training examples (D4).

**Index.** A file written beside the intent file and committed with it. Entries use block identifiers, not names.

**Written meanings.** One page that fixes, independently of any target: the ordering of text, the range of integers, what happens when a field is missing or has the wrong type, the order of groups, and the order of rows that tie in a sort.

**Targets.** Python and JavaScript. Each build produces a complete program that reads a data file and writes its result. Generated programs contain plain code and depend on nothing supplied by CDIPL. The input format is an open decision (D5).

**Commands.**

- `build`: reads an intent file and its index, classifies any new statements, updates the index, and writes a folder containing the program and a trace file mapping each generated line to an intent statement.
- `lift`: reads a generated program and returns the intent in standard phrases, or refuses.
- `explain`: shows, in plain words, which block was chosen for each statement.
- `choose`: lets the developer replace a wrong choice by picking from a list, and records it in the index (D1).

**Tests.**

| Test | What is checked |
|---|---|
| Classifier | At least 300 unseen wordings across the whole inventory. Count correct choices, wrong choices and declined statements. Record how many wrong choices the type check catches. |
| Standard phrases | Every block's standard phrase resolves to that block without declining. |
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

### Stage 3: third target

Add C, as the owner decided. Java follows later.

C will show the cost of a target more sharply than any other choice. *From general knowledge, not checked in this review:* C's standard library does not read JSON; C has no built-in growable lists or records, so memory is managed by hand; and its standard text comparison works on bytes. Since generated programs must be complete and depend on nothing from CDIPL, the C output will either carry a large amount of fixed support code or the input format must be one C can read simply. That choice (D5) should be made before Stage 2, because it affects all targets.

Record the effort relative to the second target, which written meanings needed special handling, how much of each generated C program is fixed support code, and any dependency required. The same tests apply. If C cannot meet the written meaning for a block, the target must declare it and the compiler must refuse that block for C.

### Not included

Editing of existing code, hand-written code inside intent files, markup and framework blocks, IDE integration, performance measurement, and any family beyond the first.

### Suggested time budget

*My estimates, not validated:* about one week for Stage 1, three to four weeks for Stage 2, and one to two weeks for Stage 3, for one engineer. Agree a hard stop for each stage before starting it (D7).

## Evidence that would count as success

Fix these before any result is seen. The numbers are proposals for the owner and team to ratify. They are judgment calls with no empirical basis.

**Stage 1.**

| Share of sample programs in which every unit is closed | Reading |
|---|---|
| 30% or more | Not ruled out on favourable material. Continue. |
| Between 10% and 30% | Owner's decision. The first version would produce few complete programs. |
| Below 10% | Even favourable material is mostly out of reach. Stop, or revisit the decision on hand-written code. |

**Stage 2, classifier.**

| ID | Criterion | Proposed pass mark |
|---|---|---|
| C1 | Wrong choices that are accepted, meaning not declined and not caught by the type check | At most 1 in 300 unseen wordings |
| C2 | Statements declined | At most 25% |
| C3 | Standard phrases | All resolve to their own block |
| C4 | Index | All three index checks hold |

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
| G10 | Stage 3 only: the effort for C is recorded, and any unsupported block is refused by the compiler, not mistranslated. |

**What would disprove the idea.** Stage 1 below its floor disproves usefulness for the first version as scoped. Failure of C1 that cannot be fixed without declining most statements disproves "the classifier chooses" as a safe design. Failure of G1 or G2 that can be fixed only by restricting the blocks until they are no longer useful disproves the multi-target or the Lego claim for this family. Failure of G4 disproves reversibility as stated.

**What success would not show.** That real programs, as opposed to generated samples, can be covered; that the classifier stays accurate with hundreds of blocks; that developers find this more enjoyable or more controllable than the alternatives; that markup or framework blocks work; that many kinds of intent in many languages can be maintained at acceptable cost.

**What happens next.**

| Outcome | Next step |
|---|---|
| All stages pass | Start the roadmap below, one step at a time, taking the next blocks from the Stage 1 inventory. Check coverage on real programs before the framework tier. |
| C1 fails | Revisit how the classifier's choices are checked (D1, D2) before going further |
| G1 or G2 fails | Reduce to one target language and re-examine the claim that failed |
| Stage 1 fails | Stop before writing the compiler, or revisit the decision on hand-written code |

## Roadmap after the proof of concept

This follows the owner's order. Each step adds either a target for existing blocks or a new kind of intent, and each should pass the same tests before the next begins. It is a direction, not a schedule; nothing beyond Stage 3 is planned in detail.

| Tier | Owner's item | What it adds | What is new and untested |
|---|---|---|---|
| 1 | Python, JavaScript | First two targets | Covered by Stages 1 and 2 |
| 2 | C, then Java | More targets for the same blocks | Manual memory and no built-in data formats in C; static types in both. Stage 3 covers C. |
| 2 | HTML with CSS | A new kind of intent: pages and layout | A new set of blocks. "Identical behaviour" needs a new definition, because the output is rendered, not computed. |
| 3 | FastAPI, Django | New kinds of intent: endpoints and data models | Large blocks; dependence on framework versions; whether one intent can target two frameworks at all |
| 4 | React with CSS | A new kind of intent: stateful components | State and events; equivalence across UI frameworks |

At each tier, repeat the classifier test against the enlarged library.

## Out of scope: editing existing code

The owner has decided that the first version does not work on code it did not generate. The proposal's transformation mode (§6.2 to §6.5, §8, §12) is therefore out of scope.

For the record, revision 1 of this plan examined it and ran a browser probe on nine simple cases of "make this element 10% wider". The browser reported the exact file, line and column of every matching width declaration. The proposal's rule of multiplying the declared width failed in five of the nine cases: three had nothing to edit, one produced no visible change, and one gave 7.9% in place of 10%. The full results, and a design for a proof of concept, are in revision 1 of this file at commit `d23ae96`.

## Major risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| The classifier accepts a wrong block | A wrong program is produced with no warning | Declining; type check; `explain`; criterion C1. A residual rate remains (D2). |
| Classifier accuracy falls as the library grows | Six blocks prove little | Test against the whole Stage 1 inventory; repeat at every tier |
| Too few real programs consist entirely of blocks | Complete programs with no hand-written code means partial coverage is no coverage | Stage 1 gives a one-sided check only; test on real programs before the framework tier |
| Developers cannot see or correct a choice | Undermines the goal of control | The `explain` and `choose` commands (D1) |
| Cost grows with kinds of intent multiplied by targets | Every block is written per target and must stay equivalent | Stage 3 measures one added target; one roadmap step at a time |
| Targets drift apart in meaning | The probe found four differences in two operations | Written meanings; equivalence tests on every change (G1, G9) |
| Blocks interact badly when combined | Tests of single blocks do not cover joins | Typed interfaces; the combination test (G2) |
| C makes complete, dependency-free programs expensive | Large fixed support code in every program | Decide the input format before Stage 2 (D5) |
| Developers cannot adjust generated code | Edits that do not convert back are refused, by the owner's rule | Accepted for the first version; watch for it in early use |
| Existing tools already do this well | Not evaluated in this review | A prior-art survey before Stage 2 is recommended |
| Scope returns to "everything at once" | The proposal's breadth is its main delivery risk (§10.9) | The roadmap's one-step rule and a review after each stage |

## Open decisions

Each has a default that this plan assumes if nobody decides otherwise.

| ID | Decision | Default assumed here |
|---|---|---|
| D1 | How does a developer see and correct a wrong choice by the classifier, without naming components in the intent file? | Two tool commands: `explain` shows the choices in plain words; `choose` picks a replacement from a list and records it in the index |
| D2 | What rate of accepted wrong choices is tolerable, and how many statements may the classifier decline? | At most 1 in 300 wrong; at most 25% declined |
| D3 | Who writes the compiler and the blocks? The owner answered "no" to an LLM drafting them with human verification, and also said an AI assistant should "generate the code". These need reconciling. | People write the compiler and the blocks. An AI assistant generates only the Stage 1 sample programs. |
| D4 | Who writes the example wordings that train and test the classifier? | People on the team. Test wordings come from people who did not write the training wordings. |
| D5 | Input format for generated programs, given that C cannot read JSON without added code | Decide before Stage 2. Until then, JSON, with fixed support code written out in full where a target needs it. |
| D6 | Language the compiler is written in | Python, because the repository is already set up for it. *Assumption: converting generated JavaScript and C back to intent is practical from Python; not tested.* |
| D7 | Ratify the pass marks and the time budget per stage | The values proposed above |
| D8 | Who writes or approves the Stage 1 program briefs | The owner |

## Assumptions

- No implementation exists beyond what is in the repository at commit `194e44b`. Verified for this checkout only.
- The proposal and the owner's answers are the only statements of intent.
- "No LLM generates the code" applies to what runs when a developer builds. Whether it also applies to how the team builds the product is decision D3.
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
