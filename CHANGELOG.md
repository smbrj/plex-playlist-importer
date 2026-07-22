# Changelog

All significant changes to Plex Playlist Importer are documented in this file.

This changelog focuses on changes that materially affect application capabilities, operation, compatibility, or significant behavior. Minor implementation changes and routine bug fixes may be summarized or omitted.

## [Unreleased]

### Documentation 1.1 Maintenance

- Updated cache documentation to remove the retired `refresh_on_start` behavior.
- Updated Lidarr documentation to reflect per-entry request-failure isolation.
- Documented the stabilized application exit-code contract and the standard `argparse` exit-code-2 overlap.
- Clarified normalization behavior so legitimate title words such as `Live` and `Clean` are preserved when they are not metadata.
- Clarified that album-artist matching uses a prebuilt normalized SearchIndex lookup.
- Confirmed documented M3U8 input support now matches the released parser implementation and regression coverage.
- Documentation V1.1 reflects Technical Cleanup Checkpoints 001–005 and the validated 145-test regression baseline.


### Added

- Formal project documentation library, including:
  - Developer Guide.
  - Project History.
  - Documentation Standards.
  - Architecture Decision Records.
- Apache License 2.0 project licensing.

### Changed

- Reorganized project documentation so that the README provides a high-level introduction, installation, and basic usage while detailed technical information is maintained under `docs/`.

## Version 2 — Current Application Generation

Version 2 represents the architectural rewrite of Plex Playlist Importer from the original single-purpose CLI script into a modular application designed to support multiple playlist sources and external integrations.

### Added

- Modular `plex_playlist` Python package architecture.
- Common playlist and track data models.
- Support for multiple playlist input formats.
- Configurable metadata normalization and weighted fuzzy matching.
- Match confidence and match-reason reporting.
- Artist alias support.
- Embedded SQLite Plex library caching and local search indexing.
- Persistent alias usage history.
- Centralized application logging.
- CSV reporting for match results and unmatched tracks.
- Automated testing with `pytest`.
- Optional Lidarr integration for checking and searching for media missing from Plex.
- Persistent Lidarr search history.
- XMPlaylist integration for ingesting SiriusXM channel history as a playlist source.
- Persistent XMPlaylist ingestion history and state.
- Configurable XMPlaylist API request controls and deduplication.

### Changed

- Plex library matching moved from repeated live-library processing toward a local cached search model.
- Application architecture separated playlist ingestion, matching, Plex operations, and external integrations into distinct responsibilities.
- Missing tracks can optionally continue through the Lidarr workflow rather than ending with unmatched reporting.
- External playlist sources can reuse the same matching pipeline as file-based playlists.
- Dry-run behavior is defined specifically as preventing Plex playlist modification; explicitly requested external integration operations remain live.

## Version 1 — Initial Proof of Concept

### Added

- Command-line playlist importer.
- TXT playlist parsing using numbered artist-and-title entries.
- Plex music-library connection and track searching.
- Fuzzy artist and track matching.
- Plex playlist creation and update.
- Dry-run support for testing without modifying the Plex playlist.
- CSV reporting of unmatched tracks.
- Basic configuration for Plex server URL, authentication token, and music-library selection.

### Changed

- The initial proof of concept established the feasibility of automatically converting an externally maintained playlist into a Plex playlist and provided the foundation for the Version 2 rewrite.
