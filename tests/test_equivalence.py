"""Criterion G1: every target gives byte-identical output, or the same category of error."""
import json
import unittest

from cdipl import targets
from cdipl.parser import parse

from .support import REPO, Workspace, programs, run

TARGETS = tuple(targets.TARGETS)  # every target is compared with the first, Python


def people(rows):
    return json.dumps(rows, ensure_ascii=False).encode("utf-8")


ORDINARY = [
    {"name": "Zoe", "age": 34, "city": "Lima"}, {"name": "adam", "age": 18, "city": "Quito"},
    {"name": "Bianca", "age": 17, "city": "Lima"}, {"name": "carlos", "age": 45, "city": "lima"},
    {"name": "Zoe", "age": 18, "city": "Quito"}, {"name": "Ñandú", "age": 30, "city": "Lima"},
    {"name": "～", "age": 2, "city": "😀"}, {"name": "😀", "age": 2, "city": "～"},
    {"name": "", "age": 0, "city": ""}, {"name": "m", "age": -5, "city": "m"},
]

DATASETS = {
    "ordinary": people(ORDINARY),
    "empty-list": b"[]",
    "one-record": people(ORDINARY[:1]),
    "ties": people([{"name": n, "age": 18, "city": c} for n, c in
                    [("b", "x"), ("B", "x"), ("a", "y"), ("b", "y"), ("A", "x"), ("a", "x")]]),
    "many": people([{"name": f"p{i % 7}", "age": (i * 37) % 23 - 5, "city": f"c{i % 3}"} for i in range(300)]),
    "edge-numbers": b'[{"name":"a","age":9007199254740993,"city":"x"},{"name":"b","age":9007199254740992,"city":"x"},'
                    b'{"name":"c","age":9007199254740991,"city":"x"},{"name":"d","age":-9007199254740991,"city":"x"},'
                    b'{"name":"e","age":18.0,"city":"x"},{"name":"f","age":1e3,"city":"x"},{"name":"g","age":18.5,"city":"x"},'
                    b'{"name":"h","age":-0.0,"city":"x"},{"name":"i","age":-0,"city":"x"},{"name":"j","age":1E400,"city":"x"},'
                    b'{"name":"k","age":"18","city":"x"},{"name":"l","age":true,"city":"x"},{"name":"m","age":null,"city":"x"},'
                    b'{"name":"n","age":' + b"1" + b"0" * 400 + b',"city":"x"},{"name":"o","age":2,"city":"x"}]',
    "valid-odd-numbers": b'[{"name":"e","age":18.0,"city":"x"},{"name":"f","age":1e3,"city":"x"},'
                         b'{"name":"h","age":-0.0,"city":"x"},{"name":"i","age":-0,"city":"x"},'
                         b'{"name":"c","age":9007199254740991,"city":"y"},{"name":"d","age":-9007199254740991,"city":"y"}]',
    "missing-and-extra": b'[{"name":"a","age":1,"city":"x","extra":[1,{"deep":null}]},{"name":"b","city":"x"},'
                         b'{"age":3,"city":"x"},{"name":"d","age":4},{"name":"e","age":5,"city":"y","age":6}]',
    "not-records": b'[{"name":"a","age":1,"city":"x"},null,[1,2],"text",7,{"name":"z","age":9,"city":"q"}]',
    "odd-text": b'[{"name":"\\ud800","age":1,"city":"x"},{"name":"tab\\tnew\\nline","age":2,"city":"\\u0000"},'
                b'{"name":"del\\u007f","age":3,"city":"\\u2028"},{"name":"\\ud83d\\ude00","age":4,"city":"\\u00e9"}]',
    "valid-odd-text": b'[{"name":"tab\\tnew\\nline","age":2,"city":"\\u0000"},{"name":"del\\u007f","age":3,"city":"\\u2028"},'
                      b'{"name":"\\ud83d\\ude00","age":4,"city":"\\u00e9"},{"name":"quote\\"back\\\\","age":5,"city":"/"}]',
    "an-object": b'{"name":"a","age":1,"city":"x"}',
    "a-number": b"42",
    "bad-trailing-comma": b'[{"name":"a","age":1,"city":"x"},]',
    "bad-nan": b'[{"name":"a","age":NaN,"city":"x"}]',
    "bad-infinity": b'[{"name":"a","age":1,"city":"x","other":-Infinity}]',
    "bad-empty-file": b"",
    "bad-bom": b"\xef\xbb\xbf[]",
    "bad-utf8": b'[{"name":"\xff","age":1,"city":"x"}]',
    "bad-single-quotes": b"[{'name':'a'}]",
}


class EquivalenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = Workspace()
        cls.data = {name: cls.work.write_data(f"{name}.json", content) for name, content in DATASETS.items()}

    @classmethod
    def tearDownClass(cls):
        cls.work.close()

    def test_targets_agree_on_every_pair(self):
        chosen = programs(12, seed=20261111)
        pairs = 0
        for index, program in enumerate(chosen):
            built = {target: self.work.write_program(program, target) for target in TARGETS}
            for name, path in self.data.items():
                results = {target: run(target, built[target], path) for target in TARGETS}
                pairs += 1
                with self.subTest(program=index, dataset=name):
                    for target in TARGETS[1:]:
                        self.assertEqual(results[TARGETS[0]], results[target], target)
                    self.assertFalse(results["python"][2].startswith("unexpected"), results["python"])
        self.assertGreaterEqual(pairs, 200)

    def test_missing_file_and_missing_argument(self):
        program = programs(1, seed=7)[0]
        built = {target: self.work.write_program(program, target) for target in TARGETS}
        for arguments, expected in (((), (2, b"", "usage")), ((self.work.path / "absent.json",), (3, b"", "cannot-read")),
                                    ((self.work.path,), (3, b"", "cannot-read"))):
            for target in TARGETS:
                with self.subTest(target=target, arguments=arguments):
                    self.assertEqual(run(target, built[target], *arguments), expected)

    def test_expected_results_on_known_data(self):
        """Guards against both targets being wrong in the same way."""
        text = ('language: en\n\nsource people from argument 1:\n    name: text\n    age: integer\n    city: text\n\n'
                'get people\nskip invalid records\nkeep where age >= 18\nsort by name ascending\nwrite as json\n')
        program = parse(text)
        expected = {
            "ordinary": b'[{"name":"Zoe","age":34,"city":"Lima"},{"name":"Zoe","age":18,"city":"Quito"},'
                        b'{"name":"adam","age":18,"city":"Quito"},{"name":"carlos","age":45,"city":"lima"},'
                        b'{"name":"\\u00d1and\\u00fa","age":30,"city":"Lima"}]\n',
            "edge-numbers": b'[{"name":"c","age":9007199254740991,"city":"x"},{"name":"e","age":18,"city":"x"},'
                            b'{"name":"f","age":1000,"city":"x"}]\n',
            "empty-list": b"[]\n",
        }
        for target in TARGETS:
            built = self.work.write_program(program, target)
            for name, output in expected.items():
                with self.subTest(target=target, dataset=name):
                    self.assertEqual(run(target, built, self.data[name]), (0, output, ""))
            with self.subTest(target=target, dataset="an-object"):
                self.assertEqual(run(target, built, self.data["an-object"]), (5, b"", "not-a-list"))
            with self.subTest(target=target, dataset="bad-nan"):
                self.assertEqual(run(target, built, self.data["bad-nan"]), (4, b"", "bad-json"))

    def test_strict_reading_reports_the_first_invalid_record(self):
        text = ('language: en\n\nsource people from argument 1:\n    name: text\n    age: integer\n    city: text\n\n'
                'get people\nshow name\n')
        program = parse(text)
        for target in TARGETS:
            built = self.work.write_program(program, target)
            with self.subTest(target=target):
                self.assertEqual(run(target, built, self.data["missing-and-extra"]), (6, b"", "invalid-record"))
                self.assertEqual(run(target, built, self.data["one-record"]), (0, b"Zoe\n", ""))

    def test_sample_program_j1(self):
        """The generated program behaves like the Stage 1 sample J1 on its test input."""
        program = parse((REPO / "examples" / "adult_users.intent").read_text(encoding="utf-8"))
        sample = run("javascript", REPO / "stage1/programs/javascript/j01_adult_users.js",
                     REPO / "stage1/samples/j01/users.json")
        self.assertEqual(sample[0], 0)
        for target in TARGETS:
            built = self.work.write_program(program, target)
            with self.subTest(target=target):
                self.assertEqual(run(target, built, REPO / "stage1/samples/j01/users.json"), sample)


if __name__ == "__main__":
    unittest.main()
