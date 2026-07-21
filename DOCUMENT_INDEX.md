# DOCUMENT_INDEX.md

## Version
**2.0**

---

# Purpose

This document serves as the authoritative inventory of all project documentation.

Whenever documentation is added, revised, approved, or retired, this document should be updated accordingly.

---

# Documentation Statistics

| Metric | Value |
|---------|------:|
| Approved Documents | 24 |
| Architecture Decision Records | 10 |
| Foundation Documents | 3 |
| Architecture Documents | 4 |
| Technical Reference Documents | 16 (planned total) |
| Reference Aids | 2 (planned) |
| Current Documentation Version | 2.0 |
| Latest Snapshot | Snapshot-008 |

---

# Technical Reference Documents

| Document | Version | Status | Snapshot | Depends On | Related Documents |
|----------|:-------:|--------|:--------:|------------|-------------------|
| subsystem-overview.md | 1.0 | Approved | 002 | developer-guide.md | matching.md, cache.md |
| matching.md | 1.0 | Approved | 002 | ADRs | cache.md |
| aliases.md | 1.0 | Approved | 002 | matching.md | search_index.md |
| cache.md | 1.0 | Approved | 002 | matching.md | plex.md |
| plex.md | 1.0 | Approved | 002 | cache.md | reporting.md |
| lidarr.md | 1.0 | Approved | 003 | plex.md | reporting.md |
| xmplaylist.md | 1.0 | Approved | 003 | lidarr.md | reporting.md |
| configuration.md | 1.0 | Approved | 004 | README.md, subsystem-overview.md | cache.md, plex.md, lidarr.md, xmplaylist.md, aliases.md |
| parser.md | 1.0 | Approved | 005 | configuration.md | normalization.md, matching.md |
| normalization.md | 1.0 | Approved | 006 | parser.md | matching.md, aliases.md, search_index.md |
| search_index.md | 1.0 | Approved | 007 | normalization.md | matching.md, cache.md, aliases.md |
| reporting.md | 1.0 | Approved | 008 | matching.md | plex.md, lidarr.md, aliases.md, analytics.md, configuration.md |
| runtime.md | — | Planned | — | configuration.md | deployment.md |
| testing.md | — | Planned | — | runtime.md | deployment.md |
| deployment.md | — | Planned | — | runtime.md | README.md |
| analytics.md | — | Planned | — | reporting.md | runtime.md |

---

# Documentation Roadmap

## Completed

- README.md
- developer-guide.md
- project-history.md
- CHANGELOG.md
- ADR-001 through ADR-010
- subsystem-overview.md
- matching.md
- aliases.md
- cache.md
- plex.md
- lidarr.md
- xmplaylist.md
- configuration.md
- parser.md
- normalization.md
- search_index.md
- reporting.md
- documentation-standards.md Version 2.0
- DOCUMENT_INDEX.md Version 2.0
- documentation-release-process.md Version 1.0

## Next

- runtime.md

## Remaining Technical Documents

- runtime.md
- testing.md
- deployment.md
- analytics.md

## Post-Documentation Technical Cleanup

- Configuration Audit: review hard-coded operational values that should be configurable.
- Configuration Audit: verify existing `config.ini` keys are consumed, or deprecate/remove unused keys.
- Review current `sync` playlist behavior, which presently behaves like `update`.
- Consider parser diagnostics for skipped invalid rows and malformed encoding where useful.
- Add dedicated `tests/test_normalization.py` coverage for all public normalization functions and representative Unicode/version/alias edge cases.
- Review unused normalization constants such as `PAREN_RE`.
- Review stale/commented normalization placeholder logic.
- Add regression tests for broad noise-phrase removal such as `live`.
- Add dedicated `tests/test_search_index.py` coverage for all public SearchIndex lookup methods and title-token overlap rules.
- Evaluate a prebuilt `by_album_artist` index to replace repeated full-library scans.
- Review SearchIndex O(1) wording, read-only/immutability wording, and duplicate-GUID behavior.
- Audit direct test coverage for every current report writer.
- Verify consistent report parent-directory creation and report-write failure handling.
- Verify `[reports]` configuration keys are actually consumed or remove/deprecate them.
- Review HTML-related configuration, dependencies, comments, and docs so nothing implies HTML reporting is currently supported.
- Define schema-stability expectations for CSV reports used by downstream tooling.

## Final Consolidation

- GLOSSARY.md
- Cross-reference audit
- Terminology audit
- Broken-link audit
- Documentation Version 1.0 baseline
- Final documentation snapshot

---

# Maintenance Rules

Whenever documentation changes:

- Update affected documents.
- Update this document if document status, version, or relationships change.
- Include changes in the next documentation snapshot.
- Commit documentation changes with the corresponding software changes whenever practical.

This document is the authoritative inventory of the project's documentation.
