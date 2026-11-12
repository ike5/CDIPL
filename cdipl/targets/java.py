"""Generate Java programs, and recognise programs this generator wrote."""
import atexit
import hashlib
import os
import re
import subprocess
import tempfile
from pathlib import Path

from .common import (
    Add,
    Arith,
    Concat,
    Condition,
    Count,
    Field,
    Filter,
    Group,
    IfNone,
    Limit,
    NotGenerated,
    Number,
    Read,
    Scanner,
    Show,
    Sort,
    Source,
    Text,
    WriteJson,
    assemble,
    blocks_used,
    formula_type,
    formulas,
    schemas,
)
from ..model import TypeMismatch

FILE_NAME = "Main.java"
SUPPORTED = None  # the blocks this target can build; None means every block

# Options for a quick start of the JVM: the shared class archive, and the first compiler tier only.
JAVA_OPTIONS = ("-Xshare:auto", "-XX:TieredStopAtLevel=1", "-XX:+UseSerialGC")
CACHE = Path(os.environ.get("CDIPL_JAVA_CACHE") or Path(tempfile.gettempdir()) / "cdipl-java")


def _environment():
    """The environment for javac and java, without JAVA_TOOL_OPTIONS, which makes the JVM write to standard error."""
    return {name: value for name, value in os.environ.items() if name not in ("JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS")}


# A small program that keeps one JVM running and compiles each program sent to it with the compiler in
# the JDK. Starting javac afresh for every program takes about half a second; this takes a tenth of that.
COMPILE_SERVER = """\
import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import javax.tools.JavaCompiler;
import javax.tools.ToolProvider;

public final class CompileServer {
    public static void main(String[] args) throws IOException {
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        BufferedReader input = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        String line;
        while ((line = input.readLine()) != null) {
            String[] parts = line.split("\\t", 2);
            ByteArrayOutputStream messages = new ByteArrayOutputStream();
            int status = compiler.run(null, messages, messages, "-encoding", "UTF-8", "-d", parts[1], parts[0]);
            System.out.println(status);
            System.out.flush();
        }
    }
}
"""
_server = None


def _javac(source, classes):
    """Compile with a fresh javac. Returns the completed process."""
    return subprocess.run(["javac", "-J-Xshare:auto", "-J-XX:TieredStopAtLevel=1", "-encoding", "UTF-8",
                           "-d", str(classes), str(source)], capture_output=True, text=True, check=False,
                          env=_environment())


def _start_server():
    global _server
    folder = CACHE / ("server-" + hashlib.sha256(COMPILE_SERVER.encode()).hexdigest()[:16])
    if not (folder / "CompileServer.class").exists():
        with tempfile.TemporaryDirectory(dir=CACHE) as work:
            (Path(work) / "CompileServer.java").write_text(COMPILE_SERVER, encoding="utf-8")
            if _javac(Path(work) / "CompileServer.java", Path(work) / "classes").returncode != 0:
                return None
            try:
                os.rename(Path(work) / "classes", folder)
            except OSError:
                pass
    _server = subprocess.Popen(["java", "-Xshare:auto", "-cp", str(folder), "CompileServer"], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=_environment())
    atexit.register(_stop_server)
    return _server


def _stop_server():
    global _server
    if _server is not None:
        try:
            _server.stdin.close()
            _server.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            _server.kill()
        _server = None


def _compile(source, classes):
    """Compile through the running compile server, starting it if needed. Returns whether it succeeded."""
    global _server
    try:
        server = _server if _server is not None and _server.poll() is None else _start_server()
        if server is None:
            return False
        server.stdin.write(f"{source}\t{classes}\n")
        server.stdin.flush()
        return server.stdout.readline().strip() == "0"
    except OSError:
        _server = None
        return False


def compile_program(program_path):
    """Compile a generated program once, into a cache folder named after its content. Returns the folder."""
    data = Path(program_path).read_bytes()
    folder = CACHE / hashlib.sha256(data).hexdigest()[:32]
    if (folder / "Main.class").exists():
        return folder
    CACHE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=CACHE) as work:
        source = Path(work) / FILE_NAME
        source.write_bytes(data)
        classes = Path(work) / "classes"
        if not _compile(source, classes):
            done = _javac(source, classes)  # again on its own, for the messages or if the server is not available
            if done.returncode != 0:
                raise RuntimeError(f"javac could not compile {program_path}:\n{done.stdout}{done.stderr}")
        try:
            os.rename(classes, folder)
        except OSError:
            if not (folder / "Main.class").exists():
                raise
    return folder


def run_command(program_path):
    """The command that runs a generated program. Compiles it first, unless it is already compiled."""
    folder = compile_program(program_path)
    return ["env", "-u", "JAVA_TOOL_OPTIONS", "-u", "JDK_JAVA_OPTIONS", "-u", "_JAVA_OPTIONS",
            "java", *JAVA_OPTIONS, "-cp", str(folder), "Main"]


# Import lines, each with the flag that says when it is needed.
IMPORTS = [
    ("always", "import java.io.IOException;"),
    ("always", "import java.nio.ByteBuffer;"),
    ("always", "import java.nio.charset.CharacterCodingException;"),
    ("always", "import java.nio.charset.CodingErrorAction;"),
    ("always", "import java.nio.charset.StandardCharsets;"),
    ("always", "import java.nio.file.Files;"),
    ("always", "import java.nio.file.InvalidPathException;"),
    ("always", "import java.nio.file.Path;"),
    ("always", "import java.util.ArrayDeque;"),
    ("always", "import java.util.ArrayList;"),
    ("compare", "import java.util.Arrays;"),
    ("always", "import java.util.Deque;"),
    ("always", "import java.util.HexFormat;"),
    ("always", "import java.util.LinkedHashMap;"),
    ("always", "import java.util.List;"),
    ("always", "import java.util.Map;"),
]

# Fixed support code. Each piece belongs to one block and is included only when its flag is needed.
SUPPORT = [
    ("exit-on-error", "always", r'''
    private static final class Failure extends RuntimeException {
        private static final long serialVersionUID = 1L;
        private final int status;
        private final String category;

        Failure(int status, String category, String detail) {
            super(detail);
            this.status = status;
            this.category = category;
        }
    }
'''),
    ("cli-options", "argument", r'''
    private static String readArgument(String[] args, int position) {
        if (args.length < position) {
            throw new Failure(2, "usage", "argument " + position + " is required");
        }
        return args[position - 1];
    }
'''),
    ("read-text-file", "always", r'''
    private static String readTextFile(String path) {
        byte[] data;
        try {
            data = Files.readAllBytes(Path.of(path));
        } catch (IOException | InvalidPathException error) {
            throw new Failure(3, "cannot-read", path + ": " + error.getClass().getSimpleName());
        }
        try {
            return StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(data))
                    .toString();
        } catch (CharacterCodingException error) {
            throw new Failure(4, "bad-json", "the input is not valid UTF-8");
        }
    }
'''),
    ("parse-json", "always", r'''
    private static final class JsonReader {
        private final String text;
        private int position;

        JsonReader(String text) {
            this.text = text;
        }

        private static final class Container {
            private final List<Object> array;
            private final Map<String, Object> object;
            private String key;

            Container(List<Object> array, Map<String, Object> object) {
                this.array = array;
                this.object = object;
            }

            void add(Object value) {
                if (array != null) {
                    array.add(value);
                } else {
                    object.put(key, value);
                }
            }

            Object value() {
                return array != null ? array : object;
            }
        }

        Object read() {
            Deque<Container> open = new ArrayDeque<>();
            while (true) {
                Object value;
                skipSpace();
                if (take('[')) {
                    skipSpace();
                    if (!take(']')) {
                        open.push(new Container(new ArrayList<>(), null));
                        continue;
                    }
                    value = new ArrayList<>();
                } else if (take('{')) {
                    skipSpace();
                    if (!take('}')) {
                        Container object = new Container(null, new LinkedHashMap<>());
                        object.key = readKey();
                        open.push(object);
                        continue;
                    }
                    value = new LinkedHashMap<>();
                } else {
                    value = readScalar();
                }
                while (true) {
                    Container parent = open.peek();
                    if (parent == null) {
                        skipSpace();
                        if (position < text.length()) {
                            throw invalid();
                        }
                        return value;
                    }
                    parent.add(value);
                    skipSpace();
                    if (take(',')) {
                        if (parent.object != null) {
                            parent.key = readKey();
                        }
                        break;
                    }
                    if (!take(parent.array != null ? ']' : '}')) {
                        throw invalid();
                    }
                    value = open.pop().value();
                }
            }
        }

        private static Failure invalid() {
            return new Failure(4, "bad-json", "the input is not valid JSON");
        }

        private void skipSpace() {
            while (position < text.length() && " \t\n\r".indexOf(text.charAt(position)) >= 0) {
                position++;
            }
        }

        private boolean take(char expected) {
            if (position < text.length() && text.charAt(position) == expected) {
                position++;
                return true;
            }
            return false;
        }

        private char next() {
            if (position >= text.length()) {
                throw invalid();
            }
            return text.charAt(position++);
        }

        private String readKey() {
            skipSpace();
            if (position >= text.length() || text.charAt(position) != '"') {
                throw invalid();
            }
            String key = readString();
            skipSpace();
            if (!take(':')) {
                throw invalid();
            }
            return key;
        }

        private Object readScalar() {
            if (position >= text.length()) {
                throw invalid();
            }
            return switch (text.charAt(position)) {
                case '"' -> readString();
                case 't' -> readWord("true", Boolean.TRUE);
                case 'f' -> readWord("false", Boolean.FALSE);
                case 'n' -> readWord("null", null);
                default -> readNumber();
            };
        }

        private Object readWord(String word, Object value) {
            if (!text.startsWith(word, position)) {
                throw invalid();
            }
            position += word.length();
            return value;
        }

        private String readString() {
            position++;
            StringBuilder value = new StringBuilder();
            while (true) {
                char ch = next();
                if (ch == '"') {
                    return value.toString();
                }
                if (ch < ' ') {
                    throw invalid();
                }
                if (ch != '\\') {
                    value.append(ch);
                    continue;
                }
                char escape = next();
                switch (escape) {
                    case '"', '\\', '/' -> value.append(escape);
                    case 'b' -> value.append('\b');
                    case 'f' -> value.append('\f');
                    case 'n' -> value.append('\n');
                    case 'r' -> value.append('\r');
                    case 't' -> value.append('\t');
                    case 'u' -> value.append(readUnit());
                    default -> throw invalid();
                }
            }
        }

        private char readUnit() {
            if (position + 4 > text.length()) {
                throw invalid();
            }
            for (int index = position; index < position + 4; index++) {
                if (!HexFormat.isHexDigit(text.charAt(index))) {
                    throw invalid();
                }
            }
            position += 4;
            return (char) HexFormat.fromHexDigits(text, position - 4, position);
        }

        private Double readNumber() {
            int start = position;
            take('-');
            if (!take('0') && !readDigits()) {
                throw invalid();
            }
            if (take('.') && !readDigits()) {
                throw invalid();
            }
            if (take('e') || take('E')) {
                if (!take('+')) {
                    take('-');
                }
                if (!readDigits()) {
                    throw invalid();
                }
            }
            return Double.parseDouble(text.substring(start, position));
        }

        private boolean readDigits() {
            int start = position;
            while (position < text.length() && text.charAt(position) >= '0' && text.charAt(position) <= '9') {
                position++;
            }
            return position > start;
        }
    }
'''),
    ("parse-json", "always", r'''
    private static Object parseJson(String json) {
        return new JsonReader(json).read();
    }
'''),
    ("check-list-of-records", "always", r'''
    private static List<?> checkList(Object data) {
        if (data instanceof List<?> list) {
            return list;
        }
        throw new Failure(5, "not-a-list", "the input must be a list of records");
    }
'''),
    ("check-required-types", "always", r'''
    private static boolean isWellFormed(String text) {
        for (int index = 0; index < text.length(); index++) {
            char ch = text.charAt(index);
            if (Character.isHighSurrogate(ch) && index + 1 < text.length() && Character.isLowSurrogate(text.charAt(index + 1))) {
                index++;
            } else if (Character.isSurrogate(ch)) {
                return false;
            }
        }
        return true;
    }
'''),
    ("check-required-types", "always", r'''
    private static Object toValue(Object value, String kind) {
        if (kind.equals("text")) {
            return value instanceof String text && isWellFormed(text) ? text : null;
        }
        if (value instanceof Double number && Math.rint(number) == number && Math.abs(number) <= MAX_INTEGER) {
            return number.longValue();
        }
        return null;
    }
'''),
    ("check-required-types", "always", r'''
    private static Map<String, Object> toRow(Object record) {
        if (!(record instanceof Map<?, ?> object)) {
            return null;
        }
        Map<String, Object> row = new LinkedHashMap<>();
        for (String[] field : FIELDS) {
            Object value = toValue(object.get(field[0]), field[1]);
            if (value == null) {
                return null;
            }
            row.put(field[0], value);
        }
        return row;
    }
'''),
    ("check-required-types", "strict", r'''
    private static List<Map<String, Object>> requireValid(List<?> records) {
        List<Map<String, Object>> rows = new ArrayList<>();
        for (int index = 0; index < records.size(); index++) {
            Map<String, Object> row = toRow(records.get(index));
            if (row == null) {
                throw new Failure(6, "invalid-record", "record " + (index + 1) + " does not match the declared fields");
            }
            rows.add(row);
        }
        return rows;
    }
'''),
    ("drop-invalid-rows", "skip", r'''
    private static List<Map<String, Object>> keepValid(List<?> records) {
        List<Map<String, Object>> rows = new ArrayList<>();
        for (Object record : records) {
            Map<String, Object> row = toRow(record);
            if (row != null) {
                rows.add(row);
            }
        }
        return rows;
    }
'''),
    ("check-required-types", "text-field", r'''
    private static String text(Map<String, Object> row, String name) {
        return (String) row.get(name);
    }
'''),
    ("check-required-types", "number-field", r'''
    private static long number(Map<String, Object> row, String name) {
        return (Long) row.get(name);
    }
'''),
    ("calculate", "whole", r'''
    private static long whole(long value) {
        if (Math.abs(value) > MAX_INTEGER) {
            throw new Failure(7, "out-of-range", "a calculation gave a number outside the supported range");
        }
        return value;
    }
'''),
    ("calculate", "plus", r'''
    private static long plus(long left, long right) {
        return whole(left + right);
    }
'''),
    ("calculate", "minus", r'''
    private static long minus(long left, long right) {
        return whole(left - right);
    }
'''),
    ("calculate", "times", r'''
    private static long times(long left, long right) {
        try {
            return whole(Math.multiplyExact(left, right));
        } catch (ArithmeticException error) {
            throw new Failure(7, "out-of-range", "a calculation gave a number outside the supported range");
        }
    }
'''),
    ("calculate", "add", r'''
    private static Map<String, Object> with(Map<String, Object> row, String name, Object value) {
        Map<String, Object> copy = new LinkedHashMap<>(row);
        copy.put(name, value);
        return copy;
    }
'''),
    ("sort-rows", "compare", r'''
    private static int compareText(String left, String right) {
        return Arrays.compare(left.codePoints().toArray(), right.codePoints().toArray());
    }
'''),
    ("sort-rows", "fold", r'''
    private static String foldCase(String text) {
        StringBuilder folded = new StringBuilder(text.length());
        for (int index = 0; index < text.length(); index++) {
            char ch = text.charAt(index);
            folded.append(ch >= 'A' && ch <= 'Z' ? (char) (ch + 32) : ch);
        }
        return folded.toString();
    }
'''),
    ("group-by-key", "group", r'''
    private static Map<Object, List<Map<String, Object>>> groupRows(List<Map<String, Object>> rows, String name) {
        Map<Object, List<Map<String, Object>>> groups = new LinkedHashMap<>();
        for (Map<String, Object> row : rows) {
            groups.computeIfAbsent(row.get(name), key -> new ArrayList<>()).add(row);
        }
        return groups;
    }
'''),
    ("count-values", "count", r'''
    private static List<Map<String, Object>> countGroups(Map<Object, List<Map<String, Object>>> groups, String name) {
        List<Map<String, Object>> rows = new ArrayList<>();
        for (Map.Entry<Object, List<Map<String, Object>>> group : groups.entrySet()) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put(name, group.getKey());
            row.put("count", (long) group.getValue().size());
            rows.add(row);
        }
        return rows;
    }
'''),
    ("print-message", "always", r'''
    private static void emit(String text) {
        OUTPUT.append(text);
    }
'''),
    ("print-table", "show", r'''
    private static void showTable(List<Map<String, Object>> rows, String... names) {
        int[] widths = new int[names.length];
        for (Map<String, Object> row : rows) {
            for (int column = 0; column < names.length; column++) {
                String cell = String.valueOf(row.get(names[column]));
                widths[column] = Math.max(widths[column], cell.codePointCount(0, cell.length()));
            }
        }
        for (Map<String, Object> row : rows) {
            StringBuilder line = new StringBuilder();
            for (int column = 0; column < names.length; column++) {
                String cell = String.valueOf(row.get(names[column]));
                line.append(cell);
                if (column < names.length - 1) {
                    line.append(" ".repeat(widths[column] - cell.codePointCount(0, cell.length()) + 2));
                }
            }
            emit(line.append('\n').toString());
        }
    }
'''),
    ("format-json", "json", r'''
    private static void writeJson(List<Map<String, Object>> rows) {
        StringBuilder json = new StringBuilder("[");
        for (Map<String, Object> row : rows) {
            if (json.length() > 1) {
                json.append(',');
            }
            json.append('{');
            for (Map.Entry<String, Object> entry : row.entrySet()) {
                if (json.charAt(json.length() - 1) != '{') {
                    json.append(',');
                }
                appendJsonText(json, entry.getKey());
                json.append(':');
                if (entry.getValue() instanceof String text) {
                    appendJsonText(json, text);
                } else {
                    json.append(entry.getValue());
                }
            }
            json.append('}');
        }
        emit(json.append("]\n").toString());
    }
'''),
    ("format-json", "json", r'''
    private static void appendJsonText(StringBuilder json, String text) {
        json.append('"');
        for (int index = 0; index < text.length(); index++) {
            char ch = text.charAt(index);
            switch (ch) {
                case '"' -> json.append("\\\"");
                case '\\' -> json.append("\\\\");
                case '\b' -> json.append("\\b");
                case '\f' -> json.append("\\f");
                case '\n' -> json.append("\\n");
                case '\r' -> json.append("\\r");
                case '\t' -> json.append("\\t");
                default -> {
                    if (ch < ' ' || ch > '~') {
                        json.append("\\u").append(HexFormat.of().toHexDigits(ch));
                    } else {
                        json.append(ch);
                    }
                }
            }
        }
        json.append('"');
    }
'''),
]

TAIL = r'''
    public static void main(String[] args) {
        try {
            run(args);
        } catch (Failure failure) {
            System.err.print("error: " + failure.category + ": " + SOURCE + ": " + failure.getMessage() + "\n");
            System.err.flush();
            System.exit(failure.status);
        }
        byte[] bytes = OUTPUT.toString().getBytes(StandardCharsets.UTF_8);
        System.out.write(bytes, 0, bytes.length);
        System.out.flush();
    }
}
'''

ORDER = ("<", "<=", ">", ">=")
NUMBER_OPERATORS = {"=": "==", "!=": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
FROM_NUMBER = {code: op for op, code in NUMBER_OPERATORS.items()}
ARITHMETIC = {"+": "plus", "-": "minus", "*": "times"}
FROM_ARITHMETIC = {name: op for op, name in ARITHMETIC.items()}
INT_LIMIT = 2147483647
ROWS = "List<Map<String, Object>>"
GROUPS = "Map<Object, List<Map<String, Object>>>"

# The shape of the line each block adds to run(). Part of the block's version.
FORMS = {
    "read-text-file": "String json = readTextFile(PATH);",
    "cli-options": "readArgument(args, N)",
    "parse-json": "List<?> records = checkList(parseJson(json));",
    "check-required-types": f"{ROWS} rows = requireValid(records); text(row, FIELD); number(row, FIELD)",
    "drop-invalid-rows": f"{ROWS} rows = keepValid(records);",
    "filter-rows": "rows = rows.stream().filter(row -> CONDITIONS).toList(); A == B; A.equals(B); !A.equals(B)",
    "calculate": "rows = rows.stream().map(row -> with(row, NAME, FORMULA)).toList(); plus(A, B); minus(A, B); times(A, B); A + B",
    "sort-rows": "rows = rows.stream().sorted((a, b) -> COMPARE).toList(); compareText(A, B) < 0",
    "take-first": "rows = rows.stream().limit(N).toList();",
    "group-by-key": f"{GROUPS} groups = groupRows(rows, FIELD);",
    "count-values": "rows = countGroups(groups, FIELD);",
    "print-message": "if (rows.isEmpty()) { emit(TEXT); return; }",
    "print-table": "showTable(rows, FIELDS);",
    "format-json": "writeJson(rows);",
}


def quote(text):
    """Write text as a Java string literal, in plain ASCII.

    Java turns \\u escapes into characters before it reads the program, so line breaks, quotes and
    backslashes are never written as \\u escapes.
    """
    out = []
    for ch in text:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif 32 <= ord(ch) < 127:
            out.append(ch)
        else:
            units = ch.encode("utf-16-be")
            out += [f"\\u{int.from_bytes(units[i:i + 2], 'big'):04x}" for i in range(0, len(units), 2)]
    return '"' + "".join(out) + '"'


STRING = r'"(?:[^"\\]|\\.)*"'


def unquote(literal):
    inner = literal[1:-1]
    if re.fullmatch(r'(?:[ !#-\[\]-~]|\\[\\"nr]|\\u[0-9a-f]{4})*', inner) is None:
        raise NotGenerated("a text value is not written the way the compiler writes it")
    units = bytearray()
    for match in re.finditer(r'\\([\\"nr]|u[0-9a-f]{4})|.', inner):
        body = match.group(1)
        if body is None:
            code = ord(match.group(0))
        elif body in ("n", "r"):
            code = 10 if body == "n" else 13
        elif body in ("\\", '"'):
            code = ord(body)
        else:
            code = int(body[1:], 16)
        units += code.to_bytes(2, "big")
    try:
        return units.decode("utf-16-be")
    except UnicodeDecodeError:
        raise NotGenerated("a text value cannot be read") from None


def number_literal(value):
    return f"{value}L" if abs(value) > INT_LIMIT else str(value)


def _fields_read(value, schema, found):
    if isinstance(value, Field):
        found.add("text-field" if schema.get(value.name) == "text" else "number-field")
    elif isinstance(value, Arith):
        found.add("whole")
        found.add(ARITHMETIC[value.op])
        _fields_read(value.left, schema, found)
        _fields_read(value.right, schema, found)
    elif isinstance(value, Concat):
        for part in value.parts:
            _fields_read(part, schema, found)


def _is_text(schema, value):
    try:
        return formula_type(schema, value) == "text"
    except TypeMismatch:  # an unfinished program in the live view may not fit together yet
        return isinstance(value, Text)


def needs(program):
    flags = {"always"}
    for step, schema in zip(program.steps, schemas(program)):
        if isinstance(step, Read):
            flags.add("skip" if step.skip_invalid else "strict")
            if program.source.argument is not None:
                flags.add("argument")
        elif isinstance(step, Filter):
            if any(cond.op in ORDER and _is_text(schema, cond.left) for cond in step.conditions):
                flags.add("compare")
        elif isinstance(step, Add):
            flags.add("add")
        elif isinstance(step, Sort):
            if schema.get(step.field) == "text":
                flags.update(("compare", "text-field"))
            else:
                flags.add("number-field")
            if step.ignore_case:
                flags.add("fold")
        elif isinstance(step, Group):
            flags.add("group")
        elif isinstance(step, Count):
            flags.add("count")
        elif isinstance(step, Show):
            flags.add("show")
        elif isinstance(step, WriteJson):
            flags.add("json")
        for value in formulas(step):
            _fields_read(value, schema, flags)
    return flags


def formula(value, schema):
    """Write a formula as Java."""
    if isinstance(value, Field):
        accessor = "text" if schema.get(value.name) == "text" else "number"
        return f"{accessor}(row, {quote(value.name)})"
    if isinstance(value, Number):
        return number_literal(value.value)
    if isinstance(value, Text):
        return quote(value.value)
    if isinstance(value, Arith):
        return f"{ARITHMETIC[value.op]}({formula(value.left, schema)}, {formula(value.right, schema)})"
    return " + ".join(formula(part, schema) for part in value.parts)


def condition(cond, schema):
    left, right = formula(cond.left, schema), formula(cond.right, schema)
    if not _is_text(schema, cond.left):
        return f"{left} {NUMBER_OPERATORS[cond.op]} {right}"
    if cond.op in ORDER:
        return f"compareText({left}, {right}) {cond.op} 0"
    if isinstance(cond.left, Concat):
        left = f"({left})"
    negation = "!" if cond.op == "!=" else ""
    return f"{negation}{left}.equals({right})"


def comparison(step, schema):
    first, second = ("b", "a") if step.descending else ("a", "b")
    name = quote(step.field)
    if schema.get(step.field) != "text":
        return f"Long.compare(number({first}, {name}), number({second}, {name}))"
    if step.ignore_case:
        return f"compareText(foldCase(text({first}, {name})), foldCase(text({second}, {name})))"
    return f"compareText(text({first}, {name}), text({second}, {name}))"


def main_lines(program):
    """The body of run(), as (text, intent line) pairs."""
    source = program.source
    out = []
    grouped = False
    for step, schema in zip(program.steps, schemas(program)):
        if isinstance(step, Read):
            origin = quote(source.path) if source.path is not None else f"readArgument(args, {source.argument})"
            out.append((f"        String json = readTextFile({origin});", step.line))
            out.append(("        List<?> records = checkList(parseJson(json));", step.line))
            if step.skip_invalid:
                out.append((f"        {ROWS} rows = keepValid(records);", step.skip_line))
            else:
                out.append((f"        {ROWS} rows = requireValid(records);", step.line))
        elif isinstance(step, Filter):
            joined = " && ".join(condition(cond, schema) for cond in step.conditions)
            out.append((f"        rows = rows.stream().filter(row -> {joined}).toList();", step.line))
        elif isinstance(step, Add):
            value = formula(step.formula, schema)
            out.append((f"        rows = rows.stream().map(row -> with(row, {quote(step.name)}, {value})).toList();", step.line))
        elif isinstance(step, Sort):
            out.append((f"        rows = rows.stream().sorted((a, b) -> {comparison(step, schema)}).toList();", step.line))
        elif isinstance(step, Limit):
            out.append((f"        rows = rows.stream().limit({number_literal(step.count)}).toList();", step.line))
        elif isinstance(step, Group):
            declaration = "" if grouped else f"{GROUPS} "
            grouped = True
            out.append((f"        {declaration}groups = groupRows(rows, {quote(step.field)});", step.line))
        elif isinstance(step, Count):
            out.append((f"        rows = countGroups(groups, {quote(step.field)});", step.line))
        elif isinstance(step, IfNone):
            out.append(("        if (rows.isEmpty()) {", step.line))
            out.append((f"            emit({quote(step.text + chr(10))});", step.line))
            out.append(("            return;", step.line))
            out.append(("        }", step.line))
        elif isinstance(step, Show):
            names = ", ".join(quote(name) for name in step.fields)
            out.append((f"        showTable(rows, {names});", step.line))
        elif isinstance(step, WriteJson):
            out.append(("        writeJson(rows);", step.line))
    return out


def generate(program):
    """Return the program text as a list of (line, origin) pairs.

    origin is an intent line number, or the name of the block a support line belongs to.
    """
    flags = needs(program)
    lines = [(line, "support") for flag, line in IMPORTS if flag in flags]
    fields = ", ".join(f"{{{quote(name)}, {quote(kind)}}}" for name, kind in program.source.fields)
    lines += [("", "support"), ("public final class Main {", "support"),
              (f"    private static final String SOURCE = {quote(program.source.name)};", "support"),
              (f"    private static final String[][] FIELDS = {{{fields}}};", "support"),
              ("    private static final long MAX_INTEGER = 9007199254740991L;", "support"),
              ("    private static final StringBuilder OUTPUT = new StringBuilder();", "support")]
    for block, flag, text in SUPPORT:
        if flag in flags:
            lines += [(line, block) for line in text.rstrip("\n").split("\n")]
    lines += [("", "support"), ("    private static void run(String[] args) {", "support")]
    lines += main_lines(program)
    lines.append(("    }", "support"))
    lines += [(line, "exit-on-error") for line in TAIL.rstrip("\n").split("\n")]
    return lines


NAME = r"([A-Za-z_][A-Za-z0-9_]*)"
FIELD_NAME = rf'"{NAME}"'
FIELD_VALUE = re.compile(rf"(?:text|number)\(row, {FIELD_NAME}\)")
STRING_VALUE = re.compile(STRING)
NUMBER_VALUE = re.compile(r"(-?\d+)L?")
CALCULATION = re.compile(r"(plus|minus|times)\(")
COMPARISON = re.compile(r" (==|!=|<=|>=|<|>) ")
ORDER_TEST = re.compile(r" (<=|>=|<|>) 0")


def lift(text):
    """Recover the Program from generated text. Raises NotGenerated."""
    lines = text.split("\n")
    name = _only(re.fullmatch(rf"    private static final String SOURCE = {FIELD_NAME};", line) for line in lines)
    fields_line = _only(re.fullmatch(r"    private static final String\[\]\[\] FIELDS = \{(.*)\};", line) for line in lines)
    pairs = re.findall(rf'\{{{FIELD_NAME}, "(text|integer)"\}}', fields_line.group(1))
    if not pairs or len({field for field, _ in pairs}) != len(pairs):
        raise NotGenerated("the declared fields cannot be read")
    try:
        start = lines.index("    private static void run(String[] args) {") + 1
        end = lines.index("    }", start)
    except ValueError:
        raise NotGenerated("there is no run method") from None
    body = lines[start:end]
    steps, path, argument = [], None, None
    index = 0
    while index < len(body):
        line = body[index]
        index += 1
        if match := re.fullmatch(rf"        String json = readTextFile\((?:({STRING})|readArgument\(args, (\d+)\))\);", line):
            path = unquote(match[1]) if match[1] else None
            argument = int(match[2]) if match[2] else None
            if body[index:index + 1] != ["        List<?> records = checkList(parseJson(json));"]:
                raise NotGenerated("the lines that read the source are not as generated")
            mode = body[index + 1] if index + 1 < len(body) else ""
            if mode not in (f"        {ROWS} rows = requireValid(records);", f"        {ROWS} rows = keepValid(records);"):
                raise NotGenerated("the lines that read the source are not as generated")
            steps.append(Read(skip_invalid="keepValid" in mode))
            index += 2
        elif match := re.fullmatch(r"        rows = rows\.stream\(\)\.filter\(row -> (.*)\)\.toList\(\);", line):
            steps.append(Filter(conditions=_conditions(match[1])))
        elif match := re.fullmatch(rf"        rows = rows\.stream\(\)\.map\(row -> with\(row, {FIELD_NAME}, (.*)\)\)\.toList\(\);", line):
            scanner = Scanner(match[2])
            value = _formula(scanner)
            if not scanner.done():
                raise NotGenerated("a formula cannot be read")
            steps.append(Add(name=match[1], formula=value))
        elif match := re.fullmatch(r"        rows = rows\.stream\(\)\.sorted\(\(a, b\) -> (.*)\)\.toList\(\);", line):
            steps.append(_sort(match[1]))
        elif match := re.fullmatch(r"        rows = rows\.stream\(\)\.limit\((\d+)L?\)\.toList\(\);", line):
            steps.append(Limit(count=int(match[1])))
        elif match := re.fullmatch(rf"        (?:{re.escape(GROUPS)} )?groups = groupRows\(rows, {FIELD_NAME}\);", line):
            steps.append(Group(field=match[1]))
        elif match := re.fullmatch(rf"        rows = countGroups\(groups, {FIELD_NAME}\);", line):
            steps.append(Count(field=match[1]))
        elif line == "        if (rows.isEmpty()) {":
            match = re.fullmatch(rf"            emit\(({STRING})\);", body[index] if index < len(body) else "")
            if match is None or body[index + 1:index + 3] != ["            return;", "        }"]:
                raise NotGenerated("the lines that print a message are not as generated")
            message = unquote(match[1])
            if not message.endswith("\n"):
                raise NotGenerated("the message does not end with a line break")
            steps.append(IfNone(text=message[:-1]))
            index += 3
        elif match := re.fullmatch(r"        showTable\(rows, (.*)\);", line):
            names = re.findall(FIELD_NAME, match[1])
            if ", ".join(f'"{n}"' for n in names) != match[1] or not names:
                raise NotGenerated("the list of fields to show cannot be read")
            steps.append(Show(fields=tuple(names)))
        elif line == "        writeJson(rows);":
            steps.append(WriteJson())
        else:
            raise NotGenerated(f"this line is not one the compiler generates: {line.strip()}")
    source = Source(name=name.group(1), path=path, argument=argument, fields=tuple(pairs))
    return assemble(source, steps)


def _only(matches):
    found = [match for match in matches if match]
    if len(found) != 1:
        raise NotGenerated("the header of the program is not as generated")
    return found[0]


def _sort(text):
    for descending, first, second in ((False, "a", "b"), (True, "b", "a")):
        patterns = ((rf"Long\.compare\(number\({first}, {FIELD_NAME}\), number\({second}, {FIELD_NAME}\)\)", False),
                    (rf"compareText\(text\({first}, {FIELD_NAME}\), text\({second}, {FIELD_NAME}\)\)", False),
                    (rf"compareText\(foldCase\(text\({first}, {FIELD_NAME}\)\), foldCase\(text\({second}, {FIELD_NAME}\)\)\)", True))
        for pattern, ignore_case in patterns:
            if (match := re.fullmatch(pattern, text)) and match[1] == match[2]:
                return Sort(field=match[1], descending=descending, ignore_case=ignore_case)
    raise NotGenerated("a sort cannot be read")


def _atom(scanner):
    if match := scanner.match(FIELD_VALUE):
        return Field(match[1])
    if match := scanner.match(STRING_VALUE):
        return Text(unquote(match[0]))
    if match := scanner.match(NUMBER_VALUE):
        return Number(int(match[1]))
    if match := scanner.match(CALCULATION):
        left = _atom(scanner)
        scanner.expect(", ")
        right = _atom(scanner)
        scanner.expect(")")
        return Arith(FROM_ARITHMETIC[match[1]], left, right)
    raise NotGenerated("a formula cannot be read")


def _formula(scanner):
    parts = [_atom(scanner)]
    while scanner.take(" + "):
        parts.append(_atom(scanner))
    return parts[0] if len(parts) == 1 else Concat(tuple(parts))


def _conditions(text):
    scanner, conditions = Scanner(text), []
    while True:
        if scanner.take("compareText("):
            left = _formula(scanner)
            scanner.expect(", ")
            right = _formula(scanner)
            scanner.expect(")")
            test = scanner.match(ORDER_TEST)
            if test is None:
                raise NotGenerated("a comparison of text cannot be read")
            conditions.append(Condition(left, test[1], right))
        else:
            negated = scanner.take("!")
            if scanner.take("("):
                left = _formula(scanner)
                scanner.expect(")")
            else:
                left = _atom(scanner)
            if scanner.take(".equals("):
                right = _formula(scanner)
                scanner.expect(")")
                conditions.append(Condition(left, "!=" if negated else "=", right))
            else:
                op = scanner.match(COMPARISON)
                if negated or op is None:
                    raise NotGenerated("a condition cannot be read")
                conditions.append(Condition(left, FROM_NUMBER[op[1]], _formula(scanner)))
        if scanner.done():
            return tuple(conditions)
        scanner.expect(" && ")


__all__ = ["FILE_NAME", "SUPPORT", "blocks_used", "compile_program", "generate", "lift", "run_command", "schemas"]
