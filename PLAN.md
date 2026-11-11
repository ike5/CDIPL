# PLAN: Evaluation of the CDIPL proposal and a first proof of concept

| | |
|---|---|
| **Reviewed** | `outputs/proposal-classifier-driven-intent-programming-language.md` (v0.2) and this repository at commit `194e44b` |
| **Revision** | 2, dated 2026-11-11. Revision 1 led with the engine that edits existing code. This revision follows the product owner's clarifications and leads with generating code from intent files. |
| **Status** | Recommendation for the development team. Nothing in this plan has been built. |
| **Audience** | Engineers deciding whether to build this, and what to build first |

References such as "§8" point to sections of the proposal. Sections of this plan are referred to by name.

## Conclusion

As clarified by the product owner, CDIPL is a language in which a developer writes intent in a file. A deterministic compiler, with no generative model, turns that file into folders of code in several target languages, for frontend, backend and shell scripting. Generated code can be converted back to intent and traced to it. The product is meant to replace the use of LLM coding assistants.

- **Coherent?** The core is. A deterministic compiler from a declarative language to several targets is established engineering. Three claims need narrowing before they are coherent:
  - **Reversibility** can hold only for code the tool generated and that is still in the form the tool would generate. Turning arbitrary hand-written code back into intent is a different and much harder problem.
  - **"Several languages"** requires the same intent to mean the same thing in every target. That is not automatic, even for sorting and comparing (see [Probe 2](#probe-2-the-same-operation-in-two-languages)).
  - **The classifier** does no work under the proposal's own rules.
- **Worth pursuing?** Not as a general replacement for LLM assistants. That claim is unsupported by the proposal, and I expect it not to hold: without a generative model, the tool can do only what has been hand-built for each kind of task and each target language, while the appeal of an LLM is that it accepts any request. As a deterministic, traceable generator for a few common kinds of task, it is plausible and cheap to test. Stage 1 of the proof of concept measures which of these two descriptions the evidence supports.
- **Smallest proof of concept:** three stages, with a review after each.
  1. **Demand audit**, with no code: sort a sample of real coding requests into kinds, and measure how many a fixed vocabulary could cover.
  2. **Pipeline slice**: the six operations in the proposal's own examples, compiled to two languages, tested for identical behaviour, conversion back to intent, and tracing.
  3. **Third target**: add bash, to measure what each additional language costs.

The engine that edits existing code, which revision 1 led with, is deferred. Whether it is needed at all depends on an open decision (D2).

## Product intent as clarified by the owner

| Topic | Owner's answer | Effect on this plan |
|---|---|---|
| User | Any developer: frontend, backend, shell scripts | The scope is general, not specific to user interfaces |
| Generative models | None. Hard constraint. | Every capability is hand-built. Hybrid designs are excluded. |
| Kind of project | Product candidate, used inside developers' own IDEs in place of an LLM | The eventual bar is comparison with LLM assistants |
| Workflow | Write intent in a file; run it; folders of supporting code are generated | The intent file is the source of truth, so generation leads |
| Targets | Several languages. React was only an example. | Multi-target output is a core claim and is tested early |
| Reversibility | Intent to code and code to intent; pieces stack together; code traces to intent | A new core claim, tested in Stage 2 |
| Implementation language | Python is not required | Open (D6) |
| Pace | Generate a small amount, review it, then generate more | Three stages with a review after each |

## Basis and limits of this review

What was examined:

- **The repository.** It contains no implementation. `main.py` is the PyCharm sample script, `pyproject.toml` declares `requires-python >=3.14` with no dependencies, build system or tool configuration, and there are no tests. The only substantive file is the proposal.
- **The proposal**, read in full, and the owner's written answers summarised above.
- **Probe 1**, on editing existing code: a static HTML page and one plain CSS file in headless Chromium 153.0.8010.12, driven by Playwright 1.63.0 on Node 22.
- **Probe 2**, on generating for several languages: the same sort and filter written the obvious way in Python 3.13.18 and Node 22.23.4, run on five records.

Neither probe script was committed. Inputs and method are in the [Appendix](#appendix-probe-inputs-and-method).

What was not done:

- No part of the proposed system was implemented.
- Probe 1 did not use React, TypeScript, a bundler, source maps, CSS Modules or CSS-in-JS.
- Probe 2 did not test bash. Only C locales were available in the environment, so locale-dependent sorting in shell is untested.
- No search of prior art or competing tools was performed. Statements about existing tools and about the history of similar efforts come from general knowledge and are marked as assumptions.
- `main.py` was not run. This checkout has no `.venv`, and the container's Python is 3.13.18, below the declared minimum.

## Critique

### What holds up

- **Refusing instead of guessing** (§3.2, §4, §11). Ambiguity produces a diagnostic. This is the proposal's real differentiator.
- **A compiler, not a predictor.** With the intent file as the source of truth, the same input gives the same output, and every line of output has a known cause.
- **Four distinct claims about a change** (§7): "source patch applied", "static checks passed", "tests passed" and "visual effect observed". Probe 1 shows these do come apart.
- **Candour.** The proposal says the worked example is not evidence (§8), that the scope may be too broad (§10.9), and that the classifier may be unnecessary (§9).

### The clarified vision

1. **A fixed vocabulary against open-ended demand.** An LLM assistant accepts any request. A deterministic compiler accepts the operations its authors implemented. Whether CDIPL can replace LLM use therefore depends on how concentrated real demand is: if most requests fall into a few kinds with well-defined meaning, a fixed vocabulary can cover them; if demand is spread thinly across many kinds, it cannot. Neither the proposal nor the owner's answers estimate this. It is the first thing to measure, and it needs no code.

2. **General-purpose and high-level pull in opposite directions.** `get users where age >= 18` is short because it belongs to one narrow domain. To express arbitrary program logic, the language needs variables, conditions and loops, and at that point it is a conventional programming language with English keywords. *Assumption, from general knowledge: readable keywords have not historically made programming easier, because the difficulty lies in stating exactly what is wanted.* The realistic shape is a set of narrow families of intent, each high-level within its domain.

3. **Reversibility has to be scoped.** There are three different things "code to intent" could mean:

   | Meaning | Feasibility |
   |---|---|
   | Trace each generated line to the intent line that produced it | Straightforward. The compiler records it while generating. |
   | Recover the intent from generated code that nobody has changed | Feasible, because the compiler knows every form it can emit. |
   | Recover intent from hand-written or hand-edited code | Not feasible in general. Many different programs express one intent, and deciding whether two programs behave the same is not something a tool can do for arbitrary code. |

   The moment a developer edits a generated file, the second case turns into the third. *Assumption, from general knowledge: earlier model-driven tools that promised round trips between models and code ran into this problem.* The product must say what happens then (D1). The rule proposed here is testable: conversion back to intent either returns an intent that regenerates the file exactly, or refuses.

4. **The same intent must mean the same thing in every language.** Probe 2 wrote "sort by name" and "where age >= 18" the obvious way in Python and JavaScript. The two programs disagreed on four of four checks. A specification of the intent language's own semantics, independent of any target, has to exist before the second target is written.

5. **Cost grows with families multiplied by targets.** With no generative model, each operation needs hand-written generation and hand-written conversion back, per target. Ten families in five languages is fifty adapters to build, test and keep equivalent. The proof of concept should measure the cost of adding one target.

6. **What happens when the vocabulary runs out.** Developers will need something the language lacks. Either they are stuck, or the language lets them embed raw target-language code. Embedded code is not portable across targets and cannot be converted back to intent. Both answers have a cost (D3).

7. **If the intent file is the source of truth, most of the proposal's hardest machinery may be unnecessary.** Transformation mode (§6.2 to §6.5) exists to change code the tool did not write: it needs a project graph, resolution of competing sources, and browser validation. For code CDIPL generated, a change is an edit to the intent file followed by regeneration. The edit engine is needed only if CDIPL must work on existing codebases (D2).

### The proposal document

8. **The classifier is not load-bearing.** The proposal is named after it, yet §4 starts from a rule-based parser, §9 says it "may be unnecessary", §12.1 defers it, and §13 Q1 asks whether it is useful. Under the proposal's rules the classifier may only choose among alternatives the grammar already defines as equivalent, and may not override validation. A synonym table does the same, deterministically. The one consistent role left is ranking "did you mean" suggestions in a diagnostic. A pinned classifier is also reproducible without being predictable: a user cannot tell in advance which rewording changes the result.

9. **Three languages, and no shared representation is shown.** The two examples in §5 have no fields in common, and §6.1 adds a third form. §6.2 says the modes "can share the intent IR" without showing how. The representation is called typed, but the examples carry no types and do not say where `users` is bound.

10. **The data-pipeline language needed a stated advantage, and now has one to test.** Its syntax has the shape of existing query languages, and §2's premise that the Python equivalent "takes several lines" is weak: it is one expression, `sorted((u for u in users if u.age >= 18), key=lambda u: u.name)[:10]`. The owner has since named the intended advantages: several target languages from one source, conversion back to intent, and tracing. Stage 2 tests exactly these.

### The edit engine and the proposal's own proof of concept

These points are from revision 1 and still stand. They matter if decision D2 brings the edit engine back.

11. **The tool is confident where the task is easy and silent where it is hard.** To write `make SubmitButton 10% wider`, the developer already knows the target, property and amount. In easy cases, finding the controlling construct is a text search; in hard cases §6.2 and §10 require the tool to stop.
12. **The worked example (§8) is the easy case.** Its rule, "multiply resolved width by 1.10", failed in five of nine simple cases in Probe 1.
13. **The preservation constraints cannot be checked as written.** `preserveBehavior: true` (§5) has no test procedure.
14. **"Smallest valid source change" (§6.2) has no metric.** A one-line edit to a shared rule is the smallest diff and the widest effect.
15. **The browser is placed after the patch, where it is least useful.** It already knows which declarations apply to an element and where they came from.
16. **The proof of concept in §12 is too wide and cannot fail informatively.** Five intents need five different resolvers; the single-component fixture cannot host the negative cases listed in §12.3; and no thresholds are proposed.

### Probe 1: editing an existing stylesheet

Each case is one element. The edit multiplied one declared `width` by 1.10 at the location the browser reported, then the element was re-measured. Viewport is 1280 px unless stated.

| # | Case | Width declarations reported | Before (px) | After (px) | Ratio |
|---|---|---|---|---|---|
| 1 | `<button>` with the CSS from §8 | 1, at `style.css:2:3` | 120 | 132 | 1.100 |
| 2 | `<div role="button">` with the same class | the same one | 152 | 164 | 1.079 |
| 3 | Button with padding and no width | none | 77.48 | not editable | n/a |
| 4 | Button with no width in a 300 px column flex container | none | 300 | not editable | n/a |
| 5 | `width: 120px; max-width: 100px` | 1 | 100 | 100 | 1.000 |
| 6 | `.btn-d` (120 px) and `.form .btn-d` (200 px) both match | 2 | 200 | 200 editing the first, 220 editing the second | 1.000, 1.100 |
| 7 | Base rule 120 px plus a `max-width: 600px` media rule of `100%`, at 375 px viewport | 2 | 359 | 359 editing the base rule, 394.89 editing the media rule | 1.000, 1.100 |
| 8 | Two buttons sharing one class | 1 | 120 | 132, and the other button also became 132 | 1.100 |
| 9 | Rule injected by a script at runtime | 1, in a stylesheet with no source URL | 120 | no file to edit | n/a |

Reading: the browser located every declaration accurately enough to patch it directly. The proposal's rule had nothing to edit in cases 3, 4 and 9, changed nothing in case 5, and gave the wrong amount in case 2. Case 1 works only because Chromium sizes buttons by border box by default. Repeated runs gave identical output, on one machine.

### Probe 2: the same operation in two languages

Five records, read from one JSON file. Each check is the obvious one-line implementation in each language, the kind a first code generator would emit.

| Check | Python | JavaScript (Node) |
|---|---|---|
| Sort by name, where names include `～` (U+FF5E) and `😀` (U+1F600) | `～` before `😀` | `😀` before `～` |
| `age > 9007199254740992` for ages `…993` and `…992` | selects the first record | selects nothing |
| Output of ages written as `18` and `18.0` | `18`, `18.0` | `18`, `18` |
| `age >= 18` when one record has no `age` | raises an error | silently drops the record |

Reading: two straightforward translations of one intent are not the same program. None of these differences is exotic, and each has a known remedy, but each remedy is a decision the intent language has to make and every target then has to implement. This is five records and two languages; it shows the problem exists, not how large it is.

## Recommended direction

1. **Lead with generation from an intent file.** Defer the edit engine. Do not build a classifier.
2. **Measure demand before building.** Stage 1 decides whether the product is described as a replacement for LLM assistants or as a deterministic generator for selected kinds of task.
3. **Grow by narrow families, not by generality.** Each family has a closed set of operations with defined meaning. Start with one.
4. **Write the meaning down first.** A short specification of the first family's semantics, independent of any target language, precedes the second target.
5. **State reversibility as two testable rules.** Converting generated code back gives the original intent. Converting any file back either gives an intent that regenerates that file exactly, or refuses.
6. **Every target declares what it supports.** If a target cannot implement an operation to the specification, the compiler refuses that operation for that target (as §6.4 already requires of adapters).
7. **Review after each stage,** as the owner asked, and decide then whether to continue.

## Proof of concept

### The hypothesis being tested

For one family of intents, a deterministic compiler can produce programs in at least two languages that behave identically on the same input, convert back to exactly the intent they came from, and trace line by line to it; and a fixed vocabulary of this kind covers a useful share of what developers actually ask for.

### Stage 1: demand audit

No code. It tests point 1 of the critique.

1. Collect at least 100 real coding requests of the kind this product is meant to take over. The best source is the team's own recent requests to LLM assistants, with confidential detail removed. Fix the sampling rule before reading them.
2. Two people classify each request independently, then record disagreements. For each request:
   - **Kind:** for example data pipeline, HTTP endpoint, UI component, file or text processing script, data model, test, configuration, change to existing code, explanation or debugging, other.
   - **Closed or open:** can it be fully stated as a small set of named operations with parameters, or does it need free-form logic?
   - **New or existing:** does it create new code or change code that already exists?
3. Report the share of requests per kind, the share that are closed, the share that concern existing code, and how many distinct operations would cover 50% and 80% of the closed requests.

Known weakness: requests made to an LLM are skewed toward what LLMs do well. That is acceptable here, because this is the usage the product aims to replace.

### Stage 2: pipeline slice

**Language.** Exactly the operations in the proposal's examples in §2 and §3.1: read a declared source, filter, sort, limit, group, count.

```text
source users from "users.json":
    name: text
    age: integer
    school: text

get users where age >= 18
sort by name ascending
limit 10
```

- Fields have declared types: `integer` and `text`.
- Filters compare a field with a literal using `=`, `!=`, `<`, `<=`, `>`, `>=`, joined by `and`.
- One spelling per operation. No synonyms and no classifier.
- Named predicates such as "active" (§3.1) are not included; write `where status = "active"`.

**Specification.** One page that fixes, independently of any target: the ordering of text, the range of integers, what happens when a field is missing or has the wrong type, the order of groups, and the order of records that tie in a sort. Probe 2 shows why each of these needs an answer.

**Targets.** Python and JavaScript. Input is a JSON file of records; output is JSON.

**Commands.**

- `build`: reads an intent file and writes a folder containing the generated program and a trace file that maps each generated line to an intent line.
- `lift`: reads a generated program and returns the intent, or refuses.

**Tests.**

| Test | What is checked |
|---|---|
| Equivalence | A fixed set of at least 200 pairs of intent and dataset, including the edge cases from Probe 2, empty input, ties, and a limit larger than the data. Every target produces byte-identical output, or every target reports the same category of error. |
| Round trip | For every test intent, `lift` of the built program equals the intent in normal form, with comments stripped from the program first, so that the intent is recovered from the code and not from an embedded copy. For every generated file, `build` of its `lift` reproduces the file exactly. |
| Edited code | At least 30 hand edits to generated files: changed literals, changes that stay within the vocabulary, and inserted foreign statements. `lift` either returns an intent that regenerates the edited file exactly, or refuses. It never returns anything else. |
| Trace | Every non-blank generated line maps to one intent line or is marked as fixed support code. Checked mechanically. |
| Diagnostics | At least 20 invalid intent files (unknown field, type mismatch, unknown word, missing source). Each is rejected with a message naming the line. None compiles. |
| Determinism | Ten builds from a clean checkout produce byte-identical folders. |

### Stage 3: third target

Add bash. The owner names shell scripts as a target, and bash is the least similar of the three, so it shows most quickly what a new target costs. *Assumption: generated shell scripts will need an external tool such as `jq` to read JSON.*

Record the effort relative to the second target, which parts of the specification needed special handling, and which external tools the generated scripts require. The same tests apply. If bash cannot meet the specification for an operation, the target must declare it and the compiler must refuse that operation for bash.

### Out of scope

The classifier, the edit engine, UI component generation, embedded raw target code, IDE integration (syntax highlighting, in-editor diagnostics), performance, and any family beyond the first.

### Suggested time budget

*My estimates, not validated:* two to four days for Stage 1, two to three weeks for Stage 2, and about one week for Stage 3, for one engineer. Agree a hard stop for each stage before starting it (D7).

## Evidence that would count as success

Fix these before any result is seen, as §12.3 requires. The numbers are proposals for the team to ratify. The Stage 1 numbers are judgment calls with no empirical basis.

**Stage 1.**

| Share of requests that are closed and fall within five or fewer kinds | Reading |
|---|---|
| 40% or more | A fixed vocabulary can cover a large part of demand. Continue, with "replacement within these kinds" as the claim. |
| Between 20% and 40% | Continue, but describe the product as a deterministic generator used alongside other tools. |
| Below 20% | The replacement claim is not supported. Stop, or redefine the product. |

Separately: if more than half of the requests concern existing code, the edit engine is not optional, and D2 must be revisited before Stage 2.

**Stages 2 and 3. All must hold.**

| ID | Criterion |
|---|---|
| G1 | Equivalence: no pair on which targets differ. |
| G2 | Round trip: holds for every test intent and every generated file, in every target. |
| G3 | Edited code: `lift` never returns an intent that fails to regenerate the file it was given. One such case fails the stage. |
| G4 | Trace: complete, with no unmapped lines. |
| G5 | Diagnostics: every invalid file rejected with its line; none compiled. |
| G6 | Determinism: byte-identical output across ten builds. |
| G7 | The specification was written before the second target, and every difference found between targets was resolved by changing the specification or a target, not a test. |
| G8 | Stage 3 only: the effort for the third target is recorded, and any unsupported operation is refused by the compiler, not mistranslated. |

**What would disprove the idea.** Stage 1 below its floor disproves the replacement claim. Failure of G1 that can be fixed only by restricting the language until it is no longer useful disproves the multi-target claim for this family. Failure of G3 disproves reversibility as stated.

**What success would not show.** That developers prefer this to an LLM assistant; that families other than data pipelines work; that the cost of many families in many languages is sustainable; that it works inside an IDE.

**What happens next.**

| Outcome | Next step |
|---|---|
| All stages pass | Choose the second family from the Stage 1 ranking. Run a small user comparison against an LLM assistant on tasks inside the supported families: time to a correct result, and errors that reach review. |
| Stage 1 passes; G1 or G2 fails | Reduce to one target language and re-examine the multi-target claim. |
| Stage 1 lands in the middle band | Proceed to Stage 2, with the product description changed. |
| Stage 1 fails | Stop before writing the compiler. |

## Deferred track: the edit engine

Kept here in case D2 brings it back. Its design follows from critique points 11 to 16 and Probe 1.

**One command:** `make <target> <N>% wider on <route> [at <W>px] [including shared]`, where the target is a selector matching exactly one element, and "wider" means the measured border-box width.

**Stage E1, provenance audit.** On at least two React applications the team did not write, sample visible buttons, links and inputs, and classify where each one's width comes from:

| Code | Provenance | What a tool could do |
|---|---|---|
| P1 | One controlling declaration in a source file, matching only this element | Patch |
| P2 | As P1, but the selector matches other rendered elements | Patch only with `including shared` |
| P3 | The controlling declaration differs between viewports | Patch only with `at <W>px` |
| P4 | No width declaration; sized by content or by the parent | Refuse |
| P5 | Controlling declaration has no patchable source file | Refuse |
| P6 | Changing the declaration does not move the measured width as requested | Refuse |

Proposed reading of the actionable share (P1 + P2 + P3): continue at 30% or more, stop below 15%.

**Stage E2, resolve, patch and verify.** On a small React and TypeScript fixture run through its normal development build: resolve the target; find the controlling declaration by changing each candidate and re-measuring; refuse with a named reason where P4 to P6 or an unrequested P2 or P3 applies; otherwise replace only the value token, reload and re-measure; revert and refuse if the measured result is outside tolerance (proposed 0.5 px); report the diff, the measurements and every other element that moved.

**Criteria.** No wrong patches; every fixture expected to be refused is refused for the expected reason; each patch changes one value token; ten runs give identical results; declaration locations map to the correct source file through the development build.

**Main untested risk.** Whether declaration locations survive a real build pipeline.

## Major risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| Real demand is too varied for a fixed vocabulary | The replacement claim fails | Stage 1 runs first and needs no code |
| Cost grows with families multiplied by targets | Every pair is hand-built and must stay equivalent | Stage 3 measures the cost of one added target; add families one at a time |
| Targets drift apart in meaning | Probe 2 found four differences in two operations | Written specification; equivalence tests on every change (G1, G7) |
| Developers edit generated code | Conversion back to intent stops working for that file | Decision D1; criterion G3 ensures it fails visibly |
| Developers hit the edge of the vocabulary | They leave, or ask for embedded raw code that breaks portability and reversal | Decision D3, informed by Stage 1 |
| An English-like syntax is not easier in practice | A new language to learn, with less reach than the one it generates | The user comparison after Stage 3 |
| Existing tools already do this well | Not evaluated in this review | A prior-art survey before Stage 2 is recommended |
| The Stage 1 sample is unrepresentative | It can flatter or condemn the idea | Fix the sampling rule first; two independent classifiers; keep raw records |
| Scope returns to "everything at once" | The proposal's breadth is its main delivery risk (§10.9) | The out-of-scope list and a review after each stage |

## Decisions

### Still open

Each has a default that this plan assumes if nobody decides otherwise.

| ID | Decision | Default assumed here |
|---|---|---|
| D1 | What happens when a developer hand-edits generated code? The options are: not allowed, and regeneration overwrites; allowed only when the edit can be converted back to intent; or allowed freely, with tracing lost for that file. | The second: convert back or refuse |
| D2 | Must CDIPL work on existing code it did not generate? | No, for the first product. The edit engine stays deferred unless Stage 1 shows most requests concern existing code. |
| D3 | May an intent file embed raw target-language code when the vocabulary runs out? | Not in the proof of concept. Decide after Stage 1. |
| D4 | First family and first targets | Data pipelines; Python and JavaScript; bash third |
| D5 | Is "replacement for LLM assistants" a required claim, or is "deterministic generator for common kinds of task" an acceptable product? | Let Stage 1 decide |
| D6 | Language the compiler is written in | Python, because the repository is already set up for it and the lead track no longer needs browser tooling. *Assumption: converting generated JavaScript back to intent is practical from Python; not tested.* |
| D7 | Ratify the pass and fail numbers and the time budget per stage | The values proposed above |
| D8 | What "stacked together" means | That operations chain into a pipeline, and that one intent file can read another's output |
| D9 | Whether the name stays, given that no classifier is built | Unchanged for now |

### Resolved by the owner

No generative model, as a hard constraint. Product candidate. Python not required. No specific target codebase. Several target languages. Staged delivery with reviews.

## Assumptions

- No implementation exists beyond what is in the repository at commit `194e44b`. Verified for this checkout only.
- The proposal and the owner's answers are the only statements of intent.
- The team can collect at least 100 of its own past coding requests for Stage 1.
- Statements about existing tools and about the history of similar efforts are general knowledge, not the result of a survey.
- Effort estimates are unvalidated.

## Positions on the proposal's evaluation questions (§13)

| Q | Position |
|---|---|
| 1 | A classifier is not useful in the acceptance path. Do not build it now. |
| 2 | For generation: a pipeline of typed operations over a declared source. For edits: target, measured quantity, requested relation, viewports, tolerance, and the elements allowed to change. The proposal does not show that these are one representation. |
| 3 | As refusal reasons with evidence attached, not as scores. |
| 4 | Unknown, and not needed for this proof of concept. Probe 1 shows what is unavailable statically: sizes produced by layout and styles injected at runtime. |
| 5 | For changing a CSS value, replacing the token at the browser-reported location was sufficient in Probe 1. Other techniques were not evaluated. |
| 6 | Never infer it. Require explicit scope and report which elements are affected. |
| 7 | For generation: identical output across targets and the round-trip rules. For edits: the measured target property and the boxes of other elements. |
| 8 | Deferred with the edit engine: measured boxes at declared viewports, with a pinned browser and an explicit tolerance. |
| 9 | Each target declares unsupported operations, and the compiler refuses them for that target. |
| 10 | Not done in this review. A user comparison follows Stage 3; a prior-art survey is recommended before Stage 2. |
| 11 | Generated programs are executed during testing, so tests run in an isolated environment. The deferred audit of third-party applications needs the same. |
| 12 | See "Evidence that would count as success". |
| 13 | See "What would disprove the idea". |

## Appendix: probe inputs and method

### Probe 1

Stylesheet (`style.css`), loaded by a static page through a `<link>` element:

```css
.submit-button {
  width: 120px;
  padding: 8px 16px;
}
.submit-button-bb {
  box-sizing: border-box;
  width: 120px;
  padding: 8px 16px;
}
.plain { padding: 8px 16px; }
.clamped { width: 120px; max-width: 100px; padding: 8px 16px; }
.btn-d { width: 120px; }
.form .btn-d { width: 200px; }
.col { display: flex; flex-direction: column; width: 300px; }
.btn-f { width: 120px; }
@media (max-width: 600px) { .btn-f { width: 100%; } }
.shared { width: 120px; }
```

Elements, by case number. Each sits in its own `<div>` unless noted.

| # | Element |
|---|---|
| 1 | `<button class="submit-button">` |
| 2 | `<div class="submit-button" role="button">` |
| 3 | `<button class="plain">` |
| 4 | `<button class="plain">` inside `<div class="col">` |
| 5 | `<button class="clamped">` |
| 6 | `<button class="btn-d">` inside `<div class="form">` |
| 7 | `<button class="btn-f">`, measured at 1280 px and 375 px viewports |
| 8 | Two `<button class="shared">` in one `<div>` |
| 9 | `<button class="injected">`, with `.injected{width:120px}` added by a script through a new `<style>` element |

A tenth element, a button with class `submit-button-bb`, behaved exactly as case 1 and is omitted from the results.

Method, for each case:

1. Restore the stylesheet, open the page at the stated viewport, and attach a Chrome DevTools Protocol session.
2. Call `CSS.getMatchedStylesForNode` for the element. Keep `width` declarations from the page's own stylesheets, with their file, line and column.
3. Measure `getBoundingClientRect().width`.
4. For each declaration found in the file on disk: restore the stylesheet, multiply the declared number by 1.10 at the reported position, reload, measure the target again, and measure every other button on the page.

### Probe 2

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
