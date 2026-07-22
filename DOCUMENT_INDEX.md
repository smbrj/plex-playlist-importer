# DOCUMENT_INDEX.md

## Version
**2.0**

# Documentation Statistics

| Metric | Value |
|---|---:|
| Approved Documents | 29 |
| Architecture Decision Records | 10 |
| Foundation Documents | 3 |
| Architecture Documents | 4 |
| Technical Reference Documents | 16 |
| Reference Aids | 2 |
| Latest Snapshot | Snapshot-013 |

# Technical Reference Documents

All 16 planned technical reference documents are approved through Snapshot-012.

# Reference Aids

| Document | Version | Status | Snapshot | Purpose |
|---|:---:|---|:---:|---|
| GLOSSARY.md | 1.0 | Approved | 013 | Canonical project terminology |
| snapshot_manifest.md | Active | Active | Per snapshot | Snapshot contents and change notes |

# Documentation Roadmap

All currently planned technical reference documents and reference aids are approved.

## Next

- Cross-reference audit
- Terminology audit
- Broken-link audit
- Documentation Version 1.0 baseline
- Final documentation snapshot

## Post-Documentation Technical Cleanup

- Configuration Audit for hard-coded and unused settings.
- Review current `sync` behavior.
- Add dedicated normalization and SearchIndex tests.
- Audit report-writer coverage and schema stability.
- Add runtime exit-code regression tests.
- Review logging configuration and startup.
- Perform controlled Plex playlist-mode tests.
- Protect persistent SQLite compatibility.
- Review analytics CSV and `latest_run.json` schemas.
- Add direct latest-run JSON and analytics failure tests.
- Clarify and test multi-profile analytics semantics.
- Build the Linux/Unraid container.
- Finalize cron scheduling and evaluate `cron.ini`.
- Review operational improvements after TIDAL and before containerization.
- Implement the dashboard using existing analytics/status outputs.

# Maintenance Rules

Whenever documentation changes:

- Update affected documents.
- Update this index when status, version, snapshot, or relationships change.
- Update `GLOSSARY.md` when canonical terminology changes.
- Include changes in the next snapshot.
- Commit documentation changes with corresponding software changes whenever practical.

This document is the authoritative inventory of project documentation.
