"""Extraction of the Item 1A (Risk Factors) section from a 10-K's text.

The "Item 1A" marker alone appears several times in a real 10-K: in the table
of contents, in narrative cross-references ("...discussed in Item 1A of this
10-K under the heading 'Risk Factors'..."), and in the section's real
heading. Two earlier versions of this heuristic ("occurrence with the most
text up to the next item marker") broke against a real Apple 10-K — one
cross-reference inside the MD&A had no end marker after it (turning into
"the rest of the document"); another cross-reference, near the start of the
document, had the real Item 1B much later, creating a huge span that
included the entire table of contents plus the real section.

The fix: require "Risk Factors" right after "Item 1A" in the start marker.
A narrative cross-reference never has that exact placement — only the table
of contents ("Item 1A. Risk Factors  5") and the real heading do. Between
those two, the one with the largest span up to the next item is the real one
(the table-of-contents one is short).
"""

import re

from bs4 import BeautifulSoup

_START_MARKER = re.compile(r"item\s*1a\.?\s*ris\s?k\s*factors", re.IGNORECASE)
_END_MARKERS = re.compile(r"item\s*1b\b|item\s*2\b", re.IGNORECASE)

_MIN_LENGTH = 500
_MAX_LENGTH = 100_000


class SectionNotFound(Exception):
    """No occurrence of "Item 1A" has enough text to be the real section."""


def html_to_text(html: str) -> str:
    """A filing's HTML, collapsed to plain text with normalized whitespace."""
    text = BeautifulSoup(html, "html.parser").get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()


def extract_item_1a(plain_text: str) -> str:
    """`plain_text` should already come from `html_to_text`."""
    starts = [m.end() for m in _START_MARKER.finditer(plain_text)]
    if not starts:
        raise SectionNotFound("no occurrence of 'Item 1A' in the document")

    candidates = []
    for start in starts:
        end_match = _END_MARKERS.search(plain_text, start)
        if end_match is None:
            continue  # no end marker, not the real section — see docstring
        candidates.append((end_match.start() - start, start, end_match.start()))

    if not candidates:
        raise SectionNotFound("no occurrence of 'Item 1A' has an end marker after it")

    length, start, end = max(candidates)
    if length < _MIN_LENGTH:
        raise SectionNotFound(
            "no occurrence of 'Item 1A' has enough text to be the real section"
        )

    return plain_text[start:end].strip()[:_MAX_LENGTH]
