# Stage 1 classification rubric

This rubric is applied to every unit listed in `stage1/units.csv`. A unit is a top-level function, a method of a top-level class, or `<module>` (the top-level statements of a file other than imports, constants and a bare call to the main function). The splitting is done mechanically by the tools in `stage1/tools/`.

## The question

Could this unit be produced by joining general-purpose, reusable operations ("blocks") and filling in their parameters, or does it need logic particular to this program?

## Levels

| Level | Meaning |
|---|---|
| A | The unit's whole behaviour can be stated as a sequence of general-purpose operations. Every parameter is a simple value: a name, a number, text, a field name, a file path, a comparison between a field and a fixed value, a text pattern, a format, or a list of these. |
| B | As A, except that at least one parameter has to be a formula: an arithmetic, text or true-or-false expression over values already at hand, of the kind typed into a spreadsheet cell. There is no loop or branching particular to the program. |
| C | The unit needs control flow or rules particular to this program: a loop that carries state from one pass to the next in a program-specific way, branching on program-specific cases, recursion, or a custom algorithm or parser. |

Levels A and B are called *closed*. Level C is called *open*.

## Conventions

1. An operation is general-purpose if it would plainly be useful in many unrelated programs: read a CSV file, group rows and total a field, sort, walk a folder, declare command-line options, send an HTTP request, show a message beside a form field. An operation that exists only to serve this one program, such as deciding who has won at tic-tac-toe, is not.
2. Ordinary error handling does not raise the level. Reporting a missing file or a bad argument and stopping is assumed to be part of a block.
3. Judge each unit by its own code. A unit that only calls other units of the same program in order and passes results along is level A, whatever the level of the units it calls.
4. Standard iteration inside a general operation is not program-specific control flow. "For each row", "for each file" and "for each matching element" belong to operations such as transform each, keep those that match, group, total, count, sort, take the first N, remove duplicates by a key, and retry N times with a growing delay.
5. Declaring command-line options is level A.
6. Attaching a handler to an event is level A if what the handler does is itself a sequence of general operations.
7. When in doubt between two levels, choose the less favourable one (the later letter).
