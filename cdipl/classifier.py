"""A small, fixed classifier that chooses a block from the codes of a statement.

It is a naive Bayes model with whole-number weights, so that the same model file gives
the same answer on every machine. It declines when its two best candidates are close.
"""
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent / "library"
SCALE = 1000


def train(examples, blocks):
    """examples: list of (block, codes). Returns the weights table: code -> list of whole numbers per block."""
    position = {block: index for index, block in enumerate(blocks)}
    counts = [Counter() for _ in blocks]
    for block, features in examples:
        counts[position[block]].update(features)
    vocabulary = sorted({code for counter in counts for code in counter})
    totals = [sum(counter.values()) for counter in counts]
    weights = {}
    for code in vocabulary:
        weights[code] = [round(SCALE * math.log((counts[index][code] + 0.1) / (totals[index] + 0.1 * len(vocabulary))))
                         for index in range(len(blocks))]
    return weights


def scores(weights, features, block_count):
    totals = [0] * block_count
    for code in features:
        row = weights.get(code)
        if row is not None:
            for index, weight in enumerate(row):
                totals[index] += weight
    return totals


def rank(weights, blocks, features):
    """Blocks from best to worst, with the margin between the best two."""
    totals = scores(weights, features, len(blocks))
    order = sorted(range(len(blocks)), key=lambda index: (-totals[index], blocks[index]))
    margin = totals[order[0]] - totals[order[1]]
    informative = any(code in weights for code in features)
    return [blocks[index] for index in order], (margin if informative else 0)


class Classifier:
    def __init__(self, model):
        self.blocks = model["blocks"]
        self.weights = model["weights"]
        self.threshold = model["threshold"]
        self.version = model["version"]

    def choose(self, features):
        """Returns (block or None when declining, ranked candidates, margin)."""
        ranked, margin = rank(self.weights, self.blocks, features)
        return (ranked[0] if margin >= self.threshold else None), ranked, margin


def make_model(weights, blocks, threshold):
    body = {"blocks": blocks, "threshold": threshold, "weights": weights}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return dict(body, version=hashlib.sha256(text.encode()).hexdigest()[:12])


def save(model, path=None):
    (path or HERE / "classifier.json").write_text(json.dumps(model, sort_keys=True, separators=(",", ":")) + "\n",
                                                  encoding="utf-8")


def load(path=None):
    return Classifier(json.loads((path or HERE / "classifier.json").read_text(encoding="utf-8")))
