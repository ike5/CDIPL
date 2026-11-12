"""Code generators, one per target language."""
from . import c, html, java, javascript, python

TARGETS = {"python": python, "javascript": javascript, "c": c, "java": java}

__all__ = ["TARGETS", "c", "html", "java", "javascript", "python"]
