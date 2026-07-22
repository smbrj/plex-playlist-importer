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
| Latest Snapshot | Snapshot-018 |

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
- Terminology audit — Complete; corrections applied in Snapshot-015
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


## Documentation Consolidation Status

- Cross-reference audit: Complete.
- Cross-reference corrections: Complete.
- Terminology audit: Complete.
- Terminology corrections: Complete.
- Broken-link/filesystem audit — Complete; filesystem corrections applied in Snapshot-016: In progress.
- Documentation Version 1.0 baseline: Complete — Snapshot-017.


---

## Documentation Version 1.0 Baseline

**Status:** Complete  
**Baseline Snapshot:** Snapshot-017  
**Baseline Date:** 2026-07-22

Snapshot-017 establishes the first consolidated documentation baseline after completion of:

- Technical reference drafting and approval.
- Glossary approval.
- Cross-reference audit and corrections.
- Terminology audit and corrections.
- Broken-link/filesystem audit and corrections.

Future documentation changes should be made against this baseline and included in subsequent documentation snapshots.

---

## Documentation Version 1.1 Maintenance Release

**Status:** Approved  
**Date:** 2026-07-22  
**Base:** Documentation V1.0 / Snapshot-017
**Approval Date:** 2026-07-22

Documentation V1.1 synchronizes the approved documentation with Technical Cleanup Checkpoints 001–005.

Maintenance scope:

- Retire obsolete `refresh_on_start` documentation.
- Reflect current Lidarr per-entry request-failure isolation.
- Record the stabilized and regression-tested process exit-code contract.
- Clarify normalization behavior introduced by Cleanup Checkpoint-002.
- Clarify indexed album-artist SearchIndex behavior introduced by Cleanup Checkpoint-003.
- Confirm M3U8 parser implementation now conforms to the already documented supported-format contract.
- Record the validated full regression baseline of 145 passing tests.

No new roadmap feature is introduced by Documentation V1.1.



---

## Current Documentation Release Status

- Documentation V1.0 baseline: Complete — Snapshot-017.
- Documentation V1.1 maintenance release: Approved.
- V1.1 release snapshot: Complete — Snapshot-018.
