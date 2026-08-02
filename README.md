# Plex Playlist Importer (PPI)

Plex Playlist Importer (PPI) is a Python application that builds and maintains Plex music playlists from playlist files or optional external music sources.

PPI was designed to provide high-quality matching against a Plex music library while optionally integrating with external services to locate or supplement music that is not currently available locally.

PPI is written in Python and can run on any supported operating system. While Unraid is the developer's preferred production platform, it is **not** a requirement for using PPI.

---

# Features

* High-performance Plex music library matching
* SQLite-based Plex library cache for fast operation
* Configurable fuzzy matching and artist alias support
* Playlist create, update, and trimming operations
* Detailed CSV and HTML reporting
* Operational analytics and run summaries
* Optional external music integrations
* Cross-platform (Windows, Linux, Unraid, and other Python-supported environments)

---

# Optional Integrations

PPI can operate using Plex alone or be extended with one or more optional integrations.

## XMPlaylist

Automatically build and maintain Plex playlists from recent SiriusXM channel history.

The XMPlaylist integration retrieves recently played songs, removes duplicates, matches them against the Plex library, and builds continuously refreshed playlists designed to maximize listening variety.

See **XMPLAYLIST.md** for complete setup and operational information.

---

## Lidarr

Automatically search for music that is missing from the Plex library.

When Plex cannot match a requested track, PPI can optionally submit the corresponding artist or album to Lidarr for acquisition.

Lidarr operates asynchronously and integrates naturally with existing download and Plex library workflows.

See **LIDARR.md** for complete configuration and operational details.

---

## TIDAL

Maintain companion streaming playlists for tracks that are unavailable in the local Plex library.

When enabled, PPI creates and maintains matching TIDAL companion playlists while safely coordinating updates between Plex and TIDAL.

The TIDAL integration includes configurable quality selection, conservative playlist reconciliation, search caching, and detailed diagnostic reporting.

See **TIDAL.md** for complete setup and usage instructions.

---

# Documentation

Additional documentation is provided with the project:

* **INSTALLATION.md** — Installation and platform setup
* **XMPLAYLIST.md** — XMPlaylist integration
* **LIDARR.md** — Lidarr integration
* **TIDAL.md** — TIDAL integration

---

# Platform Support

PPI is written entirely in Python and is intended to be platform independent.

The application has been validated on:

* Microsoft Windows
* Linux
* Unraid

Any operating system capable of running the supported Python version and required dependencies should be able to run PPI.

---

# Configuration

Application configuration is stored in:

```text
config.ini
```

A fully documented sample configuration is provided as:

```text
config.example.ini
```

Copy the sample configuration, update it with your environment-specific values, and enable only the optional integrations you intend to use.

---

# Scheduling

PPI is designed to run unattended using the scheduler of your choice.

Common scheduling options include:

* Unraid User Scripts
* cron
* Windows Task Scheduler

The application is equally suitable for manual execution or automated scheduled operation.

---

# Reporting

PPI generates operational reports including:

* Playlist match reports
* Unmatched-track reports
* Lidarr reports
* TIDAL matched and unmatched diagnostics
* Match analytics
* Latest run status

These reports are intended to assist with troubleshooting, operational monitoring, and integration validation.

---

# Housekeeping

PPI includes housekeeping utilities to maintain logs, reports, and selected runtime databases.

These scripts are intended to be scheduled independently of normal playlist processing and help keep long-running installations clean.

---

# License

See the project license included with this repository.
