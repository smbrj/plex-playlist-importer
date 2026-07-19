# ADR-004 — Separate Playlist Sources from the Matching Pipeline

**Status:** Accepted  
**Decision:** Convert supported playlist sources into common application models before matching rather than implementing source-specific matching workflows.

## Context

TXT, CSV, TSV, M3U/M3U8, XMPlaylist, and future sources differ in ingestion but ultimately represent requested tracks.

## Decision

Source-specific processing ends at the common application model. Matching and downstream processing reuse a shared pipeline.

```text
TXT --------+
CSV --------+
TSV --------+
M3U --------+--> Common Playlist Model --> Matching Pipeline
M3U8 -------+
XMPlaylist -+
Future -----+
```

## Rationale

This avoids duplicated matching logic and ensures improvements to normalization, aliases, scoring, and Plex resolution benefit every source.

## Alternatives Considered

Independent workflows for each source and mandatory intermediate playlist files.

## Consequences

Positive: consistent matching, less duplication, easier source extension, independent testing.

Negative: common models must remain broad enough to represent source needs; model changes can affect multiple sources.

## Future Reconsideration

Reconsider only if a future source requires genuinely different matching semantics that cannot reasonably use the common pipeline.
