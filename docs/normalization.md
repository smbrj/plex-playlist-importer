# Normalization Subsystem

**Document Version:** 1.0  
**Status:** Approved  
**Last Updated:** 2026-07-21  
**Primary Audience:** Developers  
**Depends On:** parser.md  
**Related Documents:** matching.md, aliases.md, search_index.md  
**Snapshot:** 006

---

# 1. Purpose and Scope

The normalization subsystem converts artist, title, album, and related text into stable comparison forms used by the Plex Playlist Importer.

Its purpose is to reduce superficial metadata differences that would otherwise interfere with matching.

Examples include differences in letter case, Unicode accents, quotation marks, dash variants, punctuation, repeated whitespace, common recording/version metadata, artist collaboration text, and alias-equivalent artist names.

Normalization allows text that is visually or semantically equivalent to compare more reliably.

The subsystem is implemented in:

```text
plex_playlist/normalization.py
```

The normalization layer is deterministic and intended to preserve as much useful meaning as possible while removing comparison noise.

---

# 2. Responsibilities

The normalization subsystem is responsible for Unicode folding, case folding, accent removal, common Unicode character translation, punctuation handling, whitespace normalization, selective metadata-noise removal, artist/title/album normalization, recording-version classification, title-token generation, compact comparison-key generation, and alias-aware artist keys.

It is not responsible for parsing source files, fuzzy scoring, match acceptance, maintaining alias files, playlist modification, Lidarr acquisition, or XMPlaylist ingestion.

---

# 3. Normalization Philosophy

The normalization subsystem follows two general principles:

> Remove formatting and metadata differences that should not prevent matching.

> Preserve meaningful words whenever possible.

This is why the implementation selectively removes known recording/version metadata rather than blindly discarding all parenthetical text.

---

# 4. Public Normalization Functions

The primary normalization API currently includes:

```text
normalize_text()
normalize_artist()
normalize_title()
normalize_album()
classify_version()
title_tokens()
fold_unicode()
normalize_key()
canonical_artist_key()
artist_lookup_names()
```

---

# 5. Unicode Folding

The foundational Unicode function is:

```python
fold_unicode(value)
```

It translates selected Unicode punctuation and special letters, applies NFKD decomposition, removes combining marks, and applies `casefold()`.

Examples include:

```text
Beyoncé -> beyonce
Mötley Crüe -> motley crue
What’s Going On -> what's going on
```

---

# 6. Unicode Character Translation

Curly apostrophes and quotation marks are converted to straight equivalents. Several Unicode dash characters are converted to `-`.

Special letter mappings include:

```text
æ -> ae
œ -> oe
ø -> o
ł -> l
đ -> d
ð -> d
þ -> th
ß -> ss
```

A non-breaking space is converted to a regular space.

---

# 7. Case Normalization

`fold_unicode()` applies `casefold()` rather than simple lowercase conversion.

Original display metadata is preserved in source models; normalization creates derived comparison forms.

---

# 8. General Text Normalization

General-purpose normalization is provided by:

```python
normalize_text(value)
```

Processing sequence:

```text
Input Text
    |
    v
Unicode Folding
    |
    v
Trim
    |
    v
Remove Selected Noise Phrases
    |
    v
Replace Punctuation with Spaces
    |
    v
Collapse Multiple Spaces
    |
    v
Trim
```

---

# 9. Punctuation and Whitespace

General normalization replaces punctuation with spaces so neighboring words do not accidentally merge.

Repeated whitespace is collapsed to one space, and leading/trailing whitespace is removed.

---

# 10. Noise Phrase Removal

Current standalone noise phrases include:

```text
remastered
remaster
album version
radio edit
explicit
clean
original mix
live
```

These phrases are removed case-insensitively.

---

# 11. Selective Parenthetical Noise Removal

Parenthetical text is removed when it contains known recording/version indicators such as:

```text
remaster
remastered
remix
mono
stereo
live
edit
version
deluxe
explicit
clean
```

The implementation intentionally does not remove every parenthetical phrase indiscriminately.

---

# 12. Artist Normalization

Artist-specific normalization is provided by:

```python
normalize_artist(value)
```

It first applies general normalization and then removes collaboration suffixes beginning with whole-word matches for:

```text
feat
ft
featuring
```

The removal extends through the remainder of the artist string.

---

# 13. Title Normalization

Title-specific normalization is provided by:

```python
normalize_title(value)
```

The current sequence is Unicode folding, selected noise removal, conversion of non-word characters to spaces, underscore-to-space conversion, and whitespace collapsing.

---

# 14. Album Normalization

Album normalization is provided by:

```python
normalize_album(value)
```

It currently delegates directly to `normalize_text(value)`.

---

# 15. Compact Comparison Keys

The subsystem provides:

```python
normalize_key(value)
```

for compact comparison and indexing.

Unlike `normalize_text()`, this function removes punctuation, whitespace, and underscores entirely.

Example:

```text
The Doobie Brothers -> thedoobiebrothers
```

---

# 16. Recording-Version Classification

Recording/version classification is provided by:

```python
classify_version(title)
```

Recognized classes include:

```text
live
remaster
mono
stereo
single
album
acoustic
demo
alternate
instrumental
radio
extended
edit
```

If no recognized version marker is found, `studio` is returned.

Classification order follows the insertion order of `VERSION_PATTERNS`.

---

# 17. Relationship to Preferred Versions

Normalization provides `classify_version()` to identify recording type.

Matching configuration determines preference among version classes through `preferred_versions`.

---

# 18. Title Tokens

Title-token generation is provided by:

```python
title_tokens(value)
```

The function normalizes the title, splits it into words, removes stopwords, removes duplicates, sorts the tokens, and returns a stable tuple.

Current stopwords are:

```text
a
an
the
```

Title tokens are used for candidate discovery, not final match acceptance.

---

# 19. Alias-Aware Canonical Artist Keys

Alias-aware artist resolution is provided by:

```python
canonical_artist_key(value, aliases)
```

The function creates a normalized compact artist key and compares it against normalized alias and canonical names.

If the requested artist matches either an alias or canonical key, the canonical key is returned.

---

# 20. Artist Lookup Names

The subsystem provides:

```python
artist_lookup_names(value, aliases)
```

This expands an artist into the requested name, canonical name, and aliases representing the same canonical artist.

---

# 21. Original Metadata Preservation

Normalization does not replace the original artist/title text stored in `PlaylistEntry` or `LibraryTrack`.

Normalized forms are derived values used for comparison and lookup.

---

# 22. Caching of Normalization Results

Most normalization functions use `functools.lru_cache`.

Current cache-size limits include 100,000 and 200,000 entries depending on the function.

This reduces repeated normalization work across large music libraries.

---

# 23. Determinism

Normalization is deterministic.

Given the same input string and function, the same normalized result should be produced.

---

# 24. Relationship to Parser

The parser performs structural cleanup.

Normalization performs semantic comparison cleanup afterward.

---

# 25. Relationship to Search Index

Normalization provides indexing-oriented functions including:

```text
normalize_key()
title_tokens()
canonical_artist_key()
artist_lookup_names()
```

Detailed index behavior belongs in `search_index.md`.

---

# 26. Relationship to Matching

The matcher relies on normalized representations so superficial formatting differences do not dominate fuzzy scores.

Normalization prepares the data. Matching determines whether a candidate is acceptable.

---

# 27. Relationship to Alias Handling

Normalization handles superficial textual variation.

Alias logic handles known semantic equivalence.

The two mechanisms cooperate while remaining separate responsibilities.

---

# 28. Loss-Minimizing Design

The module describes normalization as deterministic and loss-minimizing.

The subsystem should remove comparison noise without unnecessarily destroying information that could distinguish genuinely different tracks.

---

# 29. Current Test Coverage

No dedicated normalization test module exists in the current uploaded test suite.

None of the current tests directly reference the public normalization functions.

Therefore, direct unit-test coverage for normalization behavior is currently absent or at least not explicitly represented in the existing test suite.

---

# 30. Normalization Test Gap

The lack of dedicated normalization tests is significant because normalization directly affects matching behavior.

Functions that should have explicit unit coverage include:

```text
fold_unicode()
normalize_text()
normalize_artist()
normalize_title()
normalize_album()
normalize_key()
classify_version()
title_tokens()
canonical_artist_key()
artist_lookup_names()
```

---

# 31. Recommended Future Unit Tests

Future normalization tests should cover Unicode folding, special-letter mappings, punctuation, whitespace, featured-artist stripping, recording-noise handling, parenthetical behavior, version classification, title-token behavior, and alias-aware canonical keys.

---

# 32. Post-Documentation Technical Review Candidates

## 32.1 Add Dedicated Normalization Unit Tests

A dedicated:

```text
tests/test_normalization.py
```

should be added during post-documentation technical cleanup.

## 32.2 Review Unused Patterns and Constants

The module currently defines `PAREN_RE`, but the reviewed implementation does not appear to use it.

## 32.3 Review Commented Placeholder Logic

`normalize_title()` contains comments referring to selective parenthetical/noise removal and should be reviewed for stale wording.

## 32.4 Review Noise-Phrase Breadth

Some phrases, such as `live`, are removed broadly and should be protected by representative regression tests.

## 32.5 Review Alias-Key Efficiency

A future implementation could precompute normalized alias maps if alias volume grows substantially.

---

# 33. Future Considerations

Potential future improvements include dedicated normalization unit tests, expanded Unicode regression coverage, more explicit handling of edge-case recording metadata, review of unused patterns/constants, cleanup of stale implementation comments, and precomputed alias normalization maps if needed for performance.

Future changes should preserve the guiding rule:

> Normalize enough to remove superficial metadata differences, but preserve enough information to distinguish genuinely different music.
