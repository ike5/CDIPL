"""Code generators, one per target language."""
from . import javascript, python

TARGETS = {"python": python, "javascript": javascript}
