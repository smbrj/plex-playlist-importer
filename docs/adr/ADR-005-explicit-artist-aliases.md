# ADR-005 — Use Explicit Artist Aliases Rather Than Loosening Global Matching Rules

**Status:** Accepted  
**Decision:** Handle known artist-name equivalence through explicit aliases rather than globally weakening artist matching requirements.

## Context

Known naming differences can prevent legitimate matches. Globally loosening fuzzy matching to solve isolated cases increases false-positive risk.

## Decision

Use explicit artist aliases to supplement matching while keeping global matching conservative.

## Rationale

Known alias relationships are specific knowledge. Recording them directly is safer and more explainable than making every artist comparison more permissive.

## Alternatives Considered

Lower global artist thresholds, hard-coded special cases, and normalization alone.

## Consequences

Positive: conservative global rules, explainable alias-assisted matches, maintainable user knowledge.

Negative: aliases require maintenance and incorrect aliases can create incorrect matches.

## Future Reconsideration

Reconsider if alias maintenance becomes burdensome or reliable automated identity discovery becomes available. More complex alias structures should be introduced only when demonstrated real-world needs justify them.
