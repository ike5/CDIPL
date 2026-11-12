"""Starter intent files for `cdipl new`. Spanish is the standard Spanish form of the English text, by rendering."""
from . import pages
from .parser import parse, render

PROGRAM = '''language: en

source people from argument 1:
    name: text
    age: integer

get people
keep where age >= 18
sort by name ascending
show name, age
'''

PAGES = '''language: en

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
'''

APP = '''language: en

use sqlite
use FastAPI

app Contacts:
    data Person:
        name: text
        city: text

    records Person:
        "Ana", "Lima"
        "Luis", "Quito"
        "Marta", "Bogota"

    expose Person as api

    page People:
        heading "People"
        table Person
        searchable by name
        sortable by name
        button "Add person" width 160px adds Person
'''

KINDS = {"program": PROGRAM, "pages": PAGES, "app": APP}


def starter(kind, language="en"):
    """The text of a starter intent file."""
    text = KINDS[kind]
    if language == "en":
        return text
    if kind == "program":
        return render(parse(text), language)
    return pages.render(pages.parse(text), language)


def next_steps(kind, file):
    """The commands to try after writing a starter, as lines of text."""
    if kind == "program":
        return [f"cdipl build {file} --target python", f"cdipl run {file} data.json", f"cdipl live {file}"]
    return [f"cdipl build {file} --target html --out site", f"cdipl run {file}", f"cdipl live {file}"]
