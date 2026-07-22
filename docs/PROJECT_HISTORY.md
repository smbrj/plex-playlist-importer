# Plex Playlist Importer — Project History

## 1. Project Origins

Plex Playlist Importer began as a solution to a simple limitation: Plex makes building playlists within Plex easy, but it does not natively provide a general-purpose way to import externally created playlist files into a Plex music library.

For large playlists, manually searching for each track and adding it through the Plex interface is impractical. The original goal was therefore straightforward: read a text file containing artist and track information, find the corresponding music in Plex, and create the playlist automatically.

What began as a small command-line utility would eventually grow well beyond that original purpose.

## 2. Version 1 — Proof of Concept

Version 1 established that the basic idea worked.

The application could read a simple text playlist, search the Plex music library, use fuzzy matching to account for differences in music metadata, create or update a Plex playlist, and report tracks that could not be matched.

Dry-run support allowed the matching process to be tested without modifying the Plex playlist.

The first version successfully demonstrated the core workflow:

```text
External Playlist
       |
       v
Match Against Plex
       |
       v
Create Plex Playlist
```

More importantly, Version 1 provided real-world experience with the problems involved in matching externally sourced music metadata against a large personal Plex library.

Those lessons shaped the next generation of the application.

## 3. Lessons from Version 1

Real-world use showed that importing playlists involved more than simply comparing artist and track names.

Music metadata varies between sources. Artist names, album artists, punctuation, remaster descriptions, featured performers, and other metadata differences can prevent legitimate matches. At the same time, making matching too permissive can result in the wrong track being selected.

The growing Plex library also made repeatedly retrieving and processing the entire library inefficient.

As additional capabilities were considered, the original script structure became increasingly difficult to extend cleanly. Matching, Plex access, parsing, reporting, and future integrations needed clearer boundaries.

Version 1 had proven the concept.

It also demonstrated that the project needed to evolve from a single-purpose script into a more structured application.

## 4. Version 2 — The Rewrite

Version 2 was a deliberate architectural rewrite.

The application was reorganized into a Python package with separate components responsible for parsing, normalization, matching, Plex communication, caching, logging, and other application functions.

The rewrite established a common internal representation for playlist entries so that the matching process would not depend on where playlist data originated.

This created an important foundation for future growth. A playlist could come from a text file, CSV, M3U, or eventually an external service while continuing to use the same core matching pipeline.

Version 2 marked the transition from:

```text
A script that imports a playlist into Plex
```

to:

```text
An application for ingesting, matching,
and resolving playlist data across multiple systems
```

## 5. Version 2 — The Foundation

The early Version 2 development cycle focused on creating the capabilities required for the application to grow reliably.

Matching became more structured and explainable, with normalization, configurable scoring, confidence information, and match reasons. Artist aliases were introduced to handle known metadata differences without weakening matching rules globally.

A local SQLite Plex library cache improved performance when working with a library of approximately 56,000 tracks. SQLite later became the persistence mechanism for additional application history and state.

Reporting and centralized logging improved operational visibility.

Automated testing became a normal part of development through `pytest`, with later subsystems such as Lidarr and XMPlaylist receiving dedicated tests.

Together, these changes established the platform on which subsequent integrations and operational improvements could be built.

## 6. Later Milestones and Current Direction

Once the Version 2 foundation was established, development expanded beyond importing static playlist files.

### Lidarr Integration

Lidarr integration extended the workflow for tracks that could not be found in Plex. The application gained the ability to check whether missing music was known to Lidarr and, when explicitly requested, initiate searches for unavailable albums.

Operational experience showed that a completed Lidarr search does not necessarily mean that media was acquired. Search history and acquisition status therefore became persistent application knowledge.

The project also deliberately retained the existing responsibility boundary between Lidarr and Plex: Lidarr manages media acquisition, Plex manages its library synchronization, and the importer discovers newly available tracks during a later run rather than forcing an immediate Plex scan and rematch.

The detailed reasoning for this architectural decision is preserved in ADR-002.

### XMPlaylist Integration

XMPlaylist introduced the first external service capable of acting as a playlist source.

The idea began as a separate utility for extracting approximately 30 days of SiriusXM channel history into a CSV file. As the concept was explored, it became clear that XMPlaylist data could feed directly into the existing Version 2 ingestion and matching pipeline.

The design evolved from long history windows measured in days toward shorter rolling windows measured in hours. Deduplication, API request limits, persistent history, and resumable ingestion were added to support practical use within XMPlaylist service limits.

This milestone demonstrated one of the primary benefits of the Version 2 rewrite: a completely different playlist source could reuse the application's existing matching and Plex workflow.

### Operational Resiliency

As Plex, Lidarr, and XMPlaylist became part of the same workflow, failure handling became increasingly important.

The application evolved toward isolating subsystem failures where useful work could still continue. The local Plex cache also created the possibility of continuing matching work when Plex itself was temporarily unavailable, while safely skipping operations that required a live Plex server.

This moved the project toward a more resilient model suitable for future unattended and scheduled operation.

### Documentation and Project Maturity

As the application grew, documentation itself became a formal part of the project.

The original approach of placing extensive user, operational, architectural, and support information in a single README became difficult to maintain and navigate.

The documentation was reorganized so that each document serves a specific purpose:

- `README.md` introduces the application and provides installation and basic usage.
- `docs/developer-guide.md` describes the current architecture and development model.
- `docs/PROJECT_HISTORY.md` records how the project evolved.
- `CHANGELOG.md` records changes between releases.
- Architecture Decision Records preserve the reasoning behind significant decisions.
- Reference and subsystem documentation provide deeper detail where needed.

The project adopted Apache License 2.0; the licensing decision and rationale are preserved in ADR-001.

### Current Direction

Plex Playlist Importer has evolved from a simple command-line utility for creating a Plex playlist from a text file into a modular playlist-ingestion application with local matching, persistent state, missing-media integration, and external playlist-source capabilities.

The current development direction continues to favor a headless application suitable for scheduled operation and eventual containerized deployment on Linux/Unraid.

Future work includes evaluating TIDAL as a companion playlist destination for music unavailable locally, completing the containerized deployment model, and eventually providing an operational dashboard. These remain future capabilities and are not part of the currently released functionality.

The progression of the project can be summarized as:

```text
TXT Playlist Import
        |
        v
Fuzzy Plex Matching
        |
        v
Version 2 Modular Architecture
        |
        v
Improved Matching and Local Persistence
        |
        v
Lidarr Missing-Media Integration
        |
        v
XMPlaylist External Ingestion
        |
        v
Resilient, Headless Scheduled Operation
        |
        v
Future Containerization and Operational Visibility
```

The project's scope has grown considerably since its first version, but its original purpose remains unchanged:

> Make externally sourced playlists practical to use with a Plex music library.
