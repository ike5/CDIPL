# Proposal: Classifier-Driven Intent Programming Language

**Status:** Concept proposal / request for technical evaluation  
**Version:** 0.2  
**Audience:** Software engineers, compiler developers, programming language researchers, ML engineers, and AI evaluators  
**Objective:** Evaluate the feasibility, architecture, performance, and practical value of translating constrained human-readable intentions into conventional executable code and minimal, project-aware source patches.

---

# 1. Executive Summary

This proposal introduces a **Classifier-Driven Intent Programming Language (CDIPL)**: a programming approach between conventional languages and open-ended natural-language code generation.

Developers express operations using a structured, human-readable syntax. A deterministic parser and, optionally, a lightweight intent classifier identify canonical operations and parameters. A typed intermediate representation (IR) is validated, then deterministic compiler backends generate code or plan a narrowly scoped modification to an existing project.

The classifier does not author source code. It routes recognized intent to known operations. Exact values, identifiers, expressions, and constraints are parsed and type checked. Ambiguity or unsupported semantics should produce a diagnostic rather than a guess.

The initial pipeline is:

```text
Intent source or modification request
        ↓
Lexing / parsing and optional intent classification
        ↓
Typed intent representation
        ↓
Semantic validation against language and project context
        ↓
Generation or transformation planning
        ↓
Deterministic compiler backend / source-aware patch
        ↓
Diff, diagnostics, and validation results
        ↓
Developer review and application
```

The design aims for predictable, reproducible output; a compact, composable vocabulary; transparent generated code; incremental updates; multiple target languages; explicit ambiguity handling; and no dependency on generative AI at compile time. A small classifier may optionally resolve supported phrasings, but it must not override semantic validation.

**Primary hypothesis:** A defined set of composable intents, backed by deterministic parsing, project analysis, and code transformations, can reduce routine coding effort while keeping changes inspectable and reproducible.

This is a hypothesis for evaluation, not an established result.

---

# 2. Problem Statement

Traditional programming languages require developers to state implementation details even for common operations. For example, filtering and sorting a collection in Python takes several lines. An intent language could express the same operation declaratively:

```text
get users where age >= 18
sort by name ascending
limit 10
```

A generative model could translate this into code, but may introduce nondeterminism, latency, hallucinations, semantic drift, version variability, and security concerns. A conventional compiler is more predictable, but often requires syntax that is less approachable.

There is a second problem in real application work: a request such as “make the Submit button 10% wider” is not a request to emit a standalone HTML snippet. The button may be expressed in JSX, styled by CSS Modules or utilities, constrained by its parent, and wired to JavaScript behavior. A useful system must understand the project sufficiently to make the intended change without replacing unrelated code.

This proposal evaluates a deterministic approach to both **intent-to-code generation** and **intent-to-patch transformation**.

---

# 3. Proposed Solution

## 3.1 Core Concept

The system recognizes standardized programming intentions, extracts their operands, validates them, and compiles them through predefined rules.

For example:

```text
get active students
group by school
count each group
sort by count descending
```

could resolve to a sequence such as `READ → FILTER → GROUP → COUNT → SORT`. The meaning of “active” must be defined by the source schema or language environment; the compiler must not silently invent a `status` field or its semantics.

For code modification, the input is paired with project context:

```text
make SubmitButton 10% wider
```

The compiler resolves the component, the effective width source, and applicable constraints before preparing a patch.

## 3.2 Fundamental Design Principle

Separate intent recognition from semantic decisions and code generation:

- **Parser/classifier:** identifies a known operation and its syntax.
- **Parameter resolver:** extracts exact names, values, and expressions.
- **Semantic analyzer:** checks types, definitions, project bindings, and constraints.
- **Planner:** chooses generation or a minimal patch strategy.
- **Backend/transformer:** emits deterministic code changes.
- **Validator:** checks the result against configured static, behavioral, and visual criteria.

A classifier confidence score is not proof of correctness. Invalid or ambiguous input must fail safely with a useful explanation.

## 3.3 Intended Properties

- Reproducible output for identical source, compiler version, configuration, and dependencies.
- Human-readable intent syntax and inspectable generated code.
- Small, composable operation vocabulary rather than a class for every whole-program request.
- Extensible target backends and framework adapters.
- Source maps or diagnostics that connect generated output to intent input.
- Incremental compilation and caching where safe.
- Explicit behavior for unsupported, ambiguous, and destructive operations.

---

# 4. Intent Classification and Parsing

A rule-based parser is the simplest fully deterministic starting point. A small classifier may later recognize supported synonyms or route syntax to canonical operations. A hybrid is a reasonable research direction: parse the defined grammar first, and use classification only within an explicitly bounded set of alternatives.

The classifier should identify operations, not generate programs. For example, `get`, `retrieve`, and `find` could map to `READ` only where the grammar defines them as equivalent. Exact predicates such as `age > 18` must be parsed without semantic alteration.

Ambiguity handling should be conservative. Unsupported phrasing, unresolved references, or multiple plausible targets should result in a diagnostic or a request for a more precise intent. Destructive operations should require explicit syntax and a reviewable diff.

A classifier can report confidence for evaluation and telemetry, but compiler acceptance should depend on valid syntax, a well-typed representation, resolved names, and declared semantics—not confidence alone.

---

# 5. Typed Intermediate Representation

The compiler should convert recognized operations to a typed IR before generating or editing source. The IR separates user wording from target-specific syntax and makes invariants testable.

A collection operation might be represented as:

```json
{
  "pipeline": [
    { "operation": "READ", "source": "users" },
    {
      "operation": "FILTER",
      "predicate": { "field": "age", "operator": ">=", "value": 18 }
    },
    { "operation": "SORT", "field": "name", "direction": "ascending" },
    { "operation": "LIMIT", "value": 10 }
  ]
}
```

The UI transformation extension uses a representation that makes the target, property, requested change, and preservation requirements explicit:

```json
{
  "mode": "TRANSFORM",
  "action": "MODIFY",
  "target": {
    "kind": "COMPONENT",
    "name": "SubmitButton",
    "instance": null
  },
  "property": {
    "domain": "STYLE",
    "name": "width",
    "unit": "relative"
  },
  "change": {
    "kind": "RELATIVE_INCREASE",
    "value": 0.10
  },
  "constraints": {
    "preserveBehavior": true,
    "preserveUnrelatedStyles": true,
    "preservePublicAPI": true,
    "responsiveScope": "all-existing-breakpoints"
  }
}
```

“Make it slightly wider” has no universal numeric meaning. The language must define “slightly” explicitly, expose a configured value, or ask for a measurable amount. The IR should retain unresolved or underspecified fields as errors rather than guessing.

---

# 6. Compilation and Transformation Architecture

## 6.1 Generation Mode

In **generation mode**, the intent language or framework-independent UI description is the source of truth. The compiler creates new files or application structures for selected targets. This mode can use a universal component representation because there is no pre-existing source that must be losslessly reconstructed.

Example:

```text
component SubmitButton:
    element: button
    text: "Submit"
    width: 120px
    on click: submitForm
```

A React backend could generate JSX and CSS; an HTML backend could generate markup, styles, and JavaScript. The exact output is target- and configuration-dependent.

## 6.2 Transformation Mode

In **transformation mode**, the existing project remains authoritative. The input intent plus a project model produces a minimal patch. The system should preserve comments, formatting, naming, and unrelated code wherever possible.

The planner should identify the smallest valid source change, show the proposed diff, and avoid rewriting files wholesale. If multiple sources compete to control a property, or if a dynamic expression prevents safe resolution, the planner should report the ambiguity instead of applying a speculative patch.

The two modes can share the intent IR and validation vocabulary, while using separate source strategies: templates or structured generation for new code, source-preserving transforms for existing code.

## 6.3 Project-Aware Component Graph

For web applications, build a project graph that joins syntax and runtime-relevant relationships across files. It may include:

- Components, DOM elements, slots, and rendered children.
- Imports, exports, module ownership, and call sites.
- Props, state, hooks, event handlers, and data flow.
- CSS selectors, CSS Modules, utility classes, inline styles, and design tokens.
- Parent layout constraints and responsive rules.
- Tests, routes, stories, and browser-visible instances.

Illustrative graph:

```text
SubmitButton (React component)
  ├── renders → <button>
  ├── receives prop → onSubmit
  ├── binds click → onSubmit
  ├── className → submit-button
  ├── styled by → Button.css / .submit-button
  └── used by → CheckoutForm
```

This model is a combination of parsed syntax, symbols, dependency links, and framework-specific knowledge. It should be incremental and retain links back to source locations.

## 6.4 Framework Adapters

The core IR should not assume one framework’s syntax. Framework adapters translate between the project graph, IR, and source constructs. Initial candidate adapters include:

- HTML, CSS, and JavaScript.
- React with JSX/TSX and TypeScript.
- Vue single-file components.
- Svelte components.
- CSS Modules, plain CSS, and selected utility-class systems.

Each adapter must declare supported syntax, known limitations, and transformations it can prove safe. “Universal support” should not be claimed from a small set of adapters.

## 6.5 Source-Preserving Codemods

Existing-project changes should use syntax-aware, source-preserving codemods rather than broad string replacement or full-file regeneration. Candidate techniques include AST-based edits with retained source ranges, concrete syntax trees, and framework-specific compiler APIs.

A codemod should:

1. Resolve the intent target to one or more source nodes.
2. Resolve which source construct controls the requested property.
3. Check constraints and possible overrides.
4. Apply the smallest valid edit.
5. Preserve unrelated syntax and formatting.
6. Produce a diff and source map for explanation and review.

If the same component is used in several contexts, the system must distinguish editing the shared definition from editing one instance. Target scope must be explicit or safely inferable.

---

# 7. Cross-Language Semantic Preservation and Validation

The central research question is:

> Can a deterministic, project-aware transformation system change the requested aspect of an application while preserving unrelated behavior across HTML, CSS, JavaScript, and framework-specific constructs?

Preservation must be evaluated at more than one level. An unchanged event-handler line does not prove unchanged behavior: styling can affect visibility, hit targets, layout, focus, or accessibility. Validation should therefore be layered and reported honestly.

Possible checks include:

- Parsing and framework compilation.
- Type checking and linting where configured.
- Targeted unit or regression tests.
- DOM and event-binding checks for affected components.
- Accessibility checks relevant to the changed element.
- Browser preview at defined viewport sizes and states.
- Computed-style inspection to verify the requested visual property.
- Screenshot or visual-diff review, with tolerances and known nondeterminism disclosed.

Browser validation is especially important for layout intents. Source-level changes can be syntactically valid yet have no visible effect because a parent, utility class, media query, or runtime style overrides them. A browser runner should report the tested route, viewport, state, and measured result. It should not silently claim correctness when a preview cannot be launched.

Validation results should distinguish “source patch applied,” “static checks passed,” “tests passed,” and “visual effect observed.” These are different claims.

---

# 8. Worked Transformation Example

Existing React source:

```jsx
function SubmitButton({ onSubmit }) {
  return (
    <button className="submit-button" onClick={onSubmit}>
      Submit
    </button>
  );
}
```

Existing CSS:

```css
.submit-button {
  width: 120px;
  padding: 8px 16px;
}
```

Intent:

```text
make SubmitButton 10% wider
```

Resolved intent:

```text
mode: TRANSFORM
target: component SubmitButton
property: CSS width
change: multiply resolved width by 1.10
constraints: preserve click behavior, padding, text, and unrelated styles
```

A possible patch changes `width: 120px` to `width: 132px` in the CSS rule, while leaving the JSX event binding and all unrelated declarations intact. The tool should display this patch and validate the component in a browser if one is configured. If width is actually controlled by a parent or runtime prop, the tool should identify that source or stop with an ambiguity diagnostic.

This example illustrates a proposed behavior; it is not evidence of an implemented compiler.

---

# 9. Alternatives and Related Approaches to Evaluate

The team should compare the proposal with:

- A purely grammar-based domain-specific language.
- A conventional compiler with declarative syntax and no classifier.
- IDE code actions and framework codemods.
- Generative AI editing with human review.
- Design-system tokens and component APIs for UI changes.
- A universal application model for generated projects only.

The classifier may be unnecessary for a constrained syntax. Its value should be demonstrated by improved authoring flexibility without a reduction in correctness or explainability.

---

# 10. Risks and Open Technical Problems

## 10.1 Ambiguous Intent

Natural phrasing can omit units, scope, or definitions. “Slightly wider” needs a language rule; “make the button wider” may identify several buttons. The system must expose ambiguity and require a more precise instruction where needed.

## 10.2 Project-Graph Incompleteness

Dynamic imports, runtime-generated classes, aliases, conditional rendering, CSS-in-JS, custom build steps, and third-party components can hide relationships. An incomplete graph can lead to incorrect target resolution.

## 10.3 Competing Style Sources

Inline styles, classes, utility frameworks, responsive rules, parent layout, and component-library props may compete. Source inspection may not reveal the effective style without a browser runtime.

## 10.4 Semantic Preservation

A patch can preserve source text while changing user-visible behavior. Preservation claims need measurable invariants and tests appropriate to the change.

## 10.5 Framework and Language Coverage

Supporting multiple languages creates a substantial maintenance burden. Each adapter needs conformance tests and explicit capability boundaries. Unsupported patterns should fail closed.

## 10.6 Formatting and Merge Conflicts

Generated edits can disturb comments or formatting and may conflict with concurrent developer changes. Source-aware patches should detect stale source and avoid applying against a changed base.

## 10.7 Security and Execution

Generated or transformed code remains executable software. The system must consider injection, unsafe macros, untrusted packages, file and network access, and code execution permissions. Browser validation should run with appropriate isolation.

## 10.8 Reproducibility and Classifier Drift

Output should be tied to compiler, adapter, grammar, configuration, and classifier versions. If a model is included, pin its artifact and preprocessing rules. Classification should not introduce nondeterministic semantic decisions.

## 10.9 Scope and Product Complexity

A general-purpose intent language, code generator, multi-language analyzer, codemod engine, and browser verifier may be too broad for one initial product. The proof of concept should test the riskiest assumptions before broadening scope.

---

# 11. Security, Confidence, and Reproducibility

Confidence is useful as an evaluation signal but not a correctness guarantee. The compiler should accept only operations that pass syntactic, type, reference, and constraint validation.

The implementation should account for unsafe generated code, injection, untrusted input, macro expansion, package supply chains, filesystem access, network permissions, execution boundaries, and unsafe deserialization.

Given identical source, compiler and adapter versions, configuration, classifier artifacts, and dependencies, output should be reproducible. The system should record these inputs with the patch or build result.

---

# 12. MVP Scope and Proof of Concept

The first proof of concept should be narrow enough to evaluate project-aware transformation without claiming general natural-language programming.

## 12.1 Proposed Scope

Use a small React/TypeScript project with one component, one stylesheet, one event handler, and a browser preview. Support these intents:

1. Change a component’s width by an explicit percentage or pixel amount.
2. Change visible text for a named component or instance.
3. Change a color using a named token or explicit value.
4. Add or remove a specified CSS class.
5. Bind an existing named event handler to a specified event.

Start with a deterministic grammar. A classifier for carefully bounded synonyms can be evaluated as a later comparison, not as a prerequisite.

## 12.2 Required Demonstration

For each supported intent, the system should:

1. Parse the intent into the target/property/change/constraints representation.
2. Resolve the target through the component graph.
3. Identify the controlling source construct across JSX/TSX and CSS.
4. Apply a minimal source-preserving patch.
5. Show the patch and explain affected files and preserved bindings.
6. Run configured parsing, type checks, and targeted tests.
7. Open a browser route at defined viewport sizes and verify the requested visual change where applicable.
8. Report unsupported or ambiguous cases without guessing.

## 12.3 Evaluation Measures

Measure at least:

- Correct target resolution and property resolution.
- Patch correctness and minimality.
- Rate of unrelated source changes.
- Build, type-check, and test outcomes.
- Browser-observed effect for visual intents.
- Correct refusal or clarification for ambiguous cases.
- Compilation latency and incremental rebuild cost.
- Developer ability to understand and review the proposed diff.

A success threshold should be set before implementation results are reviewed. The POC should include negative cases: multiple matching buttons, width controlled by a parent, dynamic class names, responsive overrides, and a component whose click behavior must remain intact.

## 12.4 Later Expansion

If the POC shows reliable target resolution and patching, add framework adapters, broader style systems, generation mode, additional intent families, and optional synonym classification incrementally.

---

# 13. Evaluation Questions for the Development Team and AI Evaluators

1. Is a separate intent classifier useful when a formal grammar already resolves the supported syntax?
2. Which intent representation best captures target, property, magnitude, units, scope, and preservation constraints?
3. How should the system represent uncertainty without turning confidence into a correctness claim?
4. Is a unified component graph feasible across JSX, CSS, JavaScript, and runtime styles? What information is lost or unavailable statically?
5. Which parsing and source-preserving transformation techniques provide the best balance of correctness, formatting retention, and adapter cost?
6. When should the system edit a shared component versus a single usage site?
7. What invariants can be checked automatically to support semantic-preservation claims?
8. Which browser checks are needed for layout and interaction changes, and how should nondeterministic rendering be handled?
9. How should adapters declare supported syntax and fail safely on unsupported patterns?
10. How does this compare with existing IDE code actions, codemods, design tokens, and AI-assisted patching?
11. What security boundaries are needed for project analysis, build execution, and browser validation?
12. What minimum POC results would justify expanding to more frameworks or general-purpose programming?
13. Which original hypothesis is falsifiable, and what evidence would disprove it?

---

# 14. Conclusion

The proposal begins with classifier-routed, deterministic compilation of structured programming intent. The cross-language extension treats real application work as project-aware transformation: resolve an intent against a component and dependency graph, represent its target, property, change, and constraints explicitly, then generate a narrow source-preserving patch through framework adapters.

Generation and transformation should share a typed intent model while using different source strategies. New projects can be generated from a framework-independent representation. Existing projects require source-aware codemods that preserve surrounding code and prove as much as possible through static checks, tests, and browser validation.

The defining research question is whether this approach can produce useful changes with reproducible, reviewable patches while reliably identifying cases it cannot safely resolve. A small React/TypeScript proof of concept, including negative cases and browser checks, is the recommended first step.
