# Plex Playlist Importer

Plex Playlist Importer is a reliable command-line application for importing playlists into Plex, intelligently matching tracks, and helping you build a more complete music library.

## Table of Contents

* [Introduction](#introduction)
* [Overview](#overview)
* [At a Glance](#at-a-glance)
* [Why This Project Exists](#why-this-project-exists)
* [Features](#features)
* [Supported Input Formats](#supported-input-formats)
* [Optional Integrations](#optional-integrations)
* [Requirements](#requirements)
* [Installation](#installation)
* [Configuration](#configuration)
* [Quick Start](#quick-start)
* [Generated Reports](#generated-reports)
* [Design Principles](#design-principles)
* [Documentation](#documentation)
* [Current Status](#current-status)
* [Roadmap](#roadmap)
* [Contributing](#contributing)
* [License](#license)

---

## Introduction

Building playlists within Plex is easy.

Importing playlists into Plex is not.

Plex does not natively support importing playlist files such as CSV, M3U, or other common playlist formats. Creating a playlist within Plex generally requires locating individual tracks and adding them to a playlist through the user interface.

For a small playlist, that process may be manageable. For playlists containing hundreds or thousands of tracks, it quickly becomes repetitive and time-consuming.

Plex Playlist Importer was created to automate that process.

The application reads playlists from external sources, intelligently matches the requested music against an existing Plex music library, and creates or updates Plex playlists automatically.

The project emphasizes reliability, transparency, and maintainability. It is designed to operate interactively from the command line today and ultimately as a self-contained, unattended service suitable for scheduled execution.

---

## Overview

Plex Playlist Importer accepts playlist data from several common formats and converts each entry into a common internal representation.

The matching engine then compares each requested track against a locally cached representation of the Plex music library. Exact matching, configurable fuzzy matching, metadata normalization, and artist aliases help identify the best available Plex track.

Matched tracks can be used to create a new Plex playlist, update an existing playlist, or completely replace the contents of an existing playlist.

Tracks that cannot be matched are documented for review and can optionally be evaluated through Lidarr to determine whether the missing music is available for acquisition.

The application can also use XMPlaylist channel history as a playlist source, allowing recent SiriusXM programming to be recreated as continuously refreshed Plex playlists.

Throughout the process, reports, analytics, persistent history, and operational logs provide visibility into what happened during each run.

### Application Flow

```text
                    Playlist Sources
          TXT / CSV / TSV / M3U / XMPlaylist
                         |
                         v
                 Input Normalization
                         |
                         v
                  Matching Engine
                         |
              +----------+----------+
              |                     |
              v                     v
       Matched Plex Tracks     Unmatched Tracks
              |                     |
              |                     v
              |              Optional Lidarr
              |              Diagnostics/Search
              |                     |
              +----------+----------+
                         |
                         v
                  Plex Playlist
             Create / Update / Replace
                         |
                         v
              Reports / Analytics / Logs
```

The application deliberately keeps playlist management, media acquisition, and media library management as separate responsibilities. Plex Playlist Importer manages playlist creation and matching, while Plex and Lidarr continue to perform their existing library management and synchronization functions.

---

## At a Glance

* Import playlists from multiple common file formats.
* Create, update, or replace Plex playlists.
* Build Plex playlists from XMPlaylist SiriusXM channel history.
* Match tracks using exact and configurable fuzzy matching.
* Use artist aliases to resolve naming differences.
* Preserve playlist order.
* Identify and report unmatched tracks.
* Optionally use Lidarr to diagnose and search for missing music.
* Maintain a local Plex library cache for efficient matching.
* Maintain persistent operational and integration history using embedded SQLite databases.
* Generate detailed CSV and HTML reports.
* Produce match analytics and runtime health information.
* Support dry-run operation before modifying Plex.
* Continue operating gracefully when optional external services are unavailable.
* Designed for unattended, scheduled execution.

---

## Why This Project Exists

Plex is an excellent platform for managing and playing a personal music library.

Building playlists within Plex is easy.

Importing playlists into Plex is not.

Plex does not natively provide a general-purpose mechanism for importing common external playlist formats such as CSV, TSV, or M3U. Recreating an existing playlist therefore often means manually searching for each track and adding it through the Plex interface.

Plex Playlist Importer exists to bridge that gap.

The application automates the repetitive work while recognizing that music metadata is rarely perfect. Artist names differ. Track titles contain remaster information. Featured artists may be represented differently. Album metadata changes between releases.

For that reason, the project evolved beyond simple playlist importing into a matching and library-improvement workflow.

The importer attempts to find the best available match, explains how the match was made, identifies tracks that could not be found, and optionally works with Lidarr to help determine whether missing music can be added to the library.

The goal is not simply to create a playlist.

The goal is to create the most complete playlist possible while making the results understandable.

---

## Features

### Playlist Import

* Import external playlists into Plex.
* Create new Plex playlists.
* Update existing Plex playlists.
* Replace existing playlist contents.
* Preserve playlist order.
* Skip duplicate tracks according to configuration.
* Validate imports using dry-run mode.

### Intelligent Matching

* Exact artist and title matching.
* Configurable fuzzy matching.
* Weighted artist, album artist, title, and combined matching.
* Metadata normalization.
* Configurable handling of remaster, live, featured artist, and deluxe metadata.
* Artist alias support.
* Match confidence and reason reporting.
* Fallback matching when appropriate.

### Alias Intelligence

* Maintain artist aliases for known naming differences.
* Export the Plex artist inventory for analysis.
* Analyze unmatched artists and suggest possible aliases.
* Import approved alias suggestions.
* Audit configured aliases.
* Track persistent alias usage and effectiveness.

### Library Improvement

* Identify unmatched tracks.
* Produce actionable unmatched-track reports.
* Optionally evaluate unmatched music through Lidarr.
* Search for missing albums when explicitly requested.
* Maintain Lidarr search history to avoid unnecessary repeated searches.
* Allow later scheduled runs to discover music acquired between executions.

### XMPlaylist Integration

* Build playlists from SiriusXM channel history.
* Select stations by SiriusXM channel number.
* Use configurable rolling history windows.
* Limit API requests per execution.
* Target a configurable number of unique tracks per execution.
* Deduplicate tracks before matching.
* Persist ingestion state between runs.
* Resume partial history backfills.
* Support station-specific preferences and playlist naming.
* Respect API request budgets and rate limits.

### Reporting and Analytics

* Detailed CSV match reports.
* HTML summary reports.
* Unmatched-track reports.
* Lidarr diagnostic and acquisition reports.
* Match analytics history.
* Latest-run status information.
* Runtime health reporting.
* Cache status and refresh information.
* Operational logging for troubleshooting.

### Resiliency

* Use a persistent local Plex library cache.
* Detect stale Plex cache entries during playlist resolution.
* Exit gracefully when cached media no longer exists in Plex.
* Continue matching from the local cache when appropriate.
* Degrade gracefully when optional integrations are unavailable.
* Report component health at the end of each run.

### Automation

* Command-line operation.
* Configuration-driven behavior.
* Suitable for Windows Task Scheduler or cron.
* Designed for future containerized deployment.
* Intended for unattended scheduled execution.

---

## Supported Input Formats

Plex Playlist Importer is designed to work with playlist data from a variety of sources. Rather than requiring a single proprietary format, the importer accepts several common text-based formats that can be created by media players, spreadsheets, online services, or simple text editors.

Currently supported formats include:

| Format     | Typical Source                    |
| ---------- | --------------------------------- |
| TXT        | Plain text playlists              |
| CSV        | Spreadsheets and exported reports |
| TSV        | Spreadsheet exports               |
| M3U / M3U8 | Standard playlist files           |

Each format is parsed into a common internal representation before matching begins. This allows the matching engine to operate consistently regardless of the original source of the playlist.

XMPlaylist channel history is also supported as a direct playlist source and does not require an intermediate playlist file.

---

## Optional Integrations

Plex Playlist Importer is fully functional for file-based playlist imports without Lidarr or XMPlaylist.

Optional integrations extend the application's capabilities but are not required for normal playlist importing.

### Lidarr

When enabled, unmatched tracks can be evaluated through Lidarr to determine whether the artist and album are managed or available for acquisition.

Album searches are explicitly requested and operate independently from the Plex playlist update process. The importer does not force a Plex library scan after a Lidarr request. Instead, it relies on the existing synchronization mechanisms between Lidarr and Plex, allowing newly acquired music to be discovered during a later importer run.

### XMPlaylist

XMPlaylist integration uses SiriusXM channel history as a playlist source.

The importer can retrieve recent channel history, collect unique tracks across multiple API pages, preserve ingestion state between executions, and create or refresh corresponding Plex playlists.

History windows, request budgets, unique-track targets, and station-specific preferences can be configured to balance playlist freshness with API usage.

---

## Requirements

Plex Playlist Importer is designed to run in a standard Python environment and communicate with an existing Plex Media Server.

### Required

* Python 3.12 or later.
* Plex Media Server.
* Access to the target Plex music library.
* A valid Plex authentication token.

### Optional

* Lidarr for missing-music diagnostics and acquisition requests.
* XMPlaylist API access for SiriusXM channel-history playlists.

The application has very few runtime dependencies and uses embedded SQLite databases to maintain the persistent data required for efficient operation, including library caching, application history, and integration metadata.

Because these databases are self-contained, no separate database server or additional background services are required.

The application has been developed and tested primarily on Windows while remaining designed for portable execution on platforms supported by Python. Containerized Linux and Unraid deployment are planned as the final production deployment model.

---

## Installation

Obtain the application source:

```bash
git clone <repository-url>
cd plex-playlist-importer
```

Create and activate a Python virtual environment if desired:

```bash
python -m venv .venv
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Configure the application before performing the first import.

---

## Configuration

Application behavior is controlled through configuration files rather than changes to the application source.

The primary `config.ini` file contains system and application configuration, including:

* Plex server connection.
* Plex authentication.
* Music library selection.
* Matching thresholds and weights.
* Metadata normalization.
* Cache behavior.
* Reporting.
* Logging.
* Lidarr integration.
* XMPlaylist integration.

Station-specific XMPlaylist preferences are maintained separately from the primary system configuration so that operational station choices do not become mixed with core application settings.

Configuration files containing authentication tokens or other environment-specific information should not be committed to public source-control repositories.

Complete configuration details are documented separately in the project's configuration reference.

---

## Quick Start

Validate a playlist without modifying Plex:

```bash
python playlist_import_v2.py playlist.txt --dry-run
```

Create a Plex playlist:

```bash
python playlist_import_v2.py playlist.txt --playlist "My Playlist"
```

For a simple text playlist, enter one track per line using the following format:

```text
<number>. <artist> - <title>
```

For example:

```text
1. Bob Dylan - Like a Rolling Stone
2. The Rolling Stones - Satisfaction
3. John Lennon - Imagine
4. Marvin Gaye - What's Going On
```

For complete details about supported playlist formats and their required fields, see the playlist input format documentation in `docs/`.


Update an existing playlist:

```bash
python playlist_import_v2.py playlist.txt --playlist "Road Trip" --update
```

Replace an existing playlist:

```bash
python playlist_import_v2.py playlist.txt --playlist "Road Trip" --replace
```

Build or update a playlist from XMPlaylist channel history:

```bash
python playlist_import_v2.py \
    --xmstation 14 \
    --xmhours 8 \
    --xm-max-requests 3 \
    --update
```

Validate an XMPlaylist import and evaluate unmatched tracks through Lidarr without modifying Plex:

```bash
python playlist_import_v2.py \
    --xmstation 14 \
    --xmhours 8 \
    --xm-max-requests 3 \
    --dry-run \
    --lidarr-check
```

After each run, review the generated reports for unmatched tracks, metadata warnings, and match confidence information.

---

## Generated Reports

Plex Playlist Importer is designed to make each run understandable.

Depending on configuration and the options used, the application can generate:

| Report                | Purpose                                                     |
| --------------------- | ----------------------------------------------------------- |
| Playlist Match Report | Detailed matching results and confidence information        |
| HTML Report           | Human-readable import summary                               |
| Unmatched Report      | Tracks that could not be matched in Plex                    |
| Lidarr Report         | Diagnostic and acquisition information for unmatched tracks |
| Alias Suggestions     | Proposed artist aliases for review                          |
| Alias Audit           | Alias validity and usage information                        |
| Match Analytics       | Historical matching statistics                              |
| Latest Run Status     | Machine-readable operational status                         |
| Log Files             | Runtime, warning, and diagnostic information                |

Rather than simply reporting success or failure, the importer provides enough information to understand what happened and why.

This reporting model also provides the foundation for the project's planned operational health dashboard.

---

## Design Principles

Plex Playlist Importer was developed around a small set of guiding principles that influence major design decisions.

* **Reliability before cleverness** — predictable, understandable behavior is preferred over unnecessary complexity.
* **Self-contained deployment** — configuration, persistent state, reports, and logs remain within the application's deployment environment wherever practical.
* **Separation of responsibilities** — the importer manages playlist importing and matching while Plex, Lidarr, and other integrated systems retain responsibility for their own functions.
* **Transparency through reporting** — users should be able to understand what happened during a run and why.
* **Maintainability through clear architecture** — modular components, documented decisions, regression testing, and configuration-driven behavior support long-term maintenance.

These principles are discussed in greater detail in the Developer Guide and are reflected throughout the project's Architecture Decision Records (ADRs).

---

## Documentation

The project documentation is organized by audience and purpose.

| Document                          | Purpose                                                                |
| --------------------------------- | ---------------------------------------------------------------------- |
| `README.md`                       | Project overview, installation, and getting started                    |
| `DEVELOPER_GUIDE.md`              | Architecture, implementation, and development practices                |
| `CONTRIBUTING.md`                 | Contribution guidelines and development workflow                       |
| `CHANGELOG.md`                    | Release history                                                        |
| `docs/PROJECT_HISTORY.md`              | Project origins, foundational decisions, and evolution                 |
| `docs/documentation-standards.md` | Documentation philosophy, standards, and conventions                   |
| `docs/configuration.md`           | Configuration reference                                                |
| `docs/subsystem-overview.md`            | System architecture                                                    |
| `docs/runtime.md`        | End-to-end application processing flow                                 |
| `docs/testing.md`                 | Testing strategy and regression testing                                |
| `docs/runtime.md`                 | Logging, diagnostics, and operational troubleshooting                  |
| `docs/`                | Detailed subsystem documentation                                       |
| `docs/adr/`                       | Architecture Decision Records explaining significant project decisions |

The README introduces concepts. The supporting documentation explains them in greater detail.

---

## Current Status

Plex Playlist Importer is under active development.

Core playlist importing, intelligent matching, alias intelligence, reporting, analytics, Lidarr integration, XMPlaylist ingestion, embedded persistence, and runtime resiliency are operational.

The application is currently being exercised under normal operating conditions while existing capabilities are polished and hardened.

Development continues to emphasize reliability, maintainability, and incremental improvement over rapid feature growth.

---

## Roadmap

The remaining major development areas are intentionally focused on preparing the application for long-term unattended operation.

Planned areas include:

* Additional operational hardening.
* Improved Lidarr progress reporting and per-track error isolation.
* Continued reporting and analytics improvements.
* Containerized Linux and Unraid deployment.
* Scheduled playlist imports using cron within the production deployment environment.
* An operational dashboard providing overall application and integration health.

Once containerized scheduled execution and the health dashboard are complete and the application has demonstrated stable unattended operation, the project will be considered functionally complete for its current scope.

Future development may continue as new requirements and ideas emerge.

---

## Contributing

Contributions are welcome.

Before submitting significant changes, contributors should review:

* `CONTRIBUTING.md`
* `DEVELOPER_GUIDE.md`
* `docs/documentation-standards.md`
* Relevant Architecture Decision Records in `docs/adr/`

Understanding the project's design principles and the reasoning behind existing architectural decisions helps ensure that new features remain consistent with the overall direction of the project.

Significant decisions should be documented as close as possible to the time they are finalized and agreed upon.

---

## License

Plex Playlist Importer is licensed under the Apache License 2.0.

The Apache License 2.0 permits use, modification, distribution, and commercial use of the software subject to the terms and conditions of the license.

See the `LICENSE` and `NOTICE` files included with the project for complete licensing and attribution information.
