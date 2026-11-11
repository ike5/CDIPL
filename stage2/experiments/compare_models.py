"""Compare classifier designs using the training wordings only (12-fold cross-validation).

Usage: .venv/bin/python stage2/experiments/compare_models.py   (needs numpy)
This never reads the held-out test wordings. It was used to decide which model to keep.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import numpy as np

from cdipl import classifier, library
from stage2.train_classifier import FOLDS, examples

blocks = list(library.catalogue()); pos = {b: i for i, b in enumerate(blocks)}
data = []
for lang in ('en', 'es'):
    data += [(lang, b, f) for b, f, _, unknown in examples(lang) if not unknown]
seen, folds = {}, []
for lang, b, _ in data:
    seen[(lang, b)] = seen.get((lang, b), 0) + 1; folds.append((seen[(lang, b)] - 1) % FOLDS)
folds = np.array(folds); y = np.array([pos[b] for _, b, _ in data])

def feats(f, bigrams):
    out = list(f)
    if bigrams:
        out += [a + '|' + b for a, b in zip(f, f[1:])]
    return out

def matrix(bigrams, train_idx):
    vocab = sorted({x for i in train_idx for x in feats(data[i][2], bigrams)})
    col = {v: j for j, v in enumerate(vocab)}
    X = np.zeros((len(data), len(vocab)), dtype=np.float64)
    for i, (_, _, f) in enumerate(data):
        for x in set(feats(f, bigrams)):
            if x in col: X[i, col[x]] = 1.0
    return X

def lr(X, y, l2, epochs=400, rate=1.0):
    n, d = X.shape; W = np.zeros((d, len(blocks))); b = np.zeros(len(blocks))
    Y = np.eye(len(blocks))[y]
    for _ in range(epochs):
        z = X @ W + b; z -= z.max(1, keepdims=True); p = np.exp(z); p /= p.sum(1, keepdims=True)
        g = (p - Y) / n
        W -= rate * (X.T @ g + l2 * W); b -= rate * g.sum(0)
    return W, b

def report(name, margins, correct):
    margins = np.array(margins); correct = np.array(correct)
    acc = correct.mean()
    wrong = margins[~correct]
    t0 = wrong.max() + 1e-9 if len(wrong) else 0
    acc0 = (margins > t0).mean()
    # threshold allowing at most 1 wrong per 300 accepted
    best = 0
    for t in sorted(set(margins)):
        a = margins >= t
        if a.sum() and (~correct[a]).sum() / a.sum() <= 1 / 300: best = max(best, a.mean())
    print(f"{name:28} top-1 {acc:.3f}  accepted with zero wrong {acc0:.3f}  accepted at <=1/300 wrong {best:.3f}")

for bigrams in (False, True):
    # naive Bayes
    m, c = [], []
    for fold in range(FOLDS):
        tr = np.where(folds != fold)[0]; te = np.where(folds == fold)[0]
        w = classifier.train([(data[i][1], feats(data[i][2], bigrams)) for i in tr], blocks)
        for i in te:
            ranked, margin = classifier.rank(w, blocks, feats(data[i][2], bigrams))
            m.append(margin); c.append(ranked[0] == data[i][1])
    report(f"naive Bayes bigrams={bigrams}", m, c)
    for l2 in (1e-4, 1e-3):
        m, c, pairs = [], [], Counter()
        for fold in range(FOLDS):
            tr = np.where(folds != fold)[0]; te = np.where(folds == fold)[0]
            X = matrix(bigrams, tr)
            W, b = lr(X[tr], y[tr], l2)
            z = X[te] @ W + b
            order = np.argsort(-z, axis=1)
            for k, i in enumerate(te):
                top, second = order[k, 0], order[k, 1]
                m.append(z[k, top] - z[k, second]); c.append(top == y[i])
                if top != y[i]: pairs[(blocks[y[i]], blocks[top])] += 1
        report(f"logistic l2={l2} bigrams={bigrams}", m, c)
        if not bigrams and l2 == 1e-4:
            print('   most common confusions (true -> chosen):', pairs.most_common(12))
