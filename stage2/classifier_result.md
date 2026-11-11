# Stage 2 result: the classifier on wording it had not seen

**Status:** complete, 2026-11-11. The held-out test was run once, on a classifier frozen beforehand. Awaiting the product owner's decision on what to do next.

## Result in brief

The classifier chooses a block for a freely worded statement, or declines. The owner approved two pass marks: at most 1 wrong choice in 300 unseen wordings, and at most 25% of statements declined.

| | English | Spanish | Mark |
|---|---|---|---|
| Unseen wordings tested | 360 | 360 | |
| Chosen correctly | 243 (67.5%) | 271 (75.3%) | |
| **Chosen wrongly** | **3, or 1 in 120** | **3, or 1 in 120** | at most 1 in 300: **not met** |
| **Declined** | **114 (31.7%)** | **86 (23.9%)** | at most 25%: **not met in English, met in Spanish** |
| of which too close to call | 90 | 68 | |
| of which an unknown word | 24 | 18 | |
| Best guess correct, if it never declined | 336 (93.3%) | 343 (95.3%) | |

- **The mark for wrong choices is missed in both languages.** Among the statements the classifier accepted, about 1 in 85 was the wrong block.
- **The mark for declining is missed in English** and narrowly met in Spanish.
- **The classifier is right most of the time.** Its first guess is the right block for 93% to 95% of unseen wordings. The difficulty is not finding the block; it is knowing when the guess can be trusted without anyone looking.

## What was tested

- **The blocks.** All 90 blocks in the catalogue (`cdipl/library/catalogue.tsv`), which came from the Stage 1 inventory. Only 16 of them are built; the classifier is tested on all 90 so that it faces a library of realistic size.
- **The test wordings.** 360 per language, four for each block (`stage2/wordings/test_en.tsv`, `test_es.tsv`). They were written by two separate assistant sessions that were given only the catalogue, and were committed before any word list or training wording existed.
- **The training wordings and word lists.** 1,080 wordings per language, twelve for each block, and a word list per language that maps words and set phrases to 374 shared concept codes (4,391 English forms, 26,614 Spanish forms). They were written by two further sessions that were forbidden to open the test files.
- **The classifier.** A naive Bayes model over concept codes, stored as whole numbers so that it gives the same answer on every machine (`cdipl/classifier.py`). It declines when a statement contains a word that is not in the word list, or when its two best candidates are closer than a threshold.
- **The threshold.** Chosen from the training wordings alone, by a rule fixed in advance: the lowest margin at which no more than 1 in 300 accepted training wordings is wrong in twelve-fold cross-validation.
- **The freeze.** The word lists, classifier and threshold were committed (`ae2d61c`) before the test was run. The test was run once.

## The six wrong choices

| Language | Statement | Meant | Chosen |
|---|---|---|---|
| English | for every date, work out the combined amount of all the orders that fall on that date | `group-total` | `total` |
| English | work out how many records we ended up with altogether, as a single number | `count-rows` | `total` |
| English | set "#count" text to 0 | `set-text` | `update-where` |
| Spanish | el text viene en formato CSV, con comas entre valores y una fila por línea; pásalo a una lista de filas | `parse-csv` | `format-csv` |
| Spanish | de cada uno de los files necesito por un lado el nombre sin la extensión y por otro la extensión sola | `split-extension` | `choose-by-value` |
| Spanish | dame cada region que aparece en orders, sin repetir ninguna | `distinct-values` | `count-values` |

In each case the chosen block is a close neighbour of the one meant: a total where a per-group total was meant, writing CSV where reading CSV was meant, counting values where listing them was meant. A program built from these would run and give a plausible, wrong answer.

Five of the six chosen blocks are not built yet, so today the compiler would have stopped with "not built yet". That protection disappears as the library grows.

## Why statements were declined

- **Too close to call** (90 English, 68 Spanish). In 70 and 57 of these the best guess was in fact right. The classifier was being cautious, as the threshold requires.
- **An unknown word** (24 English, 18 Spanish). Examples: `complain`, `bold`, `enforce`, `figure`, `progress`; `basta`, `montón`, `descuento`, `distinguir`, `nadie`. The word lists are large, but ordinary language is larger.

## The trade-off

Raising the threshold reduces wrong choices and increases declining. These figures are from the test wordings and are for information only: a threshold must not be chosen from them.

| Threshold | English: accepted | English: wrong | English: declined | Spanish: accepted | Spanish: wrong | Spanish: declined |
|---|---|---|---|---|---|---|
| 2000 | 286 | 5 | 20.6% | 312 | 4 | 13.3% |
| 3757 (used) | 246 | 3 | 31.7% | 274 | 3 | 23.9% |
| 5000 | 194 | 1 | 46.1% | 226 | 0 | 37.2% |
| 7000 | 129 | 1 | 64.2% | 146 | 0 | 59.4% |
| 10000 | 70 | 0 | 80.6% | 98 | 0 | 72.8% |

No threshold on this table meets both marks in either language.

## What cross-validation predicted

On the training wordings alone, cross-validation gave 94.4% of best guesses correct, 30% declined and 5 wrong among 1,521 accepted (1 in 304). The test gave 93% to 95% correct and 24% to 32% declined, which is close, but about three and a half times as many wrong choices among those accepted. Wordings from a different author are harder to be sure about than wordings from the same author.

Other designs were compared by cross-validation before the test (`stage2/experiments/compare_models.py`): logistic regression, and both models with pairs of adjacent codes added. None beat the simple model. Doubling the training wordings, by adding Spanish to English, raised cross-validated accuracy from 87% to 94%.

## English and Spanish on the built blocks

A separate check uses 32 pairs of statements for the built blocks, written by the assistant in English and Spanish after the word lists existed (`tests/test_real_wording.py`).

- 14 English and 13 Spanish statements were accepted; the rest were declined.
- None was accepted as the wrong block.
- All 13 pairs accepted in both languages built byte-identical programs.

More than half were declined. The catalogue describes each block in general terms, while the built versions are specific: the built message block only speaks when there are no rows, and the built calculation block needs a name, an equals sign and a formula. Statements that fit the built version do not always resemble the training wordings for the general block.

## Limits

- **One test set, now used.** Having looked at the individual results, any change to the word lists, the training wordings or the model must be tested on new wordings written afresh. Re-running this test after such a change would prove nothing.
- **All wordings were written by AI assistants.** The test authors were kept apart from the training authors, but they are the same kind of author. Real developers may phrase things in ways none of them did.
- **Four test wordings per block** is a small sample for any one block. The totals are more reliable than the per-block picture.
- **Statements were tested one at a time,** without a surrounding program. In a real intent file, some wrong choices would be caught because the chosen block does not fit its neighbours. That was not measured.
- **Spanish was checked by no Spanish speaker.**

## Options

The plan says that if the mark for wrong choices fails, the decision that the classifier chooses without confirmation should be revisited before going further. These are the options as I see them.

1. **Confirm once, then remember.** The first time a statement is built, show the developer which block was chosen, using what `explain` already prints, and record their acceptance in the index. Later builds are silent. With a first guess that is right 93% to 95% of the time, almost every statement needs only an acceptance, and a wrong choice is caught before it produces a program. The index and the `choose` command already support this. *This is what I recommend.*
2. **Keep silent choosing, with a stricter threshold.** Fewer wrong choices, many more declined statements. The table above suggests no setting that meets both marks.
3. **Improve the classifier and test again.** More training wordings per block is the most promising route, since doubling them helped. It needs a new held-out test set, and there is no assurance of reaching 1 in 300.
4. **Accept the measured rates.** About 1 accepted statement in 85 is wrong, and a quarter to a third are declined. This is the owner's call; I would not recommend it for a product whose claim is that it does not guess.

Options 1 and 3 can be combined.

## Reproducing the figures

```bash
.venv/bin/python stage2/train_classifier.py
.venv/bin/python stage2/evaluate_classifier.py
```

The per-wording outcomes of the test run are in `stage2/classifier_test_details.json`.
