"""Train the block classifier from the training wordings and word lists.

Usage: .venv/bin/python stage2/train_classifier.py
Writes cdipl/library/classifier.json and prints what it did.

The decline threshold is chosen without the held-out test wordings: the training wordings are
split into 12 folds, each fold is classified by a model trained on the others, and the threshold
is the smallest margin above which no held-out training wording is classified wrongly, times 1.5.
"""
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from cdipl import classifier, library, words  # noqa: E402

NAMES = set("users orders items files records lines name age price city id date status email total amount region "
            "size count path title done text".split())
FOLDS = 12
SAFETY = 1.5


def examples(language):
    """(block, features, wording, unknown words) for each training wording in one language."""
    path = REPO / "stage2" / "wordings" / f"train_{language}.tsv"
    if not path.exists():
        return []
    word_list = words.load(language)
    out = []
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t", quoting=csv.QUOTE_NONE):
            tokens, unknown = words.encode(row["wording"], word_list, NAMES)
            out.append((row["block"], words.codes(tokens), row["wording"], unknown))
    return out


def main():
    blocks = list(library.catalogue())
    data = []
    for language in ("en", "es"):
        found = examples(language)
        missing = [(wording, unknown) for _, _, wording, unknown in found if unknown]
        print(f"{language}: {len(found)} training wordings, {len(missing)} with words missing from the word list")
        for wording, unknown in missing[:10]:
            print(f"   missing {unknown}: {wording}")
        data += [(language, block, features) for block, features, _, _ in found]
    if not data:
        sys.exit("no training wordings found")

    seen, folds = {}, []
    for language, block, _ in data:
        seen[(language, block)] = seen.get((language, block), 0) + 1
        folds.append((seen[(language, block)] - 1) % FOLDS)
    results = []
    for fold in range(FOLDS):
        training = [(block, features) for (_, block, features), which in zip(data, folds) if which != fold]
        weights = classifier.train(training, blocks)
        for (_, block, features), which in zip(data, folds):
            if which == fold:
                ranked, margin = classifier.rank(weights, blocks, features)
                results.append((margin, ranked[0] == block))
    wrong_margins = [margin for margin, correct in results if not correct]
    threshold = int((max(wrong_margins) + 1) * SAFETY) if wrong_margins else 1
    accepted = [correct for margin, correct in results if margin >= threshold]
    print(f"cross-validation on training wordings: {sum(c for _, c in results)}/{len(results)} best guesses correct; "
          f"largest margin of a wrong guess {max(wrong_margins, default=0)}")
    print(f"threshold {threshold}: {len(accepted)}/{len(results)} accepted "
          f"({100 * (1 - len(accepted) / len(results)):.0f}% declined), {accepted.count(False)} accepted wrongly")

    weights = classifier.train([(block, features) for _, block, features in data], blocks)
    model = classifier.make_model(weights, blocks, threshold)
    classifier.save(model)
    print(f"wrote cdipl/library/classifier.json, version {model['version']}, {len(weights)} codes, {len(blocks)} blocks")


if __name__ == "__main__":
    main()
