# Testing Strategy

**Document Version:** 1.0  
**Status:** Approved  
**Last Updated:** 2026-07-21  
**Primary Audience:** Developers  
**Depends On:** runtime.md  
**Related Documents:** matching.md, parser.md, normalization.md, cache.md, lidarr.md, xmplaylist.md, reporting.md, deployment.md  
**Snapshot:** 010

---

# 1. Purpose and Scope

This document defines the automated and live-testing strategy for the Plex Playlist Importer.

Testing is a core part of the project's maintenance process because the application:

- Integrates with independently changing external services.
- Maintains persistent local state.
- Performs fuzzy matching where incorrect results may still appear plausible.
- Performs operations that may modify Plex playlists.
- May trigger Lidarr searches.
- Consumes XMPlaylist API requests.
- Is intended for unattended scheduled execution.

The test strategy therefore focuses on protecting behavior rather than merely confirming that code executes without exceptions.

The guiding principle is:

> Every significant defect should become an opportunity to make the application permanently harder to break in the same way again.

---

# 2. Test Framework

The project uses:

```text
pytest
```

Automated tests are stored under:

```text
tests/
```

The project metadata defines:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

The complete suite can therefore be run with:

```bash
python -m pytest
```

For verbose output:

```bash
python -m pytest -v
```

---

# 3. Current Verified Test Environment

The most recent recorded full-suite execution available during this documentation review used:

```text
Windows
Python 3.12.10
pytest 9.1.1
```

The application itself currently requires:

```text
Python >= 3.11
```

The test suite should remain compatible with supported Python versions rather than relying unnecessarily on one developer workstation version.

---

# 4. Current Test Suite Size

The latest recorded full-suite run found during this review collected:

```text
76 tests
```

This number represents the recorded project state at that time and is not a permanent architectural constant.

The authoritative current count is always obtained from pytest collection or a normal full-suite run.

---

# 5. Testing Objectives

The primary objectives of the test suite are to prevent regressions, verify subsystem boundaries, protect matching behavior, validate known edge cases, confirm failure and degradation behavior, protect persistent-state compatibility, verify external API interpretation, make refactoring safer, preserve lessons learned from real-world failures, and support unattended runtime reliability.

A passing test suite does not prove that the application is defect-free.

It provides evidence that defined and tested behavior remains intact.

---

# 6. Testing Layers

The project uses several practical testing layers:

```text
Unit Tests
    |
    v
Subsystem / Behavioral Tests
    |
    v
Runtime / Resiliency Tests
    |
    v
Full Regression Suite
    |
    v
Controlled Live Integration Tests
```

Each layer serves a different purpose.

---

# 7. Unit Tests

Unit tests should exercise behavior at the smallest useful component boundary.

Examples include parsing playlist records, normalizing metadata, calculating matching scores, evaluating cache staleness, resolving aliases, classifying Lidarr status, parsing XMPlaylist responses, and evaluating station-profile configuration.

Unit tests should normally use small deterministic fixtures, avoid external network dependencies, avoid real credentials, and avoid modifying external services.

---

# 8. Behavioral and Subsystem Tests

Subsystem tests verify coordinated behavior within one bounded area.

Examples include Lidarr response interpretation, XMPlaylist source/state persistence, alias intelligence, cache resiliency, and reporting/output schema.

These tests may involve several classes or functions but should still avoid unnecessary dependence on live services.

---

# 9. Runtime and Resiliency Tests

Runtime tests protect component health, optional integration failure, cache degradation, Plex availability, startup decisions, station-profile execution, exit-code semantics, and safe playlist-operation behavior.

These tests are particularly important because the application is intended for unattended execution.

---

# 10. Regression Tests

When a real defect is identified, the preferred correction workflow is:

```text
Observe Defect
      |
      v
Create Reproducible Test
      |
      v
Confirm Test Fails
      |
      v
Correct Implementation
      |
      v
Confirm Targeted Test Passes
      |
      v
Run Full Regression Suite
```

A defect should not be considered fully corrected until the behavior that exposed it is protected by a regression test where practical.

---

# 11. Targeted Testing During Development

During development, the smallest relevant test set should be run first.

For example:

```bash
python -m pytest tests/test_lidarr_reporting.py -v
```

Targeted tests provide faster feedback while changing one subsystem.

They do not replace the full suite.

---

# 12. Full Regression Suite

After targeted tests pass:

```bash
python -m pytest -v
```

should be run before the change is considered complete.

A change in one subsystem may expose assumptions elsewhere.

The complete suite therefore remains the primary automated regression gate.

---

# 13. Parser Test Coverage

The parser has dedicated coverage through:

```text
tests/test_parser.py
```

Verified behavior includes numbered TXT parsing, invalid TXT line skipping, CSV with and without headers, TSV parsing, Unicode input, M3U `#EXTINF` parsing, unsupported extension handling, and missing-file handling.

Each new supported playlist format should receive dedicated parser tests before it is considered complete.

---

# 14. Matcher Test Coverage

Current matcher-focused coverage includes:

```text
tests/test_matcher_smoke.py
```

Recorded cases include exact matching, Unicode/accent matching, configured artist aliases, and clearly unrelated titles remaining unmatched.

Matching tests are especially valuable because they can run without a live Plex server using known `LibraryTrack` fixtures.

---

# 15. Matching Regression Expectations

Important matching behaviors that should remain protected include exact artist/title matching, case variation, Unicode variation, accent folding, artist aliases, album-artist behavior, title normalization, fuzzy matching, fallback matching, version selection, and clearly unrelated tracks remaining unmatched.

Where practical, tests should verify both the correct track and the correct reason rather than merely confirming that some track matched.

---

# 16. Normalization Test Gap

The current test inventory does not contain a dedicated:

```text
tests/test_normalization.py
```

This is a known gap identified during documentation review.

Normalization directly influences SearchIndex keys, alias resolution, candidate discovery, match scoring, and version classification.

Dedicated normalization tests should be added during post-documentation technical cleanup.

---

# 17. Required Future Normalization Coverage

Future normalization tests should directly cover:

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

Representative cases should include accented Unicode, curly quotes, special letters, featured artists, remaster text, live text, parenthetical metadata, stopwords, and alias equivalence.

---

# 18. SearchIndex Test Gap

There is currently no dedicated:

```text
tests/test_search_index.py
```

This was identified during the SearchIndex documentation review.

SearchIndex behavior includes exact artist/title/album/combined lookup, GUID lookup, token-based title candidate discovery, and album-artist scanning.

These behaviors should receive direct unit coverage.

---

# 19. Required Future SearchIndex Coverage

A dedicated SearchIndex test module should verify index construction, track count, duplicate metadata preservation, artist/title/album/combined lookup, GUID lookup, missing GUID behavior, token-overlap calculations, odd-token rounding, candidate deduplication by rating key, and album-artist lookup.

---

# 20. Cache and Resiliency Tests

Current cache-related coverage includes:

```text
tests/test_cache_resiliency.py
```

Verified cases include cache age/staleness and missing refresh metadata being treated as stale.

Cache testing should continue to protect empty-cache behavior, track replacement/count, cache age, fresh/stale state, SearchIndex loading, refresh failure behavior, and persistence compatibility.

---

# 21. Component Health Tests

Current health-related coverage includes:

```text
tests/test_component_health.py
tests/test_runtime_health.py
tests/test_xmplaylist_health.py
```

Recorded cases include Plex availability, Plex unavailability when the library is missing, explicit runtime health states, and reuse of XMPlaylist station discovery during health checking.

---

# 22. Plex Runtime Testing

Plex integration should normally be isolated using mocks or controlled fake objects during routine automated testing.

Important behaviors include availability checks, library loading, cache fallback, stale match resolution, playlist mode safety, missing Plex objects, and playlist-operation skip behavior.

Controlled live Plex testing remains necessary for behavior that mocks cannot fully guarantee.

---

# 23. Controlled Plex Integration Tests

Live Plex integration tests should use disposable playlists rather than maintained production playlists.

Important scenarios include CREATE, UPDATE, REPLACE, SYNC semantics, duplicate handling, playlist order, stale item behavior, and Plex API compatibility.

Live tests should be deliberate rather than part of every pytest execution.

---

# 24. Lidarr Test Coverage

Lidarr has extensive dedicated coverage.

Current modules include:

```text
tests/test_lidarr_client.py
tests/test_lidarr_reporting.py
tests/test_lidarr_operational_reporting.py
tests/test_lidarr_operational_resilience.py
tests/test_lidarr_retry_policy.py
tests/test_lidarr_search_history.py
```

Additional compatibility tests have also been used for older/newer Lidarr availability semantics.

---

# 25. Lidarr Client Tests

Current Lidarr client tests include managed-artist lookup, command completion, command failure, and command polling.

Routine automated tests should mock Lidarr rather than depend on a live server.

---

# 26. Lidarr Reporting Tests

Lidarr reporting tests have verified search queued without waiting, completed search without file, completed search with file, failed search, multiple tracks mapping to one album search, and acquisition-status CSV output.

Operational-reporting tests also verify summary behavior and compatibility with evolving status representations.

---

# 27. Lidarr Resiliency Tests

Lidarr operational-resilience coverage includes per-entry request failure isolation, progress callback behavior, and case-insensitive unique unmatched-artist counting.

This supports the architectural rule that one failed external request should not unnecessarily invalidate unrelated work.

---

# 28. Lidarr Retry and History Tests

Dedicated tests protect recent-search suppression, retry eligibility, search-history persistence, search request counts, and behavior when history tracking is disabled.

---

# 29. Lidarr Critical Semantic Test

A particularly important distinction is:

```text
Search command completed
```

versus:

```text
Media file available
```

These conditions are not equivalent.

Tests should continue protecting this distinction.

---

# 30. XMPlaylist Test Coverage

XMPlaylist has dedicated coverage through:

```text
tests/test_xmplaylist_client.py
tests/test_xmplaylist_source.py
tests/test_xmplaylist_state.py
tests/test_xmstation_profiles.py
tests/test_xmplaylist_health.py
```

These modules protect API interpretation, ingestion, persistent state, profile behavior, and runtime health.

---

# 31. XMPlaylist Client Tests

Client tests cover station resolution, history-page parsing, request limits, and rate-limit handling.

External network access should not normally be required.

---

# 32. XMPlaylist Source Tests

Source tests protect history-window behavior, deduplication, unique-track counting, pagination stopping conditions, request-budget behavior, track-target behavior, and cursor/backfill behavior.

Duplicate broadcast plays should not incorrectly count toward the unique-track target.

---

# 33. XMPlaylist State Tests

Persistent-state tests protect cursor persistence, resume behavior, state reset when history window changes, and SQLite-backed history continuity.

---

# 34. XMStation Profile Tests

Current station-profile tests include:

```text
test_loads_profiles_and_default_playlist
test_custom_playlist_and_blank_max_tracks
test_profile_applies_defaults
test_cli_overrides_profile
test_rejects_invalid_profile
test_listing_marks_disabled_profiles
test_aggregate_exit_code
test_profile_header_is_compact
test_profile_summary_contains_aggregate_counts
```

This provides substantial coverage for station-profile configuration and execution semantics.

---

# 35. Multi-Profile Exit-Code Coverage

The current test suite includes:

```text
test_aggregate_exit_code
```

for station-profile aggregation.

Additional direct regression coverage should verify the complete documented runtime exit behavior.

---

# 36. Runtime Exit-Code Test Gap

The current runtime explicitly uses:

```text
0
1
2
4
5
```

for meaningful execution outcomes.

These codes should receive dedicated regression tests where practical.

This is especially important for future cron/container scheduling.

---

# 37. Recommended Exit-Code Coverage

| Exit Code | Condition |
|---:|---|
| `0` | Normal successful completion |
| `1` | Keyboard interruption where testable |
| `2` | Dry run completed with warnings |
| `4` | Plex unavailable at playlist-modification stage |
| `5` | Stale-cache safety stop or Plex resolution mismatch |

Multi-profile aggregated outcomes should also remain covered.

---

# 38. Alias Intelligence Tests

Current alias-intelligence coverage includes:

```text
tests/test_alias_intelligence.py
tests/test_alias_usage.py
```

Verified behaviors include Plex artist inventory export, leading-article alias suggestion, importing only rows marked ADD, alias audit using persistent usage, alias usage persistence, and alias-status rules.

---

# 39. Analytics Tests

Current analytics coverage includes:

```text
tests/test_analytics.py
```

Recorded cases include analytics output generation, count calculation, and existing CSV schema migration.

Analytics persistence is important because historical data may outlive individual application versions.

---

# 40. Reporting Test Coverage

Reporting coverage is uneven.

Lidarr reporting has strong direct tests.

Other report writers may currently receive indirect coverage through alias intelligence, analytics, matcher tests, and Library Intelligence tests.

A complete report-writer test audit remains a known post-documentation task.

---

# 41. Required Reporting Coverage Audit

Every current report writer should be mapped to direct tests, including match report CSV, unmatched CSV, Lidarr diagnostics CSV, duplicate report, Plex artist inventory, alias suggestions, alias audit, analytics CSV, and latest-run JSON.

Important schema headers used by follow-on utilities should receive regression protection.

---

# 42. Persistence Compatibility Testing

The project maintains several SQLite data stores, including:

```text
plex_library.db
lidarr_search_history.db
xmplaylist_history.db
alias_usage.db
```

Tests should consider current schema initialization, existing database compatibility, schema migration where implemented, historical-data preservation, and behavior with missing metadata.

---

# 43. External Service Mocking

Routine automated tests should not normally depend on live Plex, live Lidarr, or the live XMPlaylist API.

Mocks and deterministic fixtures should be preferred because external dependencies introduce network variability, authentication requirements, rate limits, changing data, slow execution, and unwanted side effects.

---

# 44. Live Integration Testing

Mocks cannot fully verify every real-system assumption.

Controlled live integration tests remain appropriate for Plex playlist operations/API compatibility/library metadata behavior, Lidarr API compatibility, XMPlaylist response behavior, and timeout behavior.

Live tests should be deliberate rather than required on every development cycle.

---

# 45. Live-Test Side Effects

`--lidarr-search` may trigger a real album acquisition workflow.

XMPlaylist testing may consume API requests and update persistent ingestion state.

Non-dry-run Plex testing may modify playlists.

Live testing should therefore use controlled data and disposable targets where practical.

---

# 46. Dry Run Is Not Full Simulation

`--dry-run` prevents Plex playlist modification.

It does not make all integrations simulated.

For example:

```text
--dry-run --lidarr-search
```

may still initiate real Lidarr searches.

---

# 47. Test Data Principles

Test data should be small enough to understand, large enough to demonstrate the behavior, deterministic, free of credentials, independent of one developer workstation, and easy to reproduce.

Real-world defects should be reduced to the smallest useful fixture where practical.

---

# 48. Unicode and Metadata Fixtures

Fixtures should intentionally include difficult music metadata such as:

```text
Beyoncé
Mötley Crüe
Sinéad O'Connor
The Doobie Brothers
Doobie Brothers
Dreams (2001 Remaster)
Live versions
Featured artists
Various Artists
```

These cases protect interactions among parser, normalization, alias, SearchIndex, and matcher behavior.

---

# 49. Test Independence

Tests should avoid depending on execution order, existing local cache databases, existing report files, real user aliases, local Plex libraries, or real tokens/API keys.

Temporary directories and temporary SQLite databases should be used where practical.

---

# 50. Test Credentials

No real Plex token, Lidarr API key, or other credential should appear in test source, fixtures, test logs, or committed diagnostic output.

Credential-like values should use obvious placeholders.

---

# 51. Failed Tests

A failing test should be investigated before changing its expected result.

A failure may indicate an implementation regression, incorrect test assumption, deliberately changed requirement, stale fixture, or external compatibility change.

Changing a test solely to make the suite pass removes its value.

---

# 52. Intentional Behavior Changes

When intended behavior changes:

1. Change the implementation deliberately.
2. Change the relevant tests deliberately.
3. Document the reason where significant.
4. Run targeted tests.
5. Run the complete suite.

Tests should represent intended supported behavior rather than freeze accidental behavior forever.

---

# 53. Testing Before Code Changes

For defects, the preferred sequence is:

```text
Reproduce
   |
   v
Write Regression Test
   |
   v
Confirm Failure
   |
   v
Modify Code
   |
   v
Run Targeted Test
   |
   v
Run Full Suite
```

For new functionality, tests should be added alongside the behavior.

---

# 54. Testing Before Documentation Approval

Technical documentation should be verified against current source, configuration, automated tests, and known live behavior.

The documentation process itself has revealed several missing test areas.

Those discoveries are valid engineering outputs of documentation review.

---

# 55. Testing Before Release

Before a release is considered ready:

- Relevant targeted tests should pass.
- Full pytest suite should pass.
- Required live integration tests should be performed where external-service behavior changed.
- Documentation should reflect tested behavior.
- Version identifiers should be consistent.
- Changelog should be updated.

---

# 56. Current Known Test Gaps

The documentation review has identified:

```text
Dedicated normalization unit tests
Dedicated SearchIndex unit tests
Complete report-writer test audit
Runtime process exit-code regression tests
Controlled real Plex playlist-mode integration tests
```

These should be addressed during post-documentation technical cleanup.

---

# 57. Controlled Plex Playlist Tests

The project still benefits from controlled disposable-playlist testing for:

```text
CREATE
UPDATE
REPLACE
SYNC
```

Tests should verify real Plex API behavior, duplicate handling, ordering, existing-playlist behavior, stale Plex references, and current additive SYNC semantics.

---

# 58. Post-Documentation Technical Cleanup Test Plan

At minimum:

## Normalization

Create:

```text
tests/test_normalization.py
```

## SearchIndex

Create:

```text
tests/test_search_index.py
```

## Runtime

Add direct process/runtime tests for documented exit codes.

## Reporting

Audit all report writers and add missing direct schema/output tests.

## Plex

Perform controlled live playlist-mode integration testing.

---

# 59. Test Suite Maintenance

Tests should be focused, readable, deterministic, fast enough for normal development use, and organized by subsystem responsibility.

Large end-to-end tests should not replace focused unit tests, and unit tests should not be used to avoid necessary integration testing.

---

# 60. Test Naming

Test names should communicate expected behavior.

Examples:

```text
test_recent_search_is_not_requeued
test_unicode_accent_matching_smoke
test_cli_overrides_profile
test_cache_age_and_staleness
```

---

# 61. Pytest Command Reference

## Full Suite

```bash
python -m pytest
```

## Verbose Full Suite

```bash
python -m pytest -v
```

## One Module

```bash
python -m pytest tests/test_parser.py -v
```

## Selected Modules

```bash
python -m pytest tests/test_lidarr_client.py tests/test_lidarr_reporting.py -v
```

---

# 62. Continuous Integration

A formal hosted continuous-integration pipeline is not currently documented as implemented.

The current test suite is run locally during development.

A future CI system could automatically run pytest against supported Python versions if it provides useful regression protection without unnecessary administration.

---

# 63. Container Testing

When Linux/Unraid containerization is implemented, tests should expand to verify container startup, mounted configuration, persistent database volumes, report/log output volumes, network access to services, process exit codes, scheduled execution, container restart behavior, and health checks.

These belong to the deployment phase rather than the current Windows development baseline.

---

# 64. Testing Design Principle

The test suite is part of the project's technical history.

Each regression test preserves knowledge about a behavior that once mattered enough to define explicitly.

The guiding rule is:

> Test observable behavior, preserve real lessons learned, and make future changes safer without creating unnecessary testing bureaucracy.
