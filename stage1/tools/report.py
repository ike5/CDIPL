"""Compute the Stage 1 inventory figures.

Reads stage1/units.csv (program,unit,start,end,lines) and one or two
classification files (program,unit,level,blocks). Levels are A, B or C as
defined in stage1/inventory.md; blocks are separated by ';'.

Usage: python3 report.py UNITS CLASSIFICATION [SECOND_CLASSIFICATION]
"""
import csv
import sys
from collections import Counter, defaultdict


def read(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    units = {(r["program"], r["unit"]): int(r["lines"]) for r in read(sys.argv[1])}
    rows = read(sys.argv[2])
    level = {(r["program"], r["unit"]): r["level"] for r in rows}
    blocks = {(r["program"], r["unit"]): [b for b in r["blocks"].split(";") if b] for r in rows}
    missing = set(units) ^ set(level)
    if missing:
        sys.exit(f"units and classification disagree on: {sorted(missing)}")

    programs = sorted({p for p, _ in units}, key=lambda p: (p[0], int(p[1:])))
    total_units, total_lines = len(units), sum(units.values())
    print(f"programs {len(programs)}, units {total_units}, counted lines {total_lines}\n")

    print("program  units  A  B  C  lines  open-lines  closed-strict  closed-lenient")
    strict = lenient = 0
    for p in programs:
        keys = [k for k in units if k[0] == p]
        c = Counter(level[k] for k in keys)
        open_lines = sum(units[k] for k in keys if level[k] == "C")
        is_strict, is_lenient = c["B"] + c["C"] == 0, c["C"] == 0
        strict += is_strict
        lenient += is_lenient
        print(f"{p:7}  {len(keys):5} {c['A']:2} {c['B']:2} {c['C']:2}  {sum(units[k] for k in keys):5}  "
              f"{open_lines:10}  {'yes' if is_strict else 'no':13}  {'yes' if is_lenient else 'no'}")

    print(f"\nwhole programs closed: strict (all A) {strict}/{len(programs)}, "
          f"lenient (A or B) {lenient}/{len(programs)}")
    for name, wanted in (("A", "A"), ("A or B", "AB")):
        n = sum(1 for k in units if level[k] in wanted)
        lines = sum(units[k] for k in units if level[k] in wanted)
        print(f"units at level {name}: {n}/{total_units} ({100 * n / total_units:.0f}%), "
              f"lines {lines}/{total_lines} ({100 * lines / total_lines:.0f}%)")

    by_units, by_programs = Counter(), defaultdict(set)
    for key, names in blocks.items():
        for b in set(names):
            by_units[b] += 1
            by_programs[b].add(key[0])
    ranked = sorted(by_units, key=lambda b: (-len(by_programs[b]), -by_units[b], b))
    print(f"\ndistinct blocks: {len(ranked)}; used in 2+ programs: "
          f"{sum(1 for b in ranked if len(by_programs[b]) > 1)}; used in one program only: "
          f"{sum(1 for b in ranked if len(by_programs[b]) == 1)}")

    closed = [k for k in units if level[k] in "AB"]
    for share in (0.5, 0.8, 1.0):
        chosen = set()
        for i, b in enumerate(ranked, 1):
            chosen.add(b)
            covered = sum(1 for k in closed if set(blocks[k]) <= chosen)
            if covered >= share * len(closed):
                print(f"blocks needed to cover {int(share * 100)}% of closed units: {i}")
                break

    print("\nblock, programs, units")
    for b in ranked:
        print(f"{b}, {len(by_programs[b])}, {by_units[b]}")

    if len(sys.argv) > 3:
        other = {(r["program"], r["unit"]): r["level"] for r in read(sys.argv[3])}
        shared = [k for k in units if k in other]
        same = sum(1 for k in shared if other[k] == level[k])
        same_open = sum(1 for k in shared if (other[k] == "C") == (level[k] == "C"))
        print(f"\nsecond classification: {len(shared)} units compared; same level {same} "
              f"({100 * same / len(shared):.0f}%); same closed-or-open {same_open} "
              f"({100 * same_open / len(shared):.0f}%)")
        table = Counter((level[k], other[k]) for k in shared)
        print("first\\second  A   B   C")
        for a in "ABC":
            print(f"{a:12} " + " ".join(f"{table[(a, b)]:3}" for b in "ABC"))
        for k in shared:
            if other[k] != level[k]:
                print(f"  differs: {k[0]} {k[1]}: first {level[k]}, second {other[k]}")


if __name__ == "__main__":
    main()
