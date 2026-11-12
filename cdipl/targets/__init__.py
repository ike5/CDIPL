"""Code generators, one per target language."""
from . import html, java, javascript, python

TARGETS = {"python": python, "javascript": javascript}
TARGETS["java"] = java

__all__ = ["TARGETS", "html", "javascript", "python"]
