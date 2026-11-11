# Stage 1 program briefs

**Status:** drafted by the AI assistant, awaiting the product owner's approval. No program has been generated yet.

These are the 20 sample programs for Stage 1 of `PLAN.md` (the block inventory). Once the list is approved, the assistant generates each program, splits it into units, and records which units could be built entirely from reusable blocks and which contain logic particular to that program.

## How the list was chosen

- Ten programs for Python and ten for JavaScript, which are the first two targets.
- All are small scripts or tools of the kind developers write often. None uses a framework, because frameworks come later in the roadmap.
- The JavaScript half is split between programs that run in Node and programs that run in a browser page.
- The list is deliberately not limited to programs that suit a block library. P8, P9 and J10 are mostly logic particular to the program, and I expect them to be hard to express as blocks. Leaving such programs out would make the result look better than it should.

## Rules for every program

- One source file, using only the language's standard library (browser programs may use the standard browser APIs).
- Under about 150 lines.
- Inputs come from files or command-line arguments named in the brief. Output goes to the screen or to a named file.
- No network access unless the brief says so.

## Python

| ID | Kind | Brief |
|---|---|---|
| P1 | Data summary | Read a CSV file of sales records (region, product, amount). Print the total amount for each region, largest total first. |
| P2 | File system | Walk a folder and everything beneath it. Print the ten largest files with their sizes in readable units (KB, MB, GB). |
| P3 | Log analysis | Read a web server access log. Count requests by status code and by hour of day, and write both counts to a JSON file. |
| P4 | File renaming tool | Rename every file in a folder to a given prefix followed by a zero-padded number, keeping each file's extension. Offer a dry-run option that prints the changes without making them. |
| P5 | Download with retry | Fetch JSON from a web address given on the command line and save it to a file. Retry up to three times, waiting longer after each failure. Uses the network. |
| P6 | Configuration check | Check a JSON configuration file against a list of required keys and their expected types. Print every problem with the path to the key, and exit with an error status if any were found. |
| P7 | Comparing two tables | Read two CSV files that share a key column. Write a new CSV containing the rows whose key appears in the first file but not in the second. |
| P8 | Text conversion | Convert a plain-text file that uses `#` headings and `-` bullet lists into an HTML page. |
| P9 | Calculation | Given a loan amount, a yearly interest rate and a number of months, print a repayment table showing each month's payment, interest and remaining balance. |
| P10 | Duplicate finder | Find files in a folder that have identical contents, by comparing a hash of each file. Print each set of duplicates as a group. |

## JavaScript

| ID | Runs in | Kind | Brief |
|---|---|---|---|
| J1 | Node | Data pipeline | Read a JSON file containing a list of users. Keep those aged 18 or over, sort them by name, and print the first ten. This is the example from the proposal. |
| J2 | Node | Word count | Read a text file and print the twenty most frequent words with their counts, ignoring letter case and punctuation. |
| J3 | Browser | Form checking | On a sign-up form, check that required fields are filled, that the email address has a valid shape, and that the password is at least eight characters. Show a message beside each invalid field and prevent the form from being sent. |
| J4 | Browser | Table with search | Fetch a list of items from a web address and show it as a table. A text box above the table hides rows that do not contain what the user has typed. Uses the network. |
| J5 | Node | Small web server | A web server with no framework and two addresses: one returns the current time as JSON, the other returns whatever JSON was sent to it. |
| J6 | Browser | Countdown | Show the days, hours, minutes and seconds remaining until a given date, updating every second, and show a message when the date has passed. |
| J7 | Node | Combining files | Read every JSON file in a folder, each holding a list of records. Combine them into one list, drop records whose `id` has already been seen, and write the result to a new file. |
| J8 | Browser | To-do list | A list where the user can add an item, mark it done and delete it. The list is saved in the browser so that it is still there after the page is reloaded. |
| J9 | Node | Format conversion | Convert a CSV file to JSON or a JSON file to CSV, deciding the direction from the input file's extension. |
| J10 | Node | Game | Tic-tac-toe for two players in the terminal. Players take turns entering a square; the program detects a win or a draw. |

## To approve

Reply with "approved", or name the briefs to change, remove or add. The count should stay at ten per language so that the two halves are comparable.
