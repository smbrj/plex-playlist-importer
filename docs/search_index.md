# Search Index Subsystem

**Document Version:** 1.0  
**Status:** Approved  
**Last Updated:** 2026-07-21  
**Primary Audience:** Developers  
**Depends On:** normalization.md  
**Related Documents:** matching.md, cache.md, aliases.md  
**Snapshot:** 007

---

# 1. Purpose and Scope

The Search Index subsystem organizes Plex library tracks into in-memory lookup structures that allow the matcher to retrieve plausible candidates efficiently.

It is implemented in:

```text
plex_playlist/search_index.py
```

Its primary responsibilities are to build fast lookup structures from `LibraryTrack` records; index tracks by normalized artist, title, album, combined artist/title, title tokens, and GUID; preserve duplicate logical tracks; and provide candidate-discovery methods used by the matcher.

The Search Index does not decide whether a candidate is an acceptable match, perform final fuzzy scoring, apply confidence labels, modify Plex, parse playlist files, or persist itself independently to disk.

The central design principle is:

> The matcher should search an indexed representation of the Plex library rather than repeatedly scanning the full track collection.

---

# 2. Search Index Role

A large Plex library may contain tens of thousands of tracks.

Searching the raw list repeatedly for every requested playlist entry would require repeated full-library scans.

Instead, the Search Index creates lookup structures once and reuses them throughout the matching session.

---

# 3. SearchIndex Model

The current fields are:

```text
all_tracks
by_artist
by_title
by_title_token
by_album
by_artist_title
by_guid
```

Most index maps return `list[LibraryTrack]` rather than a single track because multiple copies or versions of the same logical song are common.

---

# 4. Source Data

The Search Index is built from `LibraryTrack` objects defined in `models.py`.

Relevant metadata includes rating key, GUID, artist, album artist, album, title, duration, year, version, and file path.

---

# 5. Index Construction

The primary construction method is:

```python
SearchIndex.build(tracks)
```

Each track is added to:

- `all_tracks`
- artist index
- title index
- title-token index
- album index
- artist/title index
- GUID index when a GUID is present

---

# 6. Normalization Dependency

The Search Index depends directly on:

```text
normalize_key()
title_tokens()
```

from `normalization.py`.

Index behavior therefore inherits the normalization rules documented in `normalization.md`.

---

# 7. Artist Index

`by_artist` is keyed by:

```python
normalize_key(track.artist)
```

Lookup uses:

```python
artist_matches(artist)
```

and returns a list of matching `LibraryTrack` records.

---

# 8. Title Index

`by_title` is keyed by:

```python
normalize_key(track.title)
```

Lookup uses:

```python
title_matches(title)
```

---

# 9. Album Index

`by_album` is keyed by:

```python
normalize_key(track.album)
```

Lookup uses:

```python
album_matches(album)
```

---

# 10. Combined Artist/Title Index

`by_artist_title` uses:

```text
<normalized artist>|<normalized title>
```

Lookup uses:

```python
artist_title_matches(artist, title)
```

This typically returns a narrower candidate set than artist-only or title-only lookup.

---

# 11. GUID Index

Tracks with a GUID are indexed through `by_guid`.

Lookup uses:

```python
guid_match(guid)
```

and returns one `LibraryTrack` or `None`.

---

# 12. GUID Collision Behavior

The GUID map uses direct dictionary assignment.

If multiple tracks share the same GUID, the later track overwrites the earlier entry in `by_guid`.

This differs from artist/title/album indexes, which preserve lists.

---

# 13. Title Token Index

The Search Index creates `by_title_token` for broader candidate discovery.

Each track title is converted through:

```python
title_tokens(track.title)
```

Each resulting token maps to tracks containing that normalized token.

---

# 14. Title Token Matching

Candidate retrieval through title tokens is performed by:

```python
title_token_matches(title)
```

If no requested tokens are produced, an empty list is returned.

Otherwise, overlap counts are calculated for each candidate track.

---

# 15. Token Overlap Threshold

A candidate must share at least 50% of the requested title tokens, rounded upward, with a minimum of one token.

Examples:

| Requested Tokens | Required Overlap |
|---:|---:|
| 1 | 1 |
| 2 | 1 |
| 3 | 2 |
| 4 | 2 |
| 5 | 3 |
| 6 | 3 |

This is a candidate-discovery threshold, not a final match threshold.

---

# 16. Token Candidate Deduplication

A candidate may appear in several token lists.

The implementation uses Plex `rating_key` as candidate identity and accumulates token overlap per rating key.

A given Plex track is returned only once even if several requested tokens match it.

---

# 17. Duplicate Metadata Preservation

For `by_artist`, `by_title`, `by_album`, and `by_artist_title`, multiple candidate tracks are intentionally preserved.

The matcher can then choose among album, compilation, remaster, single, live, or duplicate-library variants.

---

# 18. all_tracks

The index retains a full `all_tracks` list.

The `track_count` property returns its length.

This list also supports operations that do not currently have a dedicated prebuilt index.

---

# 19. Album Artist Lookup

Album artist lookup uses:

```python
album_artist_matches(artist)
```

There is currently no dedicated `by_album_artist` dictionary.

Instead, the method normalizes the requested artist, scans `all_tracks`, normalizes each track's `album_artist`, and returns matching records.

---

# 20. Album Artist Performance Characteristic

Unlike dictionary-backed artist/title/album lookups, `album_artist_matches()` performs a full-library scan.

Its per-lookup complexity is therefore approximately O(n), where n is the number of indexed tracks.

A future `by_album_artist` index should be evaluated for consistency and performance.

---

# 21. Index Immutability Intent

The class documentation describes SearchIndex as immutable.

The practical intent is that it is built once and treated as read-only during matching.

However, its underlying Python lists and dictionaries remain mutable, so immutability is currently a usage convention rather than deep runtime enforcement.

---

# 22. Relationship to Plex Cache

The Search Index is normally built from `LibraryTrack` records loaded from the SQLite Plex cache.

The cache persists library metadata; the Search Index converts that metadata into in-memory lookup structures for the current process.

---

# 23. Loading from Cache

The normal cached workflow uses:

```text
cache.load_index()
```

which returns a SearchIndex built from cached `LibraryTrack` data.

---

# 24. No-Cache Workflow

When `--no-cache` is used, the orchestrator loads the Plex library directly and calls:

```python
SearchIndex.build(...)
```

Cache and no-cache workflows therefore converge on the same SearchIndex abstraction before matching begins.

---

# 25. SearchIndex as Matcher Boundary

The module explicitly states that the matcher should interact with SearchIndex rather than raw lists of tracks.

This separates candidate retrieval from candidate evaluation.

---

# 26. Candidate Retrieval Versus Final Acceptance

The Search Index identifies plausible candidates.

The matcher remains responsible for title gates, weighted scoring, confidence, and accept/reject decisions.

---

# 27. Relationship to Alias Handling

`search_index.py` itself does not directly apply alias mappings.

Alias-aware artist expansion and canonical resolution are handled by normalization/alias-aware matching logic.

---

# 28. Search Index Build Cost

Index construction requires one pass through the supplied tracks and is approximately linear in library size.

Most exact-key lookups are dictionary-backed once construction is complete.

---

# 29. Memory Tradeoff

The Search Index stores references to the same `LibraryTrack` objects in several lookup structures.

This trades additional memory usage for faster repeated candidate discovery.

---

# 30. Empty Lookup Behavior

Collection lookups return `[]` when no candidate exists.

GUID lookup returns `None` when no GUID exists.

---

# 31. Current Test Coverage

There is currently no dedicated:

```text
tests/test_search_index.py
```

in the uploaded project test inventory.

The Search Index may receive indirect coverage through matching, cache, or integration tests, but explicit unit tests for SearchIndex behavior are absent.

---

# 32. Recommended SearchIndex Unit Tests

A future `tests/test_search_index.py` should cover:

- Index construction.
- Artist lookup.
- Title lookup.
- Album lookup.
- Combined artist/title lookup.
- Duplicate metadata preservation.
- GUID lookup and missing GUID behavior.
- Title-token overlap thresholds.
- One-token titles.
- Odd token-count rounding.
- Candidate deduplication by rating key.
- Album-artist lookup.

---

# 33. Post-Documentation Technical Review Candidates

## 33.1 Add Dedicated SearchIndex Tests

Create:

```text
tests/test_search_index.py
```

with direct unit coverage for all public lookup methods and token-overlap rules.

## 33.2 Consider a by_album_artist Index

`album_artist_matches()` currently performs a full scan over `all_tracks`.

A dedicated `by_album_artist` dictionary should be evaluated.

## 33.3 Review O(1) Module Description

The module description's O(1) wording is broadly true for dictionary-backed lookups but not for `album_artist_matches()`.

## 33.4 Review Deep Immutability Claim

The SearchIndex is intended to be read-only after construction, but its lists and dictionaries are mutable.

## 33.5 Review Duplicate GUID Assumption

`by_guid` keeps only the last track for a duplicate GUID.

This assumption should be confirmed against Plex metadata expectations.

---

# 34. Operational Troubleshooting

When investigating search-index-related behavior:

1. Confirm the Plex cache contains the expected track.
2. Confirm the expected `LibraryTrack` metadata.
3. Compare normalized artist/title keys.
4. Check exact artist lookup.
5. Check exact title lookup.
6. Check combined artist/title lookup.
7. Check title-token lookup.
8. Calculate the required 50% token-overlap threshold.
9. Confirm aliases are being applied by the matching layer where expected.
10. Review album-artist behavior separately because it scans the full library.
11. Continue to matcher scoring only after confirming candidate retrieval.

A candidate-retrieval failure and a candidate-scoring failure are different problems and should be diagnosed separately.

---

# 35. Future Considerations

Potential future improvements include:

- Dedicated SearchIndex unit tests.
- A prebuilt album-artist index.
- Candidate-count metrics.
- Index-build timing metrics.
- Memory-usage visibility.
- Better diagnostics showing which lookup path produced a candidate.
- Duplicate GUID diagnostics.
- Dashboard visibility into index size and build health.

Future changes should preserve the guiding principle:

> The Search Index should retrieve plausible Plex candidates efficiently while leaving final match acceptance to the matcher.
