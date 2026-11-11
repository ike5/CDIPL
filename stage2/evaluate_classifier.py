"""Run the classifier once on the held-out test wordings and report the result.

Usage: .venv/bin/python stage2/evaluate_classifier.py [--details FILE]
The test wordings were written by sessions that never saw the word lists or training wordings,
and were committed before those existed. Do not use the output to adjust the word lists,
the training wordings or the threshold: that would make the test meaningless.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from cdipl import classifier, words
from stage2.train_classifier import NAMES


def evaluate(language, model):
    word_list = words.load(language)
    outcomes, details = Counter(), []
    with open(REPO / "stage2" / "wordings" / f"test_{language}.tsv", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t", quoting=csv.QUOTE_NONE):
            try:
                tokens, unknown = words.encode(row["wording"], word_list, NAMES)
            except words.WordError as problem:
                outcome, chosen, margin, unknown = "declined: cannot be read", "", 0, [str(problem)]
            else:
                block, ranked, margin = model.choose(words.codes(tokens))
                chosen = ranked[0]
                if unknown:
                    outcome = "declined: unknown word"
                elif block is None:
                    outcome = "declined: too close to call"
                else:
                    outcome = "correct" if block == row["block"] else "wrong"
            outcomes[outcome] += 1
            details.append({"language": language, "block": row["block"], "wording": row["wording"], "outcome": outcome,
                            "best_guess": chosen, "best_guess_correct": chosen == row["block"], "margin": margin,
                            "unknown": unknown})
    return outcomes, details


def main():
    model = classifier.load()
    print(f"classifier version {model.version}, threshold {model.threshold}")
    everything = []
    for language in ("en", "es"):
        outcomes, details = evaluate(language, model)
        everything += details
        total = sum(outcomes.values())
        declined = sum(count for name, count in outcomes.items() if name.startswith("declined"))
        accepted = outcomes["correct"] + outcomes["wrong"]
        guesses = sum(1 for d in details if d["best_guess_correct"])
        known = [d for d in details if not d["unknown"]]
        print(f"\n{language}: {total} wordings")
        for name in sorted(outcomes):
            print(f"   {name}: {outcomes[name]} ({100 * outcomes[name] / total:.1f}%)")
        print(f"   accepted {accepted}, of which wrong {outcomes['wrong']}"
              f" ({100 * outcomes['wrong'] / accepted:.1f}% of accepted)" if accepted else "   accepted 0")
        print(f"   declined in all: {declined} ({100 * declined / total:.1f}%)")
        print(f"   best guess correct, ignoring declining: {guesses}/{total} ({100 * guesses / total:.1f}%); "
              f"among wordings with no unknown word: {sum(d['best_guess_correct'] for d in known)}/{len(known)}")
    if "--details" in sys.argv:
        path = Path(sys.argv[sys.argv.index("--details") + 1])
        path.write_text(json.dumps(everything, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nwrote details to {path}")


if __name__ == "__main__":
    main()
