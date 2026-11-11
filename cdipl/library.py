"""The block library: what each block is, its review status and its version."""
import csv
import hashlib
import json
from pathlib import Path

from .targets import TARGETS

HERE = Path(__file__).parent / "library"
STATUSES = ("draft", "verified", "flagged")


def catalogue():
    """Every block the library plans to hold, with a one-line description."""
    with open(HERE / "catalogue.tsv", newline="", encoding="utf-8") as handle:
        return {row["block"]: row["description"] for row in csv.DictReader(handle, delimiter="\t")}


def statuses():
    """Review status of each implemented block: draft, verified or flagged."""
    return json.loads((HERE / "status.json").read_text(encoding="utf-8"))


def version(block):
    """A short fingerprint of a block's code in every target. It changes when the code does."""
    digest = hashlib.sha256()
    for name in sorted(TARGETS):
        for owner, flag, text in TARGETS[name].SUPPORT:
            if owner == block:
                digest.update(f"{name}\0{flag}\0{text}\0".encode("utf-8"))
        digest.update(TARGETS[name].FORMS.get(block, "").encode("utf-8"))
    return digest.hexdigest()[:12]
