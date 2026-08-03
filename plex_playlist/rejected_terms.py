from __future__ import annotations

from collections.abc import Iterable
import re

from plex_playlist.normalization import fold_unicode


_NON_WORD_RE = re.compile(r"[^\w\s]")
_MULTI_SPACE_RE = re.compile(r"\s+")


def _normalize_rejected_text(value: str) -> str:
    folded = fold_unicode(str(value or ""))
    without_punctuation = _NON_WORD_RE.sub(" ", folded)
    return _MULTI_SPACE_RE.sub(" ", without_punctuation).strip()


def parse_rejected_terms(value: str | Iterable[str] | None) -> tuple[str, ...]:
    """Return unique, normalized rejected terms in configured order."""
    if value is None:
        return ()

    raw_values = value.split(",") if isinstance(value, str) else value
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in raw_values:
        term = _normalize_rejected_text(str(raw or ""))
        if term and term not in seen:
            seen.add(term)
            normalized.append(term)
    return tuple(normalized)


def _contains_normalized_term(value: str, term: str) -> bool:
    normalized_value = _normalize_rejected_text(value or "")
    if not normalized_value or not term:
        return False
    return f" {term} " in f" {normalized_value} "


def rejected_term_reason(
    *,
    title: str = "",
    album: str = "",
    version: str = "",
    rejected_terms: Iterable[str] | None = None,
) -> str | None:
    """Return a field-specific rejection reason, or ``None`` when eligible."""
    terms = parse_rejected_terms(rejected_terms)
    if not terms:
        return None

    fields = (
        ("track title", title),
        ("album title", album),
        ("version metadata", version),
    )
    for field_name, value in fields:
        for term in terms:
            if _contains_normalized_term(value, term):
                return f"rejected term '{term}' found in {field_name}"
    return None
