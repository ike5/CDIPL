"""Code generators, one per target language."""
from . import c, html, javascript, python

TARGETS = {"python": python, "javascript": javascript, "c": c}

__all__ = ["TARGETS", "c", "html", "javascript", "python"]
