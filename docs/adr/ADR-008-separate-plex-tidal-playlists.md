# ADR-008 — Maintain Separate Plex and TIDAL Playlist Responsibilities

**Status:** Proposed  
**Decision:** If TIDAL integration is implemented, maintain locally available tracks in Plex and use a companion TIDAL playlist for tracks unavailable from the local Plex library rather than downloading subscription content into Plex.

## Context

Some requested tracks may remain unavailable locally even after Lidarr processing.

## Decision

```text
Locally Available Track
        |
        v
   Plex Playlist

Unavailable Locally
        |
        v
TIDAL Companion Playlist
```

TIDAL subscription access will not be treated as a mechanism for downloading subscription tracks into Plex.

## Rationale

This preserves the boundary between locally managed media and subscription streaming content.

## Alternatives Considered

Download TIDAL subscription content into Plex, use TIDAL as the only destination, or ignore unavailable tracks.

## Consequences

Positive: clear ownership boundary and improved optional playlist completeness.

Negative: two playlists may be required; synchronization adds state and failure considerations.

## Future Reconsideration

Review when TIDAL design begins, including current API capabilities, service terms, authentication, and playlist synchronization. The boundary remains: subscription access does not imply local media ownership.
