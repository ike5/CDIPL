# The Java target

`cdipl/targets/java.py` turns a checked program into one Java source file, `Main.java`, and lifts such a file back into the program. It was added as a third target after Python and JavaScript, partly to measure what an additional target costs. This page records what the generated code depends on, how to run it, where it could differ from `docs/meaning.md`, and what it took.

**Status:** written by the AI assistant. Not yet reviewed by a person. Every block remains a draft.

## What the generated program depends on

- **Java 21 or later.** The program uses `switch` expressions with arrow labels, pattern matching for `instanceof`, `Stream.toList()` (Java 16) and `java.util.HexFormat` (Java 17). It was tested with OpenJDK 21 on Linux.
- **Only the module `java.base`.** There is no JSON reader in the standard library, so every program carries its own (about 190 lines, see below).
- **Nothing at run time beyond the JVM.** The program reads the file as bytes, decodes it with a UTF-8 decoder set to report malformed input, and writes its output as UTF-8 bytes with line-feed line breaks, whatever the platform's default encoding and line separator are.

## Compiling and running

By hand:

```bash
javac Main.java
java -cp . Main people.json      # or, without a separate compile step: java Main.java people.json
```

`run_command(path)` in `cdipl/targets/java.py`, which the tests use, does three things:

1. **Compiles once per distinct file.** The classes are written to a cache folder named after the SHA-256 of the file's content, under the system temporary folder (`/tmp/cdipl-java/` here; the environment variable `CDIPL_JAVA_CACHE` overrides it). A program that was compiled before, in this run of the tests or an earlier one, is not compiled again.
2. **Compiles through a compile server.** Starting `javac` costs about 0.6 s per program on this machine; the combination test alone builds 399 distinct programs. The first compilation therefore starts one small JVM (`CompileServer`, kept as a string in `java.py` and compiled into the cache) that reads one source path per line on standard input and compiles it with `javax.tools.ToolProvider.getSystemJavaCompiler()`; it takes about 0.1 s per program once warm. It stops when the Python process that started it exits. If it cannot be started, or a compilation fails, the file is compiled again with a fresh `javac` so that the error message is reported.
3. **Runs the classes with options for a quick start:** `java -Xshare:auto -XX:TieredStopAtLevel=1 -XX:+UseSerialGC -cp FOLDER Main`. A run of `examples/adult_users.intent` over the 300-record test file takes about 60 ms, against about 25 ms for Python and 28 ms for Node.

The command is wrapped in `env -u JAVA_TOOL_OPTIONS -u JDK_JAVA_OPTIONS -u _JAVA_OPTIONS`. When `JAVA_TOOL_OPTIONS` is set (it is in this environment), the JVM writes a line `Picked up JAVA_TOOL_OPTIONS: ...` to standard error before the program starts, which would break the rule that the first line of standard error is the error. `env` is a POSIX tool: on Windows the command would have to be built differently. The generated program itself does not depend on the platform.

## Code style

**No formatter was applied.** No Java formatter is installed on this machine and none was installed for this work. The generator writes one fixed style: four spaces per level, braces on the same line, one statement per line, imports sorted, no wildcard imports, no comments. Lines are not wrapped, so a long condition stays on one line. `tests/test_quality_java.py` compiles 43 generated programs, which between them contain every piece of support code, with `javac -Xlint:all -Werror` and expects no output. It is skipped, with a message, when `javac` is not installed.

## How the generated code is laid out

```java
import ...;

public final class Main {
    private static final String SOURCE = "users";
    private static final String[][] FIELDS = {{"name", "text"}, {"age", "integer"}};
    private static final long MAX_INTEGER = 9007199254740991L;
    private static final StringBuilder OUTPUT = new StringBuilder();

    ... fixed support code, only the pieces the program needs ...

    private static void run(String[] args) {
        String json = readTextFile(readArgument(args, 1));
        List<?> records = checkList(parseJson(json));
        List<Map<String, Object>> rows = keepValid(records);
        rows = rows.stream().filter(row -> number(row, "age") >= 18).toList();
        rows = rows.stream().sorted((a, b) -> compareText(foldCase(text(a, "name")), foldCase(text(b, "name")))).toList();
        rows = rows.stream().limit(10).toList();
        if (rows.isEmpty()) {
            emit("No adult users found.\n");
            return;
        }
        showTable(rows, "name", "age");
    }

    public static void main(String[] args) { ... prints the error or the output ... }
}
```

A row is a `LinkedHashMap<String, Object>` holding `String` and `Long` values in the declared order. Each statement of the intent is one line of `run` (two or four for reading the source and for `if none say`). Whole-number arithmetic is written `plus(A, B)`, `minus(A, B)` and `times(A, B)`; each checks the range of its result. Text is compared for equality with `equals`, and ordered with `compareText`. Output is collected in `OUTPUT` and written only after `run` has returned, so a program that fails writes nothing to standard output.

`lift` reads the header and the lines of `run` by fixed patterns, as the other targets do, and `cdipl.compiler.lift` then regenerates the file and refuses it unless it is identical. `tests/test_edited_java.py` checks 48 hand edits (18 lifted, 30 refused).

## How much fixed support code a program carries

Counted with the 120 random programs of `tests/test_roundtrip.py` (seed 4242). "Support" means every line that does not come from a statement of the intent: imports, declarations, support functions and the entry point. Blank lines are not counted.

| Target | Support lines, average | Range | All support pieces together | `examples/adult_users.intent` (total lines / support lines) |
|---|---|---|---|---|
| Python | 78 | 70 to 91 | 89 | 119 / 76 |
| JavaScript | 108 | 93 to 132 | 123 | 137 / 109 |
| Java | 364 | 336 to 405 | 416 (plus 16 import lines) | 402 / 354 |

A typical Java program therefore carries about 4.7 times the support code of the Python program and 3.4 times that of the JavaScript program. Most of the difference is the JSON reader: 195 of the 416 lines belong to `parse-json`, against 9 in Python and 7 in JavaScript, where the language's own reader is used and only adjusted. Next come the checks of records and values in `check-required-types` (51 lines, against 34 and 29) and `format-json` (46 lines, against 2 and 4), because Java has no JSON writer either. The generated Java is also longer per statement only in its types; the lines of `run` correspond one to one to the other targets' lines of `main`.

The generator module itself has 1,073 lines, of which about 500 are the Java support code held as text and about 150 the compiling, caching and compile server (lines 1 to 160); `python.py` has 460 lines and `javascript.py` 545.

## Where Java could differ from the specification

These are the places where Java's habits differ from the rules in `docs/meaning.md`, and how the generated code deals with each. Where it says "matches", the equivalence and combination tests (all 240 pairs and all 399 chains), and an extra comparison of 64 programs on 34 hand-made inputs that was run during development but is not part of the test suite, found no difference from Python and JavaScript.

- **Strings are UTF-16.** Java's `String`, like JavaScript's, can hold an unpaired surrogate, which a `\ud800` escape in the JSON produces. The program checks every text value and treats one holding an unpaired surrogate as invalid. Matches.
- **`String.compareTo` compares UTF-16 code units**, which orders characters above U+FFFF before U+E000 to U+FFFF. The program compares code points instead (`Arrays.compare` of `codePoints()`). Lengths for `show` are counted with `codePointCount`. Matches.
- **`long` arithmetic overflows silently.** Addition and subtraction of two values in range cannot overflow a `long`; multiplication can, so `times` uses `Math.multiplyExact` and reports `out-of-range` if it overflows, and every operation then checks the range. Arithmetic is always done through these methods, which take `long` parameters, so two small literals are never added as `int`. Matches.
- **Numbers in the JSON.** The reader checks the JSON grammar itself and converts a number with `Double.parseDouble`, which is correctly rounded, like Python's `float()` and JavaScript's `Number`. A value is an integer if the double is whole and within the range. Python reads short integer literals exactly instead of as doubles; this gives the same answer, because every whole number in range is exact as a double and nothing outside the range rounds into it. Matches, including `1E400`, `-0`, `-0.0`, `1e-400` and 400-digit literals.
- **A consequence the specification does not state.** In all three targets, "a whole number" means "the nearest double is whole". `9007199254740990.5` has no exact double; it rounds to 9007199254740990, so every target accepts it as that integer, although the specification's example `18.5` suggests a number with a fraction is refused. This is a gap in the specification, not a difference between targets.
- **Nesting depth.** The reader keeps open lists and objects on a stack of its own instead of recursing, so like Node it accepts any depth that fits in memory. Python 3.14 here accepted 10,000 levels and refused 50,000 (as `bad-json`). A file nested more deeply than Python allows is therefore accepted by Java and Node and refused by Python, which is the known limit already listed in `docs/meaning.md`. (That page says Python refuses nesting "more than about a thousand levels deep"; with Python 3.14.6 here the limit is between 10,000 and 50,000.)
- **Very large files.** A Java array or `String` holds at most about 2^31 elements, so a file over 2 GB cannot be read (`Files.readAllBytes` fails with an `OutOfMemoryError`, not `cannot-read`), and the default heap is a quarter of the machine's memory. Not measured.
- **Wording after the category.** For `cannot-read` the detail is the Java exception's class name, for example `NoSuchFileException`, where Python gives the operating system's message and Node its error code. The specification allows this.
- **A path that is not a valid path** (for example one holding a NUL character) is reported as `cannot-read`; Python stops with an unhandled `ValueError` in that case. Not covered by the tests.
- **Standard error encoding.** The error line is written with the platform's default encoding. It is plain ASCII except for a path, which can contain any character.

## What was hardest to match

1. **The JSON reader.** Writing a strict RFC 8259 reader that agrees with Python's and Node's on every input the tests use: no leading zeros, no `+`, digits only from 0 to 9 (not `Character.isDigit`, which accepts other scripts' digits), exactly four hexadecimal digits after `\u` (not `Integer.parseInt`, which accepts a sign), unescaped control characters refused, `DEL` accepted, whitespace limited to space, tab, line feed and carriage return, a byte-order mark refused, duplicate keys keeping the last value. A first version recursed and failed with `bad-json` on 5,000 levels of nesting, which Python accepts; it was rewritten to use its own stack.
2. **Java's `\u` escapes in the source.** `javac` replaces `\u000a`, `\u0022` and `\u005c` in a string literal before it reads the program, which ends the literal or breaks it. The generator never writes a line break, quote or backslash as a `\u` escape, and `lift` refuses one.
3. **Starting fast enough to test.** Compiling with a fresh `javac` for every program made the whole suite take about six minutes from an empty cache, four of them in the combination test. With the compile server the whole suite (66 tests, all targets) takes about 2 minutes 15 seconds from an empty cache and about 1 minute 50 seconds with the cache filled, on this four-core machine.
4. **Avoiding warnings under `-Xlint:all`.** Generic types are checked with wildcards (`List<?>`, `Map<?, ?>`) so that no unchecked cast is needed, and the exception class declares a `serialVersionUID`.
5. **One support method per arithmetic operator.** `plus`, `minus` and `times` are included only when used, so an edit that changes `plus` to `minus` is refused (the `minus` method is missing), where the Python and JavaScript targets lift the same edit. This is deliberate: the edited Java would not compile.

## Tests that cover the Java target

Registering the target makes the shared tests cover it: `tests/test_equivalence.py` (all 240 pairs, and the other cases), `tests/test_combination.py` (all 399 fitting chains), `tests/test_roundtrip.py`, `tests/test_edited.py` (changes to the whole file), `tests/test_library.py` and `tests/test_live.py`. `tests/test_quality_java.py` and `tests/test_edited_java.py` are specific to Java. The suite needs `javac` and `java` 21 on the path.
