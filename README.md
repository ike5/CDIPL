# CDIPL

CDIPL is a compiler. You write what a program or a small web application should do, called intent, in a plain text file in English or Spanish. CDIPL builds the program from blocks of code that were written beforehand: a program in Python, JavaScript, C or Java, or an application made of HTML, CSS and JavaScript pages, optionally with a FastAPI server over a SQLite database and with signing in. No AI model writes code when you build: the same intent gives the same files every time. The generated code can be converted back to intent, and a live view shows your intent beside the exact files it produces.

CDIPL is early. Only a part of the block catalogue is built (see [What is not built yet](#what-is-not-built-yet)), and no developer other than its authors has used it.

## Install

You need Python 3.13 or 3.14. The compiler uses only the standard library.

```bash
git clone <this repository> && cd CDIPL
python -m venv .venv && . .venv/bin/activate
pip install -e .
```

This gives you the `cdipl` command (`python -m cdipl` also works). A generated server needs FastAPI and uvicorn, which are optional:

```bash
pip install -e ".[server]"     # fastapi and uvicorn, the versions the server was tested with
pip install -e ".[dev]"        # the above, plus ruff and httpx, for running all the tests
```

## A two-minute tour

Write a starter intent file. The kinds are `program` (the default), `pages` and `app`:

```console
$ cdipl new people.intent
wrote people.intent
next:
    cdipl build people.intent --target python
    cdipl run people.intent data.json
    cdipl live people.intent
```

```
language: en

source people from argument 1:
    name: text
    age: integer

get people
keep where age >= 18
sort by name ascending
show name, age
```

`cdipl new` will not overwrite a file that exists. Build it:

```console
$ cdipl build people.intent --target python --out out
wrote out/main.py
wrote out/trace.json
note: 10 block(s) used are drafts awaiting human review: cli-options, read-text-file, parse-json, check-list-of-records, exit-on-error, check-required-types, filter-rows, sort-rows, print-table, print-message
```

`out/main.py` is a complete Python program that depends on nothing from CDIPL. The same file builds as JavaScript, C or Java with `--target javascript`, `--target c` or `--target java`, and the four programs behave identically: the same output and the same exit status for the same input. `cdipl run --target c people.intent people.json` builds and runs in one step (C needs `gcc`, Java needs `javac` and `java`). `out/trace.json` records which block each line came from. Without `--out`, files go to `build/<target>` beside the intent file.

Run it. This program reads a JSON file given as its first argument:

```console
$ echo '[{"name":"Zoe","age":30},{"name":"Al","age":9},{"name":"Bo","age":20}]' > people.json
$ python out/main.py people.json
Bo   20
Zoe  30
```

`cdipl run` does the build into a temporary folder and runs the result in one step, passes the arguments to the program and exits with the program's status:

```console
$ cdipl run people.intent people.json
Bo   20
Zoe  30
```

Convert generated code back to intent, in either language:

```console
$ cdipl lift out/main.py --language es
idioma: es

fuente people desde argumento 1:
    name: texto
    age: entero

obtener people
conservar donde age >= 18
ordenar por name ascendente
mostrar name, age
```

`lift` refuses a file that differs from what the compiler would generate for any intent, so a hand-edited file is either recovered exactly or refused.

Open the live view:

```console
$ cdipl live people.intent
Live view for people.intent: http://127.0.0.1:8765/  (Ctrl+C to stop)
```

Open that address in a browser. The intent is on the left and the generated files are on the right. Each statement is marked with how it was read, and saving rewrites the file in standard phrases. The view is served from your machine only.

Two more commands: `cdipl explain FILE` lists which block each statement was read as and its review status, and `cdipl affected BLOCK FOLDER` lists the intent files under a folder that use a block.

## Three examples

### A program

The example above is a program: a source with typed fields, then steps. The generated `out/main.py` is about 100 lines. It reads the file, checks it is a JSON list of records with the declared fields, then does the steps:

```python
def main():
    text = read_text_file(read_argument(1))
    records = check_list(parse_json(text))
    rows = require_valid(records)
    rows = [row for row in rows if row["age"] >= 18]
    rows = sorted(rows, key=lambda row: row["name"])
    show_table(rows, ["name", "age"])
```

The meaning of every statement is in [docs/meaning.md](docs/meaning.md).

### Pages

```console
$ cdipl new site.intent --kind pages
$ cdipl run site.intent
open http://127.0.0.1:8000/people.html  (stop with Ctrl+C)
```

```
language: en

app Contacts:
    data Person:
        name: text
        city: text

    records Person:
        "Ana", "Lima"
        "Luis", "Quito"
        "Marta", "Bogota"

    page People:
        heading "People"
        table Person
        searchable by name
        sortable by name
```

`cdipl build site.intent --target html --out site` writes `people.html`, `styles.css`, `scripts.js`, `person.json` (the records) and `trace.json`. The page loads `person.json` with `fetch`, so it has to be served over HTTP rather than opened as a file; `cdipl run` does that with Python's `http.server`, on 127.0.0.1 only. Use `--port` to change the port (put it before the file name: `cdipl run --port 9000 site.intent`). The table in the page is filled by `scripts.js`, and the search box and the sortable column heading are in `people.html`:

```html
<label>name <input type="search" data-search="Person" data-field="name" /></label>
<table data-name="Person" data-source="person.json">
  <thead>
    <tr>
      <th scope="col"><button type="button" data-sort="name">name</button></th>
      <th scope="col">city</th>
    </tr>
  </thead>
  <tbody></tbody>
</table>
```

### An application with a server

```console
$ pip install -e ".[server]"
$ cdipl new shop.intent --kind app
$ cdipl run shop.intent
open http://127.0.0.1:8000/  (stop with Ctrl+C)
```

This is the pages example plus three things: `use sqlite` and `use FastAPI` at the top, `expose Person as api` in the application, and a button on the page, `button "Add person" width 160px adds Person`. `cdipl build shop.intent --target html --out shop` writes `server.py`, `requirements.txt`, the records and a `static/` folder with the pages. The server serves the pages, redirects `/` to the first page, and has an API over a SQLite table: listing, adding, changing and deleting records. With the server running, `GET /api/person` returns:

```
[{"id":1,"name":"Ana","city":"Lima"},{"id":2,"name":"Luis","city":"Quito"},{"id":3,"name":"Marta","city":"Bogota"}]
```

`cdipl run` builds into a temporary folder, so the SQLite database is deleted when you stop it. To keep records, build to a folder with `--out`, then run `python -m uvicorn server:app` inside it.

If FastAPI or uvicorn is missing, `cdipl run` says so and tells you to run `pip install "cdipl[server]"`.

### Editing, rules and signing in

`examples/inventory_server.intent` adds two things to an application. `editable` under a table gives each row a control to change it and one to delete it. A rule stores a notification whenever a record that is added or changed meets its condition, and `notifications` lists them on a page:

```
    page Products:
        table Product
        editable
        notifications

    when Product.stock < 5:
        notify inventory_manager
```

`examples/inventory_auth.intent` adds `use authentication`. Nothing can then be reached without signing in, except the page that holds the sign-in form, which you write yourself, with your own words for the two boxes, the button and the message for a wrong password:

```
use sqlite
use FastAPI
use authentication

app Inventory:
    page Welcome:
        heading "Inventory"
        sign in "Name" "Password" "Sign in" "Wrong name or password"

    page Products:
        table Product
        button "Sign out" signs out
```

There is no default account. Build to a folder and add a user there; the password is asked for and never written anywhere:

```console
$ cdipl build examples/inventory_auth.intent --target html --out shop
$ cd shop
$ python server.py add-user ana
$ python -m uvicorn server:app
```

`set-password NAME`, `remove-user NAME` and `list-users` are the other commands. In the live view the preview is the real server, and a user is made up for it; the name and password are shown under the text.

## Writing in Spanish

Start a file in Spanish with `--language es`, or give `idioma: es` as the first line. Every command that reads or writes intent works in both languages, and the same program in the two languages builds identical code.

```console
$ cdipl new sitio.intent --kind pages --language es
```

```
idioma: es

aplicación Contacts:
    datos Person:
        name: texto
        city: texto

    registros Person:
        "Ana", "Lima"
        "Luis", "Quito"
        "Marta", "Bogota"

    página People:
        encabezado "People"
        tabla Person
        buscable por name
        ordenable por name
```

The starter files use English names for data and fields in both languages. You can use any names you like.

## Free wording, and statements that are not understood

You do not have to use the standard phrases. A statement worded freely is turned into one of the blocks by word lists and a small classifier, using fixed rules and no AI model at build time. For example, this builds the same program as the standard phrases above:

```
get people
drop the malformed rows
only keep the rows where age >= 18
sort them by name, highest first
show name, age
```

`cdipl explain` shows how each line was read (`chosen by the classifier`, `standard phrase`, or `chosen by the developer`). The choice is recorded in an index file beside the intent file (`people.index.json`), so the same line gives the same block next time.

When a statement is not understood, the build stops and names the line and the reason. Adding the line `frobnicate everything` gives:

```console
$ cdipl build free.intent --target python --out out
free.intent:11: not understood: 'frobnicate' is not in the word list. Reword the statement, or record the block you mean with the choose command.
```

`cdipl choose FILE LINE` lists the closest blocks for a line, and `cdipl choose FILE LINE --block NAME` records your choice in the index. The live view reports on every statement in the file and does not stop at the first problem.

The classifier is not reliable enough to trust unseen wording unattended: on 360 wordings per language that it had not seen, it chose the wrong block for 3 in each language and declined to choose for 114 in English and 86 in Spanish. Declining is the safe outcome; a wrong choice is not, which is why you can check every choice with `explain`. The full result is in `stage2/classifier_result.md`.

## What is not built yet

- Only part of the block catalogue is implemented (37 of 108 blocks), and every implemented block is a draft until a person reviews it. A build prints a note listing the drafts it used.
- The targets are Python, JavaScript, C and Java for programs, and HTML, CSS and JavaScript (with FastAPI and SQLite) for applications.
- Understood but not built: `use postgres`, `create postgres:` with `using docker`, and any other `use`. Django and React are not started.
- A rule stores a notification that a page can list. Nothing is delivered to a person.
- Free wording covers the statements of a program and the common lines of a page. `use`, `expose`, buttons with an action, `editable`, `notifications`, rules and the sign-in element are read in their fixed form only.
- **Without `use authentication`, the generated server lets anyone who can reach it read and change every record.** Run it only on your own machine. `cdipl run` listens on 127.0.0.1 for this reason.
- **With `use authentication`, the protecting code is a draft that no person experienced in authentication has reviewed.** Its limits are listed in [docs/meaning.md](docs/meaning.md). Put it behind HTTPS and have it reviewed before using it for anything beyond your own machine.

The details and the open decisions are in `PLAN.md`.

## Reference and results

- [docs/meaning.md](docs/meaning.md): what each statement means, independently of any target language.
- `PLAN.md`: the plan and the product owner's decisions.
- `stage1/inventory.md`: the Stage 1 result, a study of 20 sample programs that the block catalogue came from.
- `stage2/classifier_result.md`: the result of testing the classifier on wording it had not seen.

## Tests

```bash
pip install -e ".[dev]"
python -m unittest discover -s tests -t .
```

The tests need `node`, `gcc`, `javac` and `java` on the path, to run the generated JavaScript, C and Java. The formatter and linter tests are skipped, and reported as skipped, unless `ruff` and some JavaScript tools are installed; `tests/README.md` lists what each test file checks and which tools it uses.
