"""Fill in a block's parameters from the values in a freely worded statement.

The classifier chooses the block. Everything else is read by the fixed rules here:
field names, numbers, text in quotes and comparisons are taken exactly as written.
"""
import json
from pathlib import Path

from .model import MAX_INTEGER, Condition, Count, Filter, Group, IfNone, IntentError, Limit, Read, Show, Sort, WriteJson

HERE = Path(__file__).parent / "library"
BUILT = ("drop-invalid-rows", "filter-rows", "sort-rows", "take-first", "group-by-key", "count-values",
         "print-message", "print-table", "format-json")


def concepts():
    return {name: set(codes) for name, codes in json.loads((HERE / "slots.json").read_text(encoding="utf-8")).items()}


def fill(block, tokens, line, source_name, steps):
    """Return the step a statement stands for. Raises IntentError when the values do not fit the block."""
    fields = [token.value for token in tokens if token.kind == "name" and token.value != source_name]
    texts = [token.value for token in tokens if token.kind == "text"]
    numbers = [token.value for token in tokens if token.kind == "number"]
    comparisons = [token.value for token in tokens if token.kind == "op"]
    found = {token.code for token in tokens if token.kind == "word"}
    known = concepts()

    def has(concept):
        return bool(found & known[concept])

    def no_values(*kinds):
        present = {"text": texts, "number": numbers, "comparison": comparisons, "field": fields}
        for kind in kinds:
            if present[kind]:
                raise IntentError(line, f"this statement was read as '{block}', which takes no {kind} here")

    for number in numbers:
        if abs(number) > MAX_INTEGER:
            raise IntentError(line, f"the number {number} is outside the range of whole numbers the language supports")
    for text in texts:
        if any(ord(ch) < 32 for ch in text):
            raise IntentError(line, "the text must not contain control characters")

    if block == "filter-rows":
        conditions, used = [], set()
        for index in range(len(tokens) - 2):
            first, second, third = tokens[index:index + 3]
            if first.kind == "name" and second.kind == "op" and third.kind in ("number", "text") and index not in used:
                conditions.append(Condition(field=first.value, op=second.value, value=third.value))
                used.update((index, index + 1, index + 2))
        stray = [token for index, token in enumerate(tokens) if index not in used
                 and (token.kind in ("op", "number", "text") or (token.kind == "name" and token.value != source_name))]
        if not conditions or stray:
            raise IntentError(line, "write each condition as a field, a comparison and a value, such as age >= 18")
        return Filter(conditions=tuple(conditions), line=line)
    if block == "sort-rows":
        no_values("text", "number", "comparison")
        if len(fields) != 1:
            raise IntentError(line, "name exactly one field to sort by")
        if has("ascending") == has("descending"):
            raise IntentError(line, "say whether to sort in ascending or descending order")
        return Sort(field=fields[0], descending=has("descending"), ignore_case=has("ignore-case"), line=line)
    if block == "take-first":
        no_values("text", "comparison", "field")
        if len(numbers) != 1 or numbers[0] < 0:
            raise IntentError(line, "give the number of rows to keep, as one whole number that is not negative")
        return Limit(count=numbers[0], line=line)
    if block == "group-by-key":
        no_values("text", "number", "comparison")
        if len(fields) != 1:
            raise IntentError(line, "name exactly one field to group by")
        return Group(field=fields[0], line=line)
    if block == "count-values":
        no_values("text", "number", "comparison")
        grouped = next((step.field for step in reversed(steps) if isinstance(step, Group)), "")
        if any(name != grouped for name in fields):
            raise IntentError(line, "counting works on the groups formed by the step before it and takes no other field")
        return Count(field=grouped, line=line)
    if block == "print-message":
        no_values("number", "comparison", "field")
        if len(texts) != 1 or not has("empty"):
            raise IntentError(line, "the only message built so far is the one shown when there are no rows: "
                                    "say that it applies when there are none, and give the text in double quotes")
        return IfNone(text=texts[0], line=line)
    if block == "print-table":
        no_values("text", "number", "comparison")
        if not fields or len(set(fields)) != len(fields):
            raise IntentError(line, "name the fields to show, each once")
        return Show(fields=tuple(fields), line=line)
    if block == "format-json":
        no_values("text", "number", "comparison", "field")
        return WriteJson(line=line)
    if block == "drop-invalid-rows":
        no_values("text", "number", "comparison", "field")
        return Read(skip_invalid=True, skip_line=line)
    raise IntentError(line, f"this statement was read as '{block}', which is not built yet")
