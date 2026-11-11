"""Decide which block a freely worded statement means, and remember the decision in an index."""
from . import classifier as classifier_module
from . import library, words
from .model import IntentError


def empty_index():
    return {"classifier": "", "statements": {}}


def key_for(statement):
    return " ".join(statement.split())


class Resolver:
    """Resolves statements for one intent file.

    Decisions already in the index are reused without consulting the classifier.
    `entries` collects the decisions used in this run, which become the new index.
    """

    def __init__(self, language, index=None, classifier=None, word_list=None):
        self.language = language
        self.index = index or empty_index()
        self._classifier = classifier
        self._words = word_list
        self.entries = {}
        self.consulted = 0

    @property
    def classifier(self):
        if self._classifier is None:
            self._classifier = classifier_module.load()
        return self._classifier

    @property
    def words(self):
        if self._words is None:
            self._words = words.load(self.language)
        return self._words

    def candidates(self, statement, names):
        tokens, unknown = words.encode(statement, self.words, names)
        _, ranked, margin = self.classifier.choose(words.codes(tokens))
        return ranked, margin, unknown

    def resolve(self, statement, line, names):
        """Returns (block, tokens). Raises IntentError when no block can be chosen safely."""
        try:
            tokens, unknown = words.encode(statement, self.words, names)
        except words.WordError as problem:
            raise IntentError(line, str(problem)) from None
        key = key_for(statement)
        entry = self.index["statements"].get(key)
        if entry is None:
            if unknown:
                listed = ", ".join(f"'{word}'" for word in unknown)
                raise IntentError(line, f"not understood: {listed} is not in the word list. Reword the statement, "
                                        f"or record the block you mean with the choose command.")
            self.consulted += 1
            block, ranked, _ = self.classifier.choose(words.codes(tokens))
            if block is None:
                descriptions = library.catalogue()
                closest = "; ".join(f"{name} ({descriptions[name]})" for name in ranked[:2])
                raise IntentError(line, f"cannot tell which operation this statement means. The closest are: {closest}. "
                                        f"Reword the statement, or record the block you mean with the choose command.")
            entry = {"block": block, "by": "classifier", "classifier": self.classifier.version}
        self.entries[key] = dict(entry, version=library.version(entry["block"]))
        return entry["block"], tokens

    def new_index(self):
        version = self._classifier.version if self._classifier is not None else self.index.get("classifier", "")
        return {"classifier": version, "statements": dict(sorted(self.entries.items()))}
