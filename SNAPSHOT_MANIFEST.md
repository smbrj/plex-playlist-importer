# Documentation Snapshot Manifest

Snapshot purpose: preserve the approved Plex Playlist Importer documentation state so future work does not depend on conversational cache.

## Included exact/final or approved-current documents

- `docs/developer-guide.md` — Developer Guide V1.0 final review copy.
- `PROJECT_HISTORY.md` — Project History V1.0 approved.
- `CHANGELOG.md` — Changelog baseline approved.
- `docs/adr/ADR-002...ADR-010` — approved ADR set (ADR-008 through ADR-010 remain Proposed by design).
- `docs/subsystems/subsystem-overview.md` — approved overview, updated with current pytest mapping.
- `docs/subsystems/matching.md` — approved matching subsystem document, updated with current pytest mapping.
- `docs/subsystems/aliases.md` — approved alias subsystem document, updated with current pytest mapping.

## Approved documents not included because exact approved source text was not present in the active source set

The following documents were approved earlier in the project, but their exact approved text was not available in the current active files when this snapshot was generated. They are intentionally not reconstructed from memory:

- `README.md` V1.0
- `docs/documentation-standards.md`
- `docs/adr/ADR-001-apache-license-2.0.md`

These three should be copied into this snapshot from the user's known-good repository copy when available.

## Test-source note

The uploaded `playlist_import_v2_CURRENT_BASELINE.zip` contained the current Python application modules but did not contain the `tests/` directory.

The subsystem test mappings were verified against the most recent recorded full pytest run:

- 75 tests collected.
- 75 tests passed.
- Python 3.12.10 / pytest 9.1.1.

Primary test mappings added in this snapshot include:

- Matching: `tests/test_matcher_smoke.py`
- Alias usage: `tests/test_alias_usage.py`
- Alias intelligence: `tests/test_alias_intelligence.py`

## Latest snapshot additions

- `docs/subsystems/cache.md` — approved, including `--refresh-cache`, `max_age_hours`, and `--no-cache` operational guidance.
- `docs/subsystems/plex.md` — approved, including the Plex playlist flow, `--dry-run` boundary, and `--no-cache` performance cross-reference.

### Documentation conventions added

- Show relevant CLI options and `config.ini` settings when they materially trigger or control a subsystem flow.
- Document material performance effects of CLI/configuration options in the owning subsystem's Operational Notes.
- Create clean documentation snapshot ZIPs after every few approved documents.
