# CP028 / GitHub Issue #2

Adds configurable rejected matching terms.

Configuration:

    [matching]
    rejected_terms = karaoke

Behavior:

- Terms are comma-separated, case-insensitive, Unicode-folded, and punctuation-tolerant.
- Track title, album title, and version metadata are checked.
- Rejection occurs before preferred-version ranking and normal scoring.
- rejected_terms takes precedence over preferred_versions.
- Configuration overlap emits one startup warning.
- Plex unmatched reasons and TIDAL diagnostic reports identify the term and field.
- Lidarr album searches are not queued when the resolved track/album is rejected.
- TIDAL cache keys include the rejection policy so old cached matches cannot bypass it.

Focused validation performed:

    44 passed

Ten tests are added, so the expected full-suite total is 334.
