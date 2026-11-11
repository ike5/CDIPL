"""Word lists: turn the words of a statement into language-independent codes."""
import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).parent / "library"
TOKEN = re.compile(r'(?P<text>"(?:[^"\\]|\\["\\])*")|(?P<number>-?\d+)(?![\w.])|(?P<op>>=|<=|!=|=|<|>)|(?P<comma>,)|'
                   r"(?P<word>[^\W\d][\w'’-]*)|(?P<sym>[-+*&()])|(?P<stray>\S)")
SUFFIXES = {
    "en": (("ies", "y"), ("es", ""), ("s", ""), ("ing", ""), ("ing", "e"), ("ed", ""), ("ed", "e"), ("d", "")),
    "es": (("es", ""), ("s", "")),
}
IGNORED = set(".:;?!¿¡/")
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
FILLER = "-"


@dataclass(frozen=True)
class Token:
    kind: str  # text, number, op, comma, name or word
    value: object
    code: str = ""  # for words: the concept code, "-" for filler, "" if unknown


class WordError(Exception):
    pass


def fold(form):
    """Lower-case and strip accents, so that 'más' and 'mas' are found alike."""
    decomposed = unicodedata.normalize("NFD", form.lower().replace("’", "'"))
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


class WordList:
    def __init__(self, language, pairs):
        self.language = language
        self.single = {}
        self.phrases = {}
        folded = {}
        for form, code in pairs:
            words = tuple(form.split())
            if len(words) == 1:
                self.single[form] = code
                folded.setdefault(fold(form), set()).add(code)
            else:
                self.phrases.setdefault(fold(words[0]), []).append((tuple(fold(word) for word in words), code))
        for options in self.phrases.values():
            options.sort(key=lambda option: (-len(option[0]), option[0]))
        self.folded = {form: next(iter(codes)) for form, codes in folded.items() if len(codes) == 1}

    def lookup(self, word):
        """The code for one word, "-" for filler, or "" if the word is not known."""
        lowered = word.lower().replace("’", "'")
        candidates = [lowered]
        if lowered.endswith("'s"):
            candidates.append(lowered[:-2])
        for ending, replacement in SUFFIXES.get(self.language, ()):
            if lowered.endswith(ending) and len(lowered) > len(ending) + 2:
                candidates.append(lowered[: -len(ending)] + replacement)
        for candidate in candidates:
            if candidate in self.single:
                return self.single[candidate]
        for candidate in candidates:
            if fold(candidate) in self.folded:
                return self.folded[fold(candidate)]
        return ""

    def phrase_at(self, words, position):
        """The longest listed phrase starting at this position: (length, code) or None."""
        for phrase, code in self.phrases.get(fold(words[position]), ()):
            if tuple(fold(word) for word in words[position:position + len(phrase)]) == phrase:
                return len(phrase), code
        return None


def load(language):
    path = HERE / f"words_{language}.tsv"
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle, delimiter="\t", quoting=csv.QUOTE_NONE))
    return WordList(language, [(row[0], row[1]) for row in rows[1:] if len(row) >= 2])


def split(statement):
    """Split a statement into raw tokens. Raises WordError for text that is not closed."""
    found = []
    for match in TOKEN.finditer(statement):
        kind = match.lastgroup
        value = match.group(kind)
        if kind == "stray":
            if value == '"':
                raise WordError("a piece of text in double quotes is not closed")
            if value not in IGNORED:
                raise WordError(f"cannot read '{value}'")
            continue
        if kind == "text":
            value = re.sub(r"\\(.)", r"\1", value[1:-1])
        elif kind == "number":
            value = int(value)
        elif kind == "word":
            value = value.strip("-'’") or value
        found.append((kind, value))
    return found


def encode(statement, words, names):
    """Turn a statement into tokens with codes.

    names are the source and field names in force; they pass through untouched.
    Returns (tokens, unknown words).
    """
    raw = split(statement)
    tokens, unknown = [], []
    index = 0
    while index < len(raw):
        kind, value = raw[index]
        if kind != "word":
            tokens.append(Token(kind, value))
            index += 1
            continue
        if value in names:
            tokens.append(Token("name", value))
            index += 1
            continue
        if raw[index + 1:index + 2] == [("op", "=")] and IDENTIFIER.match(value):
            tokens.append(Token("newname", value))  # a word just before an equals sign names a new field
            index += 1
            continue
        run = []
        for other_kind, other in raw[index:]:
            if other_kind != "word" or other in names:
                break
            run.append(other)
        phrase = words.phrase_at(run, 0)
        if phrase is not None:
            length, code = phrase
            tokens.append(Token("word", " ".join(run[:length]), code))
            index += length
            continue
        code = words.lookup(value)
        if not code:
            unknown.append(value)
        tokens.append(Token("word", value, code))
        index += 1
    return tokens, unknown


def codes(tokens):
    """The features the classifier sees: concept codes and markers for values."""
    out = []
    for token in tokens:
        if token.kind == "word":
            if token.code and token.code != FILLER:
                out.append(token.code)
        elif token.kind != "comma":
            out.append({"text": "<text>", "number": "<number>", "op": "<comparison>", "name": "<name>",
                        "newname": "<newname>", "sym": "<arithmetic>"}[token.kind])
    return out
