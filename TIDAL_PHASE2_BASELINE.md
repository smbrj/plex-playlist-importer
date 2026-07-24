# TIDAL Phase 2 — Production Baseline

**Baseline checkpoint:** CP020  
**Date:** 2026-07-23  
**Pre-closure regression baseline:** CP019 — 274 tests passing

## Status

TIDAL Phase 2 is functionally complete pending the final CP020 live validation
commands listed below.

CP020 intentionally makes **no production-code behavior changes**. It freezes
the CP019 implementation and adds closure/architecture tests plus this baseline
record.

## Final matching policy

A TIDAL candidate must:

1. match the requested artist, including configured artist aliases;
2. match the requested track title;
3. qualify as an accepted studio recording;
4. satisfy the configured explicit-content policy.

Album is not part of the match decision.

Stereo, mono, and accepted remasters remain eligible.

### Explicit content

```ini
[tidal]
allow_explicit = true
```

When `allow_explicit = false`, a candidate is rejected only when TIDAL itself
returns the literal boolean `explicit=true`.

Missing, null, empty, false, string, or otherwise non-boolean explicit metadata
is treated as not explicit.

Diagnostic reason:

```text
explicit content rejected by configuration
```

### Quality preference

Current default:

```ini
quality_preference = DOLBY_ATMOS,HIRES_LOSSLESS,LOSSLESS
```

Quality is a tie-breaker only among otherwise qualifying candidates.

## Catalog cache

Default behavior:

```ini
cache_enabled = true
cache_database = cache/tidal_search_cache.db
cache_max_age_hours = 24
```

Positive and negative results are cached.

Explicit-policy state participates in cache identity so changing
`allow_explicit` cannot reuse a result created under the opposite policy.

## User authorization and account state

Production write scopes require:

```text
playlists.read
playlists.write
collection.read
collection.write
user.read
```

Token storage remains local and must never be committed to source control.

Operational state:

```ini
state_database = cache/tidal_state.db
```

The state database records companion memberships and whether PPI can prove it
created a favorite.

## Companion playlist policy

For each Plex-unmatched track that resolves in TIDAL:

1. find/create a same-named TIDAL companion playlist;
2. add the selected track if missing;
3. favorite it if missing;
4. record local ownership/membership state.

Operations are idempotent.

## Reconciliation policy

A TIDAL secondary copy is removed only after it is no longer part of the
desired TIDAL set for that companion.

The policy protects favorite ownership:

```text
stale in current companion
    |
    +-- another PPI companion still needs it
    |      -> remove current playlist membership only
    |      -> keep favorite
    |
    +-- no other companion needs it
           |
           +-- PPI proved favorite ownership
           |      -> remove playlist membership
           |      -> remove favorite
           |
           +-- ownership unproven/user-owned
                  -> remove playlist membership
                  -> keep favorite
```

Playlist DELETE payloads use TIDAL's server-provided relationship metadata.
PPI does not invent destructive relationship metadata.

## Lidarr coexistence

Plex-unmatched tracks form one external dispatch pool.

When Lidarr processing is requested:

```text
Plex unmatched
   |---> Lidarr
   `---> TIDAL
```

The two services receive the same post-Plex matching session independently.

Lidarr acquisition remains asynchronous. TIDAL does not depend on a successful
Lidarr outcome.

## Matched-track reporting

When one or more TIDAL matches are found:

```text
reports/tidal-matched=mmddhhmm.csv
```

Schema:

```text
tidal_url,artist,album,track
```

No matched report is created for zero TIDAL matches.

The TIDAL browse URL is derived from the track ID at report time and is not
persisted as catalog state.

## Failure behavior

TIDAL runtime processing is isolated from the main import pipeline.

A TIDAL exception:

- is logged as a warning;
- marks TIDAL unavailable for that run;
- is appended to the run warning state;
- does not erase Plex/Lidarr results already obtained.

A dry run that contains warnings exits with code 2.

HTTP 429 handling honors `Retry-After` when available and otherwise uses
bounded retry/backoff behavior implemented in the account client.

## Retained diagnostic commands

```text
--tidal-search
--tidal-authorize
--tidal-authorize-write
--tidal-account-test
--tidal-write-test
--tidal-favorite-test
--tidal-favorite-cleanup
```

The temporary CP016 ownership-forcing command is not part of production.

## CP020 validation

### Automated

```powershell
python -m pytest tests/test_tidal_phase2_closure.py -v
python -m pytest -v
```

### Final representative XMPlaylist dry run

Use an enabled XM station/profile with TIDAL enabled.

Preferred profile form:

```powershell
python playlist_import_v2.py --xmprofile <profile> --dry-run --lidarr-search --lidarr-report reports\lidarr_unmatched_report.csv
```

or direct station form:

```powershell
python playlist_import_v2.py --xmstation 14 --dry-run --lidarr-search --lidarr-report reports\lidarr_unmatched_report.csv
```

The run should demonstrate:

1. XMPlaylist source ingestion;
2. Plex matching;
3. one post-Plex external unmatched pool;
4. Lidarr processing of that pool;
5. TIDAL processing of that same pool;
6. timestamped TIDAL matched reporting when matches exist;
7. no Plex/TIDAL playlist mutation because `--dry-run` is active;
8. SUCCESS when all required services succeed, or a controlled warning/exit 2
   if an optional external service fails.

## Phase completion

After automated tests and one representative XMPlaylist dry run pass, CP020 is
the final TIDAL Phase 2 production baseline.

The next project work should move outside core TIDAL Phase 2 behavior rather
than extend this checkpoint.
