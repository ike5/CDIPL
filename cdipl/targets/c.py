"""Generate C programs, and recognise programs this generator wrote.

The generated program is one C11 file that uses only the C standard library. See docs/target-c.md.
"""
import hashlib
import os
import re
import shutil
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

FILE_NAME = "main.c"
SUPPORTED = None  # the blocks this target can build; None means every block

# How a generated program is compiled before it is run. -O0 keeps the tests fast; the output does not depend on it.
COMPILE_FLAGS = ("-std=c11", "-O0")
CACHE = Path(tempfile.gettempdir()) / "cdipl-c-binaries"


def compiler():
    return os.environ.get("CC") or shutil.which("gcc") or shutil.which("cc") or "gcc"


def run_command(program_path):
    """The command that runs a generated program, compiling it first unless a binary of the same text exists.

    Binaries are kept in a folder in the system's temporary directory, named by a hash of the source and
    the compile command, so that running the same program again does not compile it again.
    """
    cc = compiler()
    source = Path(program_path).read_bytes()
    digest = hashlib.sha256("\0".join([cc, *COMPILE_FLAGS]).encode() + b"\0" + source).hexdigest()[:24]
    binary = CACHE / digest
    if not binary.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        partial = CACHE / f"{digest}.{os.getpid()}.part"
        done = subprocess.run([cc, *COMPILE_FLAGS, "-o", str(partial), str(program_path)], capture_output=True, text=True, check=False)
        if done.returncode != 0:
            raise RuntimeError(f"{cc} could not compile {program_path}:\n{done.stderr}")
        os.replace(partial, binary)
    return [str(binary)]


# The includes are written with the digraph %: (ISO C 6.4.6), which is the same as #, because the shared
# tests take any line that starts with # as a comment. See docs/target-c.md.
PRELUDE = '''\
%:include <errno.h>
%:include <stdarg.h>
%:include <stdbool.h>
%:include <stddef.h>
%:include <stdio.h>
%:include <stdlib.h>
%:include <string.h>

typedef struct {
  const char *text;
  size_t length;
  long long number;
} Value;

typedef struct {
  Value **items;
  size_t count;
} Rows;

typedef enum { IS_TEXT, IS_INTEGER } Kind;

static const long long MAX_INTEGER = 9007199254740991;
'''

# Fixed support code. Each piece belongs to one block and is included only when its flag is needed.
SUPPORT = [
    ("print-message", "always", '''\
static Value literal(const char *text) {
  return (Value){text, strlen(text), 0};
}
'''),
    ("exit-on-error", "always", '''\
static _Noreturn void fail(int status, const char *category, const char *format, ...) {
  va_list details;
  va_start(details, format);
  fprintf(stderr, "error: %s: %s: ", category, SOURCE);
  vfprintf(stderr, format, details);
  va_end(details);
  fputc('\\n', stderr);
  exit(status);
}
'''),
    ("exit-on-error", "always", '''\
static void *allocate(size_t count, size_t size) {
  void *memory = calloc(count == 0 ? 1 : count, size);
  if (memory == NULL) {
    fail(8, "out-of-memory", "there is not enough memory");
  }
  return memory;
}
'''),
    ("exit-on-error", "always", '''\
static size_t larger(size_t capacity, size_t size) {
  if (capacity > (size_t)-1 / 2 / size) {
    fail(8, "out-of-memory", "there is not enough memory");
  }
  return capacity == 0 ? 16 : capacity * 2;
}
'''),
    ("exit-on-error", "always", '''\
static void *resize(void *memory, size_t capacity, size_t size) {
  memory = realloc(memory, capacity * size);
  if (memory == NULL) {
    fail(8, "out-of-memory", "there is not enough memory");
  }
  return memory;
}
'''),
    ("cli-options", "argument", '''\
static const char *read_argument(int argc, char **argv, int position) {
  if (argc <= position) {
    fail(2, "usage", "argument %d is required", position);
  }
  return argv[position];
}
'''),
    ("read-text-file", "always", '''\
typedef struct {
  char *data;
  size_t length;
} Bytes;
'''),
    ("read-text-file", "always", '''\
static bool valid_utf8(const unsigned char *at, const unsigned char *end) {
  while (at < end) {
    unsigned long code = *at;
    size_t size = 1;
    if (code >= 0xC2 && code <= 0xDF) {
      size = 2;
      code &= 0x1F;
    } else if (code >= 0xE0 && code <= 0xEF) {
      size = 3;
      code &= 0x0F;
    } else if (code >= 0xF0 && code <= 0xF4) {
      size = 4;
      code &= 0x07;
    } else if (code >= 0x80) {
      return false;
    }
    if ((size_t)(end - at) < size) {
      return false;
    }
    for (size_t index = 1; index < size; index++) {
      if ((at[index] & 0xC0) != 0x80) {
        return false;
      }
      code = code << 6 | (at[index] & 0x3F);
    }
    if ((size == 3 && (code < 0x800 || (code >= 0xD800 && code <= 0xDFFF))) || (size == 4 && (code < 0x10000 || code > 0x10FFFF))) {
      return false;
    }
    at += size;
  }
  return true;
}
'''),
    ("read-text-file", "always", '''\
static Bytes read_text_file(const char *path) {
  FILE *file = fopen(path, "rb");
  if (file == NULL) {
    fail(3, "cannot-read", "%s: %s", path, strerror(errno));
  }
  Bytes bytes = {NULL, 0};
  size_t capacity = 0;
  size_t got;
  do {
    if (bytes.length == capacity) {
      capacity = larger(capacity, 1);
      bytes.data = resize(bytes.data, capacity, 1);
    }
    got = fread(bytes.data + bytes.length, 1, capacity - bytes.length, file);
    bytes.length += got;
  } while (got > 0);
  if (ferror(file)) {
    fail(3, "cannot-read", "%s: %s", path, strerror(errno));
  }
  fclose(file);
  if (!valid_utf8((const unsigned char *)bytes.data, (const unsigned char *)bytes.data + bytes.length)) {
    fail(4, "bad-json", "the input is not valid UTF-8");
  }
  return bytes;
}
'''),
    ("parse-json", "always", '''\
typedef enum { JSON_NULL, JSON_FALSE, JSON_TRUE, JSON_NUMBER, JSON_STRING, JSON_ARRAY, JSON_OBJECT } JsonKind;
'''),
    ("parse-json", "always", '''\
typedef struct Json {
  JsonKind kind;
  bool valid_text;
  Value key;
  Value value;
  struct Json *items;
  size_t count;
} Json;
'''),
    ("parse-json", "always", '''\
typedef struct {
  char *at;
  char *end;
  int depth;
} Parser;
'''),
    ("parse-json", "always", '''\
static _Noreturn void bad_json(void) {
  fail(4, "bad-json", "the input is not valid JSON");
}
'''),
    ("parse-json", "always", '''\
static void skip_space(Parser *parser) {
  while (parser->at < parser->end && (*parser->at == ' ' || *parser->at == '\\t' || *parser->at == '\\n' || *parser->at == '\\r')) {
    parser->at++;
  }
}
'''),
    ("parse-json", "always", '''\
static bool next_is(Parser *parser, char expected) {
  if (parser->at < parser->end && *parser->at == expected) {
    parser->at++;
    return true;
  }
  return false;
}
'''),
    ("parse-json", "always", '''\
static long hex4(const char *at, const char *end) {
  long code = 0;
  if (end - at < 4) {
    return -1;
  }
  for (int index = 0; index < 4; index++) {
    char digit = at[index];
    int value = digit >= '0' && digit <= '9' ? digit - '0' : digit >= 'a' && digit <= 'f' ? digit - 'a' + 10 : digit >= 'A' && digit <= 'F' ? digit - 'A' + 10 : -1;
    if (value < 0) {
      return -1;
    }
    code = code * 16 + value;
  }
  return code;
}
'''),
    ("parse-json", "always", '''\
static size_t put_utf8(char *out, long code) {
  if (code < 0x80) {
    out[0] = (char)code;
    return 1;
  }
  if (code < 0x800) {
    out[0] = (char)(0xC0 | code >> 6);
    out[1] = (char)(0x80 | (code & 0x3F));
    return 2;
  }
  if (code < 0x10000) {
    out[0] = (char)(0xE0 | code >> 12);
    out[1] = (char)(0x80 | (code >> 6 & 0x3F));
    out[2] = (char)(0x80 | (code & 0x3F));
    return 3;
  }
  out[0] = (char)(0xF0 | code >> 18);
  out[1] = (char)(0x80 | (code >> 12 & 0x3F));
  out[2] = (char)(0x80 | (code >> 6 & 0x3F));
  out[3] = (char)(0x80 | (code & 0x3F));
  return 4;
}
'''),
    ("parse-json", "always", '''\
static char simple_escape(char escape) {
  for (const char *pair = "\\"\\"\\\\\\\\//b\\bf\\fn\\nr\\rt\\t"; pair[0] != '\\0'; pair += 2) {
    if (pair[0] == escape) {
      return pair[1];
    }
  }
  return '\\0';
}
'''),
    ("parse-json", "always", '''\
static Json parse_string(Parser *parser) {
  char *start = ++parser->at;
  size_t length = 0;
  bool valid = true;
  for (;;) {
    if (parser->at == parser->end) {
      bad_json();
    }
    unsigned char next = (unsigned char)*parser->at++;
    if (next == '"') {
      break;
    }
    if (next < 0x20) {
      bad_json();
    }
    if (next != '\\\\') {
      start[length++] = (char)next;
      continue;
    }
    if (parser->at == parser->end) {
      bad_json();
    }
    char escape = *parser->at++;
    char simple = simple_escape(escape);
    if (simple != '\\0') {
      start[length++] = simple;
      continue;
    }
    long code = escape == 'u' ? hex4(parser->at, parser->end) : -1;
    if (code < 0) {
      bad_json();
    }
    parser->at += 4;
    if (code >= 0xD800 && code <= 0xDBFF && parser->end - parser->at >= 6 && parser->at[0] == '\\\\' && parser->at[1] == 'u') {
      long low = hex4(parser->at + 2, parser->end);
      if (low >= 0xDC00 && low <= 0xDFFF) {
        code = 0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00);
        parser->at += 6;
      }
    }
    valid = valid && (code < 0xD800 || code > 0xDFFF);
    length += put_utf8(start + length, code);
  }
  return (Json){.kind = JSON_STRING, .valid_text = valid, .value = {start, length, 0}};
}
'''),
    ("parse-json", "always", '''\
static void digits(Parser *parser) {
  if (parser->at == parser->end || *parser->at < '0' || *parser->at > '9') {
    bad_json();
  }
  while (parser->at < parser->end && *parser->at >= '0' && *parser->at <= '9') {
    parser->at++;
  }
}
'''),
    ("parse-json", "always", '''\
static Value parse_number(Parser *parser) {
  char *start = parser->at;
  next_is(parser, '-');
  if (!next_is(parser, '0')) {
    digits(parser);
  }
  if (next_is(parser, '.')) {
    digits(parser);
  }
  if (next_is(parser, 'e') || next_is(parser, 'E')) {
    if (!next_is(parser, '+')) {
      next_is(parser, '-');
    }
    digits(parser);
  }
  return (Value){start, (size_t)(parser->at - start), 0};
}
'''),
    ("parse-json", "always", '''\
static Json parse_word(Parser *parser, const char *word, JsonKind kind) {
  size_t length = strlen(word);
  if ((size_t)(parser->end - parser->at) < length || memcmp(parser->at, word, length) != 0) {
    bad_json();
  }
  parser->at += length;
  return (Json){.kind = kind};
}
'''),
    ("parse-json", "always", '''\
static Json parse_value(Parser *parser);
'''),
    ("parse-json", "always", '''\
static Json parse_items(Parser *parser, JsonKind kind, char close) {
  Json value = {.kind = kind};
  size_t capacity = 0;
  if (++parser->depth > 10000) {
    bad_json();
  }
  parser->at++;
  skip_space(parser);
  if (!next_is(parser, close)) {
    do {
      Json key = {.kind = JSON_NULL};
      if (kind == JSON_OBJECT) {
        skip_space(parser);
        if (parser->at == parser->end || *parser->at != '"') {
          bad_json();
        }
        key = parse_string(parser);
        skip_space(parser);
        if (!next_is(parser, ':')) {
          bad_json();
        }
      }
      Json item = parse_value(parser);
      item.key = key.value;
      if (value.count == capacity) {
        capacity = larger(capacity, sizeof(Json));
        value.items = resize(value.items, capacity, sizeof(Json));
      }
      value.items[value.count++] = item;
      skip_space(parser);
    } while (next_is(parser, ','));
    if (!next_is(parser, close)) {
      bad_json();
    }
  }
  parser->depth--;
  return value;
}
'''),
    ("parse-json", "always", '''\
static Json parse_value(Parser *parser) {
  skip_space(parser);
  char first = parser->at < parser->end ? *parser->at : '\\0';
  if (first == '"') {
    return parse_string(parser);
  }
  if (first == '[') {
    return parse_items(parser, JSON_ARRAY, ']');
  }
  if (first == '{') {
    return parse_items(parser, JSON_OBJECT, '}');
  }
  if (first == 't') {
    return parse_word(parser, "true", JSON_TRUE);
  }
  if (first == 'f') {
    return parse_word(parser, "false", JSON_FALSE);
  }
  if (first == 'n') {
    return parse_word(parser, "null", JSON_NULL);
  }
  if (first != '-' && (first < '0' || first > '9')) {
    bad_json();
  }
  return (Json){.kind = JSON_NUMBER, .value = parse_number(parser)};
}
'''),
    ("parse-json", "always", '''\
static Json parse_json(Bytes text) {
  Parser parser = {text.data, text.data + text.length, 0};
  Json root = parse_value(&parser);
  skip_space(&parser);
  if (parser.at != parser.end) {
    bad_json();
  }
  return root;
}
'''),
    ("check-list-of-records", "always", '''\
static Json check_list(Json data) {
  if (data.kind != JSON_ARRAY) {
    fail(5, "not-a-list", "the input must be a list of records");
  }
  return data;
}
'''),
    ("check-required-types", "always", '''\
static const Json *member(const Json *record, const char *name) {
  size_t length = strlen(name);
  for (size_t index = record->count; index > 0; index--) {
    const Json *item = &record->items[index - 1];
    if (item->key.length == length && memcmp(item->key.text, name, length) == 0) {
      return item;
    }
  }
  return NULL;
}
'''),
    ("check-required-types", "always", '''\
static bool to_text(const Json *value, Value *out) {
  if (value->kind != JSON_STRING || !value->valid_text) {
    return false;
  }
  out->text = value->value.text;
  out->length = value->value.length;
  return true;
}
'''),
    ("check-required-types", "always", '''\
static bool to_integer(const Json *value, Value *out) {
  if (value->kind != JSON_NUMBER) {
    return false;
  }
  char *copy = allocate(value->value.length + 1, 1);
  memcpy(copy, value->value.text, value->value.length);
  double number = strtod(copy, NULL);
  free(copy);
  if (!(number >= -(double)MAX_INTEGER && number <= (double)MAX_INTEGER) || (double)(long long)number != number) {
    return false;
  }
  out->number = (long long)number;
  return true;
}
'''),
    ("check-required-types", "always", '''\
static Value *to_row(const Json *record) {
  if (record->kind != JSON_OBJECT) {
    return NULL;
  }
  Value *row = allocate(WIDTH, sizeof *row);
  for (size_t field = 0; field < sizeof DECLARED / sizeof DECLARED[0]; field++) {
    const Json *value = member(record, NAMES[field]);
    if (value == NULL || !(DECLARED[field] == IS_TEXT ? to_text(value, &row[field]) : to_integer(value, &row[field]))) {
      free(row);
      return NULL;
    }
  }
  return row;
}
'''),
    ("check-required-types", "strict", '''\
static Rows require_valid(Json records) {
  Rows rows = {allocate(records.count, sizeof(Value *)), 0};
  for (size_t index = 0; index < records.count; index++) {
    Value *row = to_row(&records.items[index]);
    if (row == NULL) {
      fail(6, "invalid-record", "record %zu does not match the declared fields", index + 1);
    }
    rows.items[rows.count++] = row;
  }
  return rows;
}
'''),
    ("drop-invalid-rows", "skip", '''\
static Rows keep_valid(Json records) {
  Rows rows = {allocate(records.count, sizeof(Value *)), 0};
  for (size_t index = 0; index < records.count; index++) {
    Value *row = to_row(&records.items[index]);
    if (row != NULL) {
      rows.items[rows.count++] = row;
    }
  }
  return rows;
}
'''),
    ("filter-rows", "filter", '''\
static Rows filter_rows(Rows rows, bool (*test)(const Value *row)) {
  size_t kept = 0;
  for (size_t index = 0; index < rows.count; index++) {
    if (test(rows.items[index])) {
      rows.items[kept++] = rows.items[index];
    }
  }
  rows.count = kept;
  return rows;
}
'''),
    ("filter-rows", "same", '''\
static bool same_text(Value left, Value right) {
  return left.length == right.length && memcmp(left.text, right.text, left.length) == 0;
}
'''),
    ("calculate", "calculate", '''\
static long long calculate(long long left, char operation, long long right) {
  if (operation == '*' && left != 0 && llabs(right) > MAX_INTEGER / llabs(left)) {
    fail(7, "out-of-range", "a calculation gave a number outside the supported range");
  }
  long long result = operation == '+' ? left + right : operation == '-' ? left - right : left * right;
  if (result < -MAX_INTEGER || result > MAX_INTEGER) {
    fail(7, "out-of-range", "a calculation gave a number outside the supported range");
  }
  return result;
}
'''),
    ("calculate", "join", '''\
static Value join(Value left, Value right) {
  char *text = allocate(left.length + right.length + 1, 1);
  memcpy(text, left.text, left.length);
  memcpy(text + left.length, right.text, right.length);
  return (Value){text, left.length + right.length, 0};
}
'''),
    ("calculate", "integer", '''\
static Value integer(long long number) {
  return (Value){NULL, 0, number};
}
'''),
    ("calculate", "add", '''\
static Rows add_field(Rows rows, int slot, Value (*formula)(const Value *row)) {
  for (size_t index = 0; index < rows.count; index++) {
    rows.items[index][slot] = formula(rows.items[index]);
  }
  return rows;
}
'''),
    ("sort-rows", "compare", '''\
static int compare_text(Value left, Value right) {
  int order = memcmp(left.text, right.text, left.length < right.length ? left.length : right.length);
  if (order != 0) {
    return order < 0 ? -1 : 1;
  }
  return (left.length > right.length) - (left.length < right.length);
}
'''),
    ("sort-rows", "fold", '''\
static int compare_folded(Value left, Value right) {
  for (size_t index = 0; index < left.length && index < right.length; index++) {
    int a = (unsigned char)left.text[index];
    int b = (unsigned char)right.text[index];
    a += a >= 'A' && a <= 'Z' ? 'a' - 'A' : 0;
    b += b >= 'A' && b <= 'Z' ? 'a' - 'A' : 0;
    if (a != b) {
      return a < b ? -1 : 1;
    }
  }
  return (left.length > right.length) - (left.length < right.length);
}
'''),
    ("sort-rows", "numbers", '''\
static int compare_numbers(Value left, Value right) {
  return (left.number > right.number) - (left.number < right.number);
}
'''),
    ("sort-rows", "sort", '''\
enum { DESCENDING = -1, ASCENDING = 1 };
'''),
    ("sort-rows", "sort", '''\
static void merge_rows(Value **items, Value **spare, size_t count, int slot, int (*order)(Value left, Value right), int direction) {
  if (count < 2) {
    return;
  }
  size_t half = count / 2;
  merge_rows(items, spare, half, slot, order, direction);
  merge_rows(items + half, spare, count - half, slot, order, direction);
  memcpy(spare, items, count * sizeof *items);
  size_t left = 0;
  size_t right = half;
  for (size_t out = 0; out < count; out++) {
    if (left < half && (right == count || direction * order(spare[right][slot], spare[left][slot]) >= 0)) {
      items[out] = spare[left++];
    } else {
      items[out] = spare[right++];
    }
  }
}
'''),
    ("sort-rows", "sort", '''\
static Rows sort_rows(Rows rows, int slot, int (*order)(Value left, Value right), int direction) {
  Value **spare = allocate(rows.count, sizeof *spare);
  merge_rows(rows.items, spare, rows.count, slot, order, direction);
  free(spare);
  return rows;
}
'''),
    ("take-first", "limit", '''\
static Rows first_rows(Rows rows, long long count) {
  if ((unsigned long long)count < rows.count) {
    rows.count = (size_t)count;
  }
  return rows;
}
'''),
    ("group-by-key", "group", '''\
typedef struct {
  Value **first;
  size_t *sizes;
  size_t count;
} Groups;
'''),
    ("group-by-key", "group", '''\
static size_t hash_value(Value value) {
  unsigned long long hash = 14695981039346656037ULL;
  if (value.text == NULL) {
    return (size_t)((hash ^ (unsigned long long)value.number) * 1099511628211ULL);
  }
  for (size_t index = 0; index < value.length; index++) {
    hash = (hash ^ (unsigned char)value.text[index]) * 1099511628211ULL;
  }
  return (size_t)hash;
}
'''),
    ("group-by-key", "group", '''\
static bool same_value(Value left, Value right) {
  if (left.text == NULL || right.text == NULL) {
    return left.text == right.text && left.number == right.number;
  }
  return left.length == right.length && memcmp(left.text, right.text, left.length) == 0;
}
'''),
    ("group-by-key", "group", '''\
static Groups group_rows(Rows rows, int slot) {
  Groups groups = {allocate(rows.count, sizeof(Value *)), allocate(rows.count, sizeof(size_t)), 0};
  size_t capacity = 1;
  while (capacity < rows.count * 2) {
    capacity *= 2;
  }
  size_t *table = allocate(capacity, sizeof *table);
  for (size_t index = 0; index < rows.count; index++) {
    Value *row = rows.items[index];
    size_t at = hash_value(row[slot]) & (capacity - 1);
    while (table[at] != 0 && !same_value(groups.first[table[at] - 1][slot], row[slot])) {
      at = (at + 1) & (capacity - 1);
    }
    if (table[at] == 0) {
      groups.first[groups.count++] = row;
      table[at] = groups.count;
    }
    groups.sizes[table[at] - 1]++;
  }
  free(table);
  return groups;
}
'''),
    ("count-values", "count", '''\
static Rows count_groups(Groups groups, int slot, int count_slot) {
  Rows rows = {allocate(groups.count, sizeof(Value *)), groups.count};
  for (size_t index = 0; index < groups.count; index++) {
    Value *row = allocate(WIDTH, sizeof *row);
    row[slot] = groups.first[index][slot];
    row[count_slot] = (Value){NULL, 0, (long long)groups.sizes[index]};
    rows.items[index] = row;
  }
  return rows;
}
'''),
    ("print-message", "always", '''\
static void emit(Value text) {
  fwrite(text.text, 1, text.length, stdout);
}
'''),
    ("print-table", "show", '''\
static Value cell_text(Value value, char *buffer, size_t size) {
  if (value.text != NULL) {
    return value;
  }
  int length = snprintf(buffer, size, "%lld", value.number);
  return (Value){buffer, (size_t)length, 0};
}
'''),
    ("print-table", "show", '''\
static size_t code_points(Value text) {
  size_t count = 0;
  for (size_t index = 0; index < text.length; index++) {
    count += ((unsigned char)text.text[index] & 0xC0) != 0x80;
  }
  return count;
}
'''),
    ("print-table", "show", '''\
static void show_table(Rows rows, size_t columns, const int *slots) {
  size_t *widths = allocate(columns, sizeof *widths);
  char buffer[32];
  for (size_t index = 0; index < rows.count; index++) {
    for (size_t column = 0; column + 1 < columns; column++) {
      size_t width = code_points(cell_text(rows.items[index][slots[column]], buffer, sizeof buffer));
      widths[column] = width > widths[column] ? width : widths[column];
    }
  }
  for (size_t index = 0; index < rows.count; index++) {
    for (size_t column = 0; column < columns; column++) {
      Value cell = cell_text(rows.items[index][slots[column]], buffer, sizeof buffer);
      emit(cell);
      if (column + 1 < columns) {
        for (size_t width = code_points(cell); width < widths[column]; width++) {
          emit(literal(" "));
        }
        emit(literal("  "));
      }
    }
    emit(literal("\\n"));
  }
  free(widths);
}
'''),
    ("format-json", "json", '''\
static void write_json_text(Value text) {
  emit(literal("\\""));
  for (size_t index = 0; index < text.length;) {
    unsigned long code = (unsigned char)text.text[index];
    size_t size = code < 0x80 ? 1 : code < 0xE0 ? 2 : code < 0xF0 ? 3 : 4;
    code &= size == 1 ? 0x7F : 0x3F >> (size - 1);
    for (size_t part = 1; part < size; part++) {
      code = code << 6 | ((unsigned char)text.text[index + part] & 0x3F);
    }
    index += size;
    const char *simple = code < 0x20 ? strchr("\\bb\\ff\\nn\\rr\\tt", (int)code) : NULL;
    if (code == '"' || code == '\\\\') {
      printf("\\\\%c", (int)code);
    } else if (code >= 0x20 && code <= 0x7E) {
      putchar((int)code);
    } else if (simple != NULL && code != 0) {
      printf("\\\\%c", simple[1]);
    } else if (code >= 0x10000) {
      printf("\\\\u%04lx\\\\u%04lx", 0xD800 + ((code - 0x10000) >> 10), 0xDC00 + ((code - 0x10000) & 0x3FF));
    } else {
      printf("\\\\u%04lx", code);
    }
  }
  emit(literal("\\""));
}
'''),
    ("format-json", "json", '''\
static void write_json(Rows rows, size_t columns, const int *slots) {
  emit(literal("["));
  for (size_t index = 0; index < rows.count; index++) {
    emit(index == 0 ? literal("{") : literal(",{"));
    for (size_t column = 0; column < columns; column++) {
      Value value = rows.items[index][slots[column]];
      printf(column == 0 ? "\\"%s\\":" : ",\\"%s\\":", NAMES[slots[column]]);
      if (value.text != NULL) {
        write_json_text(value);
      } else {
        printf("%lld", value.number);
      }
    }
    emit(literal("}"));
  }
  emit(literal("]\\n"));
}
'''),
]

# The shape of the line each block adds to main(). Part of the block's version.
FORMS = {
    "read-text-file": "Bytes text = read_text_file(PATH);",
    "cli-options": "read_argument(argc, argv, N)",
    "parse-json": "Json records = check_list(parse_json(text));",
    "check-required-types": "Rows rows = require_valid(records);",
    "drop-invalid-rows": "Rows rows = keep_valid(records);",
    "filter-rows": "rows = filter_rows(rows, keep_N); static bool keep_N(const Value *row) { return CONDITIONS; }",
    "calculate": "rows = add_field(rows, F_NAME, add_N); static Value add_N(const Value *row) { return FORMULA; } calculate(A, '+', B); join(A, B); integer(A)",
    "sort-rows": "rows = sort_rows(rows, F_NAME, COMPARE, DIRECTION);",
    "take-first": "rows = first_rows(rows, N);",
    "group-by-key": "Groups groups = group_rows(rows, F_NAME);",
    "count-values": "rows = count_groups(groups, F_NAME, F_count);",
    "print-message": "if (rows.count == 0) { emit(literal(TEXT)); return 0; }",
    "print-table": "show_table(rows, N, (const int[]){F_NAME});",
    "format-json": "write_json(rows, N, (const int[]){F_NAME});",
}

ORDER = ("<", "<=", ">", ">=")
NUMBER_OPERATORS = {"=": "==", "!=": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
FROM_NUMBER = {code: op for op, code in NUMBER_OPERATORS.items()}


def quote(text):
    """A C string literal holding the UTF-8 bytes of the text, in plain ASCII."""
    out = []
    for byte in text.encode("utf-8"):
        ch = chr(byte)
        if ch in '\\"?':
            out.append("\\" + ch)
        elif ch == "\n":
            out.append("\\n")
        elif 32 <= byte < 127:
            out.append(ch)
        else:
            out.append(f"\\{byte:03o}")
    return '"' + "".join(out) + '"'


STRING = r'"(?:[^"\\]|\\.)*"'


def unquote(literal):
    inner = literal[1:-1]
    if re.fullmatch(r'(?:[ !#->@-\[\]-~]|\\[\\"?n]|\\[0-3][0-7]{2})*', inner) is None:
        raise NotGenerated("a text value is not written the way the compiler writes it")
    data = bytearray()
    for match in re.finditer(r'\\([\\"?n]|[0-3][0-7]{2})|.', inner):
        body = match.group(1)
        if body is None:
            data += match.group(0).encode("ascii")
        elif body == "n":
            data.append(10)
        elif len(body) == 1:
            data += body.encode("ascii")
        else:
            data.append(int(body, 8))
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise NotGenerated("a text value is not valid UTF-8") from None


def slot_names(program):
    """Every field name the program uses, in order of first appearance. Each gets a fixed place in a row."""
    names = [name for name, _ in program.source.fields]
    for step in program.steps:
        added = step.name if isinstance(step, Add) else "count" if isinstance(step, Count) else None
        if added is not None and added not in names:
            names.append(added)
    return names


def _parts(value):
    """Every formula inside a formula, itself included."""
    yield value
    if isinstance(value, Arith):
        yield from _parts(value.left)
        yield from _parts(value.right)
    elif isinstance(value, Concat):
        for part in value.parts:
            yield from _parts(part)


def needs(program):
    flags = {"always"}
    for step, schema in zip(program.steps, schemas(program)):
        if isinstance(step, Read):
            flags.add("skip" if step.skip_invalid else "strict")
            if program.source.argument is not None:
                flags.add("argument")
        elif isinstance(step, Filter):
            flags.add("filter")
            for cond in step.conditions:
                if formula_type(schema, cond.left) == "text":
                    flags.add("compare" if cond.op in ORDER else "same")
        elif isinstance(step, Add):
            flags.add("add")
            if formula_type(schema, step.formula) == "integer":
                flags.add("integer")
        elif isinstance(step, Sort):
            flags.add("sort")
            flags.add("numbers" if schema[step.field] == "integer" else "fold" if step.ignore_case else "compare")
        elif isinstance(step, Limit):
            flags.add("limit")
        elif isinstance(step, Group):
            flags.add("group")
        elif isinstance(step, Count):
            flags.add("count")
        elif isinstance(step, Show):
            flags.add("show")
        elif isinstance(step, WriteJson):
            flags.add("json")
        for value in formulas(step):
            for part in _parts(value):
                if isinstance(part, Arith):
                    flags.add("calculate")
                elif isinstance(part, Concat):
                    flags.add("join")
    return flags


def formula(value, schema):
    """Write a formula as C: an integer formula is a long long, a text formula a Value."""
    if isinstance(value, Field):
        return f"row[F_{value.name}].number" if schema[value.name] == "integer" else f"row[F_{value.name}]"
    if isinstance(value, Number):
        return str(value.value)
    if isinstance(value, Text):
        return f"literal({quote(value.value)})"
    if isinstance(value, Arith):
        return f"calculate({formula(value.left, schema)}, '{value.op}', {formula(value.right, schema)})"
    joined = formula(value.parts[0], schema)
    for part in value.parts[1:]:
        joined = f"join({joined}, {formula(part, schema)})"
    return joined


def condition(cond, schema):
    left, right = formula(cond.left, schema), formula(cond.right, schema)
    if formula_type(schema, cond.left) == "text":
        if cond.op in ORDER:
            return f"compare_text({left}, {right}) {cond.op} 0"
        return f"{'!' if cond.op == '!=' else ''}same_text({left}, {right})"
    return f"{left} {NUMBER_OPERATORS[cond.op]} {right}"


def columns(names):
    listed = ", ".join(f"F_{name}" for name in names)
    return f"{len(names)}, (const int[]){{{listed}}}"


def step_lines(program):
    """The functions written for steps, and the body of main(), as lists of (text, intent line) pairs."""
    source = program.source
    functions, body = [], []
    grouped = False
    numbers = {"keep": 0, "add": 0}
    for step, schema in zip(program.steps, schemas(program)):
        if isinstance(step, Read):
            origin = quote(source.path) if source.path is not None else f"read_argument(argc, argv, {source.argument})"
            body.append((f"  Bytes text = read_text_file({origin});", step.line))
            body.append(("  Json records = check_list(parse_json(text));", step.line))
            if step.skip_invalid:
                body.append(("  Rows rows = keep_valid(records);", step.skip_line))
            else:
                body.append(("  Rows rows = require_valid(records);", step.line))
        elif isinstance(step, Filter):
            numbers["keep"] += 1
            name = f"keep_{numbers['keep']}"
            joined = " && ".join(condition(cond, schema) for cond in step.conditions)
            functions += [(f"static bool {name}(const Value *row) {{", step.line), (f"  return {joined};", step.line), ("}", step.line), ("", "support")]
            body.append((f"  rows = filter_rows(rows, {name});", step.line))
        elif isinstance(step, Add):
            numbers["add"] += 1
            name = f"add_{numbers['add']}"
            value = formula(step.formula, schema)
            if formula_type(schema, step.formula) == "integer":
                value = f"integer({value})"
            functions += [(f"static Value {name}(const Value *row) {{", step.line), (f"  return {value};", step.line), ("}", step.line), ("", "support")]
            body.append((f"  rows = add_field(rows, F_{step.name}, {name});", step.line))
        elif isinstance(step, Sort):
            order = "compare_numbers" if schema[step.field] == "integer" else "compare_folded" if step.ignore_case else "compare_text"
            direction = "DESCENDING" if step.descending else "ASCENDING"
            body.append((f"  rows = sort_rows(rows, F_{step.field}, {order}, {direction});", step.line))
        elif isinstance(step, Limit):
            body.append((f"  rows = first_rows(rows, {step.count});", step.line))
        elif isinstance(step, Group):
            keyword = "" if grouped else "Groups "
            grouped = True
            body.append((f"  {keyword}groups = group_rows(rows, F_{step.field});", step.line))
        elif isinstance(step, Count):
            body.append((f"  rows = count_groups(groups, F_{step.field}, F_count);", step.line))
        elif isinstance(step, IfNone):
            body.append(("  if (rows.count == 0) {", step.line))
            body.append((f"    emit(literal({quote(step.text + chr(10))}));", step.line))
            body.append(("    return 0;", step.line))
            body.append(("  }", step.line))
        elif isinstance(step, Show):
            body.append((f"  show_table(rows, {columns(step.fields)});", step.line))
        elif isinstance(step, WriteJson):
            body.append((f"  write_json(rows, {columns(list(schema))});", step.line))
    return functions, body


def generate(program):
    """Return the program text as a list of (line, origin) pairs.

    origin is an intent line number, or the name of the block a support line belongs to.
    """
    source = program.source
    names = slot_names(program)
    kinds = ", ".join("IS_TEXT" if kind == "text" else "IS_INTEGER" for _, kind in source.fields)
    lines = [(line, "support") for line in PRELUDE.rstrip("\n").split("\n")]
    lines += [("", "support"), (f"static const char SOURCE[] = {quote(source.name)};", "support"),
              ("enum { " + ", ".join(f"F_{name}" for name in names) + ", WIDTH };", "support"),
              ("static const char *const NAMES[WIDTH] = {" + ", ".join(quote(name) for name in names) + "};", "support"),
              ("static const Kind DECLARED[] = {" + kinds + "};", "support")]
    flags = needs(program)
    for block, flag, text in SUPPORT:
        if flag in flags:
            lines.append(("", "support"))
            lines += [(line, block) for line in text.rstrip("\n").split("\n")]
    functions, body = step_lines(program)
    lines.append(("", "support"))
    lines += functions
    arguments = "int argc, char **argv" if source.argument is not None else "void"
    lines.append((f"int main({arguments}) {{", "support"))
    lines += body
    lines += [("  return 0;", "support"), ("}", "support")]
    return lines


NAME = r"([A-Za-z_][A-Za-z0-9_]*)"
SLOT = rf"F_{NAME}"
FIELD_NAME = rf'"{NAME}"'
FIELD_VALUE = re.compile(rf"row\[{SLOT}\](\.number)?")
STRING_VALUE = re.compile(rf"literal\(({STRING})\)")
NUMBER_VALUE = re.compile(r"-?\d+")
CALCULATION = re.compile(r", '([-+*])', ")
COMPARISON = re.compile(r" (==|!=|<=|>=|<|>) ")
ORDER_TEST = re.compile(r" (<=|>=|<|>) 0")
FUNCTION = re.compile(r"static (bool keep|Value add)_(\d+)\(const Value \*row\) \{")


def lift(text):
    """Recover the Program from generated text. Raises NotGenerated."""
    lines = text.split("\n")
    name = _only(re.fullmatch(rf"static const char SOURCE\[\] = {FIELD_NAME};", line) for line in lines)
    names_line = _only(re.fullmatch(r"static const char \*const NAMES\[WIDTH\] = \{(.*)\};", line) for line in lines)
    kinds_line = _only(re.fullmatch(r"static const Kind DECLARED\[\] = \{(.*)\};", line) for line in lines)
    names = re.findall(FIELD_NAME, names_line[1])
    kinds = re.findall(r"IS_(TEXT|INTEGER)", kinds_line[1])
    if not kinds or len(kinds) > len(names) or len(set(names)) != len(names):
        raise NotGenerated("the declared fields cannot be read")
    pairs = tuple((field, kind.lower()) for field, kind in zip(names, kinds))
    functions = {}
    for index, line in enumerate(lines):
        if match := FUNCTION.fullmatch(line):
            body = re.fullmatch(r"  return (.*);", lines[index + 1] if index + 1 < len(lines) else "")
            if body is None or lines[index + 2:index + 3] != ["}"]:
                raise NotGenerated("a function written for a step is not as generated")
            functions[(match[1].split()[1], int(match[2]))] = body[1]
    start = [index for index, line in enumerate(lines) if line in ("int main(void) {", "int main(int argc, char **argv) {")]
    if len(start) != 1 or "}" not in lines[start[0]:]:
        raise NotGenerated("there is no main function")
    body = lines[start[0] + 1:lines.index("}", start[0])]
    if body[-1:] != ["  return 0;"]:
        raise NotGenerated("the main function does not end as generated")
    body = body[:-1]
    steps, path, argument = [], None, None
    index = 0
    while index < len(body):
        line = body[index]
        index += 1
        if match := re.fullmatch(rf"  Bytes text = read_text_file\((?:({STRING})|read_argument\(argc, argv, (\d+)\))\);", line):
            path = unquote(match[1]) if match[1] else None
            argument = int(match[2]) if match[2] else None
            if body[index:index + 1] != ["  Json records = check_list(parse_json(text));"]:
                raise NotGenerated("the lines that read the source are not as generated")
            mode = body[index + 1] if index + 1 < len(body) else ""
            if mode not in ("  Rows rows = require_valid(records);", "  Rows rows = keep_valid(records);"):
                raise NotGenerated("the lines that read the source are not as generated")
            steps.append(Read(skip_invalid="keep_valid" in mode))
            index += 2
        elif match := re.fullmatch(r"  rows = filter_rows\(rows, keep_(\d+)\);", line):
            steps.append(Filter(conditions=_conditions(_function(functions, "keep", match[1]))))
        elif match := re.fullmatch(rf"  rows = add_field\(rows, {SLOT}, add_(\d+)\);", line):
            written = _function(functions, "add", match[2])
            if written.startswith("integer(") and written.endswith(")"):
                written = written[len("integer("):-1]
            scanner = Scanner(written)
            value = _formula(scanner)
            if not scanner.done():
                raise NotGenerated("a formula cannot be read")
            steps.append(Add(name=match[1], formula=value))
        elif match := re.fullmatch(rf"  rows = sort_rows\(rows, {SLOT}, (compare_numbers|compare_text|compare_folded), (ASCENDING|DESCENDING)\);", line):
            steps.append(Sort(field=match[1], descending=match[3] == "DESCENDING", ignore_case=match[2] == "compare_folded"))
        elif match := re.fullmatch(r"  rows = first_rows\(rows, (\d+)\);", line):
            steps.append(Limit(count=int(match[1])))
        elif match := re.fullmatch(rf"  (?:Groups )?groups = group_rows\(rows, {SLOT}\);", line):
            steps.append(Group(field=match[1]))
        elif match := re.fullmatch(rf"  rows = count_groups\(groups, {SLOT}, F_count\);", line):
            steps.append(Count(field=match[1]))
        elif line == "  if (rows.count == 0) {":
            match = re.fullmatch(rf"    emit\(literal\(({STRING})\)\);", body[index] if index < len(body) else "")
            if match is None or body[index + 1:index + 3] != ["    return 0;", "  }"]:
                raise NotGenerated("the lines that print a message are not as generated")
            message = unquote(match[1])
            if not message.endswith("\n"):
                raise NotGenerated("the message does not end with a line break")
            steps.append(IfNone(text=message[:-1]))
            index += 3
        elif match := re.fullmatch(r"  show_table\(rows, (\d+), \(const int\[\]\)\{(.*)\}\);", line):
            steps.append(Show(fields=_slots(match[2], match[1])))
        elif match := re.fullmatch(r"  write_json\(rows, (\d+), \(const int\[\]\)\{(.*)\}\);", line):
            _slots(match[2], match[1])
            steps.append(WriteJson())
        else:
            raise NotGenerated(f"this line is not one the compiler generates: {line.strip()}")
    source = Source(name=name.group(1), path=path, argument=argument, fields=pairs)
    return assemble(source, steps)


def _only(matches):
    found = [match for match in matches if match]
    if len(found) != 1:
        raise NotGenerated("the header of the program is not as generated")
    return found[0]


def _function(functions, kind, number):
    try:
        return functions[(kind, int(number))]
    except KeyError:
        raise NotGenerated(f"there is no function {kind}_{number}") from None


def _slots(text, count):
    names = re.findall(SLOT, text)
    if not names or ", ".join(f"F_{name}" for name in names) != text or len(names) != int(count):
        raise NotGenerated("the list of fields cannot be read")
    return tuple(names)


def _atom(scanner):
    if match := scanner.match(FIELD_VALUE):
        return Field(match[1])
    if match := scanner.match(STRING_VALUE):
        return Text(unquote(match[1]))
    if match := scanner.match(NUMBER_VALUE):
        return Number(int(match[0]))
    if scanner.take("calculate("):
        left = _atom(scanner)
        op = scanner.match(CALCULATION)
        if op is None:
            raise NotGenerated("a calculation cannot be read")
        right = _atom(scanner)
        scanner.expect(")")
        return Arith(op[1], left, right)
    raise NotGenerated("a formula cannot be read")


def _formula(scanner):
    """A formula: an atom, or text joined by nested calls of join, the first part innermost."""
    depth = 0
    while scanner.take("join("):
        depth += 1
    parts = [_atom(scanner)]
    for _ in range(depth):
        scanner.expect(", ")
        parts.append(_atom(scanner))
        scanner.expect(")")
    return parts[0] if len(parts) == 1 else Concat(tuple(parts))


def _conditions(text):
    scanner, conditions = Scanner(text), []
    while True:
        if scanner.take("compare_text("):
            left = _formula(scanner)
            scanner.expect(", ")
            right = _formula(scanner)
            scanner.expect(")")
            test = scanner.match(ORDER_TEST)
            if test is None:
                raise NotGenerated("a comparison of text cannot be read")
            conditions.append(Condition(left, test[1], right))
        elif (negated := scanner.take("!same_text(")) or scanner.take("same_text("):
            left = _formula(scanner)
            scanner.expect(", ")
            right = _formula(scanner)
            scanner.expect(")")
            conditions.append(Condition(left, "!=" if negated else "=", right))
        else:
            left = _formula(scanner)
            op = scanner.match(COMPARISON)
            if op is None:
                raise NotGenerated("a condition cannot be read")
            conditions.append(Condition(left, FROM_NUMBER[op[1]], _formula(scanner)))
        if scanner.done():
            return tuple(conditions)
        scanner.expect(" && ")


__all__ = ["FILE_NAME", "SUPPORT", "blocks_used", "generate", "lift", "schemas"]
