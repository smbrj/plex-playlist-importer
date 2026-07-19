# ADR-002 — Rely on Native Lidarr and Plex Library Synchronization

**Status:** Accepted  
**Decision:** Rely on the existing Lidarr and Plex synchronization workflow rather than forcing an immediate Plex library scan and rematch after a Lidarr acquisition request.

## Context

A Lidarr search is asynchronous. Submitting a search does not guarantee immediate acquisition or Plex availability. A release may not be found, may be rejected, may download later, or may not yet be indexed by Plex.

## Decision

Plex Playlist Importer will not force an immediate Plex library scan or perform an acquisition-wait-refresh-rematch cycle after submitting a Lidarr search request.

```text
Plex Playlist Importer
        |
        | Request search
        v
      Lidarr
        |
        | Acquire and manage media
        v
  Media Library
        |
        | Existing library synchronization
        v
       Plex
        |
        | Discover and index media
        v
Plex Playlist Importer
   (subsequent run)
```

The importer treats Lidarr acquisition as asynchronous. A subsequent importer execution discovers newly available media after Plex and the local cache are updated.

## Rationale

Forcing an immediate end-to-end acquisition cycle would require the importer to coordinate download completion, Lidarr import, Plex scanning, Plex indexing, cache refresh, and rematching. Each stage adds timing, timeout, retry, and failure conditions.

The chosen approach keeps the workflow non-blocking: request acquisition now and discover newly available media during a later run.

## Alternatives Considered

- Force an immediate Plex library scan.
- Wait for Lidarr acquisition to complete.
- Wait, scan Plex, refresh cache, and rematch.
- Make immediate synchronization optional.

All were rejected for the current architecture because they introduce unnecessary coupling and asynchronous orchestration complexity.

## Consequences

Positive: clear responsibility boundaries, non-blocking imports, fewer external failure conditions, natural fit for scheduled execution.

Negative: newly acquired tracks normally appear in the Plex playlist on a later importer run rather than the same execution.

## Future Reconsideration

Reconsider if delayed discovery creates a significant usability problem, reliable event-based notifications become available, or a future orchestration subsystem is explicitly designed to manage the complete asynchronous acquisition lifecycle.
