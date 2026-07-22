# GLOSSARY.md

**Document Version:** 1.0  
**Status:** Approved  
**Last Updated:** 2026-07-21  
**Primary Audience:** Developers and Operators  
**Depends On:** DOCUMENT_INDEX.md  
**Related Documents:** All technical reference documents  
**Snapshot:** 013

---

# Purpose

This glossary defines the canonical terminology used throughout the Plex Playlist Importer documentation.

Its goals are to establish consistent terminology, eliminate ambiguous wording, support documentation reviews, simplify cross-reference validation, and provide one authoritative definition for recurring technical terms.

When terminology conflicts arise, this glossary is the authoritative source.

# General Project Terms

## Alias
A user-defined mapping identifying equivalent artist names for matching purposes.

## Analytics
Run-level operational summaries stored for historical analysis.

## Cache
Persistent local SQLite data used to reduce Plex API usage and support degraded operation.

## Component
An external system with which the importer communicates, such as Plex, Lidarr, XMPlaylist, or future TIDAL integration.

## Configuration
Persistent user-editable application settings, primarily stored in `config.ini`.

## Dashboard
Future health-monitoring interface that consumes existing runtime and analytics data rather than creating a separate status model.

## Import Run
One complete execution of the importer.

## Playlist Source
The origin of playlist data, such as file-based input or XMPlaylist.

## RunStatus
The internal runtime-status model used to summarize application health and execution state.

# Matching and Search Terms

## Alias Match
A successful match achieved through a configured artist alias.

## Confidence
The relative quality of a proposed match.

## Exact Match
A match in which artist and title resolve without fuzzy comparison.

## Fallback Match
A successful lower-priority match used after higher-confidence methods fail.

## Fuzzy Match
A match determined using similarity scoring rather than exact equality.

## Match Rate
The ratio of matched tracks to total requested tracks.

## Matching Engine
The subsystem responsible for resolving playlist entries into Plex tracks.

## Search Index
The in-memory lookup structures built from cached Plex library data.

## Track Candidate
A possible Plex track considered during matching.

# Plex Terms

## Library Cache
The SQLite representation of the Plex music library.

## Playlist Mode
The behavior selected when creating or modifying a Plex playlist: CREATE, UPDATE, REPLACE, or SYNC.

## Search Index Refresh
Rebuilding the in-memory search index after refreshing the Plex library cache.

## Stale Cache
A cache older than the configured freshness threshold.

# Lidarr Terms

## Album Search
A Lidarr request asking configured indexers to search for an album.

## Indexer
A search source used by Lidarr.

## Retry Window
The minimum time before retrying a previously unsuccessful Lidarr search.

## Search History
Persistent state used to prevent unnecessary repeated Lidarr searches.

# XMPlaylist Terms

## History Window
The configured amount of SiriusXM playback history to retrieve, currently measured in hours.

## Profile
A named XMPlaylist configuration stored in `resources/xmstations.ini`.

## Request Budget
The maximum number of XMPlaylist API requests permitted during one import run.

## Rolling History
Playback history accumulated across multiple importer runs.

## Station
One SiriusXM channel.

# Analytics and Reporting Terms

## Historical Analytics
Persistent run-level summaries stored in `reports/match_analytics.csv`.

## Latest Run
Machine-readable status for the most recent import run, stored in `reports/latest_run.json`.

## Report
Detailed output describing one importer execution or one workflow within that execution.

## Trend
Operational behavior observed across multiple import runs.

## Warning
A degraded condition that does not necessarily invalidate the import run.

# Deployment Terms

## Container
The future Linux deployment package for the importer.

## Persistent Storage
Host-mounted storage that survives container restart, recreation, and image upgrade.

## Scheduler
The mechanism responsible for unattended importer execution. The current working preference is cron inside the container.

## cron.ini
A possible future user-maintained configuration file that generates the actual crontab. It is not currently implemented.

# Testing Terms

## Fixture
Reusable test data or setup.

## Integration Test
A test involving multiple subsystems or an application workflow.

## Mock
A simulated external dependency or controlled replacement used during testing.

## Regression Test
A test intended to prevent reintroduction of a previously corrected defect.

## Unit Test
A test targeting one isolated function, method, or class.

# Future TIDAL Terms

## Companion Playlist
A TIDAL playlist containing tracks unavailable in the local Plex library.

## Missing Track
A track unavailable in the local Plex library.

## Routed Track
A track intentionally directed to the TIDAL companion playlist.

# Canonical Terminology Rules

| Preferred Term | Avoid or Limit |
|---|---|
| Import Run | Job or process when referring to one complete execution |
| Playlist Source | Input file when the source may not be a file |
| Match Rate | Success percentage |
| Search Index | Index cache |
| History Window | Lookback |
| Request Budget | API limit |
| Historical Analytics | Statistics |
| Latest Run | Current JSON |
| Dashboard | GUI, unless referring to a desktop interface |
| Component Health | Service status |
| Companion Playlist | Missing playlist |

These rules establish preferred terminology for the specific project concepts defined here.

# Abbreviations

| Abbreviation | Meaning |
|---|---|
| API | Application Programming Interface |
| CLI | Command-Line Interface |
| CSV | Comma-Separated Values |
| GUID | Globally Unique Identifier |
| JSON | JavaScript Object Notation |
| KISS | Keep It Simple, Stupid |
| SQLite | Lightweight embedded relational database |
| TSV | Tab-Separated Values |
| UTF-8 | Unicode Transformation Format, 8-bit |
| XML | Extensible Markup Language |

# Maintenance

When a significant new technical concept is introduced:

1. Add or revise its canonical glossary definition.
2. Update affected documents.
3. Include the change in the next documentation snapshot.
4. Include terminology changes in the next terminology audit.

# Design Principle

> Every significant technical term should have one canonical definition, and every document should use that definition consistently.
