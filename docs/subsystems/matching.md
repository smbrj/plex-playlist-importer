# Matching Subsystem

## 1. Purpose and Scope

The matching subsystem determines whether a requested playlist entry corresponds to a track available in the cached Plex music library.

It is designed around two priorities:

1. Find legitimate matches despite reasonable differences in music metadata.
2. Avoid false matches when confidence is insufficient.

A track that cannot be matched confidently should remain unmatched.

## 2. Responsibilities

The matching subsystem is responsible for matching requested entries, applying configured normalization, considering artist/album-artist/title metadata, using approved aliases, calculating weighted scores, applying thresholds, and producing confidence and match-reason information.

It is not responsible for parsing source-specific formats, refreshing the Plex cache, modifying Plex playlists, acquiring media, or deciding downstream actions for unmatched tracks.

## 3. Processing Flow

```text
Playlist Entry
PlaylistEntry
(models.py)
     |
     v
Matching Entry Point
match_playlist()
(matcher.py)
     |
     v
Per-Entry Matching
_match_entry()
(matcher.py)
     |
     v
Candidate Discovery
_candidate_set()
(matcher.py)
     |
     +---- alias-aware artist names
     |     artist_lookup_names()
     |     (normalization.py)
     |
     +---- exact artist/title lookup
     |     SearchIndex.artist_title_matches()
     |     (search_index.py)
     |
     +---- artist lookup
     |     SearchIndex.artist_matches()
     |     (search_index.py)
     |
     +---- exact title lookup
     |     SearchIndex.title_matches()
     |     (search_index.py)
     |
     +---- token title lookup
           SearchIndex.title_token_matches()
           (search_index.py)
     |
     v
Candidate Prioritization
_prioritize_candidates()
(matcher.py)
     |
     +---- canonical alias-aware artist comparison
           canonical_artist_key()
           (normalization.py)
     |
     v
Artist Eligibility / Fallback Evaluation
_eligible_candidates()
(matcher.py)
     |
     v
Title Similarity Gate
_title_similarity()
(matcher.py)
     |
     v
Duplicate Candidate Collapse
_deduplicate_candidates()
(matcher.py)
     |
     v
Weighted Candidate Scoring
_score()
(matcher.py)
     |
     +---- Artist
     +---- Album Artist
     +---- Title
     +---- Combined Metadata
     |
     v
Threshold and Confidence Decision
(matcher.py)
     |
     +-------------------------+
     |                         |
     v                         v
Matched Result            Unmatched Result
MatchResult               MatchResult
(models.py)               (models.py)
     |                         |
     +------------+------------+
                  |
                  v
          MatchingSession.results
               (models.py)
                  |
          +-------+--------+
          |                |
          v                v
      Reporting       Alias Usage Analysis
    reporting.py      count_alias_usage()
                     (alias_usage.py)
                          |
                          v
                     AliasUsageStore
                     (alias_usage.py)
                          |
                          v
                  cache/alias_usage.db
                    table: alias_usage
```

### Alias Handling During Matching

```text
resources/aliases.txt
        |
        v
load_artist_aliases()
(resources.py)
        |
        v
MatchingConfig.artist_aliases
(models.py)
        |
        v
artist_lookup_names()
canonical_artist_key()
(normalization.py)
        |
        v
Candidate selection and scoring
(matcher.py)
```

`alias_usage.py` operates after matching to record successful alias usage. `alias_intelligence.py` is a separate maintenance/analysis workflow and is not part of the normal per-track match decision.

## 4. Matching Inputs

Inputs include requested artist/title metadata and Plex library metadata supplied through the local cache and `SearchIndex`.

A cached match identifies the best known Plex candidate. Live Plex resolution remains a later responsibility when Plex action is required.

## 5. Normalization

Normalization reduces predictable differences such as capitalization, punctuation, remaster/live/featured/deluxe metadata according to configuration.

Known artist equivalence belongs in the alias system rather than general normalization.

## 6. Artist and Album-Artist Matching

The subsystem may consider both track artist and album artist because source and Plex metadata may differ in which field carries useful performer identity.

## 7. Artist Aliases

Alias mappings from `resources/aliases.txt` are loaded through `resources.py` and supplied through `MatchingConfig`. They expand candidate lookup and canonical artist comparison.

See `docs/subsystems/aliases.md` and ADR-005.

## 8. Weighted Matching

Representative configured weights:

```ini
[matching]
artist=0.25
album_artist=0.15
title=0.45
combined=0.15
```

These are configuration values, not architectural constants.

## 9. Match Threshold

Representative configuration:

```ini
[matching]
threshold=85
```

Lowering the threshold may increase false positives; raising it may increase unmatched tracks. Global thresholds should not be changed solely to solve isolated metadata cases.

## 10. Confidence and Match Reasons

Results support confidence labels, reasons, and notes so users and developers can understand why a candidate was accepted or rejected.

## 11. Unmatched Tracks

Unmatched is a valid result and may indicate missing media, metadata differences, alias needs, cache staleness, or a matching defect. Downstream actions belong outside the matching subsystem.

## 12. Configuration

Matching behavior is controlled primarily through `[matching]` in `config.ini`. Detailed keys belong in `docs/configuration.md`.

## 13. Persistent State

The matcher consumes data from `cache/plex_library.db` and alias mappings loaded from `resources/aliases.txt`. It does not own cache lifecycle.

Post-match alias usage is written by `alias_usage.py` to `cache/alias_usage.db`.

## 14. Failure Behavior

No acceptable candidate should normally produce an unmatched result. Unexpected internal failures must remain distinguishable from normal unmatched behavior.

## 15. Logging and Reporting

Detailed candidate scoring belongs at DEBUG/trace level. Structured `MatchResult` data is presented by the reporting subsystem.

## 16. Testing

Matching should be testable without a live Plex server.

### Current Test Coverage

Primary pytest coverage recorded in the current project test suite:

- `tests/test_matcher_smoke.py`
  - `test_exact_match_smoke`
  - `test_unicode_accent_matching_smoke`
  - `test_configured_artist_alias_smoke`
  - `test_unrelated_title_remains_unmatched`

Related coverage also exists in:

- `tests/test_alias_intelligence.py` — alias discovery/maintenance behavior that can affect future alias configuration.
- `tests/test_alias_usage.py` — post-match alias usage persistence.
- `tests/test_parser.py` — verifies playlist entries are constructed correctly before matching.
- `tests/test_cache_resiliency.py` — verifies cache freshness behavior feeding the search index.
- `tests/test_plex_stale_resolution.py` — verifies the boundary between cached matches and live Plex resolution.

### Running the Primary Matching Tests

```bash
python -m pytest tests/test_matcher_smoke.py -v
```

Run the complete regression suite before finalizing matching changes:

```bash
python -m pytest -v
```

### Regression Expectations

When a real-world matching defect is corrected, add a focused regression test where practical. Evaluate both the intended new result and previously correct matches to avoid trading false negatives for false positives.

## 17. Design Decisions and ADR References

- ADR-004 — Separate Playlist Sources from the Matching Pipeline
- ADR-005 — Use Explicit Artist Aliases Rather Than Loosening Global Matching Rules
- ADR-006 — Treat the Plex Library Cache as a Performance Layer, Not the Authority

## 18. Operational Notes

When investigating an unexpected result:

1. Confirm requested artist/title parsing.
2. Confirm the expected track exists in the cache.
3. Review normalization.
4. Check artist and album-artist metadata.
5. Check aliases.
6. Review score/confidence/reason.
7. Confirm threshold and weights.
8. Consider cache staleness.
9. Confirm live Plex identity when resolution is required.

## 19. Future Considerations

Potential improvements include improved alias-analysis tooling, additional explainability, and targeted tuning based on real regression cases.

The long-term objective remains:

> Match legitimate tracks despite reasonable metadata differences while minimizing false positives.
