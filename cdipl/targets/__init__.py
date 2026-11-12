"""Code generators, one per target language."""
from . import html, javascript, python

TARGETS = {"python": python, "javascript": javascript}

__all__ = ["TARGETS", "html", "javascript", "python"]
