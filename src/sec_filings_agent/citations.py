"""Deterministic citation verification — the piece that makes grounding count.

No LLM call here. A citation is only valid if it appears, literally (after
normalizing whitespace and case), in the source text. It's this function —
not the model's good behavior — that guarantees a reported change wasn't
invented.
"""

import re


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def is_valid_citation(citation: str, source_text: str) -> bool:
    if not citation.strip():
        return False
    return _normalize(citation) in _normalize(source_text)
