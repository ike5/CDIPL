"""Read a freely worded line of a page: the classifier chooses the block, fixed rules read the values."""
import json
from pathlib import Path

from . import classifier as classifier_module
from . import library, pages, words
from .model import IntentError

HERE = Path(__file__).parent / "library"
PAGE_BLOCKS = ("page-heading", "page-text", "page-button", "data-table", "render-table", "filter-elements-by-text",
               "table-sort", "page-button-resize")


def make_resolver(language, notes=None, accept_unsure=False, classifier=None, word_list=None):
    """Returns the function pages.read_lines calls for a line that is not a standard phrase.

    notes, if given, collects for each line how the choice was made and what the alternatives were.
    With accept_unsure the best guess is used even when the classifier is not sure, as the live view does.
    """
    state = {"classifier": classifier, "words": word_list}

    def resolve(line, number, items, data):
        try:
            state["words"] = state["words"] or words.load(language)
            state["classifier"] = state["classifier"] or classifier_module.load()
        except FileNotFoundError:
            raise IntentError(number, f"'{line}' is not written in standard phrases, and free wording is not "
                                      f"available for this language") from None
        names = set(data) | {name for item in data.values() for name, _ in item.fields}
        try:
            tokens, unknown = words.encode(line, state["words"], names)
        except words.WordError as problem:
            raise IntentError(number, str(problem)) from None
        _, ranked, margin = state["classifier"].choose(words.codes(tokens))
        note = {"alternatives": ranked[:3], "how": "sure" if margin >= state["classifier"].threshold else "unsure"}
        if notes is not None:
            notes[number] = note
        if unknown:
            listed = ", ".join(f"'{word}'" for word in unknown)
            raise IntentError(number, f"not understood: {listed} is not in the word list")
        if note["how"] == "unsure" and not accept_unsure:
            descriptions = library.catalogue()
            closest = "; ".join(f"{name} ({descriptions[name]})" for name in ranked[:2])
            raise IntentError(number, f"cannot tell which part of a page this means. The closest are: {closest}")
        block = ranked[0]
        note["block"] = block
        if block not in PAGE_BLOCKS:
            raise IntentError(number, f"this was read as '{block}', which a page cannot hold")
        return fill(block, tokens, number, items, data, state["words"])

    return resolve


def concepts():
    return json.loads((HERE / "slots.json").read_text(encoding="utf-8"))


def fill(block, tokens, number, items, data, word_list):
    """Add the element a line stands for, or change one. Returns the line changed, or None."""
    texts = [token.value for token in tokens if token.kind == "text"]
    pixels = [token.value for token in tokens if token.kind == "pixels"]
    names = [token.value for token in tokens if token.kind == "name"]
    others = [token for token in tokens if token.kind in ("number", "decimal", "op", "sym", "newname")]
    found = {token.code for token in tokens if token.kind == "word"}
    known = concepts()
    if others:
        raise IntentError(number, f"this was read as '{block}', which takes no numbers, comparisons or formulas")

    def one_text(what):
        if len(texts) != 1:
            raise IntentError(number, f"give the {what} once, in double quotes")
        value = pages.Quoted(texts[0])
        if not value.strip() or value != value.strip() or "  " in value or any(ord(ch) < 32 for ch in value):
            raise IntentError(number, "the text must not be empty, start or end with a space, hold two spaces in a row, "
                                      "or contain control characters")
        return str(value)

    if block == "page-heading":
        if pixels or names:
            raise IntentError(number, "a heading takes only its text, in double quotes")
        items.append(pages.Heading(text=one_text("heading"), line=number))
        return None
    if block == "page-text":
        if pixels or names:
            raise IntentError(number, "a paragraph takes only its text, in double quotes")
        items.append(pages.Paragraph(text=one_text("text"), line=number))
        return None
    if block == "page-button":
        if names or len(pixels) > 1:
            raise IntentError(number, "a button takes its label in double quotes and, if wanted, one width such as 120px")
        width = pixels[0] if pixels else None
        if width is not None and not 1 <= width <= pages.MAX_WIDTH:
            raise IntentError(number, f"the width must be between 1px and {pages.MAX_WIDTH}px")
        items.append(pages.Button(text=one_text("label"), width=width, line=number))
        return None
    if block in ("data-table", "render-table"):
        tables = [name for name in names if name in data]
        if texts or pixels or len(tables) != 1 or len(names) != 1:
            raise IntentError(number, "name exactly one kind of data for the table to show")
        items.append(pages.Table(data=tables[0], line=number))
        return None
    if block in ("filter-elements-by-text", "table-sort"):
        if texts or pixels or len(names) != 1:
            raise IntentError(number, "name exactly one field")
        return pages._table_feature("searchable" if block == "filter-elements-by-text" else "sortable", names[0], number, items)
    wider = any(set([option] if isinstance(option, str) else option) <= found for option in known.get("wider", []))
    narrower = any(set([option] if isinstance(option, str) else option) <= found for option in known.get("narrower", []))
    if names or len(pixels) != 1 or len(texts) > 1 or wider == narrower:
        raise IntentError(number, "say whether the button gets wider or narrower, and by how many pixels, such as 40px")
    return pages.resize(items, number, pixels[0] if wider else -pixels[0], texts[0] if texts else None)
