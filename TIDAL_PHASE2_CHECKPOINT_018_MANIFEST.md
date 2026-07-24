# TIDAL Phase 2 — Checkpoint-018

**Date:** 2026-07-23
**Scope:** Configurable explicit-content filtering in TIDAL candidate selection

## Purpose

CP018 adds an explicit-content policy to the TIDAL matcher before the remaining
reporting and lifecycle checkpoints are built on top of it.

Configuration:

```ini
[tidal]
allow_explicit = true
```

`true` is the compatibility/default behavior.

## Authoritative metadata rule

PPI uses only TIDAL's track-level `attributes.explicit` value.

A candidate is explicit only when the TIDAL API returns the literal JSON
boolean:

```json
"explicit": true
```

The following are all treated as **not explicit**:

- field absent;
- `null`;
- empty value;
- `false`;
- non-boolean values.

PPI does not infer explicit content from the track title, artist, album, lyrics,
or any other field.

The current official TIDAL OpenAPI defines `Tracks_Attributes.explicit` as a
boolean described as `Explicit content`.

## Matching order

```text
exact artist/title
      ↓
studio-version eligibility
      ↓
explicit-content policy
      ↓
configured quality ranking
      ↓
selected candidate
```

When:

```ini
allow_explicit = true
```

explicit status has no ranking effect.

When:

```ini
allow_explicit = false
```

candidates explicitly flagged by TIDAL are removed before quality ranking.
A lower-quality clean candidate may therefore win over a higher-quality
explicit candidate.

## Diagnostic output

TIDAL search diagnostics now include:

```text
Explicit : YES
```

or:

```text
Explicit : NO
```

An otherwise qualifying explicit candidate rejected by configuration reports
exactly:

```text
Reason   : explicit content rejected by configuration
```

## Cache behavior

The disposable TIDAL search cache now persists the explicit flag.

Existing cache databases are migrated in place by adding:

```text
explicit INTEGER NOT NULL DEFAULT 0
```

Normal runtime cache keys are also separated by explicit policy. A result or
NO_MATCH generated with `allow_explicit=true` is not reused when the setting is
`false`, and vice versa.

This intentionally bypasses pre-CP018 legacy cache keys during normal TIDAL
resolution so older cached records cannot silently bypass the new policy.

## Files changed

```text
playlist_import_v2.py
plex_playlist/tidal_client.py
plex_playlist/tidal_matcher.py
plex_playlist/tidal_service.py
plex_playlist/tidal_cache.py
plex_playlist/tidal_diagnostics.py
```

## New regression tests

```text
tests/test_tidal_explicit.py
tests/test_tidal_explicit_metadata.py
tests/test_tidal_explicit_cache.py
tests/test_tidal_explicit_diagnostics.py
tests/test_tidal_explicit_service.py
```

The checkpoint build environment passed:

```text
18 explicit-policy tests
54 focused TIDAL tests including existing matcher/cache/client/service tests
```

The complete project regression suite must be run in the user's full repository.

## Validation

### Automated

```powershell
python -m pytest tests/test_tidal_explicit.py tests/test_tidal_explicit_metadata.py tests/test_tidal_explicit_cache.py tests/test_tidal_explicit_diagnostics.py tests/test_tidal_explicit_service.py -v
python -m pytest -v
```

### Live read-only diagnostic — explicit disabled

Temporarily set:

```ini
allow_explicit = false
```

Then run:

```powershell
python playlist_import_v2.py --tidal-search "69 Boyz" "Tootsee Roll"
python playlist_import_v2.py --tidal-search "Sublime" "What I Got"
```

For candidates that TIDAL marks explicit, expected diagnostic fields include:

```text
Explicit : YES
Reason   : explicit content rejected by configuration
```

No account mutation is performed by `--tidal-search`.

Then perform a safe importer dry run:

```powershell
python playlist_import_v2.py tidal-test.txt --playlist test-tidal --dry-run
```

Explicit-only qualifying results should be excluded from TIDAL resolution.
Dry run does not mutate the TIDAL companion playlist or favorites.

### Compatibility check — explicit enabled

Restore:

```ini
allow_explicit = true
```

Run the same dry run again:

```powershell
python playlist_import_v2.py tidal-test.txt --playlist test-tidal --dry-run
```

The previously validated TIDAL matches should again be eligible, with quality
ranking unchanged.

## Safety note

CP018 changes candidate eligibility. The live validation procedure above uses
`--tidal-search` and `--dry-run` so the policy can be verified without changing
the existing `test-tidal` companion playlist or favorite collection.
