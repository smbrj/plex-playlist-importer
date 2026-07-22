# DOCUMENT_INDEX.md

## Version
**2.0**

# Documentation Statistics

| Metric | Value |
|---------|------:|
| Approved Documents | 28 |
| Architecture Decision Records | 10 |
| Foundation Documents | 3 |
| Architecture Documents | 4 |
| Technical Reference Documents | 16 |
| Reference Aids | 2 (planned) |
| Latest Snapshot | Snapshot-012 |

# Technical Reference Documents

| Document | Version | Status | Snapshot |
|----------|:-------:|--------|:--------:|
| subsystem-overview.md | 1.0 | Approved | 002 |
| matching.md | 1.0 | Approved | 002 |
| aliases.md | 1.0 | Approved | 002 |
| cache.md | 1.0 | Approved | 002 |
| plex.md | 1.0 | Approved | 002 |
| lidarr.md | 1.0 | Approved | 003 |
| xmplaylist.md | 1.0 | Approved | 003 |
| configuration.md | 1.0 | Approved | 004 |
| parser.md | 1.0 | Approved | 005 |
| normalization.md | 1.0 | Approved | 006 |
| search_index.md | 1.0 | Approved | 007 |
| reporting.md | 1.0 | Approved | 008 |
| runtime.md | 1.0 | Approved | 009 |
| testing.md | 1.0 | Approved | 010 |
| deployment.md | 1.0 | Approved | 011 |
| analytics.md | 1.0 | Approved | 012 |

# Documentation Roadmap

All currently planned technical reference documents are approved.

## Next

- GLOSSARY.md
- Cross-reference audit
- Terminology audit
- Broken-link audit
- Documentation baseline/final consolidation snapshot

## Post-Documentation Technical Cleanup

- Configuration Audit for hard-coded and unused settings.
- Review current `sync` behavior.
- Add dedicated normalization and SearchIndex tests.
- Audit report-writer coverage and schema stability.
- Add runtime exit-code regression tests.
- Review logging configuration/startup.
- Perform controlled Plex playlist-mode tests.
- Protect persistent SQLite compatibility.
- Review analytics CSV and `latest_run.json` schemas.
- Add direct latest-run JSON and analytics failure tests.
- Clarify/test multi-profile analytics semantics.
- Build the Linux/Unraid container.
- Finalize cron scheduling and evaluate `cron.ini`.
- Review real-world operational improvements after TIDAL and before containerization.
- Implement the dashboard using existing analytics/status outputs.

# Reference Aids

| Document | Status |
|----------|--------|
| GLOSSARY.md | Planned |
| snapshot_manifest.md | Active |

This document is the authoritative inventory of project documentation.
