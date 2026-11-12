# What the blocks mean

This page fixes the meaning of the intent language's first family of blocks, independently of any target language. Every target must behave exactly as described here. Where a target's own habits differ, the generated code overrides them. The tests in `tests/test_equivalence.py` check that the Python and JavaScript targets agree with each other on these rules.

**Status:** written by the AI assistant for Stage 2 of `PLAN.md`. Not yet reviewed by a person. All blocks are marked draft.

## Values

There are two types.

- **text**: a sequence of Unicode characters. Text that cannot be encoded as UTF-8 (an unpaired surrogate) is not valid text.
- **integer**: a whole number from -9007199254740991 to 9007199254740991. This is the range every target can hold exactly.

## Reading the source

The source is a file whose path is written in the intent file or given as a command-line argument.

1. The file is read as bytes and must be valid UTF-8. A byte-order mark at the start is not accepted.
2. The text must be valid JSON as defined by the JSON standard. `NaN`, `Infinity` and `-Infinity` are not accepted.
3. The top-level value must be a list.
4. Each item of the list is a record. A record is **valid** when it is a JSON object and every declared field is present with a value of the declared type:
   - a text field holds a JSON string that is valid text;
   - an integer field holds a JSON number whose value is a whole number in range. `18`, `18.0` and `1e3` are all accepted and mean 18, 18 and 1000. `18.5`, `"18"`, `true` and `null` are not accepted. Negative zero means 0.
5. From each valid record a **row** is made, holding only the declared fields, in the order they were declared. Fields that were not declared are ignored. If a field name appears twice in a record, the last value counts.
6. An invalid record stops the program with an error, unless the intent says `skip invalid records`, in which case invalid records are left out and the rest are kept in their original order.

## Order of text

Text is ordered by comparing Unicode code points from left to right. A shorter text that is the start of a longer one comes first. This order is used by sorting and by the comparisons `<`, `<=`, `>` and `>=`. It is not alphabetical order in any human language: all capital letters A to Z come before all small letters, and accented letters come after both.

**Ignoring case** means that the letters A to Z are treated as a to z before comparing. No other characters are changed.

## Formulas

A formula works out a value from the fields of one row. It is one of:

- a field, a whole number, or text in double quotes;
- `A + B`, `A - B` or `A * B`, where both sides are integers. The result is an integer. If the result of any step of a calculation is outside the integer range, the program stops with the error `out-of-range`. There is no division yet.
- `A & B`, where both sides are text. The result is the two pieces of text joined end to end.
- a formula in brackets.

`*` is worked out before `+` and `-`; otherwise formulas are worked out from left to right. There is no conversion between integers and text. A minus sign directly before digits is part of the number, so write `0 - age` to negate a field.

A condition must involve at least one field, and must not compare a formula with itself.

## The blocks

| Statement | Takes | Gives | Meaning |
|---|---|---|---|
| `get S` | nothing | rows | Read the source as described above. |
| `skip invalid records` | rows | rows | Changes how the source is read: invalid records are left out. Must come directly after `get`. |
| `keep where C and C` | rows | rows | Keep the rows for which every condition holds, in their original order. A condition compares two formulas of the same type. `=` and `!=` test whether the values are identical. Conditions are tested from left to right, and testing stops at the first that does not hold. |
| `add N = formula` | rows | rows | Give every row a new field N holding the value of the formula for that row. N must not already be a field. The new field comes after the existing ones. |
| `sort by F ascending` or `descending` | rows | rows | Order the rows by the field. Rows with equal values keep their original order, in both directions. With `ignoring case` (text only), two values that differ only in the case of A to Z count as equal. |
| `limit N` | rows | rows | Keep the first N rows. If there are fewer, keep them all. N may be 0. |
| `group by F` | rows | groups | Collect the rows into groups with identical values of the field. Groups are in the order in which their value first appears. |
| `count each group` | groups | rows | Give one row per group, with two fields: the grouping field, holding the group's value, and `count`, an integer holding the number of rows in the group. A source field named `count` therefore cannot be grouped on. |
| `if none say "T"` | rows | rows | If there are no rows, print T followed by a line break and end the program successfully. Otherwise do nothing. |
| `show F, F` | rows | output | Print one line per row. Values are separated by two spaces. Every column but the last is padded on the right with spaces to the width of its widest value, counted in Unicode code points. Integers are printed in decimal. With no rows, nothing is printed. |
| `write as json` | rows | output | Print the rows as one line of JSON followed by a line break. Fields are in the order of the row. There are no spaces between tokens. Every character outside the range from space to `~` is written as a `\u` escape with lower-case hexadecimal digits, so the output is plain ASCII. |

A statement of the form `get S where C` means `get S` followed by `keep where C`.

A program must end with exactly one statement that produces output, and nothing may follow it.

## Output

Output is written as UTF-8 bytes. Line breaks are a single line-feed character. Nothing is written until every step has succeeded, so a program that fails writes no output.

## Errors

A program that fails writes one line to the error stream, beginning `error: <category>:`, and ends with the status shown. Targets must agree on the category and the status. The wording after the category may differ between targets.

| Category | Status | When |
|---|---|---|
| `usage` | 2 | A command-line argument the program needs is missing |
| `cannot-read` | 3 | The file cannot be opened or read |
| `bad-json` | 4 | The file is not valid UTF-8 or not valid JSON |
| `not-a-list` | 5 | The top-level JSON value is not a list |
| `invalid-record` | 6 | A record is invalid and the intent does not say to skip invalid records |
| `out-of-range` | 7 | A calculation gave a number outside the integer range |

## Known limits

These are cases where the targets may behave differently, or where the rules above leave something out. They are not covered by tests.

- **Very deeply nested JSON.** Python refuses JSON nested more than about a thousand levels deep, which is reported as `bad-json`. Node accepts far deeper nesting. A file nested that deeply inside a field that was not declared would be accepted by one target and refused by the other.
- **Very large files.** Each program reads the whole file into memory. Limits on size differ between targets and were not measured.
- **Platforms.** The tests were run on Linux only, with Python 3.14.6 and Node 22.23.4.
- **Formulas.** There is no division, no conversion between integers and text, and no way to choose between values by a condition.

## Web pages

A second kind of intent file describes the pages of an application and is built into HTML and CSS. It is separate from the blocks above: it has no source and no chain of steps.

```text
language: en

app Inventory:
    data Product:
        name: text
        price: decimal
        stock: integer

    page Products:
        heading "Products"
        table Product
        button "Add product" width 160px
```

**Status:** a first step, written by the AI assistant and not yet reviewed by a person. The pages are static: they have structure and style and no behaviour.

| Statement | Meaning |
|---|---|
| `app N:` | The application. Its name appears in the title of every page. |
| `data N:` with fields beneath | A kind of record, with fields of type `text`, `integer` or `decimal`. Here the types affect only how a column is aligned. Every data declaration must be shown by at least one table. |
| `page N:` with elements beneath | One page, written to a file named after the page in lower case, ending `.html`. The page title is the page name, a hyphen and the application name. When there is more than one page, every page starts with links to all the pages, in the order they are declared. |
| `heading "T"` | A heading. The first on a page is the main heading; later ones are second-level headings. |
| `text "T"` | A paragraph. |
| `table D` | A table with one column for each field of the data D, in the order declared, headed by the field's name. Columns of numbers are aligned to the right. The table has no rows: nothing yet supplies them. |
| `button "T"` and optionally `width Npx` | A button. It does nothing when pressed. With a width, the button is exactly that many pixels wide. |

All pages share one stylesheet, `styles.css`, which holds fixed rules for the elements that are used and one rule for each button width that is used. The colours, spacing and fonts are fixed choices of the generator.

Text in double quotes is shown exactly as written; the characters `&`, `<` and `>` are escaped. No words are added that the developer did not write.

Some statements are recognised but cannot be built yet, and say so: choosing parts of an application (`use web`), an API for a data type (`expose Product as api`), searching, sorting and editing a table, and rules that react to data (`when ...:` and `notify`).

Known limits: there is no behaviour of any kind; the language of the page is not declared in the HTML; and a line of text longer than about 300 characters would be re-wrapped by the formatter used for criterion G6.
