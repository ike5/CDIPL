# PLAN: Evaluation of the CDIPL proposal and a first proof of concept

| | |
|---|---|
| **Reviewed** | `outputs/proposal-classifier-driven-intent-programming-language.md` (v0.2) and this repository at commit `194e44b` |
| **Date** | 2026-11-11 |
| **Status** | Recommendation for the development team. Nothing in this plan has been built. |
| **Audience** | Engineers deciding whether to build this, and what to build first |

References such as "§8" point to sections of the proposal. Sections of this plan are referred to by name.

## Conclusion

The proposal bundles four things under one name: a small language for data pipelines, a language for generating new UI components, an engine that edits existing UI code from short commands ("transformation mode"), and an optional classifier.

- **Coherent?** Partly. The edit engine is a coherent design. The classifier is not doing any work under the proposal's own rules, the data-pipeline language is an ordinary query language with no stated advantage, and the claim that all of this shares one typed intermediate representation is asserted but not shown.
- **Worth pursuing?** Only the edit engine, and only as a short experiment with a stop rule. Its value depends on a number nobody has measured: on real UI code, how often can a deterministic tool both find the source construct that controls a property and safely change it? The proposal correctly says the tool must refuse when it cannot be sure. If refusals dominate, the tool is correct and useless.
- **Smallest proof of concept:** one command (`make <target> N% wider`), with the browser used to find the controlling declaration and to verify the result. It has two stages: first measure on real applications how often the command could act at all, then build the resolve, patch and verify loop for that one command and test that it never emits a wrong patch.

A small browser probe run for this review (see [Probe results](#probe-results)) supports this direction: the browser reported the exact file, line and column of every matching width declaration, and in five of nine simple cases the proposal's rule had nothing to edit (three cases), produced a patch with no visible effect (one), or produced the wrong amount (one).

## Basis and limits of this review

What was examined:

- **The repository.** It contains no implementation. `main.py` is the PyCharm sample script, `pyproject.toml` declares `requires-python >=3.14` with no dependencies, build system or tool configuration, and there are no tests. The only substantive file is the proposal. There is no JavaScript or TypeScript toolchain, although the proposal's proof of concept targets React and TypeScript.
- **The proposal**, read in full.
- **A browser probe**, written and run for this review: a static HTML page and one plain CSS file, loaded in headless Chromium 153.0.8010.12 through Playwright 1.63.0 on Node 22. The inputs are in the [Appendix](#appendix-probe-inputs-and-method). The probe script was not committed.

What was not done:

- No part of the proposed system was implemented.
- The probe did not use React, TypeScript, a bundler, source maps, CSS Modules or any CSS-in-JS library. Whether declaration locations survive a real build pipeline is untested.
- No search of prior art or competing tools was performed. Statements about existing tools come from general knowledge and are marked as assumptions.
- `main.py` was not run. This checkout has no `.venv`, and the container's Python is 3.13.18, below the declared minimum.

## Critique

### What holds up

- **Refusing instead of guessing** (§3.2, §4, §11). Classifier confidence never decides acceptance, and ambiguity produces a diagnostic. This is the proposal's real differentiator and should be kept.
- **Four distinct claims** (§7): "source patch applied", "static checks passed", "tests passed" and "visual effect observed". The probe shows these do come apart. Adopt them as the report format.
- **The existing project stays authoritative** (§6.2, §6.5), with small source-preserving patches and no whole-file regeneration.
- **Candour.** The proposal says the worked example is not evidence (§8), that the scope may be too broad (§10.9), and that the classifier may be unnecessary (§9).

### Coherence problems

1. **The classifier is not load-bearing.** The proposal is named after it, yet §4 starts from a rule-based parser, §9 says it "may be unnecessary", §12.1 defers it, and §13 Q1 asks whether it is useful. Under the proposal's rules, the classifier may only choose among alternatives the grammar already defines as equivalent, and may not override validation. Every input it accepts is therefore one a synonym table would accept, deterministically and at no cost. A classifier adds capability only for inputs the grammar rejects, and for those §4 requires a diagnostic. The one consistent role left is ranking "did you mean" suggestions inside a diagnostic.

   A related gap: a pinned classifier is reproducible, but it is not predictable. A user cannot tell in advance which rewording changes the result. §3.3 and §10.8 address reproducibility only.

2. **Three languages, and no shared representation is shown.** The two examples in §5 have no fields in common: one is a dataflow pipeline, the other a target, property and change record. §6.1 adds a third form, component declarations. §6.2 says generation and transformation "can share the intent IR"; the proposal does not show how. The representation is also called typed, but the examples carry no types and do not say where `users` is bound. §3.1 concedes that "active" needs a schema or environment that is not specified.

3. **The data-pipeline language is a query language.** `get users where age >= 18 / sort by name ascending / limit 10` has the shape of existing query languages. §2 motivates it by saying the Python equivalent "takes several lines", but it is one expression: `sorted((u for u in users if u.age >= 18), key=lambda u: u.name)[:10]`. The proposal names no advantage over a grammar-only language, which §9 itself lists as an alternative. *Assumption: existing query languages already cover this ground; no survey was done.*

### Problems with the substance of the edit engine

4. **The tool is confident where the task is easy and silent where it is hard.** To write `make SubmitButton 10% wider`, the developer already knows the target, the property and the amount. What the tool adds is finding the controlling construct, bounding side effects and verifying the result. In easy cases, finding the construct is a text search. In hard cases (competing style sources, parent layout, dynamic class names), §6.2 and §10 require the tool to stop. The tool's value therefore lies in the cases that are hard enough to be worth automating and still resolvable. The proposal does not estimate how many such cases exist or propose to measure it. This is the main reason the question "worth pursuing?" cannot be answered from the document.

5. **The worked example (§8) is the easy case, and its rule is right only by context.** The rule is "multiply resolved width by 1.10", applied to the declared value. In the probe, that rule gave exactly 10% on a `<button>`, 7.9% on a `<div>` carrying the same class, and no change when a `max-width` applied. Two cases had no width declaration to multiply. "10% wider" has to be defined on a measured quantity at a stated viewport, and the new value has to be solved for and verified, not computed from source text.

6. **The preservation constraints cannot be checked as written.** `preserveBehavior: true` and `preserveUnrelatedStyles: true` (§5) are flags with no test procedure, and §7 itself notes that unchanged source does not prove unchanged behaviour. "Unrelated" also needs a definition: widening an element in normal flow legitimately moves its neighbours. The representation should carry measurable postconditions and a declared set of elements that are allowed to change.

7. **"Smallest valid source change" (§6.2) has no metric.** A one-line edit to a shared rule is the smallest diff and the widest effect. §6.5 notes the shared-versus-instance distinction but does not say which kind of smallness wins.

8. **The browser is placed after the patch, where it is least useful.** §6.3 has a static project graph find the controlling construct, and §7 uses the browser to validate afterwards. Yet §10.2 says the static graph will be incomplete, and §10.3 says source inspection "may not reveal the effective style without a browser runtime". The browser already knows which declarations apply to an element and where they came from. Using it to resolve, and not only to validate, removes the most expensive and least reliable component from the first version.

9. **No comparison with alternatives is made.** §9 lists them without comparing. *Assumption: the practical baselines today are a manual edit, browser developer tools, and an AI coding assistant whose diff a human reviews.* The proposal's advantages over the last of these (reproducibility, no invented edits, principled refusal, no model at compile time) are real properties, but the proposal does not say who needs them enough to accept a restricted grammar and frequent refusals.

### Problems with the proposed proof of concept (§12)

10. **It is too wide and cannot fail informatively.**
    - The fixture is "one component, one stylesheet, one event handler", but the negative cases in §12.3 (several matching buttons, width controlled by a parent) need more than one component.
    - With one component the component graph is trivial, so the feasibility of the graph (§13 Q4) is not tested.
    - The five intents need five different resolvers: style cascade, text (and translation catalogues), design tokens, class-name expressions, and JavaScript scope for event handlers. The fifth intent changes behaviour, which is a different risk class from the other four.
    - Fixtures written by the tool's authors test whether anticipated cases are handled. They cannot show how often real code falls inside the supported cases.
    - §12.3 says thresholds must be set before results are seen but proposes none.
    - Latency, incremental rebuild cost and developer comprehension are premature measures for a first test.

### Probe results

Each case is one element on the test page. "Declarations reported" is what the browser's inspection interface (Chrome DevTools Protocol, `CSS.getMatchedStylesForNode`) returned for `width` from the page's own stylesheet. The edit multiplied one declared value by 1.10 in the CSS file on disk, at the reported line and column; the page was then reloaded and the element re-measured with `getBoundingClientRect().width`. Viewport is 1280 px wide unless stated.

| # | Case | Declarations reported | Before (px) | After (px) | Ratio |
|---|---|---|---|---|---|
| 1 | `<button>` with the CSS from §8 | 1, at `style.css:2:3` | 120 | 132 | 1.100 |
| 2 | `<div role="button">` with the same class | the same one | 152 | 164 | 1.079 |
| 3 | Button with padding and no width | none | 77.48 | not editable | n/a |
| 4 | Button with no width inside a 300 px column flex container | none | 300 | not editable | n/a |
| 5 | `width: 120px; max-width: 100px` | 1 | 100 | 100 | 1.000 |
| 6 | `.btn-d` (120 px) and `.form .btn-d` (200 px) both match | 2 | 200 | 200 editing the first, 220 editing the second | 1.000, 1.100 |
| 7 | Base rule 120 px plus `@media (max-width: 600px)` rule `100%`, at 375 px viewport | 2 (only the base rule at 1280 px) | 359 | 359 editing the base rule, 394.89 editing the media rule | 1.000, 1.100 |
| 8 | Two buttons sharing one class | 1 | 120 | 132, and the other button also became 132 | 1.100 |
| 9 | Rule injected by a script at runtime | 1, in a stylesheet with no source URL | 120 | no file to edit | n/a |

What this shows, within the limits stated above:

- **Resolution through the browser worked.** For every case with a declaration in the CSS file, the reported location was accurate enough to replace the value token directly. No CSS parser was needed.
- **"Patch applied" and "effect observed" differ.** In cases 5, 6 and 7, a syntactically valid edit to a matching width declaration changed nothing.
- **The declared-value rule depends on context outside the edited rule.** Case 1 works because Chromium gives buttons `box-sizing: border-box` by default (measured). Case 2, with the same rule on a `<div>`, does not. My own prediction for case 1 before running it was wrong, which is the point: reading the source is not enough.
- **A satisfied request can still be a bad edit.** In case 7 the ratio is exactly 1.10 and the element is now wider than the viewport. In cases 1 and 8, other elements sharing the class changed too.
- **Cases 3, 4 and 9 have nothing the proposed patcher can edit.** *My expectation, not a measurement: cases like 3 and 4 will be common for buttons in real applications, because buttons are usually sized by content and padding.* Stage A of the proof of concept tests this.

In cases 6 and 7 the declaration that took effect was the last one in the returned list. `!important`, cascade layers and inline styles were not tested, so the proof of concept should not rely on list order. It should find the controlling declaration the way the probe did: change each candidate and see which one moves the measurement.

Repeated runs of the probe produced identical output. That is one machine and one browser build, and says little about stability elsewhere.

## Recommended direction

1. **Narrow to the edit engine.** Park the data-pipeline language and generation mode. Do not build a classifier.
2. **State the product claim as:** given a precise command and a running preview of an existing application, the tool either produces a minimal patch with a measured result or refuses with a categorised reason. It never produces a patch whose measured effect differs from the request.
3. **Change the division of labour.** The browser resolves which declaration controls the property and verifies the result. Static analysis is used later for the one thing the browser cannot do: finding usages on routes and in states that were never rendered.
4. **Define each command as a measurable postcondition:** which element, which measured quantity, what relation between before and after, at which viewports, with what tolerance, and which other elements may change.
5. **Make refusal a first-class output** with a fixed list of reasons (see Stage B).
6. **Measure coverage before building the patcher** (Stage A).
7. **Build the verifier so that it does not care who wrote the patch.** A check of "did this diff achieve the stated measurable change, and what else moved?" is useful for patches written by a person, a codemod or an AI assistant. If the deterministic resolver turns out to cover too few cases, the verifier is the part most likely to remain useful.
8. **Defer the value comparison until feasibility is shown,** but do not skip it. Passing the proof of concept shows the tool can work, not that anyone should prefer it.

## Proof of concept

### Questions it answers

- **Coverage (Stage A).** On real React user interfaces, for what share of elements is the width controlled by a declaration that a tool could locate and patch?
- **Soundness (Stage B).** For one command, can a deterministic tool emit only patches whose measured effect equals the request, and refuse everything else for the right reason?

### The single command

```text
make <target> <N>% wider on <route> [at <W>px] [including shared]
```

- `<target>` is a CSS selector or `data-testid` that must match exactly one element on `<route>`. Component names are out of scope; see decision D7.
- "Wider" means the element's border-box width as returned by `getBoundingClientRect().width`.
- Without `at <W>px`, the result must hold at every configured viewport (proposed: 1280 px and 375 px).
- The command is parsed by a fixed grammar. There is no classifier.

### Stage A: provenance audit

A throwaway measurement script, not product code.

1. Choose at least two React applications that the team did not write and that use different styling approaches. Choose them before looking at their styles, and record each one's styling approach. If the team has a specific target codebase, include it (decision D5).
2. Run each application's development build. Visit a fixed list of routes at both viewports. Sample the visible `button`, `a`, `input` and `[role=button]` elements, with a cap per route.
3. For each sampled element, classify where its width comes from:

| Code | Provenance | What a tool could do |
|---|---|---|
| P1 | One controlling declaration, in a source file, whose selector matches only this element on the visited routes | Patch |
| P2 | As P1, but the selector matches other rendered elements | Patch only with `including shared` |
| P3 | The controlling declaration differs between the configured viewports | Patch only with `at <W>px` |
| P4 | No width declaration; sized by content or by the parent | Refuse |
| P5 | Controlling declaration has no patchable source file (runtime-injected styles, inline styles set by script) | Refuse |
| P6 | A declaration matches, but changing it does not move the measured width as requested | Refuse |

4. Report the frequency of each code, overall and per application, and keep the raw records. The **actionable share** is P1 + P2 + P3.
5. Record the same classification for `color` and `background-color`. This costs little and shows whether width is unusually hard, which matters if the team needs to pivot.

Known weakness: sampling elements is a stand-in for sampling real edit requests. If time allows, also look through each application's commit history for small style changes and classify those.

### Stage B: resolve, patch and verify

**Fixture.** A small React and TypeScript application run through its normal development build. This exercises the main thing the probe did not: mapping a declaration back to a source file through a real build. It contains the nine probe cases, plus: a target matching two elements, a target matching none, a CSS Modules class, an `!important` declaration, and an inline `style` attribute. For every fixture, write down the expected outcome before the tool is run: either a specific patch (file, line, old value, new value) or a specific refusal reason.

**Behaviour.**

1. Parse the command.
2. Open the route at each viewport and resolve the target. Refuse with `target-not-found` or `target-ambiguous` unless exactly one element matches.
3. Measure the starting width.
4. List the candidate width declarations and find the controlling one by changing each and re-measuring.
5. Refuse with one of `no-declaration`, `no-patchable-source`, `differs-by-viewport` (when no `at` was given) or `shared-reach` (when `including shared` was not given; list the other elements).
6. Compute the new value from the measured starting width, so that the measured width and not merely the declared number changes by N%. Write it to the source file by replacing only the value token, reload, and re-measure.
7. If the measured width is not within tolerance of the request (proposed: 0.5 px), revert the file and refuse with `effect-not-achieved`.
8. Report, separately: the diff; whether the build still succeeded; the measured before and after at each viewport; and every other element whose box changed.

**Out of scope.** The classifier, generation mode, the data-pipeline language, component-name targets, the other four intents in §12.1, a static project graph, frameworks other than React, latency measurement, editor integration, and automatic commits.

**Known limit.** "Other elements that changed" is measured only on the routes, viewports and states the tool renders. A usage on an unvisited route is invisible to it. Closing that gap with a static search is the first follow-on step.

### Suggested timebox

*My estimate, not validated:* a few days for Stage A and one to two weeks for Stage B, for one engineer who is comfortable with browser automation. Agree a hard stop before starting (decision D8).

## Evidence that would count as success

Fix these thresholds before any result is seen, as §12.3 requires. The numbers below are proposals for the team to ratify; the coverage numbers in particular are judgment calls with no empirical basis.

**Stage B, soundness. All must hold.**

| ID | Criterion |
|---|---|
| S1 | No wrong patches. Every emitted patch achieves the requested measured change within tolerance at the stated viewports, and changes no element outside the declared scope. A single wrong patch fails the stage. |
| S2 | Every fixture expected to be refused is refused, with the expected reason. |
| S3 | Every fixture expected to be patched is patched, at the expected location. |
| S4 | Each patch changes one value token in one file, and the rest of the file is byte-identical. |
| S5 | Ten runs from a clean checkout produce byte-identical patches and identical refusal reasons. |
| S6 | Through the development build, declaration locations map to the correct source file and line for the plain CSS and CSS Modules fixtures. |

S1 is strict because never being silently wrong is the main advantage this approach claims over asking an AI assistant for a diff.

**Stage A, coverage.**

| Actionable share for width | Reading |
|---|---|
| 30% or more | Continue with width as the lead command. |
| Between 15% and 30% | Team decision. Look at the `color` and `background-color` results. |
| Below 15% | Stop the width-first approach. |

**What would disprove the idea.** The falsifiable hypothesis is: for a bounded set of edit commands on existing React code, a deterministic tool can act on a useful share of real cases and never emit a patch whose measured effect differs from the request. It is disproved if S1 cannot be met without heuristics that guess, if declaration locations cannot be mapped to source for mainstream styling approaches (S6), or if the actionable share is below the floor for every property measured.

**What success would not show.** That the tool is better than the alternatives; that it generalises beyond React; that component-name targets work; that the other four intents work.

**What happens next.**

| Outcome | Next step |
|---|---|
| Both stages pass | Add component-name targets, a static search for unrendered usages, and a second property. Then compare against the baselines (manual edit and an AI assistant with review) on tasks drawn from the Stage A applications, measuring wrong edits, refusals and time to an accepted diff. |
| Stage B passes; Stage A fails for width but passes for colour | Re-scope to properties that are usually backed by a declaration, and re-examine against design-token tooling. |
| Stage B passes; Stage A fails everywhere | Stop the resolver. Consider keeping the verifier as a standalone tool. |
| Stage B fails | Stop, and write up the failing cases. |

## Major risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| Source locations do not survive real build pipelines (bundlers, preprocessors, CSS Modules, CSS-in-JS) | The whole approach depends on it, and it is untested | Stage B fixture uses a real development build; criterion S6 |
| Coverage is low | A correct tool that mostly refuses has no users | Stage A runs first and is cheap |
| The browser sees only what is rendered | Hover, focus and disabled states, authenticated routes and data-dependent rendering can hide usages | Reports list the routes, viewports and states tested; static search is the first follow-on |
| Measurements vary between machines | Fonts, sub-pixel rounding, animation and asynchronous rendering; the probe was stable on one machine only | Pinned browser build, explicit tolerance, explicit wait conditions; criterion S5 |
| The Stage A applications are unrepresentative | Two applications can flatter or condemn the idea | Choose before looking, record the styling approach, publish raw records |
| Stage A runs third-party code | Installing and running unknown applications (see §10.7 and §11) | Isolated container, no credentials |
| Scope returns to "a language" | The proposal's breadth is its main delivery risk (§10.9) | The out-of-scope list and the stop rule |
| Alternatives are simply better | Not evaluated in this review | The comparison step after the gate; decision D1 |
| Dependence on Chromium's inspection interface | Ties the tool to one browser family; its stability guarantees were not checked | Keep it behind one small module; accept for the proof of concept |

## Unresolved decisions

Each has a default that this plan assumes if nobody decides otherwise.

| ID | Decision | Default assumed here |
|---|---|---|
| D1 | Who is the user, and what do they use today? | Professional front-end developers in an existing React codebase, who would otherwise edit by hand or use an AI assistant |
| D2 | Is this a product, a research result or a learning project? | A product candidate, so "stop" is an acceptable outcome |
| D3 | Is "no generative model at compile time" a hard constraint or a preference? | Hard constraint. If it is a preference, a hybrid in which a model proposes and the deterministic verifier checks may be stronger, and should be evaluated. |
| D4 | Implementation language. The repository declares Python 3.14 or later; the target ecosystem is TypeScript. | TypeScript for the proof of concept. As designed, it needs only browser automation and file edits, so Python is workable, though Playwright for Python is not installed in this environment and was not tested. *Assumption: later static analysis of TSX is easier with TypeScript's own tooling.* |
| D5 | Which applications for Stage A? Is there a specific target codebase? | Two open-source React applications with different styling approaches |
| D6 | Ratify thresholds and tolerance | The values in the success section |
| D7 | Are the data-pipeline language and generation mode dropped or parked? Does the name stay? Do component-name targets come back in? | Parked; name unchanged for now; component names after the gate |
| D8 | Timebox and staffing | About three weeks, one engineer |

## Assumptions

- No implementation exists beyond what is in the repository at commit `194e44b`. Verified for this checkout only.
- The proposal is the only design document.
- The target is web UI in React, because §12 says so.
- The team can run a Chromium-based browser in development and continuous integration.
- Statements about existing tools and query languages are general knowledge, not the result of a survey.
- Effort estimates are unvalidated.

## Positions on the proposal's evaluation questions (§13)

| Q | Position |
|---|---|
| 1 | A classifier is not useful in the acceptance path. Its only consistent role is ranking suggestions in diagnostics. Do not build it now. |
| 2 | Target (route, selector, state), measured quantity, requested relation, viewports, tolerance, and the set of elements allowed to change. Postconditions, not boolean flags. |
| 3 | As refusal reasons with evidence attached, not as scores. |
| 4 | Unknown, and not needed for the proof of concept. The probe shows what is unavailable statically: sizes produced by layout (cases 3, 4 and 7) and styles injected at runtime (case 9). |
| 5 | For changing a CSS value, replacing the token at the browser-reported location was sufficient in the probe. Techniques for editing JSX were not evaluated. |
| 6 | Never infer it. Require explicit scope and report which elements are affected. |
| 7 | The measured target property; the boxes of other elements; no new horizontal overflow; a successful build. Event-binding and accessibility checks are outside the proof of concept. |
| 8 | Measured boxes at declared viewports, with a pinned browser, an explicit tolerance and repeated runs. |
| 9 | Through a fixed list of refusal reasons, with fixtures of unsupported patterns that must be refused. Adapters are outside the proof of concept. |
| 10 | Not done in this review. Required after the gate. |
| 11 | Stage A runs third-party code, so it needs an isolated container without credentials. |
| 12 | See "Evidence that would count as success". |
| 13 | See "What would disprove the idea". |

## Appendix: probe inputs and method

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

Elements, by case number in the results table. Each sits in its own `<div>` unless noted.

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

A tenth element, a button with class `submit-button-bb`, behaved exactly as case 1 and is omitted from the table.

Method, for each case:

1. Restore the stylesheet, open the page at the stated viewport, and attach a Chrome DevTools Protocol session.
2. Call `CSS.getMatchedStylesForNode` for the element. Keep `width` declarations from rules whose origin is the page's own stylesheets, with their file, line and column.
3. Measure `getBoundingClientRect().width`.
4. For each declaration found in the file on disk: restore the stylesheet, multiply the declared number by 1.10 at the reported position, reload, measure the target again, and measure every other button on the page.
