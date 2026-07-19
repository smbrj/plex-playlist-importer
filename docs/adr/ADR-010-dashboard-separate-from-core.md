# ADR-010 — Keep the Operational Dashboard Separate from Core Execution

**Status:** Proposed  
**Decision:** If an operational dashboard is implemented, use it as an observability and status interface rather than making it a required component of playlist processing.

## Context

Headless scheduled operation creates a future need for convenient visibility into run status, matching, integration health, warnings, and historical activity.

## Decision

```text
Scheduled / Manual Invocation
          |
          v
   Core Application
          |
          +--> Logs
          +--> Reports
          +--> Persistent Status / History
                    |
                    v
             Future Dashboard
```

The core application must function without the dashboard.

## Rationale

Making a dashboard part of the required execution path would introduce an unnecessary dependency and complicate a workload that is fundamentally scheduled/on-demand.

## Alternatives Considered

Integrate the dashboard directly into the core application, use the dashboard as the scheduler, or provide no dashboard.

## Consequences

Positive: dashboard outages do not stop imports; observability can evolve independently.

Negative: status schemas and history require explicit design; the dashboard becomes another component to package and secure.

## Future Reconsideration

Review when dashboard design begins, including data needs, persistence, read/write scope, authentication, network exposure, and deployment topology.
