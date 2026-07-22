# Alias Subsystem

## 1. Purpose and Scope

The alias subsystem handles known artist-name variations that cannot be safely resolved through general normalization alone.

It has three distinct responsibilities:

1. Live alias matching.
2. Alias usage tracking.
3. Alias intelligence.

The governing decision is ADR-005.

## 2. Responsibilities

The subsystem maintains explicit artist alias definitions, loads them for matching, records successful historical usage, and provides export/suggestion/import/audit tools.

It does not independently determine complete track matches or automatically approve uncertain alias suggestions.

## 3. Alias Architecture

```text
                 ALIAS DEFINITIONS
                        |
                        v
              resources/aliases.txt
                        |
                        v
                   resources.py
             load_artist_aliases()
                        |
                        v
                  MatchingConfig
                    models.py
                        |
                        v
              LIVE ALIAS MATCHING
       matcher.py + normalization.py


               SUCCESSFUL MATCH RESULTS
                        |
                        v
               playlist_import_v2.py
                        |
                        v
                  alias_usage.py
                        |
                        v
              cache/alias_usage.db
                        |
                        v
             ALIAS USAGE HISTORY


        Plex Artists + Alias Definitions
              + Alias Usage History
                        |
                        v
              alias_intelligence.py
                        |
            +-----------+-----------+
            |           |           |
            v           v           v
          Export     Suggest      Audit /
          Artists    Aliases      Import
```

## 4. Live Alias Matching Flow

```text
Alias Definitions
resources/aliases.txt
        |
        v
Load Alias Mappings
load_artist_aliases()
(resources.py)
        |
        v
Matching Configuration
MatchingConfig.artist_aliases
(models.py)
        |
        +---------------------------+
        |                           |
        v                           v
Generate Artist             Canonical Artist
Lookup Names                Comparison
artist_lookup_names()       canonical_artist_key()
(normalization.py)          (normalization.py)
        |                           |
        +-------------+-------------+
                      |
                      v
            Candidate Discovery /
            Candidate Prioritization
                 (matcher.py)
                      |
                      v
              Candidate Scoring
                 (matcher.py)
                      |
                      v
                 MatchResult
                  (models.py)
```

## 5. Alias Definitions

Approved aliases are stored in `resources/aliases.txt`, loaded by `load_artist_aliases()` in `resources.py`, and supplied through `MatchingConfig.artist_aliases`.

Alias definitions should represent known artist equivalence, not uncertain similarity.

## 6. Alias-Aware Normalization

`artist_lookup_names()` supports approved lookup expansion. `canonical_artist_key()` supports canonical alias-aware comparison.

## 7. Post-Match Alias Usage Tracking

```text
Completed MatchingSession
(models.py)
        |
        v
MatchingSession.results
        |
        v
Record Alias Effectiveness
playlist_import_v2.py
        |
        v
Count Alias Usage
count_alias_usage()
(alias_usage.py)
        |
        v
AliasUsageStore
(alias_usage.py)
        |
        v
cache/alias_usage.db
        |
        v
table: alias_usage
```

Usage tracking occurs after matching and does not influence the match that already occurred.

## 8. Alias Usage Database

Database: `cache/alias_usage.db`

Owned by: `alias_usage.py`

Tables:

- `metadata`
- `alias_usage`

The alias file answers "what aliases are approved?" The usage database answers "how have those aliases been used?"

## 9. Alias Intelligence

Implemented primarily in `alias_intelligence.py`.

```text
Plex Library Artist Data
        +
resources/aliases.txt
        +
cache/alias_usage.db
        |
        v
alias_intelligence.py
        |
        +----------------------+
        |                      |
        v                      v
Artist Inventory         Alias Suggestions
Export
        |
        +----------------------+
        |                      |
        v                      v
Approved Alias           Existing Alias
Import                   Audit
```

Alias intelligence supports human review and maintenance rather than silently changing live matching.

## 10. Plex Artist Export

Exports Plex artist inventory for analysis and alias discovery.

## 11. Alias Suggestions

Suggestions include candidate relationships for review. They are not automatically approved.

## 12. Approved Alias Import

Rows explicitly approved for addition can be imported into `resources/aliases.txt` and become available to future matching runs.

## 13. Alias Audit

Audits can identify demonstrated usage, never-observed aliases, and definitions that may deserve review. Lack of use does not automatically mean an alias is invalid.

## 14. Configuration and Resources

Primary live configuration: `resources/aliases.txt`

Historical usage: `cache/alias_usage.db`

Relevant configuration also includes the `[alias_intelligence]` settings consumed by `playlist_import_v2.py`.

## 15. Persistent State

`resources/aliases.txt` is authoritative for approved live aliases.

`cache/alias_usage.db` is historical state and contains `metadata` and `alias_usage`.

## 16. Failure Behavior

Failure to record usage should not invalidate a completed correct match. Alias-intelligence failures should remain isolated from normal playlist import unless the intelligence command itself was requested.

## 17. Logging and Reporting

Useful observability includes aliases loaded, alias-assisted matches, usage tracking results, and intelligence/audit output. Alias intelligence favors CSV outputs for review.

## 18. Testing

Alias testing is divided across live matching, usage tracking, and intelligence.

### Current Test Coverage

Relevant pytest files in the recorded current test suite:

- `tests/test_matcher_smoke.py`
  - `test_configured_artist_alias_smoke`
  - Verifies configured aliases participate in live matching.

- `tests/test_alias_usage.py`
  - `test_alias_usage_is_persisted`
  - `test_alias_status_rules`
  - Verifies persistent usage tracking and status classification.

- `tests/test_alias_intelligence.py`
  - `test_export_artist_inventory`
  - `test_suggests_leading_article_alias`
  - `test_imports_only_add_rows`
  - `test_audit_uses_persistent_usage`
  - Verifies export, suggestion, controlled import, and audit workflows.

### Running the Alias Tests

```bash
python -m pytest \
  tests/test_matcher_smoke.py \
  tests/test_alias_usage.py \
  tests/test_alias_intelligence.py -v
```

On Windows PowerShell, the same tests can be run on one line:

```powershell
python -m pytest tests/test_matcher_smoke.py tests/test_alias_usage.py tests/test_alias_intelligence.py -v
```

### Regression Expectations

Add regression tests when a real-world alias defect is corrected. Preserve the separation between live matching, post-match usage recording, and intelligence/maintenance behavior.

## 19. Design Decisions and ADR References

- ADR-005 — Use Explicit Artist Aliases Rather Than Loosening Global Matching Rules
- ADR-003 — Use Embedded SQLite for Local Persistence
- ADR-004 — Separate Playlist Sources from the Matching Pipeline

## 20. Operational Notes

When investigating an alias problem:

1. Confirm source artist.
2. Confirm Plex artist/album-artist.
3. Determine whether normalization should already resolve the difference.
4. Check `resources/aliases.txt`.
5. Confirm the alias resource loaded.
6. Review match reason/candidate behavior.
7. Review `cache/alias_usage.db` only for historical effectiveness.
8. Use alias-intelligence tools for broader discovery/audit.

## 21. Future Considerations

Potential improvements include better suggestions, explanations, audits, and review workflows.

More complex alias relationships should be introduced only when demonstrated real-world requirements justify them.

> Explicitly record known artist equivalence, measure how that knowledge is used, and keep automated discovery separate from approval.
