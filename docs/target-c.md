# The C target

`cdipl/targets/c.py` turns a checked program into one C file, `main.c`, and lifts a generated `main.c` back to the program. It implements the blocks described in `docs/meaning.md` up to "Web pages"; it does not build applications.

**Status:** written by the AI assistant. Not yet reviewed by a person. Every block remains a draft; adding this target changes the version fingerprint of every block, because a block's version covers its code in every target.

## What the generated C depends on

- A C11 compiler and the C standard library: `<errno.h>`, `<stdarg.h>`, `<stdbool.h>`, `<stddef.h>`, `<stdio.h>`, `<stdlib.h>` and `<string.h>`. Nothing else: no third-party code, no maths library (`-lm` is not needed), no POSIX functions.
- Behaviour the C standard leaves to the platform, which the program relies on:
  - `double` is an IEEE 754 binary64 number and `strtod` rounds correctly. Both hold for glibc on Linux, where the tests were run. The integer rule depends on it (see below).
  - `fopen` sets `errno` when it fails. POSIX requires this; ISO C does not. Only the wording of the `cannot-read` message depends on it.
  - The program never calls `setlocale`, so `strtod` and `printf` work in the "C" locale.
  - Standard output is a byte stream. On Windows, standard output is opened in text mode and each line feed would be written as carriage return and line feed. The program has not been built or run on Windows.

## Compiling and running

```bash
.venv/bin/python -m cdipl build examples/adult_users.intent --target c --out OUT
gcc -std=c11 -O2 -o OUT/main OUT/main.c
OUT/main stage1/samples/j01/users.json
```

Any C11 compiler will do; `clang -std=c11` gives the same program. `run_command` in `c.py`, which the tests use, compiles with `gcc -std=c11 -O0` (or the compiler named by the environment variable `CC`) the first time a program is run and keeps the binary in `cdipl-c-binaries` in the system's temporary folder, named by a SHA-256 hash of the compiler, its flags and the source. Running the same text again does not compile it again, also across test runs; the folder can be deleted at any time. `-O0` is used because compiling is most of the time the tests spend on C; the output does not depend on the optimisation level.

## Code quality

`tests/test_quality_c.py` builds 43 programs (the 40 random programs that `test_quality.py` uses, and three written so that every piece of support code appears at least once) and checks:

- `gcc -std=c11 -Wall -Wextra -Werror -pedantic -O2` compiles each without a warning, and so does `clang` with the same flags;
- `clang-format --style="{BasedOnStyle: LLVM, ColumnLimit: 400, AllowShortFunctionsOnASingleLine: None}"` changes nothing.

The column limit is 400 rather than the 320 of the other targets because C is wordier: an integer field is written `row[F_age].number` and a calculation `calculate(a, '*', b)`. The longest line in 3,000 random programs is 341 characters in C, against 246 in Python and 233 in JavaScript; 4 of the 3,000 C programs have a line longer than 320. A formula long enough to pass 400 characters would be re-wrapped, as a line past 320 would be in the other targets. Each test is skipped, with a message, when its tool is not installed. Tested with gcc 13.3, clang 18.1 and clang-format 18.1.3.

**Includes are written `%:include`.** `%:` is the C digraph for `#` (ISO C 6.4.6) and means exactly the same. It is used because `tests/test_roundtrip.py` checks that no generated line starts with `#`, `//`, `/*` or `*`, treating `#` as a comment as it is in Python. In C, `#` starts a preprocessor directive, and an include cannot be written without one, so the test as written cannot pass with ordinary `#include` lines. The test was left unchanged; if it learns each target's comment markers, the generator can write `#include` instead by changing seven lines of `PRELUDE` in `c.py`. For the same reason no generated line starts with `*`: pointers are written through `->` and indexes instead of `*p = ...`.

The generated code holds no comments.

## How the generated program is laid out

1. The includes, the types `Value` (a text, its length in bytes, and a whole number; a `NULL` text means the value is an integer), `Rows` and `Kind`, and `MAX_INTEGER`.
2. The source name, an `enum` with one constant `F_name` per field name the program uses (declared fields first, then added fields and `count`), the names as text, and the declared types. A field keeps the same place in every row for the whole program, so a field added after counting reuses its place if the name was used before.
3. Fixed support code, one piece at a time, each included only when the program needs it (an unused `static` function would be a warning).
4. One function per `keep where` (`keep_1`, `keep_2`, ...) and per `add` (`add_1`, ...), because C has no anonymous functions. They are numbered in order of appearance, never by intent line, so that the English and Spanish intents build the same file.
5. `main`, with one line (or, for `if none say`, four) per statement, in the shapes listed in `FORMS`.

`lift` reads the header, the step functions and the lines of `main`, rebuilds the program and regenerates it; `cdipl.compiler.lift` refuses the file unless the result is identical. `tests/test_edited_c.py` checks 47 hand edits: 17 are lifted exactly (changed literals, operators, comparisons, fields shown, sort direction and field, file and source name, a repeated or moved step) and 30 are refused (a removed range check, division, foreign statements, both kinds of comment, changed support code, `#include` in place of `%:include`, edits that leave the text and the declared types inconsistent). Unlike Python and JavaScript, deleting a `limit` step by hand is refused, because its support function `first_rows` is left behind unused; the same holds for deleting any step whose support code no other step uses.

## Size of the fixed support code

Counted with `generate` on the programs named, excluding blank lines. "Fixed" means lines not traced to an intent line.

| | Python | JavaScript | C |
|---|---|---|---|
| All support pieces of the target (lines, including blank lines inside pieces) | 89 | 123 | 625, plus a 22-line prelude |
| `examples/adult_users.intent`: whole file | 86 | 120 | 520 |
| of which fixed | 76 | 109 | 506 |
| of which traced to the intent | 10 | 11 | 14 |
| 200 random programs: median fixed lines | 77 | 107 | 495 |
| Generator source, `cdipl/targets/*.py` (lines) | 460 | 545 | 1,253 |

C carries about six and a half times the fixed code of Python, because the standard library has no JSON, no growing lists, no sorting that keeps equal items in order, and no hash map. By block, the C support code is: JSON parser 226 lines, reading the file and checking UTF-8 61, record checks 57, sorting 47, grouping 43, writing JSON 42, the table 38, errors and memory 29, calculation 25, and 6 to 13 for each of the rest. The parser alone is longer than all the Python support code put together.

## Matching the specification

- **Reading.** The file is read with `fopen` and `fread` into memory. A directory opens but cannot be read, which gives `cannot-read`, as required. The bytes are checked as UTF-8 before parsing: overlong forms, encoded surrogates, values above U+10FFFF and truncated sequences give `bad-json`. A byte-order mark is valid UTF-8 but not JSON whitespace, so it also gives `bad-json`, as in Python.
- **JSON.** A recursive-descent parser following RFC 8259: only space, tab, line feed and carriage return as whitespace; no control characters inside strings; the escapes `\" \\ \/ \b \f \n \r \t` and `\uXXXX` with either case of hexadecimal digits; a high surrogate escape followed directly by a low one makes one character, as Python does; `NaN`, `Infinity`, leading zeros, `+1`, `.5` and `1.` are refused. Strings are decoded in place in the file's buffer. Duplicate keys are kept and the last one is found first, so the last value counts.
- **Text validity.** A string that holds an unpaired surrogate escape is marked as not valid text; a record whose declared text field holds one is invalid.
- **Integers.** The number's text is converted with `strtod`, and it is accepted when the result is at least -9007199254740991, at most 9007199254740991, and whole. This agrees with Python (`int` for short integer literals, `float(text).is_integer()` otherwise) and JavaScript (`Number.isSafeInteger`) in every case: an integer literal within range converts exactly; one outside it converts to a `double` of at least 2^53; a literal with a fraction or exponent is rounded once, correctly, in all three. `18.0`, `1e3`, `-0.0`, `1e-400` and `9007199254740990.5` (which rounds to an even whole number) are accepted; `18.5`, `1E400` and `9007199254740992` are not.
- **Calculations** use `long long`. `calculate` checks multiplication before multiplying, so a product never overflows, and checks every result against the range; the error is `out-of-range`. The arguments of one call are evaluated in an order C leaves unspecified, but every way a formula can fail gives the same error, so the order cannot be seen. Conditions are joined with `&&`, which stops at the first that does not hold.
- **Order of text** is `memcmp` on the UTF-8 bytes and then length, which for valid UTF-8 is the order of code points. Ignoring case folds the bytes A to Z only, which gives the same order because every byte of a multi-byte character is 128 or more.
- **Sorting** is a merge sort that takes from the right half only when its row is strictly before the left one in the chosen direction, so equal rows keep their order in both directions. `qsort` is not used because it is not stable.
- **Grouping** uses a hash table with linear probing, so groups are found in time proportional to the number of rows; groups are listed in order of first appearance.
- **Show** measures widths in code points by counting bytes that do not continue a character.
- **Write as JSON** decodes each character and writes it as the specification and Python's `json.dumps` do: `\"`, `\\`, the five short escapes, other characters outside space to `~` as `\u` with four lower-case digits, and characters beyond U+FFFF as a surrogate pair.
- **Errors** go through `fail`, which writes `error: <category>: <source>: <detail>` and calls `exit` with the status in the table. Output is written only by the last step or by `if none say`, after every step that can fail.

Besides the shared tests, two checks were run during development and are not part of the suite: 120 random programs built with AddressSanitizer and UndefinedBehaviorSanitizer and run on the 20 datasets of `test_equivalence.py`, matching Python every time; and about 4,000 crafted and randomly mutated JSON inputs (numbers at the edges of the range, every escape, surrogate combinations, invalid UTF-8, broken structure) run through three programs, matching Python every time.

## Known limits and where C could differ

- **Running out of memory** is outside the specification. Every allocation goes through `allocate`, `larger` and `resize`, which on failure write `error: out-of-memory: <source>: there is not enough memory` and exit with status **8**. Nothing has been written to standard output at that point, because the only allocation made while producing output, the column widths of `show`, happens before the first line is printed. Python would end with a `MemoryError` and status 1, and Node with its own message.
- **Deep nesting.** The parser is recursive and refuses JSON nested more than 10,000 levels deep (counting the outer list and the record) as `bad-json`, to stay well inside an 8 MB stack. Python 3.14 refuses at about 40,000 levels on this machine (the limit depends on the stack) and Node accepts at least a million, so a file nested between 10,000 and 40,000 levels inside an undeclared field is accepted by Python and refused by C.
- **Memory is not freed.** The program reads the whole file and keeps every parsed value until it exits, like the other targets. Each JSON value takes 72 bytes on a 64-bit machine, besides its text. A 36 MB file of 500,000 records was processed in 1.4 seconds (Python 2.1, Node 3.3) with identical output.
- **Output errors** (a closed pipe, a full disk) are not detected; the program still ends with status 0. Python and Node would fail. This is outside the specification.
- **Platform.** Tested only on Linux with glibc, gcc 13.3 and clang 18.1. A C library whose `strtod` does not round correctly could accept or refuse a different set of long decimal numbers.

## What was hardest

- **Integers.** The rule is defined by what Python and JavaScript do with floating-point numbers; C had to reproduce it with `strtod` and range checks, and the argument that this agrees in every case depends on correct rounding.
- **Surrogates.** JSON escapes are UTF-16 code units. Matching Python meant pairing a high escape only with an immediately following low escape and treating any other surrogate as making the text invalid, while still storing it.
- **No anonymous functions.** Filters and added fields became separate numbered functions, and `lift` had to match each line of `main` with its function.
- **Unused code is an error.** With `-Wall -Werror` an unused `static` function fails the build, so support code had to be split into pieces with exact conditions for inclusion, and an added field that uses no field had to mark its parameter as used with `(void)row;`.
- **The shared tests' idea of a comment** (lines starting with `#` or `*`) forced the `%:include` digraph and some reshaping of ordinary C.

## Cost in the test suite

Registering the target makes `test_equivalence` (240 pairs and the other cases), `test_combination` (all 399 fitting chains), `test_roundtrip`, `test_live`, `test_edited` (whole-file changes) and `test_library` cover C. With an empty binary cache the whole suite took 105 seconds on this machine, against 45 seconds before the C target; most of the difference is about 400 compilations at about 0.1 second each. With the cache filled by an earlier run it takes less. The tests need `gcc` (or the compiler named by `CC`) to run C programs.
