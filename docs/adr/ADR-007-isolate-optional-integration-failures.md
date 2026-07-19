# ADR-007 — Isolate Optional Integration Failures

**Status:** Accepted  
**Decision:** Fail optional integrations independently where useful work can safely continue rather than treating every subsystem failure as fatal to the entire run.

## Context

Plex, Lidarr, and XMPlaylist have independent availability and failure modes.

## Decision

Follow the principle:

> Fail only the work that cannot safely continue.

The application should distinguish complete success, degraded/partial success, and fatal failure.

## Rationale

Treating every integration failure as fatal creates unnecessary coupling and discards useful completed work.

## Alternatives Considered

Abort on any integration failure, ignore failures, or retry every failure automatically.

## Consequences

Positive: useful partial results, clearer subsystem attribution, better unattended operation.

Negative: partial success is more complex to communicate and requires explicit safety boundaries.

## Future Reconsideration

Evaluate failure boundaries individually as new integrations are added. Correctness and data integrity take precedence over continued execution.
