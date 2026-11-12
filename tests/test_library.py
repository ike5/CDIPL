"""Criterion G8: flagged blocks stop a build, and builds are repeatable."""
import filecmp
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cdipl import library
from cdipl.compiler import BuildError, build
from cdipl.parser import parse
from cdipl.targets import TARGETS, html
from cdipl.targets.common import blocks_used

from .support import REPO

EXAMPLE = REPO / "examples" / "adult_users.intent"


class LibraryTest(unittest.TestCase):
    def test_every_implemented_block_is_in_the_catalogue_with_a_status(self):
        catalogue, statuses = library.catalogue(), library.statuses()
        self.assertEqual(len(catalogue), 103)  # the 90 blocks of the Stage 1 inventory and thirteen for applications
        for block, status in statuses.items():
            self.assertIn(block, catalogue)
            self.assertIn(status, library.STATUSES)
            self.assertRegex(library.version(block), r"^[0-9a-f]{12}$")
        owners = {owner for generator in [*TARGETS.values(), html] for owner, _, _ in generator.SUPPORT}
        owners |= {owner for owner, _, _ in html.SCRIPT} | {owner for owner, _ in html.SERVER}
        self.assertLessEqual(owners, set(statuses))

    def test_a_flagged_block_stops_every_build_that_uses_it(self):
        text = EXAMPLE.read_text(encoding="utf-8")
        for block in blocks_used(parse(text)):
            statuses = dict(library.statuses(), **{block: "flagged"})
            for target in TARGETS:
                with self.subTest(block=block, target=target):
                    with self.assertRaises(BuildError) as caught:
                        build(text, target, statuses)
                    self.assertIn(block, str(caught.exception))
        statuses = dict(library.statuses(), **{"format-json": "flagged"})
        build(text, "python", statuses)  # a flagged block the program does not use is no obstacle

    def test_ten_builds_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as folder:
            for target in TARGETS:
                outputs = []
                for attempt in range(10):
                    out = Path(folder) / f"{target}-{attempt}"
                    subprocess.run([sys.executable, "-m", "cdipl", "build", str(EXAMPLE), "--target", target,
                                    "--out", str(out)], cwd=REPO, check=True, capture_output=True)
                    outputs.append(out)
                names = sorted(path.name for path in outputs[0].iterdir())
                self.assertEqual(len(names), 2)
                for other in outputs[1:]:
                    match, mismatch, errors = filecmp.cmpfiles(outputs[0], other, names, shallow=False)
                    self.assertEqual((sorted(match), mismatch, errors), (names, [], []))


if __name__ == "__main__":
    unittest.main()
