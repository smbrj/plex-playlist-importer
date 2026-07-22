"""
Normalization utilities for Plex Playlist Manager (V2).

This module ensures consistent string representation across:
- playlist input
- Plex library metadata
- matching engine
- future Lidarr integration

Normalization is deterministic and loss-minimizing.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache


# ============================================================
# Precompiled patterns (performance critical)
# ============================================================

PUNCTUATION_RE = re.compile(r"[^\w\s]")
MULTISPACE_RE = re.compile(r"\s+")
FEAT_RE = re.compile(r"\b(feat|ft|featuring)\b.*$", re.IGNORECASE)
PAREN_RE = re.compile(r"(\([^)]*\)|\[[^\]]*\])")
PAREN_NOISE_RE = re.compile(
    r"""
    \(
        [^)]*
        (
            remaster(?:ed)? |
            remix |
            mono |
            stereo |
            live |
            edit |
            version |
            deluxe |
            explicit |
            clean
        )
        [^)]*
    \)
    """,
    re.IGNORECASE | re.VERBOSE,
)

NOISE_WORDS = {
    "remastered",
    "remaster",
    "album version",
    "radio edit",
    "explicit",
    "clean",
    "original mix",
    "live",
}

TITLE_TOKEN_STOPWORDS = {
    "a",
    "an",
    "the",
}

VERSION_PATTERNS = {
    "live": [
        r"\blive\b",
        r"live at",
        r"in concert",
        r"concert",
    ],
    "remaster": [
        r"remaster",
        r"remastered",
    ],
    "mono": [
        r"\bmono\b",
        r"mono mix",
    ],
    "stereo": [
        r"\bstereo\b",
        r"stereo mix",
    ],
    "single": [
        r"single version",
        r"single edit",
    ],
    "album": [
        r"album version",
    ],
    "acoustic": [
        r"acoustic",
        r"unplugged",
    ],
    "demo": [
        r"\bdemo\b",
    ],
    "alternate": [
        r"alternate",
        r"take \d+",
        r"session",
    ],
    "instrumental": [
        r"instrumental",
    ],
    "radio": [
    r"radio edit",
    r"radio version",
    ],
    "extended": [
        r"extended",
        r"12['\"]?\s*version",
        r"club mix",
    ],
    "edit": [
        r"\bedit\b",
    ],
}

_UNICODE_TRANSLATION = str.maketrans({
    # Apostrophes and quotation marks
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201b": "'",
    "\u2032": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',

    # Dashes
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",

    # Common letters that do not always decompose
    "æ": "ae",
    "Æ": "AE",
    "œ": "oe",
    "Œ": "OE",
    "ø": "o",
    "Ø": "O",
    "ł": "l",
    "Ł": "L",
    "đ": "d",
    "Đ": "D",
    "ð": "d",
    "Ð": "D",
    "þ": "th",
    "Þ": "TH",
    "ß": "ss",

    # Miscellaneous spacing
    "\u00a0": " ",
})

# ============================================================
# Public API
# ============================================================

@lru_cache(maxsize=100_000)
def normalize_text(value: str) -> str:
    """
    General-purpose normalization for artist, title, album, etc.
    """

    if not value:
        return ""

    value = fold_unicode(value).strip()

    value = _remove_noise_phrases(value)
    value = PUNCTUATION_RE.sub(" ", value)
    value = MULTISPACE_RE.sub(" ", value)

    return value.strip()


@lru_cache(maxsize=100_000)
def normalize_artist(value: str) -> str:
    """
    Artist-specific normalization.
    Slightly more aggressive than generic text normalization.
    """

    value = normalize_text(value)

    # Remove common collaboration noise
    value = FEAT_RE.sub("", value).strip()

    return value


def _remove_title_noise(value: str) -> str:
    """
    Remove common recording/version metadata while preserving
    meaningful title text.
    """

    return _remove_noise_phrases(value)

@lru_cache(maxsize=200_000)
def normalize_title(value: str) -> str:
    """
    Normalize a title while preserving word boundaries for fuzzy and
    token-based comparison.
    """

    text = fold_unicode(value)

    #
    # Keep your existing selective parenthetical/noise removal here.
    #
    # Example:
    # text = _NOISE_PARENTHESES_PATTERN.sub(" ", text)
    #

    text = _remove_title_noise(text)

    #
    # Convert remaining punctuation to spaces, preserving tokens.
    #

    text = re.sub(
        r"[^\w]+",
        " ",
        text,
        flags=re.UNICODE,
    )

    text = text.replace("_", " ")

    return " ".join(text.split())


@lru_cache(maxsize=100_000)
def normalize_album(value: str) -> str:
    """
    Album normalization.
    """

    return normalize_text(value)

@lru_cache(maxsize=100_000)
def classify_version(title: str) -> str:
    """
    Classify a track recording/version type from its title.

    Defaults to 'studio' when no version markers are found.
    """

    if not title:
        return "studio"

    value = fold_unicode(title).strip()

    for version, patterns in VERSION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, value, flags=re.IGNORECASE):
                return version

    return "studio"
    
@lru_cache(maxsize=100_000)
def title_tokens(value: str) -> tuple[str, ...]:
    """
    Produce stable, unique tokens for title candidate lookup.

    This is used for candidate discovery only. Final acceptance still
    depends on title gating and weighted scoring.
    """

    normalized = normalize_title(value)

    if not normalized:
        return ()

    tokens = {
        token
        for token in normalized.split()
        if token not in TITLE_TOKEN_STOPWORDS
    }

    return tuple(sorted(tokens))

@lru_cache(maxsize=200_000)
def fold_unicode(value: str) -> str:
    """
    Normalize Unicode for matching while preserving original display text.

    Examples:
        Beyoncé      -> beyonce
        Mötley Crüe  -> motley crue
        What’s Going On -> what's going on
    """

    if not value:
        return ""

    text = str(value).translate(_UNICODE_TRANSLATION)

    #
    # NFKD separates accented characters into a base character plus
    # combining marks.
    #

    text = unicodedata.normalize("NFKD", text)

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    return text.casefold()


# ============================================================
# Internal helpers
# ============================================================




def _remove_noise_phrases(value: str) -> str:
    """
    Remove common music metadata noise while preserving
    meaningful title text.
    """

    #
    # Remove only metadata parentheses.
    #

    value = PAREN_NOISE_RE.sub("", value)

    #
    # Remove standalone noise phrases.
    #

    for noise in NOISE_WORDS:
        # Standalone version/metadata words are only noise when they appear
        # as trailing metadata. Removing them globally corrupts legitimate
        # titles such as "Live and Let Die" and "Clean Up Woman".
        value = re.sub(
            rf"(?:\s*[-–—:]\s*|\s+)\b{re.escape(noise)}\b\s*$",
            "",
            value,
            flags=re.IGNORECASE,
        )

    return value.strip()


# ============================================================
# Key utility for indexing
# ============================================================

@lru_cache(maxsize=200_000)
def normalize_key(value: str) -> str:
    """
    Produce a compact comparison/index key.
    """

    text = fold_unicode(value)

    #
    # Keep Unicode letters and numbers, but remove punctuation,
    # whitespace, and underscores.
    #

    text = re.sub(
        r"[\W_]+",
        "",
        text,
        flags=re.UNICODE,
    )

    return text

def canonical_artist_key(
    value: str,
    aliases: dict[str, str],
) -> str:
    """
    Resolve an artist name to its normalized canonical key.
    """

    artist_key = normalize_key(value)

    if not artist_key:
        return ""

    for alias, canonical in aliases.items():
        alias_key = normalize_key(alias)
        canonical_key = normalize_key(canonical)

        if artist_key == alias_key:
            return canonical_key

        if artist_key == canonical_key:
            return canonical_key

    return artist_key


def artist_lookup_names(
    value: str,
    aliases: dict[str, str],
) -> tuple[str, ...]:
    """
    Return all artist names that may represent the same artist.

    Includes:
      - requested name
      - canonical name
      - aliases pointing to the same canonical artist
    """

    requested_key = canonical_artist_key(
        value,
        aliases,
    )

    names: dict[str, str] = {
        normalize_key(value): value,
    }

    for alias, canonical in aliases.items():
        if canonical_artist_key(alias, aliases) == requested_key:
            names.setdefault(normalize_key(alias), alias)
            names.setdefault(normalize_key(canonical), canonical)

    return tuple(names.values())   