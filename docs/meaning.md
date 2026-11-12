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
   - an integer field holds a JSON number whose value is a whole number in range. `18`, `18.0` and `1e3` are all accepted and mean 18, 18 and 1000. `18.5`, `"18"`, `true` and `null` are not accepted. Negative zero means 0. The test is made on the number as every target reads it, which is the nearest double-precision value: a number written with a fraction too small to survive that, such as `9007199254740990.5`, is read as the whole number beside it and accepted.
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

- **Very deeply nested JSON.** The targets stop at different depths, and a file refused for its depth is reported as `bad-json`. As measured with the versions used here: Python 3.14 accepts 10,000 levels and refuses 50,000; C refuses more than 10,000; Node and Java accept whatever fits in memory. A file nested that deeply inside a field that was not declared would be accepted by some targets and refused by others.
- **Very large files.** Each program reads the whole file into memory. Limits on size differ between targets and were not measured.
- **Platforms.** The tests were run on Linux only, with Python 3.14.6 and Node 22.23.4.
- **Formulas.** There is no division, no conversion between integers and text, and no way to choose between values by a condition.

## Web pages

A second kind of intent file describes the pages of an application and is built into HTML, CSS, JavaScript and JSON. It is separate from the blocks above: it has no source and no chain of steps.

```text
language: en

app Inventory:
    data Product:
        name: text
        price: decimal
        stock: integer

    records Product:
        "Widget", 9.99, 12
        "Gadget", 24.50, 3

    page Products:
        heading "Products"
        table Product
        searchable by name
        sortable by price
        button "Add product" width 160px
```

**Status:** written by the AI assistant and not yet reviewed by a person. All blocks are marked draft.

| Statement | Meaning |
|---|---|
| `app N:` | The application. Its name appears in the title of every page. |
| `data N:` with fields beneath | A kind of record, with fields of type `text`, `integer` or `decimal`. Every data declaration must be shown by at least one table. |
| `records N:` with one record per line beneath | Records of the data N. Each line gives one value for each field, in order, separated by commas: text in double quotes, whole numbers, or decimals such as `9.99`. They are written to a JSON file named after the data in lower case, ending `.json`, as a list of objects. |
| `page N:` with elements beneath | One page, written to a file named after the page in lower case, ending `.html`. The page title is the page name, a hyphen and the application name. When there is more than one page, every page starts with links to all the pages, in the order they are declared. |
| `heading "T"` | A heading. The first on a page is the main heading; later ones are second-level headings. |
| `text "T"` | A paragraph. |
| `table D` | A table with one column for each field of the data D, in the order declared, headed by the field's name. Columns of numbers are aligned to the right. If D has records, the table fills itself from their JSON file when the page opens, one row per record in the order written. Otherwise it has no rows. |
| `searchable by F` | Directly after a table: a search box, labelled with the field's name. As the reader types, rows whose value of F does not contain the typed text are hidden. The letters A to Z are treated as a to z; nothing else is changed. An empty box shows every row. |
| `sortable by F` | Directly after a table, and may be repeated for other fields: the heading of column F becomes a control. The first press sorts the rows by F in ascending order; pressing the same heading again reverses the order. Numbers are compared by value and text in the order of text defined above. Rows that are equal keep their order. |
| `button "T"` and optionally `width Npx` | A button. With a width, it is exactly that many pixels wide. On its own it does nothing when pressed; see below for buttons that add a record or open a page. |
| `increase button size by Npx`, `decrease button size by Npx` | Makes a button declared above it on the same page wider or narrower by N pixels. If the page has more than one button, the label must be given: `increase button "T" size by Npx`. The button must already have a width. This statement changes the declaration: in standard phrases the button's line carries the new width and the statement is gone. |

### Applications with a database and an API

```text
language: en

use sqlite
use FastAPI

app Inventory:
    data Product:
        name: text
        price: decimal
        stock: integer

    records Product:
        "Widget", 9.99, 12

    expose Product as api

    page Products:
        table Product
        editable
        button "Add product" adds Product
        button "Suppliers" opens Suppliers
        notifications

    when Product.stock < 5:
        notify inventory_manager
```

| Statement | Meaning |
|---|---|
| `use FastAPI` | Before the application. A server, `server.py`, is generated with the FastAPI framework. It serves the pages, which are then written to a folder named `static`, and opening its root address leads to the first page. `requirements.txt` names the versions of FastAPI and uvicorn the server was tested with. |
| `use sqlite` | Before the application. Data that is exposed is kept in a SQLite database file beside the server, named after the application in lower case. It is an error to choose it when nothing is exposed. |
| `expose D as api` | Needs both of the above. Creates a table for the data D and an API over it, at the address `/api/` followed by the name of D in lower case. A table of D on a page then fills itself from the API. |
| `button "T" adds D` | D must be exposed. Pressing the button opens a form with one input for each field of D. Sending the form adds the record through the API and refills the tables of D on the page. The browser refuses a number that is not written as a number before anything is sent. |
| `button "T" opens P` | Pressing the button opens the page P. |
| `editable` | The same word in English and Spanish. Directly after a table, and after its `searchable by` and `sortable by` lines if it has any; in standard phrases it is written last. The table's data must be exposed. See "Changing and deleting from a page" below. |
| `when D.F < V:` with `notify N` on the one line beneath it | Spanish `cuando D.F < V:` and `notificar N`. Inside the application, at the same level as `data` and `page`. A rule: after a record of D is added or changed through the API, if the condition holds for the record as stored, a notification for N is stored. D must be exposed. See "Rules and notifications" below. |
| `notifications` | Spanish `notificaciones`. A list of the notifications the rules have stored. The application must have at least one rule. |
| `use authentication` | Spanish `usar autenticación`. Before the application; needs `use sqlite` and `use FastAPI`. Nothing in the application can be reached without signing in. See "Authentication" below. |
| `sign in "N" "P" "B" "F"` | Spanish `iniciar sesión`. Needs `use authentication`. The form for signing in: N labels the box for the name, P the box for the password, B is the text of the button, and F is the message shown when signing in fails. All four are required, because a page holds no words the developer did not write. |
| `button "T" signs out` | Spanish `botón "T" cierra sesión`, optionally with `width Npx` before the action. Needs `use authentication`. Pressing the button ends the session and leads to the sign-in page. |

**The table.** One row per record, with a column for each field and an `id` that the database assigns, starting at 1 and never reused while the record with the highest id still exists. Text and decimals are stored as text and integers as integers. No field may be named `id`. The table is created the first time the server starts. The records written in the intent file are put into it at that moment and never again; they are also written to a JSON file beside the server, which the server reads once and does not serve.

**The API.**

| Request | Result |
|---|---|
| `GET /api/d` | Every record, as a list of objects with `id` and the fields, in order of `id`. |
| `POST /api/d` with a record | Adds the record. Replies 201 with the record and its `id`. |
| `PUT /api/d/7` with a record | Replaces record 7. Replies with the record, or 404 if there is none. |
| `DELETE /api/d/7` | Removes record 7. Replies 204, or 404 if there is none. |

A record sent to the API must be a JSON object with exactly the declared fields. Text must be a JSON string, an integer a JSON whole number in range, and a decimal a JSON string such as `"9.99"` with at most 15 digits. Anything else is refused with status 422 and nothing is stored. Unlike reading a source file, `18.0` is not accepted as an integer here.

**Changing and deleting from a page.** A table marked `editable` has one more column at the end, with no heading. When the table fills, each row is given the `id` of its record, which is kept on the row and not shown, and the last cell of the row holds two buttons: ✎ and ×. No words are added; the buttons are the same whatever human language the intent was written in, and nothing asks for confirmation.

- ✎ opens a form, after the table, with one input for each field of the data, in the order declared, each labelled with the field's name and filled with the value the row shows. The browser checks numbers as in the form for adding a record. Sending the form with ✓ replaces the record through the API (`PUT /api/d/ID`), closes the form and fills every table of the same data on the page again. × in the form closes it and changes nothing.
- × in a row deletes the record through the API (`DELETE /api/d/ID`) at once, and fills every table of the same data on the page again.
- If the server refuses a change or a deletion, the page stays as it was, the form stays open, and the problem is written to the browser's console only.
- The form for changing a record is the same kind of form as the one for adding a record, and shares its style; the trace therefore lists the block `add-record-form` with `edit-table-rows`.

**Rules and notifications.**

- **The condition** is one or more comparisons joined by `and` (Spanish `y`). Each comparison is written `D.F`, an operator, and a fixed value: `Product.stock < 5`. The operators are `=`, `!=`, `<`, `<=`, `>` and `>=`. Every comparison of one rule names the same data D, which must be exposed, and a field F of it. The value must fit the field, as in records: text in double quotes, a whole number, or a decimal such as `9.99`; a whole number may be written for a decimal field, as in records. In standard phrases the comparisons are written with one space on each side of the operator, decimals keep the digits as written, and text is written in double quotes with `"` and `\` escaped by `\`.
- **Comparing.** Integers are compared by value. Decimals are compared by value exactly, not as floating point: `"10.5"` is not below `9.99`, and `"9.990"` equals `9.99`. Text is compared exactly for `=` and `!=`, and by Unicode code point, character by character, for the others, as in the order of text above; capital and small letters are different.
- **When a rule is applied.** After a record is added (`POST`) or changed (`PUT`) through the API, to the record as stored, in the same transaction as the record itself: either both are stored or neither is. A request that is refused, a change to a record that does not exist, a deletion, and the records written in the intent file do not apply any rule. When several rules hold for one record, one notification is stored for each, in the order of the rules.
- **A notification** holds its own `id` (assigned like a record's), `recipient` (the name after `notify`), `condition` (the rule's condition in standard English phrases, with the data name, exactly as an intent file in standard phrases writes it after `when`; this does not depend on the human language the intent was written in), `record` (the `id` of the record), and `time` (when it was stored, by the server's clock, in UTC, ISO 8601 to the second, ending in `Z`, such as `2026-11-12T09:30:00Z`).
- **Nothing is sent.** The name after `notify` is a label: no message, e-mail or other signal goes to anyone. Notifications are only stored and listed.
- **Where they are kept.** In a table named `notification` in the same database, created the first time the server starts with at least one rule. Notifications are kept when their record is changed again or deleted, and when the server restarts. Because the table is named `notification`, no data type with an API may be named `Notification`, in any mix of capital and small letters, in an application that has a rule; this is reported at its `expose` line.
- **The API.** `GET /api/notification` lists every notification, as objects with the five keys above, in order of `id`. Notifications cannot be added, changed or deleted through the API: such requests are refused with 405 and change nothing.
- **The list on a page.** `notifications` is a list with one item per notification, oldest first and newest last, each written `recipient: condition #record`, such as `inventory_manager: Product.stock < 5 #4`, and no other words. It is filled when the page opens and again after a record is added or changed from that page. It is not filled again after a deletion, nor when another page or another reader adds a record.
- **Order and standard phrases.** A rule has exactly one `notify` line. The same rule may not be written twice. In standard phrases the rules come after the pages, ordered by the order of their data (the order of the `data` declarations in standard phrases), and for one data in the order written.

**Authentication.** With `use authentication`, the server lets in only people who have signed in. It is a draft written by the AI assistant and has **not been reviewed by a person experienced in authentication**; do not rely on it until it has been.

*What the developer writes.* Exactly one page holds a `sign in` element; that page is the sign-in page. It may hold only headings, text and the one `sign in`, and there must be at least one other page. In standard phrases the sign-in page is written first. No data type may be declared whose table would be named `auth_user` or `auth_session`, in any mix of capital and small letters: those tables keep the users and their sessions. `sign in` and `signs out` without `use authentication` are errors.

*Users.* There is one kind of user, and every user can do everything the application allows: read, add, change and delete every record, and read every notification. Users are added and removed only from the command line, in the folder of the generated server, never from the intent file, and there is no account to begin with:

| Command | What it does |
|---|---|
| `python server.py add-user NAME` | Adds a user. Refused if the name is taken. |
| `python server.py set-password NAME` | Gives the user a new password, unlocks the name and ends all of the user's sessions. |
| `python server.py remove-user NAME` | Removes the user and ends all of the user's sessions. |
| `python server.py list-users` | Lists the names, in code point order. |

When the command is run at a terminal, the password is asked for twice without being shown; otherwise it is read as one line from standard input, so that scripts can supply it. A password has from 8 to 1000 characters. A name has from 1 to 200 characters, no control characters and no space at either end. Names are compared exactly: `Ana` and `ana` are two users. Importing `server.py`, which is what uvicorn does, runs none of the commands.

*Passwords.* A password is kept as a hash made with scrypt (`n = 2^14`, `r = 8`, `p = 1`, 32 bytes) and a random 16-byte salt for each user. The password itself is never stored, logged or sent back.

*Signing in.* `POST /api/sign-in` with a JSON object `{"name": ..., "password": ...}`. Both must be text; the name may have at most 200 characters and the password at most 1000, or the request is refused with 422 before anything is hashed, and the reply does not repeat what was sent. If the name and password are right, the reply is 204 and a session cookie; otherwise 401, with the same body whether the name is unknown, the password is wrong or the name is locked. For an unknown name a hash is still worked out, with a fixed salt, so that the time taken does not show which names exist.

*The lock.* Every attempt for a known name that is not locked is counted before its password is checked, so that attempts made at the same moment are all counted. The fifth attempt in a row that fails locks the name for five minutes; while it is locked every attempt is refused, even with the right password, and is not counted. A right password, when the name is not locked, sets the count back to zero. A name that has been locked and has failed again since is locked again after one more failure. Nothing is recorded for a name that does not exist.

*Sessions.* Signing in starts a session that lasts 12 hours and cannot be extended. Its token is 32 random bytes, written in URL-safe Base64; the server keeps only the SHA-256 hash of the token, the user's name and the time it ends. The cookie is named `session`, and is `HttpOnly`, `SameSite=Lax`, `Path=/`, with `Max-Age` of 12 hours, and `Secure` when the request came over HTTPS. Sessions that have ended are deleted whenever anyone signs in. `POST /api/sign-out` deletes the session the cookie names and clears the cookie (204). A session also stops working when its user is removed or given a new password.

*Default deny.* Before anything else, every request is checked. Only these pass without a session, compared exactly, path and method: `GET` of the sign-in page, `GET /styles.css`, `GET /sign-in.js`, and `POST /api/sign-in`. Every other request needs a session that exists and has not ended: without one, a request to an address under `/api/` gets 401 and `{"detail": "sign in first"}`, and anything else gets a 303 redirect to the sign-in page. This covers the API of every data type, the notifications, every page, `scripts.js`, every JSON file of records, `/`, FastAPI's own `/docs` and `/openapi.json`, and addresses that do not exist. Responses given with a session carry `Cache-Control: no-store`, so that the browser does not keep a copy of a page after signing out. With a session, `/` leads to the first page other than the sign-in page.

*The pages.* The sign-in page holds a form built from the four texts, with `autocomplete="username"` and `"current-password"`, and loads only `styles.css` and its own script, `sign-in.js`, so that `scripts.js` can need a session. It links to no other page, and no page links to it. On success the browser goes to `/`, and so to the first other page; on failure the developer's message is shown and the password box is emptied. A `signs out` button posts to `/api/sign-out` and then goes to `/`, and so to the sign-in page. In `scripts.js`, every request goes through `fetchSignedIn`, which leads to `/` when the server answers 401 or answered by redirecting. No words are added to any page.

*What it does not do.*

- There are no roles and no permissions per record: every user can do everything.
- There is no way to register, to change one's own password, or to reset a forgotten one, other than the commands above.
- A session lasts exactly 12 hours from signing in, whether or not it is used. There is no "remember me" and no ending a session after a time without use.
- The lock can be used against a user: anyone who knows a name can keep it locked by trying five wrong passwords every five minutes. There is no limit per address and no limit on attempts across many names.
- **It must be served over HTTPS for anything beyond the developer's own machine.** Over plain HTTP the password and the session cookie cross the network as they are. The generated server does not set up HTTPS itself; put it behind a server that does. The cookie is marked `Secure` only when the request reached the server as HTTPS, which behind such a server depends on it passing the scheme on (uvicorn reads `X-Forwarded-Proto` from addresses it trusts).
- Protection against requests from other sites rests on the cookie being `SameSite=Lax` and on the API accepting only JSON; there is no separate token for that, and other sites under the same registrable domain count as the same site.
- Each attempt to sign in takes about 16 MB of memory and tens of milliseconds of work, so a flood of attempts can slow the server or exhaust its memory.
- The time taken for a known name and an unknown one differs a little, by the time to store the counted attempt; the hash, which takes far longer, is worked out for both.
- Nothing is logged by the application, so failed attempts leave no trace other than the count.
- **The code is a draft that has not been reviewed by a person experienced in authentication.**

**What the generated server does not do.** These are fixed choices of the generator, and anyone who runs the server should know them.

- **Without `use authentication`, there is no authentication.** Anyone who can reach the server can read, add, change and delete every record. Run it only where that is acceptable, such as on your own machine.
- There is no limit on how many records are returned or how large a request may be.
- Two changes to the same record at the same moment are not reconciled; the last one wins.
- Changing a `data` declaration does not change a table that already exists. Delete the database file to start again.
- The pages can add records, and change and delete them in a table marked `editable`. There is no undo and no confirmation.
- Notifications are never removed; the table `notification` grows with every one.

To run it, from the generated folder: `python -m pip install -r requirements.txt`, then `python -m uvicorn server:app`.

**Decimals** are kept exactly as written, digits and all, so `24.50` stays `24.50`. In the JSON file they are written as text, so that no digit is lost; they are compared by value when sorting. A decimal may have at most 15 digits.

**Files.** All pages share one stylesheet, `styles.css`, which holds fixed rules for the elements that are used and one rule for each button width that is used. If any table fills, searches, sorts or is editable, or a button adds a record or signs out, or a page lists notifications, the pages other than the sign-in page also share `scripts.js`, which holds fixed code for the behaviours that are used. With authentication, the sign-in page loads `sign-in.js` instead. The colours, spacing and fonts are fixed choices of the generator.

**Opening the pages.** A table that fills itself reads its JSON file over the web, so the folder has to be served by a web server; opened directly from disk, browsers refuse the request and the table stays empty.

Text in double quotes is shown exactly as written; the characters `&`, `<` and `>` are escaped. No words are added that the developer did not write.

Some statements are recognised but cannot be built yet, and say so: other parts of an application (`use postgres`), and creating a service (`create postgres:` and `using docker`).

Free wording reads the lines of a page into the page blocks the classifier was trained on. `editable`, `notifications`, rules, `notify`, `use authentication`, `sign in` and `signs out` are read in standard phrases only: the blocks `edit-table-rows`, `notify-when`, `authentication`, `sign-in-form` and `sign-out-button` were added after the classifier was trained and it has not been taught them.

Known limits: the language of the page is not declared in the HTML; sorting text puts all capital letters before all small letters, as the order of text above says; when a table is filled again after a record is added, changed or deleted, the rows are shown in order of `id` and unfiltered, even if the reader had sorted the table or typed in its search box; a list of notifications is not filled again after a deletion or a change made elsewhere until the page is opened again; and a line of text longer than about 300 characters would be re-wrapped by the formatter used for criterion G6, which includes a rule whose condition holds long text, since it is written into `server.py`.

The live view's preview of an application with a server is the generated server itself, run on the developer's own machine in a temporary folder, so adding, changing, deleting and notifications work there as they will when it is built. Its database starts again from the records in the intent file whenever the data, the API or the rules change. With authentication, each new database of the preview is given one user, named `preview`, with a random password made when the live view starts; the note under the preview gives both, so that the developer can sign in there. The user is added, with the generated `server.py add-user` command, just before the preview server starts. `python -m cdipl run` starts with no user, and says how to add one. If `fastapi` and `uvicorn` are not installed, the preview imitates the API instead: it lists the records written in the intent file and no notifications, and nothing done in the preview is saved.
