# ADR-009 — Target Headless Containerized Deployment

**Status:** Proposed  
**Decision:** Design the application toward headless Linux container deployment with scheduled execution while keeping containerization separate from core application logic.

## Context

The long-term deployment target is a Linux-based container hosted on an Unraid server. The intended model includes headless execution, manual CLI runs, scheduled runs, persistent state, and graceful handling of external-service failures.

## Decision

Keep the core application CLI/headless and suitable for a Linux container. Persistent data must survive container replacement. Container concerns should remain outside core matching and integration logic where practical.

## Rationale

A headless model fits scheduled server operation and allows containerization to package runtime dependencies without making the core application dependent on a graphical interface.

## Alternatives Considered

Desktop GUI as the primary interface, native-host-only installation, and embedding scheduling directly in the application.

## Consequences

Positive: unattended operation, consistent deployment, durable externalized state, direct CLI usability.

Negative: persistent volumes, permissions, paths, networking, scheduling, and Linux/Windows differences require deliberate testing.

## Future Reconsideration

Review when containerization begins and persistent paths, scheduling, exit codes, and health/status reporting are finalized.
