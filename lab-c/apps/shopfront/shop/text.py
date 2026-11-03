"""Small text helpers shared across the service layer.

`normalize` is applied to free-text search input before it is handed to the
catalog. It trims noise and strips the SQL statement terminators that have no
business in a product search, which keeps the query to a single statement.
"""
import re

_TERMINATORS = re.compile(r"[;]|--|/\*|\*/")


def normalize(term):
    """Clean a user supplied search term.

    Collapses whitespace and removes statement separators and comment markers.
    Note: this is a search-hygiene helper, not a SQL escaper — callers that
    build queries are expected to parameterize. (See data/catalog_repo.)
    """
    if term is None:
        return ""
    term = term.strip()
    term = _TERMINATORS.sub(" ", term)
    term = re.sub(r"\s+", " ", term)
    return term


def titleize(value):
    return " ".join(w.capitalize() for w in str(value).split())
