# ADR-006 — Treat the Plex Library Cache as a Performance Layer, Not the Authority

**Status:** Accepted  
**Decision:** Use the local Plex library cache for efficient matching while retaining Plex as the authoritative source for actual library identity and playlist operations.

## Context

A large Plex library makes repeated full-library retrieval inefficient. Cached data can also become stale.

## Decision

Use `cache/plex_library.db` and the in-memory search index for matching. Use live Plex when an operation requires actual Plex objects or playlist modification.

## Rationale

The cache improves performance and limited resiliency without creating a second competing library authority.

## Alternatives Considered

Always query Plex directly, treat the cache as authoritative, or maintain an independent media catalog.

## Consequences

Positive: faster matching and limited degraded operation during Plex outages.

Negative: cached matches may later fail live Plex resolution; cache freshness requires management.

## Future Reconsideration

Reconsider if the project evolves beyond Plex as the primary local-library authority or introduces a broader canonical catalog.
