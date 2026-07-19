# Plex Playlist Importer Developer Guide

**Version:** 1.0  
**Document location:** `docs/developer-guide.md`

1. Introduction
Plex Playlist Importer is a Python command-line application designed to import externally defined music
playlists into a Plex music library.


At its simplest, the application solves a straightforward problem: Plex can create and manage playlists, but
it does not provide a general-purpose mechanism for importing playlists from common external formats.


The original application therefore had a simple objective:


    1. Read a list of requested tracks.
    2. Find those tracks in Plex.
    3. Create a Plex playlist.

In practice, the second step proved to be considerably more complex than the first and third.


Music metadata is rarely consistent across different sources. The same track may appear under different
artist names, album artists, title variations, remaster descriptions, featured-artist notations, or release
metadata. A strict text comparison that works for one playlist may fail unnecessarily for another.


As a result, Plex Playlist Importer evolved from a simple playlist loader into a matching and library-
improvement system.


The application now combines several related capabilities:


     • Playlist input and normalization.
     • Local Plex library caching.
     • Exact and fuzzy track matching.
     • Artist alias management.
     • Match confidence and reason reporting.
     • Unmatched-track analysis.
     • Optional Lidarr integration.
     • XMPlaylist channel-history ingestion.
     • Persistent operational state.
     • Reporting and historical analytics.
     • Runtime health monitoring.

These capabilities support a common objective:


       Build the most complete Plex playlist possible while making the application's decisions
       understandable.


The importer does not attempt to replace the systems with which it integrates.


                                                       1

Plex remains responsible for managing and serving the media library.


Lidarr remains responsible for managing artists, albums, and media acquisition.


XMPlaylist remains the source of SiriusXM channel-history information.


Plex Playlist Importer coordinates information from these systems for the specific purpose of building and
maintaining Plex playlists.


This separation of responsibilities is an important part of the application's architecture and influences many
of the design decisions described throughout this guide.


2. Purpose and Audience
This Developer Guide explains how Plex Playlist Importer is designed, how its major components interact,
and how developers can safely maintain or extend the application.


It is intended primarily for:


      • Developers modifying the application.
      • Contributors adding or reviewing functionality.
      • Future maintainers learning the codebase.
      • Operators who need a deeper understanding of runtime behavior.

The guide is not intended to replace the README or user reference documentation.


The documentation library separates information according to audience and purpose.


The README answers questions such as:


      • What is the application?
      • Why does it exist?
      • How do I install it?
      • How do I perform my first import?

Reference documentation answers questions such as:


      • What configuration options are available?
      • What fields are required in a CSV playlist?
      • What log files are produced?

This Developer Guide answers a different set of questions:


      • How does the application work internally?
      • Why are responsibilities divided the way they are?
      • How does data move through the application?


                                                      2

      • Where is persistent state maintained?
      • How do integrations interact with the core matching workflow?
      • How should new functionality be added without breaking existing behavior?

The guiding assumption for this document is:


       Assume intelligence, not familiarity.


Readers are assumed to understand general software concepts but are not expected to know the history of
Plex Playlist Importer or its internal terminology.


Basic familiarity with the following is helpful:


      • Python.
      • Command-line applications.
      • REST APIs.
      • Configuration files.
      • Relational databases and SQLite.
      • Automated testing.

Readers should not need prior experience with the application's source code before beginning this guide.


The goal is to provide enough context that a developer can first understand the system as a whole and then
progressively examine individual components in greater detail.


For this reason, this guide presents the application lifecycle and high-level architecture before describing
individual subsystems.


3. Development Philosophy
Plex Playlist Importer has evolved incrementally as real operational problems have been encountered.


Many of the application's design principles emerged from that experience rather than being imposed in
advance.


These principles guide implementation decisions and provide context for the architecture described later in
this document.


3.1 Reliability Before Unnecessary Complexity

The application favors predictable behavior over clever implementation.


A technically sophisticated solution is not automatically better than a simpler one.


                                                       3

Complexity should be introduced when it solves a demonstrated problem or provides meaningful
operational value.


This principle is especially important for an application intended to run unattended.


A matching algorithm, cache mechanism, or integration workflow must not only work when everything is
available. It must also behave predictably when:


     • Plex is temporarily unreachable.
     • Lidarr does not return search results.
     • XMPlaylist reaches an API request limit.
     • A cached Plex item has been deleted.
     • A network request times out.
     • Metadata differs from expectations.

Reliable behavior includes clearly reporting what happened rather than silently hiding problems.


3.2 Separation of Responsibilities

Each system should remain responsible for the function it is designed to perform.


Plex Playlist Importer manages:


     • Playlist input.
     • Track matching.
     • Plex playlist creation and maintenance.
     • Match reporting.
     • Integration coordination.

Plex manages:


     • The media library.
     • Library scanning.
     • Media metadata.
     • Plex media objects.

Lidarr manages:


     • Artists.
     • Albums.
     • Acquisition monitoring.
     • Download searches.
     • Media acquisition workflows.

XMPlaylist provides:


     • SiriusXM station information.


                                                      4

      • SiriusXM channel play history.

The importer coordinates these systems but does not attempt to duplicate their responsibilities.


For example, after requesting an album search through Lidarr, the importer does not force Plex to rescan
the media library and immediately attempt another match.


Lidarr and Plex already provide synchronization mechanisms for newly acquired media.


The importer allows those systems to operate normally and discovers newly available tracks during a later
scheduled execution.


This approach reduces coupling and keeps the importer focused on its primary responsibility.

This architectural decision is documented in ADR-002, which records the decision to rely on native Lidarr and Plex library synchronization and includes conditions for future reconsideration.


3.3 Self-Contained Deployment

The application is designed to minimize external infrastructure requirements.


Persistent application data is stored using embedded SQLite databases rather than requiring a separate
database server.


Configuration, persistent state, reports, logs, and related runtime artifacts are intended to remain within
the application's deployment environment wherever practical.


This design simplifies:


      • Initial installation.
      • Backup.
      • Migration.
      • Containerization.
      • Disaster recovery.
      • Unraid deployment.
      • Development and testing.

Self-contained deployment does not mean that the application has no external dependencies.


Plex, Lidarr, and XMPlaylist are external systems.


The principle means that the importer itself should not introduce additional infrastructure unless that
infrastructure provides a clear benefit that cannot reasonably be achieved within the application.


3.4 Configuration-Driven Behavior

Operational behavior should normally be controlled through configuration rather than source-code
changes.


                                                      5

Examples include:


      • Matching thresholds.
      • Matching weights.
      • Metadata normalization options.
      • Cache age.
      • Logging behavior.
      • Report locations.
      • Integration settings.
      • XMPlaylist request budgets.
      • Playlist duplicate handling.

Command-line arguments provide execution-specific overrides and actions.


Configuration files define longer-lived application behavior.


This distinction allows the same application build to operate differently across environments without
requiring source modifications.


3.5 Graceful Degradation

Not every external component is required for every operation.


The application should therefore distinguish between:


      • A failure of a required component.
      • A failure of an optional integration.
      • A failure that prevents playlist modification.
      • A failure that still allows useful work to continue.

For example, if Plex is temporarily unavailable but a usable local library cache exists, the application may
still be able to:


      • Parse the playlist.
      • Perform matching.
      • Generate reports.
      • Identify unmatched tracks.
      • Perform Lidarr analysis.

It cannot safely create or update a Plex playlist until Plex becomes available.


Similarly, if Lidarr is unavailable, normal Plex playlist importing should not fail solely because an optional
integration cannot be reached.


Graceful degradation allows the application to complete as much useful work as possible while clearly
reporting limitations.


                                                         6

3.6 Observable Behavior

The application should explain what it is doing.


Operational visibility is provided through several mechanisms:


     • Console messages.
     • Log files.
     • CSV reports.
     •      • Unmatched-track reports.
     • Integration reports.
     • Historical analytics.
     • Latest-run status information.
     • Component health summaries.

A user should not need to inspect source code to determine why a track was not added to a playlist.


Likewise, a developer should have enough information to distinguish between:


     • A track that could not be matched.
     • A track that matched with low confidence.
     • A Plex item that existed in the local cache but was deleted from Plex.
     • A Lidarr search that returned no releases.
     • An XMPlaylist request that stopped because of an API budget.

Transparency is treated as an operational feature rather than merely a debugging aid.


3.7 Persist State When Persistence Adds Value

The application does not maintain state simply because it can.


Persistent state is used when remembering information improves future behavior.


Examples include:


     • Caching the Plex music library.
     • Remembering Lidarr searches.
     • Preserving XMPlaylist ingestion cursors.
     • Tracking artist alias usage.
     • Maintaining historical match analytics.

These categories serve different purposes.


Some persisted data is a performance optimization and can be rebuilt.


                                                      7

Some represents historical knowledge that should survive application restarts.


The distinction between rebuildable cache data and durable application history is discussed later in this
guide.


3.8 Incremental Development and Regression Testing

The project has evolved through small, testable changes.


A typical development cycle is:


  Observed Problem or New Requirement
                  |
                  v
          Define Expected Behavior
                  |
                  v
         Add or Update Tests
                  |
                  v
          Implement the Change
                    |
                    v
             Run Targeted Tests
                    |
                    v
          Run Full Regression Suite


This approach is particularly important because changes in one area can affect behavior elsewhere.


For example:


     • Metadata normalization may affect matching.
     • Matching changes may affect reports.
     • Alias handling may affect confidence scores.
     • Cache changes may affect Plex resolution.
     • XMPlaylist changes may affect deduplication and playlist size.

Regression testing provides confidence that improving one workflow has not unintentionally damaged
another.


                                                      8

3.9 Documentation Is a First-Class Engineering Artifact

Documentation is maintained as part of the project rather than being treated as work performed after
development is complete.


Significant decisions should be documented close to the time they are finalized.


The reason is simple:


The details of a decision tend to remain visible in the code.


The reasoning behind the decision tends to disappear.


Architecture Decision Records preserve significant design choices and their alternatives.


The Developer Guide explains how the architecture works.


Subsystem documentation provides deeper implementation detail.


Project History explains how the application evolved.


Together, these documents preserve both implementation knowledge and engineering intent.


4. System Architecture
Plex Playlist Importer is organized as a pipeline supported by a set of persistent and external services.


At a high level, data enters the application from a playlist source, is normalized, matched against the Plex
library, and then used to build or maintain a Plex playlist.


Unmatched tracks may optionally be evaluated through Lidarr.


Reports, analytics, and runtime status information are produced throughout the process.


                           Playlist Sources
                  TXT / CSV / TSV / M3U / XMPlaylist
                                |
                                v
                         Input Processing
                                |
                                v
                        Normalized Entries
                                |
                                v


                                                        9

                    Plex Library Search Index
                                |
                                v
                         Matching Engine
                          /
                        /
                       v                     v
                Matched Tracks          Unmatched Tracks
                       |                     |
                       |               v
                       |         Lidarr Integration
                       |          Check / Search
                       |               |
                       +-------+-------+
                               |
                               v
                         Plex Client
                               |
                               v
                  Create / Update / Replace
                               |
                               v
               Reports / Analytics / Runtime Status


              Persistent Application Services
            ------------------------------------
            Plex Library Cache
            XMPlaylist State and History
            Lidarr Search History
            Artist Alias Usage
            Match Analytics


4.1 Playlist Sources

The application currently accepts two general categories of playlist sources.


File-based sources include:


     • TXT.
     • CSV.
     • TSV.
     • M3U.
     • M3U8.


                                                     10

Service-based sources currently include:


      • XMPlaylist SiriusXM channel history.

Regardless of origin, playlist data is converted into a common internal representation before reaching the
matching engine.


This prevents the matching layer from needing to understand the details of every supported input format.


4.2 Input Processing

Each source is responsible for translating its native representation into normalized playlist entries.


For file-based playlists, this is performed by the parsing layer.


For XMPlaylist, the source integration retrieves channel history, processes API pagination, applies history-
window rules, and removes duplicate tracks before producing playlist entries.


Once entries reach the common model, downstream processing is largely independent of the original
playlist source.


4.3 Plex Library Cache

Loading a large Plex music library directly from Plex during every execution would create unnecessary
network traffic and startup time.


The application therefore maintains a local SQLite representation of relevant Plex track metadata.


The cache supports:


      • Faster startup.
      • Efficient local search.
      • Reduced dependency on Plex availability during the matching phase.
      • Repeatable matching behavior.

The cache is not the authoritative source for live Plex media objects.


Plex remains authoritative.


Before modifying a Plex playlist, cached match records must ultimately be resolved back to live Plex objects.


This distinction becomes important when a track has been removed from Plex after the cache was created.


                                                        11

4.4 Search Index

The local Plex cache is transformed into a search index optimized for repeated track matching.


The search index supports operations such as:


     • Normalized artist lookup.
     • Album artist comparison.
     • Title comparison.
     • Alias handling.
     • Exact-match shortcuts.
     • Fuzzy scoring.

Separating the search index from the Plex client allows the matching process to operate primarily against
local data.


4.5 Matching Engine

The matching engine compares each requested playlist entry with candidate Plex tracks.


The process may include:


     • Text normalization.
     • Artist alias substitution.
     • Exact comparisons.
     • Weighted fuzzy scoring.
     • Artist preference rules.
     • Album artist consideration.
     • Configurable metadata stripping.

The result is not merely a matched or unmatched state.


Match results also include information such as:


     • Confidence.
     • Confidence label.
     • Match reason.
     • Candidate metadata.

These results feed both playlist creation and reporting.


4.6 Unmatched-Track Processing

Tracks that cannot be matched remain valid application results.


                                                     12

They are not silently discarded.


Unmatched tracks are:


     • Included in reports.
     • Available for manual review.
     • Available for alias analysis.
     • Optionally passed to Lidarr workflows.

This turns failed matches into actionable information.


4.7 Lidarr Integration

Lidarr operates as an optional downstream integration for unmatched music.


The application can use Lidarr in two general modes:


Check


Evaluate whether the artist or album is known and provide diagnostic information.


Search


Request an active album search through Lidarr.


Lidarr searches are asynchronous.


A successful API request means Lidarr accepted the search request. It does not guarantee that a release will
be found or downloaded.


The importer therefore does not treat a Lidarr search request as an immediate successful acquisition.


4.8 Plex Client

When matching is complete and playlist modification is requested, matched cache records are resolved to
live Plex track objects.


The Plex client is responsible for operations such as:


     • Connecting to Plex.
     • Selecting the configured music library.
     • Retrieving library metadata for cache refresh.
     • Resolving matched tracks.
     • Creating playlists.


                                                         13

     • Updating playlists.
     • Replacing playlist contents.

The matching engine should not need to know how Plex performs those operations.


4.9 Reporting and Analytics

Reporting is distributed throughout the architecture rather than being treated as an afterthought at the
end.


The application records information about:


     • Match results.
     • Match confidence.
     • Unmatched tracks.
     • Lidarr diagnostics.
     • Alias behavior.
     • Runtime health.
     • Historical match statistics.

This information serves both users and developers.


Users need to understand the outcome of an import.


Developers need enough operational information to diagnose unexpected behavior.


4.10 Persistent Application Services

Several parts of the application maintain state between executions.


These currently include:


     • Plex library cache.
     • XMPlaylist ingestion state.
     • Lidarr search history.
     • Artist alias usage history.
     • Match analytics.

These persistent stores are logically independent even when they use the same underlying SQLite
technology.


Each exists because remembering information across runs provides specific operational value.


                                                     14

5. Repository Structure
The repository is organized to separate executable entry points, application logic, tests, runtime resources,
generated output, and documentation.


The exact structure may evolve as the project grows, but the general organization is:


  plex-playlist-importer/
  |
  |-- playlist_import_v2.py
  |-- config.ini
  |-- requirements.txt
  |-- README.md
  |-- DEVELOPER_GUIDE.md
  |-- CONTRIBUTING.md
  |-- CHANGELOG.md
  |-- PROJECT_HISTORY.md
  |-- LICENSE
  |-- NOTICE
  |
  |-- plex_playlist/
  |   |-- __init__.py
  |   |-- models.py
  |   |-- normalization.py
  |   |-- matcher.py
  |   |-- parser.py
  |   |-- cache.py
  |   |-- plex_client.py
  |   |-- lidarr_client.py
  |   |-- xmplaylist_client.py
  |   |-- xmplaylist_source.py
  |   |-- xmplaylist_state.py
  |   `-- logging_config.py
  |
  |-- resources/
  |
  |-- reports/
  |
  |-- logs/
  |
  |-- tests/
  |
  `-- docs/
      |-- documentation-standards.md
      |-- architecture.md
      |-- application-flow.md


                                                      15

       |-- configuration.md
       |-- playlist-formats.md
       |-- testing.md
       |-- logging.md
       |
       |-- subsystems/
       |
       `-- adr/


This diagram represents the logical repository layout rather than a guarantee that every listed document or
directory exists in every historical project version.


5.1 Main Entry Point

playlist_import_v2.py


This is the primary command-line entry point.


Its responsibilities include coordinating top-level application behavior such as:


     • Command-line argument handling.
     • Configuration loading.
     • Component initialization.
     • Cache evaluation.
     • Playlist source selection.
     • Match-session orchestration.
     • Integration invocation.
     • Playlist modification.
     • Reporting.
     • Runtime summary generation.

The entry point should primarily coordinate components rather than contain subsystem implementation
logic.


As the application grows, business logic should remain in dedicated modules where it can be independently
tested.


5.2 Application Package

plex_playlist/


This package contains the core application modules.


Current major responsibilities include:


                                                      16

models.py

Defines common application data structures.


These models allow different subsystems to exchange structured data without depending on one another's
internal implementations.


normalization.py

Contains metadata-normalization logic used during matching.


Normalization may account for variations such as:


      • Case.
      • Punctuation.
      • Remaster descriptions.
      • Live indicators.
      • Featured artists.
      • Deluxe-edition metadata.

Normalization behavior is configurable where appropriate.


matcher.py

Contains the core track-matching logic and search-index behavior.


This module is designed so that matching can be tested independently from Plex network access.


parser.py

Provides parsing support for file-based playlist formats.


Parsers convert external playlist representations into the application's common playlist-entry model.


cache.py

Manages the local Plex library cache.


Responsibilities include:


      • SQLite initialization.
      • Schema handling.


                                                      17

      • Track storage.
      • Cache replacement.
      • Metadata.
      • Last-refresh information.
      • Cache-state evaluation.


plex_client.py

Encapsulates communication with Plex.


Responsibilities include library access, metadata retrieval, track resolution, and playlist operations.


lidarr_client.py

Encapsulates communication with Lidarr.


Responsibilities include artist lookup, album information, managed-state evaluation, and album-search
requests.


xmplaylist_client.py

Handles low-level communication with XMPlaylist.


Responsibilities include API requests, response parsing, and station/history retrieval.


xmplaylist_source.py

Provides higher-level XMPlaylist playlist-source behavior.


Responsibilities include turning channel history into playlist entries while applying application rules such as
deduplication, request budgets, and unique-track targets.


xmplaylist_state.py

Maintains persistent XMPlaylist ingestion state.


This allows history retrieval to continue across multiple executions without unnecessarily repeating
completed work.


                                                       18

logging_config.py

Centralizes logging configuration and setup.


Logging behavior should be consistent across subsystems rather than independently configured by each
module.


5.3 Resources

resources/


The resources directory contains persistent, user-maintained files that support application behavior but are
not application source code.


Examples may include:


     • Artist aliases.
     • XMPlaylist station preferences.
     • Other future user-maintained reference data.

Operational preference files should remain logically distinct from core application configuration when they
serve different purposes.


5.4 Reports

reports/


Contains generated application reports.


Examples include:


     • Playlist match reports.
     • Unmatched-track reports.
     • Lidarr reports.
     • Alias analysis.
     • Match analytics exports.

Reports are application output and should normally not be treated as source-controlled project
documentation.


5.5 Logs

logs/


                                                      19

Contains application runtime logs.


Logs provide detailed operational information for troubleshooting and diagnostics.


Log retention and rotation behavior may evolve as the application approaches unattended production
deployment.


5.6 Tests

tests/


Contains the automated test suite.


Tests should mirror application behavior rather than implementation details wherever practical.


The test suite includes coverage for areas such as:


     • Matching.
     • Parsing.
     • Cache behavior.
     • Lidarr integration.
     • XMPlaylist retrieval.
     • Persistent state.
     • Reporting.
     • Regression scenarios.

Detailed testing standards are documented in docs/testing.md .


5.7 Documentation

docs/


Contains documentation that goes beyond the project overview provided by the README.


Documentation is divided by purpose.


Examples include:


     • Architecture.
     • Application flow.
     • Configuration.
     • Playlist formats.
     • Testing.
     • Logging.


                                                      20

     • Subsystem documentation.
     • Architecture Decision Records.

The documentation structure is defined in docs/documentation-standards.md .


5.8 Runtime Databases

The application uses one or more embedded SQLite database files for persistent state.


Database files may be placed according to application configuration and deployment requirements.


They are runtime data rather than source files.


The architecture does not require every category of persistent data to reside in the same physical database.


Logical ownership is more important than minimizing the number of database files.


6. Application Lifecycle
Understanding the execution lifecycle is the most useful starting point before examining individual
subsystems.


Although command-line options can enable or disable particular behaviors, most executions follow the
same general sequence.


  Command-Line Invocation
            |
            v
  Load Configuration
            |
            v
  Initialize Logging
            |
            v
  Initialize Resources and Persistent State
            |
            v
  Evaluate Component Availability
            |
            v
  Evaluate / Refresh Plex Cache
            |
            v
  Build Search Index


                                                     21

            |
            v
  Load Playlist Source
            |
            v
  Normalize Playlist Entries
            |
            v
  Run Matching Session
             |
             +--------------------+
             |                    |
             v                    v
       Matched Tracks       Unmatched Tracks
             |                    |
             |                    v
             |              Optional Lidarr
             |               Check / Search
             |                    |
             +---------+----------+
                       |
                       v
                Generate Reports
                       |
                       v
           Resolve Live Plex Objects
                       |
                       v
           Create / Update / Replace
                       |
                       v
             Write Analytics / Status
                       |
                       v
                 Final Health Summary


The individual stages are described below.


6.1 Parse Command-Line Arguments

Execution begins at the command-line entry point.


Arguments determine the requested operation.


                                                    22

Examples include:


     • Input playlist file.
     • Plex playlist name.
     • Dry-run mode.
     • Cache refresh.
     • Lidarr check or search.
     • XMPlaylist station.
     • XMPlaylist history window.
     • Report locations.

Command-line arguments represent actions or execution-specific overrides.


Long-lived application behavior should normally remain in configuration.


6.2 Load Configuration

The application loads system configuration before initializing dependent components.


Configuration may define:


     • Plex connection information.
     • Music library name.
     • Matching behavior.
     • Cache behavior.
     • Reporting.
     • Logging.
     • Lidarr settings.
     • XMPlaylist settings.

Configuration errors should be identified before expensive or destructive processing begins.


Secrets such as authentication tokens should not be written into logs or reports.


6.3 Initialize Logging

Logging is initialized early so that the remainder of application startup is observable.


Once logging is active, subsequent stages can report:


     • Startup conditions.
     • Configuration warnings.
     • Component availability.
     • Cache state.
     • Processing progress.


                                                      23

      • Recoverable failures.
      • Final status.

Both console and file logging may be enabled depending on configuration.


6.4 Load Resources and Persistent State

The application initializes resources required for the requested operation.


These may include:


      • Artist aliases.
      • Plex cache database.
      • Lidarr search history.
      • XMPlaylist state.
      • Analytics storage.

Only the components required for the current execution should need to be active.


For example, a normal file-based import without Lidarr or XMPlaylist should not depend on either optional
service.


6.5 Evaluate Component Availability

External services may be checked before processing begins.


Depending on the requested operation, this may include:


      • Plex.
      • Lidarr.
      • XMPlaylist.

Availability should be expressed explicitly rather than inferred from later failures.


Typical conceptual states include:


      • AVAILABLE.
      • UNAVAILABLE.
      • NOT_CONFIGURED.

The application uses component state to determine what work can safely continue.


For example, an unavailable Lidarr instance should not prevent normal playlist matching.


                                                       24

An unavailable Plex server may prevent playlist modification but does not necessarily prevent matching
when a usable local cache exists.


6.6 Evaluate Plex Cache State

Before building the matching index, the application evaluates the local Plex library cache.


Possible considerations include:


      • Whether the cache exists.
      • Whether it contains tracks.
      • The last successful refresh time.
      • Configured maximum age.
      • Whether refresh-on-start is enabled.
      • Whether the user explicitly requested a refresh.

If a refresh is required and Plex is available, the application retrieves the configured music library and
replaces the cached track data.


If Plex is unavailable but an acceptable cache already exists, the application may continue matching from
local data.


If no usable cache exists and Plex cannot be reached, matching cannot proceed safely.


6.7 Build the Search Index

Once a usable Plex cache is available, the application builds an in-memory search index.


This index is optimized for repeated lookup and matching.


Building the index once per execution avoids repeatedly scanning the underlying SQLite database for every
requested track.


The index may prepare structures for:


      • Artist lookup.
      • Album artist lookup.
      • Track-title lookup.
      • Normalized metadata.
      • Alias-aware matching.

Once complete, the application is ready to process playlist entries.


                                                       25

6.8 Load the Playlist Source

The application then obtains the requested playlist.


For file-based imports, the appropriate parser is selected and the file is read.


For XMPlaylist imports, the application:


      • Resolves the requested station.
      • Determines the configured history window.
      • Reads persistent ingestion state.
      • Requests channel-history pages.
      • Applies request-budget limits.
      • Deduplicates tracks.
      • Stops when the configured work target or retrieval limit is reached.

Both workflows ultimately produce the same common playlist-entry representation.


6.9 Normalize Playlist Entries

Playlist entries are normalized into forms suitable for matching.


Normalization may address:


      • Capitalization.
      • Punctuation.
      • Whitespace.
      • Metadata suffixes.
      • Featured-artist notation.
      • Remaster descriptions.
      • Live descriptions.

The original input should remain available for reporting.


Normalization exists to improve comparison, not to destroy the identity of the source data.


6.10 Run the Matching Session

The application creates a matching session and evaluates each playlist entry against the search index.


The matching process may attempt:


    1. Exact matches.
    2. Alias-aware matches.
    3. Preferred artist matches.


                                                       26

    4. Album artist matches.
    5. Weighted fuzzy comparisons.
    6. Configured fallback strategies.

Each entry produces a match result.


A result may include:


     • Matched Plex track record.
     • Match score.
     • Confidence label.
     • Match reason.
     • Original playlist metadata.

Entries that do not meet the configured acceptance threshold remain unmatched.


The matching session also gathers statistics used by reports and analytics.


6.11 Record Alias Usage

When aliases contribute to successful matching, their usage can be recorded.


Persistent alias history allows the project to distinguish between:


     • An alias that is configured.
     • An alias used during the current run.
     • An alias that has demonstrated historical value.

This information supports later alias auditing and cleanup.


6.12 Generate Match Reports

Once matching is complete, the application can generate reports describing the results.


Reports may include:


     • Matched tracks.
     • Unmatched tracks.
     • Confidence scores.
     • Confidence labels.
     • Match reasons.
     • Metadata warnings.

Generating matching reports before modifying Plex ensures that useful diagnostic output can still exist
even if a later Plex operation fails.


                                                      27

6.13 Process Unmatched Tracks Through Lidarr

When Lidarr functionality is requested, unmatched tracks are passed to the Lidarr workflow.


In check mode, the application may determine:


     • Whether the artist exists in Lidarr.
     • Whether the artist is monitored or managed.
     • Whether the album exists.
     • Whether track files are available.

In search mode, the application may request album searches.


Search history is used to avoid unnecessary repeated search requests according to configured retry
behavior.


The importer does not wait for Lidarr to download media.


Lidarr acquisition is asynchronous and may succeed, fail, or return no releases after the importer execution
has completed.


6.14 Resolve Matched Cache Records to Live Plex Objects

If Plex playlist modification is requested, locally matched cache records must be resolved to live Plex media
objects.


This step reestablishes the boundary between:


     • Matching data.
     • Authoritative Plex objects.

A cache record may still exist even if its corresponding media item has since been deleted from Plex.


Such conditions should be treated as expected operational inconsistencies rather than unhandled
programming errors.


Affected tracks can be skipped and reported while the remaining playlist operation continues when safe.


6.15 Create, Update, or Replace the Plex Playlist

Once live Plex track objects have been resolved, the requested playlist operation is performed.


The exact behavior depends on the selected mode.


                                                     28

Create


Create a new playlist using matched tracks.


Update


Add or reconcile tracks according to update and duplicate-handling rules.


Replace


Replace the existing playlist contents with the newly matched track set.


Playlist order should be preserved according to the source order unless a future feature explicitly defines
different behavior.


6.16 Dry-Run Behavior

Dry-run mode follows as much of the normal application lifecycle as practical without making requested
changes to Plex or initiating explicitly destructive behavior.


A dry run may still:


      • Load configuration.
      • Use or refresh the Plex cache when appropriate.
      • Build the search index.
      • Parse playlist data.
      • Retrieve XMPlaylist data.
      • Perform matching.
      • Generate reports.
      • Perform non-destructive Lidarr checks.
      • Produce analytics and status information.

It should not perform the final Plex playlist modification.


An explicitly requested active Lidarr search should be treated according to the command's documented
semantics rather than assumed to be harmless merely because Plex modification is disabled.


Dry-run behavior must therefore be defined per operation, not simply as a blanket "do nothing" switch.


6.17 Write Analytics and Latest-Run Status

At the end of processing, the application records information useful for historical analysis and operational
monitoring.


                                                       29

This may include:


     • Total playlist entries.
     • Matched tracks.
     • Unmatched tracks.
     • Unique artists.
     • Confidence distributions.
     • Stale-cache events.
     • Integration health.
     • Execution outcome.

Historical analytics describe trends across executions.


Latest-run status describes the most recent execution and can support future dashboard functionality.


6.18 Report Final Runtime Health

The execution concludes with a summary of what occurred.


The final status should distinguish between:


     • Successful execution.
     • Successful execution with warnings.
     • Partial execution caused by an unavailable optional service.
     • Processing completed but Plex playlist modification skipped.
     • Fatal failure.

Component health should be reported separately from overall execution status.


For example:


  Plex Cache : AVAILABLE
  Plex       : UNAVAILABLE
  Lidarr     : AVAILABLE
  XMPlaylist : NOT_CONFIGURED

  Matching completed using local Plex cache.
  Plex playlist update skipped because Plex was unavailable.
  Reports written successfully.


This distinction is important for unattended execution.


A scheduled job should provide enough information to determine whether corrective action is required
without forcing an operator to reconstruct events from a Python traceback.


                                                      30

Sections 1–6 Summary
The first six sections establish the application's high-level mental model.


The key architectural flow is:


       Source data enters the application, is normalized into a common model, matched locally
       against cached Plex metadata, optionally analyzed through external integrations, resolved
       back to authoritative Plex objects when necessary, and finally reported and persisted.


The following sections examine each major part of that flow in greater detail.


                                                       31


7. Core Data Model
Plex Playlist Importer uses common internal data structures to separate external data sources from
downstream processing.


This separation is important because playlist data can originate from different sources and formats:


     • Plain-text playlist files.
     • CSV files.
     • TSV files.
     • M3U and M3U8 files.
     • XMPlaylist channel history.

Likewise, matching results may later be consumed by several different parts of the application:


     • Plex playlist operations.
     • Match reports.
     • Unmatched-track processing.
     • Lidarr diagnostics.
     • Alias analytics.
     • Historical analytics.

Rather than allowing each subsystem to exchange source-specific dictionaries, API responses, or Plex
objects, the application converts data into common internal models.


The primary models are defined in:


plex_playlist/models.py


Additional integration-specific models may be defined within the modules responsible for those
integrations.


The objective is to maintain clear boundaries between subsystems.


A parser should not need to understand Plex.


The matching engine should not need to understand CSV files.


XMPlaylist ingestion should not need to understand Plex playlist operations.


Lidarr should receive unmatched-track information without needing to know whether the original request
came from a text file or SiriusXM channel history.


                                                     1

7.1 Playlist Entry
A playlist entry represents one requested track.


Conceptually, the minimum information required for matching is:


  Artist
  Title


Depending on the source format, additional metadata may also be available.


Examples include:


     • Sequence number.
     • Album.
     • Source-specific metadata.

The original source information should be preserved wherever practical so that reports can show what the
user requested even after normalized values have been created for matching.


For example:


  Original Artist : Bob Marley and the Wailers
  Original Title : Three Little Birds


The matching engine may internally normalize or alias the artist name, but reports should continue to
identify the original request.


Playlist entries provide the common boundary between input processing and matching.


Once an input source has produced playlist entries, the matching engine generally does not need to know
where those entries originated.


7.2 Plex Track Record
A Plex track record represents the metadata required to identify and match a track from the Plex music
library.


These records are stored in the local Plex library cache and loaded into the search index.


                                                      2

Relevant metadata may include:


     • Plex track identifier.
     • Artist.
     • Album artist.
     • Album.
     • Track title.
     • Other identifiers required to resolve the cached record back to Plex.

The cached track record is intentionally different from a live Plex media object.


A cached record is optimized for:


     • Persistence.
     • Searching.
     • Matching.
     • Local processing.

A live Plex object is required when the application performs an actual Plex operation.


This distinction allows the matching engine to operate primarily against local data without requiring
continuous access to the Plex server.


7.3 Match Result
Each playlist entry produces a match result.


A match result records the outcome of comparing the requested track with the Plex search index.


Conceptually, a result may contain:


  Requested Track
         |
         v
  Matching Process
         |
         +----> Matched Plex Track
         |
         +----> Match Score
         |
         +----> Confidence Label
         |
         +----> Match Reason


                                                       3

             |
             +----> Metadata Warnings


If no acceptable candidate is found, the result remains unmatched.


An unmatched result is still a complete and useful result.


It can be:


      • Written to an unmatched report.
      • Evaluated for artist alias opportunities.
      • Passed to Lidarr diagnostics.
      • Included in match analytics.

This distinction is important to the architecture.


A failed match is not treated as an application failure.


It is a valid outcome of the matching process.


7.4 Matching Session
A matching session represents the processing of a collection of playlist entries during one application
execution.


The session provides a common context for:


      • Matching entries.
      • Collecting results.
      • Separating matched and unmatched tracks.
      • Recording statistics.
      • Tracking alias effectiveness.
      • Producing summary information.

The matching session helps prevent application-wide state from being scattered across individual matching
operations.


It also provides a natural boundary for reporting.


For example, the application can summarize a session using information such as:


  Total Entries             : 100
  Normal Matches            : 30
  Fallback Matches          : 11


                                                           4

  Unmatched                 : 59
  Metadata Warnings         : 13
  Unique Artists            : <count>


The exact statistics available may evolve, but the session remains the logical representation of one
matching workload.


7.5 Confidence Labels
A numeric similarity score alone does not always communicate enough information to a user reviewing a
match.


The application therefore associates match results with confidence information.


Confidence labels provide a human-readable interpretation of matching quality.


The exact classification rules are controlled by the matching implementation and configuration.


The important architectural distinction is:


      • Score represents a calculated matching value.
      • Confidence label provides a human-readable classification.
      • Match reason explains why a particular candidate was selected.

Together, these fields make the matching process more transparent.


7.6 Match Reason
The match reason records the path by which a track was selected.


Examples may include:


      • Exact artist and title match.
      • Alias-assisted match.
      • Album-artist match.
      • Fuzzy match.
      • Fallback match.

The match reason is intended to answer:


       Why did the application choose this Plex track?


This information is valuable both operationally and during development.


                                                      5

A high match score may indicate that two strings are similar.


The match reason explains which matching strategy actually produced the accepted result.


7.7 Metadata Warnings
A track may be successfully matched while still containing metadata differences worth reporting.


For example, a requested artist and the Plex artist may differ in a way that does not prevent a successful
match but may indicate:


       • A possible alias opportunity.
       • A metadata inconsistency.
       • A fallback match that deserves review.

Metadata warnings allow the application to distinguish between:


  Match Failed


and:


  Match Succeeded, but Review Recommended


This supports the project's goal of making matching decisions understandable rather than treating every
accepted match as equally certain.


7.8 Integration-Specific Models
External integrations may require additional internal models.


Examples include:


       • Lidarr command status.
       • Lidarr diagnostic rows.
       • XMPlaylist station metadata.
       • XMPlaylist play records.
       • XMPlaylist history pages.
       • XMPlaylist ingestion results.
       • Runtime component health.

These models belong close to the integration or subsystem that owns them.


                                                      6

They should expose only the information required by other parts of the application.


Raw external API responses should generally be converted into application models before being passed
deeper into the system.


This limits the impact of external API changes and keeps service-specific details from spreading throughout
the codebase.


7.9 Model Design Principle
The general data-flow pattern is:


  External Representation
          |
          v
  Subsystem Parser / Client
          |
          v
  Application Model
          |
          v
  Core Application Processing


For example:


  CSV Row
     |
     v
  CSV Parser
     |
     v
  Playlist Entry
     |
     v
  Matching Engine


or:


  XMPlaylist API Response
          |
          v
  XMPlaylist Client


                                                     7

          |
          v
  History Page / Play Records
          |
          v
  XMPlaylist Source
          |
          v
  Playlist Entries
          |
          v
  Matching Engine


This model-based separation reduces coupling between subsystems and makes individual components
easier to test.


8. Playlist Input and Parsing
Playlist input is the first application boundary where externally supplied data is converted into the
application's common internal representation.


The parsing layer is implemented primarily in:


plex_playlist/parser.py


The parser's responsibility is limited.


It should:


     1. Identify the requested input format.
     2. Read the source file.
     3. Interpret records according to that format.
     4. Validate enough information to construct playlist entries.
     5. Return those entries in source order.

The parser should not:


      • Connect to Plex.
      • Perform fuzzy matching.
      • Apply Plex-specific logic.
      • Search Lidarr.
      • Modify playlists.

Those responsibilities belong to downstream components.


                                                       8

8.1 Supported File Formats
The application currently supports:


     • TXT.
     • CSV.
     • TSV.
     • M3U.
     • M3U8.

Detailed end-user specifications and examples belong in:


docs/playlist-formats.md


The Developer Guide focuses on how those formats participate in the application architecture.


8.2 Parser Selection
For file-based imports, the application determines the appropriate parsing behavior from the input file type.


Conceptually:


  Input File
      |
      v
  File Extension
      |
      +----> .txt ------> Text Parser
      |
      +----> .csv ------> CSV Parser
      |
      +----> .tsv ------> TSV Parser
      |
      +----> .m3u ------> M3U Parser
      |
      +----> .m3u8 -----> M3U Parser


Unsupported file types should be rejected clearly rather than passed through a best-effort parser that may
produce unpredictable results.


8.3 Text Playlist Parsing
The simple text format is intended to provide an easy human-readable playlist source.


                                                     9

The standard format is:


  <number>. <artist> - <title>


For example:


  1. Bob Dylan - Like a Rolling Stone
  2. The Rolling Stones - Satisfaction
  3. John Lennon - Imagine


The sequence number identifies playlist order.


The artist and title provide the primary matching information.


Invalid lines should not cause unrelated valid entries to become unusable when the parser can safely
identify and skip the invalid record.


Parser behavior should remain observable so that malformed input does not disappear silently.


8.4 CSV and TSV Parsing
CSV and TSV files provide structured playlist input suitable for:


      • Spreadsheet exports.
      • External data-processing tools.
      • Generated playlists.
      • Manual editing.

The parser supports the delimiter appropriate to each format while converting records into the same
playlist-entry representation used by other sources.


Header handling should be explicit.


Current parser behavior supports both header-based and supported headerless input where the expected
field positions can be determined.


The original delimiter should not affect downstream matching behavior.


Once parsing is complete:


  CSV


                                                       10

      +----> Playlist Entry ----> Matching
     /
   /
  TSV


The matching engine should not need separate CSV and TSV logic.


8.5 M3U and M3U8 Parsing
M3U-family playlist files require different parsing behavior because they may contain both metadata and
media-location information.


Where supported metadata is available, the parser extracts the information required to construct playlist
entries.


The parser should isolate M3U-specific interpretation from the rest of the application.


Downstream components should receive the same common playlist-entry model used for TXT, CSV, and TSV
input.


Detailed supported M3U behavior should be documented in:


docs/playlist-formats.md


8.6 Input Validation
Validation should occur as close as practical to the input boundary.


Examples include:


      • Missing input files.
      • Unsupported extensions.
      • Records without sufficient matching information.
      • Malformed lines.

The parser should distinguish between:


      • A fatal input problem that prevents the playlist from being processed.
      • An invalid individual record that can safely be skipped.

For example, a missing playlist file is fatal.


One malformed line within an otherwise valid text playlist may not be.


                                                     11

The objective is to reject unusable input without unnecessarily discarding usable data.


8.7 Order Preservation
Playlist entries should remain in their source order.


The parser should not sort entries alphabetically by:


      • Artist.
      • Title.
      • Album.

Source order may have meaning even when the user ultimately chooses random playback.


Preserving order also prevents the importer from making assumptions about the intent of the playlist
creator.


The general rule is:


          Input processing preserves order. It does not reinterpret it.


8.8 Duplicate Handling
Parsing and duplicate handling are separate concerns.


The parser's primary responsibility is to represent the source accurately.


Policies governing duplicate tracks belong to the playlist-processing or playlist-update workflow.


This distinction prevents format-specific parsers from making inconsistent decisions about duplicates.


XMPlaylist ingestion is a special case because deduplication is part of converting repeated channel plays
into a playlist of unique tracks.


That behavior belongs to the XMPlaylist source subsystem rather than the general file parser.


8.9 Parsing Error Philosophy
Input errors should produce messages that identify the problem in terms meaningful to the user.


Prefer:


                                                         12

  Unsupported playlist format: .xyz


over an internal parser exception.


Prefer:


  Playlist file not found: playlist.txt


over a raw filesystem traceback during normal operation.


Unexpected programming errors should remain visible during development and testing.


Expected input errors should be converted into controlled application behavior.


8.10 Extending Playlist Format Support
New playlist formats should be added without requiring changes to the matching engine.


The expected extension pattern is:


  New External Format
          |
          v
  New or Extended Parser
          |
          v
  Existing Playlist Entry Model
          |
          v
  Existing Matching Pipeline


When a new format is added:


    1. Implement parsing.
    2. Add parser tests.
    3. Add invalid-input tests.
    4. Confirm order preservation.
    5. Update docs/playlist-formats.md .
    6. Update the README Supported Input Formats section.
    7. Update the changelog.


                                                    13

If supporting a new format requires changes to the matching engine, the design should be reviewed to
determine whether source-specific behavior is leaking into the core matching architecture.


9. Plex Library Cache
The Plex library cache is one of the central architectural components of Plex Playlist Importer.


The application may operate against music libraries containing tens of thousands of tracks.


Retrieving and processing the complete Plex library during every execution would add unnecessary startup
time, network activity, and dependency on Plex availability.


The application therefore maintains a local SQLite representation of relevant Plex track metadata.


The cache database path is configurable in config.ini . In the current project configuration, the Plex
library cache is stored under the configured cache/ directory.


The exact configured filename should be treated as configuration rather than hard-coded application
behavior.


The cache implementation is primarily located in:


plex_playlist/cache.py


9.1 Purpose of the Cache
The cache serves two primary purposes.


Performance

Matching can be performed against local SQLite data and an in-memory search index rather than
repeatedly querying Plex.


Resiliency

A temporary Plex outage does not necessarily prevent the application from performing useful work.


If a usable cache exists, the application may still be able to:


      • Load the search index.
      • Parse playlist input.
      • Match tracks.
      • Identify unmatched tracks.


                                                        14

      • Generate reports.
      • Perform optional Lidarr processing.

Plex playlist modification still requires Plex to be available.


9.2 Authoritative Data
The cache is not authoritative.


Plex is authoritative for:


      • Whether a media item currently exists.
      • The current Plex media object.
      • The contents of Plex playlists.
      • The current state of the Plex library.

The cache is a local representation of Plex metadata as of the most recent successful refresh.


This distinction is fundamental.


  Plex Media Library
     AUTHORITATIVE
          |
          | Cache Refresh
          v
  Local SQLite Cache
     MATCHING COPY
          |
          | Load
          v
  In-Memory Search Index
     EXECUTION COPY


Each layer serves a different purpose.


9.3 Cache Initialization
The cache layer is responsible for ensuring that the required SQLite structures exist before they are used.


Initialization may include:


      • Opening or creating the database.
      • Creating required tables.


                                                         15

     • Creating metadata structures.
     • Applying supported schema initialization or migration behavior.
     • Configuring SQLite connection behavior.

Application code outside the cache subsystem should not need to know the details of SQLite table creation.


9.4 Cache Contents
The cache stores the metadata required to support track matching and later Plex resolution.


Conceptually, this includes information such as:


     • Plex identifiers.
     • Artist.
     • Album artist.
     • Album.
     • Track title.

The cache may also maintain metadata describing the cache itself, including:


     • Last successful refresh.
     • Track count.
     • Schema version.

The detailed physical schema belongs in subsystem documentation rather than the Developer Guide.


9.5 Cache Refresh
A cache refresh obtains current track metadata from the configured Plex music library and replaces the
locally cached library representation.


A refresh may occur because:


     • The cache is empty.
     • The cache is considered too old.
     • Refresh-on-start behavior is enabled.
     • The user explicitly invokes --refresh-cache .

A successful refresh updates the cache metadata so future executions can evaluate its age.


A refresh should replace the library data as a controlled operation rather than leave a partially updated
representation if the refresh fails midway.


                                                     16

9.6 Cache Age and Freshness
The application records when the Plex cache was last successfully refreshed.


Configuration determines how old a cache may become before it is considered stale.


Conceptually:


  Current Time
       -
  Last Successful Refresh
       =
  Cache Age


The cache state can then be classified according to application rules.


For example:


  FRESH
  STALE
  EMPTY


A stale cache does not necessarily mean that every record is incorrect.


It means that the application can no longer assume the cached representation is sufficiently current
according to the configured policy.


Cache freshness and Plex availability are separate conditions.


For example:


  Plex            : UNAVAILABLE
  Plex Cache      : FRESH


may allow matching to continue.


Whereas:


  Plex            : UNAVAILABLE
  Plex Cache      : EMPTY


does not provide enough local information for matching.


                                                      17

9.7 Manual Cache Refresh
The command:


  --refresh-cache


allows the user to explicitly request synchronization of the local cache with the Plex library.


This is useful after known library changes.


For example:


     1. An album is removed from the Plex music directory.
     2. Plex scans the library and removes the tracks.
     3. The importer cache still contains the previous track records.
     4. The user runs --refresh-cache .
     5. The local cache is rebuilt from the current Plex library.

The refreshed cache then reflects the new Plex state.


9.8 Stale Plex Track References
A cache can be fresh according to its age while still containing a record that no longer corresponds to a live
Plex item.


This can occur when the underlying media library changes after the most recent cache refresh.


For example:


  10:00    Plex cache refreshed
  10:30    Album deleted from media directory
  10:45    Plex library scan removes album
  11:00    Importer runs


The cache may still be considered fresh by age, but it contains tracks that no longer exist in Plex.


The matching engine may therefore successfully match a requested track to a cached record that cannot
later be resolved to a live Plex object.


This is an expected operational inconsistency.


                                                        18

It should not result in an uncontrolled Python traceback during normal execution.


The application should identify the stale reference, report it, and handle the remaining playlist operation
safely.


A subsequent Plex library scan and importer cache refresh restores synchronization.


9.9 SQLite Behavior
The cache uses SQLite because it provides persistent relational storage without requiring an external
database server.


The cache implementation uses SQLite features appropriate for a self-contained application, including
connection settings intended to improve safe local operation.


Where configured by the implementation, this includes behavior such as:


      • Write-Ahead Logging (WAL).
      • Busy timeouts.

These settings help make local database access more resilient without introducing additional infrastructure.


Detailed SQLite implementation and schema information should be documented in the cache subsystem
documentation.


9.10 Cache Replacement
Refreshing the cache should produce a coherent representation of the Plex library.


The cache subsystem therefore treats replacement as a distinct operation rather than expecting callers to
manually insert and remove individual tracks.


This reduces the risk that application-level code will leave the cache in a partially synchronized state.


The cache owns its persistence behavior.


The Plex client owns retrieval of authoritative Plex metadata.


The boundary is:


  Plex Client
       |
       | Current Library Track Records


                                                       19

       v
  Cache
       |
       | Persisted Track Records
       v
  Search Index


9.11 Cache Failure Behavior
Cache problems should be classified according to whether useful processing can continue.


Examples include:


Cache unavailable, Plex available


The application may be able to rebuild the cache.


Cache stale, Plex available


The application may refresh according to configuration.


Cache fresh, Plex unavailable


Matching may continue using local data, but Plex playlist modification cannot occur.


Cache empty, Plex unavailable


Matching cannot proceed because no usable representation of the Plex library exists.


The application should report these states explicitly.


9.12 Cache Design Principle
The cache exists to reduce dependency, not to redefine authority.


The governing principle is:


       Match locally when possible. Validate against Plex when Plex action is required.


This provides performance and resiliency while preserving Plex as the authoritative media system.


                                                         20

10. Search Index and Matching Engine
The matching engine is the core of Plex Playlist Importer.


Importing a playlist file is mechanically simple.


Determining whether:


  Requested:
  Bob Marley and the Wailers - Three Little Birds


represents the same track as:


  Plex:
  Bob Marley & The Wailers - Three Little Birds


requires more than direct string equality.


The matching subsystem exists to bridge reasonable metadata differences without accepting unrelated
tracks.


The primary implementation is located in:


plex_playlist/matcher.py


with supporting normalization behavior in:


plex_playlist/normalization.py


and configured artist aliases in:


resources/aliases.txt


10.1 Matching Objectives
The matching engine attempts to balance two competing risks.


False Negative

A track exists in Plex but the importer fails to recognize it.


                                                         21

False Positive

The importer selects the wrong Plex track because the metadata appears similar.


An overly strict matcher produces incomplete playlists.


An overly permissive matcher produces incorrect playlists.


The matching system therefore combines several strategies rather than relying on a single fuzzy-score
threshold.


10.2 Search Index
Before matching begins, cached Plex track records are loaded into an in-memory search index.


The search index prepares the library for repeated comparisons during the current execution.


For a playlist containing hundreds of tracks, repeatedly scanning the complete SQLite cache for every entry
would be inefficient.


The index allows likely candidates to be located before more expensive comparisons are performed.


Conceptually:


  SQLite Plex Cache
         |
         v
  Load Once Per Execution
         |
         v
  Search Index
         |
         +----> Artist Candidates
         |
         +----> Album Artist Candidates
         |
         +----> Title Candidates
         |
         v
  Matching Engine


The search index is an execution-time structure.


It does not replace the persistent cache.


                                                     22

10.3 Metadata Normalization
Metadata is normalized before comparison so that superficial differences do not unnecessarily prevent
matching.


Normalization may address:


       • Letter case.
       • Whitespace.
       • Punctuation.
       • Configured remaster indicators.
       • Live indicators.
       • Featured-artist metadata.
       • Deluxe-edition metadata.

For example, depending on configured normalization rules:


  Song Title (2011 Remaster)


may be compared using a normalized form closer to:


  song title


The original metadata remains available for reporting.


Normalization changes the comparison representation, not the source record.


10.4 Case-Insensitive Comparison
Text comparison should generally be case-insensitive after normalization.


For example:


  Bob Marley & the Wailers


and:


  Bob Marley & The Wailers


                                                    23

should not be treated as different artists solely because of capitalization.


This rule also applies to alias resolution.


Alias validity and usage should be evaluated using the same normalized comparison principles used by the
matching system.


Case differences alone should not cause an otherwise valid alias to be classified as broken or unused.


10.5 Artist Aliases
Artist aliases handle known naming differences that normalization alone cannot reliably resolve.


Aliases are maintained in:


resources/aliases.txt


Conceptually:


  Source Artist Name
          =
  Canonical Plex Artist Name


For example:


  Bob Marley and the Wailers = Bob Marley & The Wailers


When an alias applies, the matcher can use the canonical form when searching for Plex candidates.


Aliases are explicit knowledge supplied to the matching system.


They should not be confused with fuzzy matching.


An alias says:


       These artist names are intentionally considered equivalent for matching purposes.


Fuzzy matching says:


       These values are sufficiently similar to be considered as possible candidates.


                                                       24

That distinction allows aliases to resolve known metadata differences without requiring globally more
permissive fuzzy thresholds.


10.6 Exact Matching
Where possible, exact normalized matches should be preferred over fuzzy matches.


An exact match provides stronger evidence and avoids unnecessary scoring.


A simplified conceptual path is:


  Requested Track
        |
        v
  Normalize Metadata
        |
        v
  Apply Artist Alias if Configured
        |
        v
  Exact Artist + Title Match?
        |
     YES|        NO
        |         |
        v         v
    Accept     Candidate Search


The actual matching implementation may include additional checks, but the principle remains:


       Use stronger evidence before weaker evidence.


10.7 Artist and Album Artist
Music libraries do not always represent artist metadata consistently.


A track may have:


     • Track artist.
     • Album artist.

Compilation albums and collaborative releases make this distinction particularly important.


The matcher can consider both fields according to configured weighting and preference rules.


                                                     25

Configuration may prefer exact artist matches while still allowing album-artist information to contribute to
candidate selection.


This improves matching without assuming that one metadata field is universally correct for every library.


10.8 Weighted Matching
When exact matching is insufficient, candidate tracks may be evaluated using weighted comparisons.


Current matching configuration can assign relative importance to fields such as:


     • Artist.
     • Album artist.
     • Title.
     • Combined metadata.

Conceptually:


  Final Score =
      Artist Score               * Artist Weight
     + Album Artist Score * Album Artist Weight
     + Title Score        * Title Weight
     + Combined Score     * Combined Weight


The exact configured weights determine how strongly each field influences the result.


This allows matching behavior to be tuned without rewriting the matching algorithm.


Track title generally carries significant weight because selecting the correct artist but wrong song is not a
useful playlist match.


10.9 Matching Threshold
The configured matching threshold defines the minimum acceptable evidence for fuzzy matching.


Candidates below the threshold remain unmatched.


The threshold represents a trade-off.


Raising it generally reduces false positives but may increase false negatives.


Lowering it may improve playlist completeness while increasing the risk of incorrect matches.


                                                      26

Changes to matching thresholds should therefore be evaluated using:


     • Representative playlists.
     • Match reports.
     • Regression tests.
     • Known difficult metadata cases.

Matching configuration should not be tuned solely to make one problematic track succeed.


10.10 Fallback Matching
Some tracks may require a secondary matching strategy when the normal path does not produce an
acceptable result.


Fallback matching exists to recover reasonable matches that would otherwise be lost because of metadata
differences.


Fallback matches should remain visible in reporting.


For example, the summary may distinguish:


  Normal Matches   : 30
  Fallback Matches : 11
  Unmatched        : 59


This distinction allows users to review lower-certainty matching behavior without treating fallback results as
identical to stronger matches.


10.11 Confidence and Explainability
Every accepted match should provide enough information to understand why it was accepted.


The matching system therefore exposes information such as:


     • Score.
     • Confidence label.
     • Match reason.
     • Metadata warnings.

This creates an explainable result:


                                                       27

  Requested:
  The Doobie Brothers - Listen to the Music

  Matched:
  Doobie Brothers - Listen to the Music

  Reason:
  Artist alias applied; exact normalized title match


  Confidence:
  High


The objective is not merely to return a Plex track.


The objective is to return a Plex track and enough context to evaluate the decision.


10.12 Unmatched Results
If no candidate satisfies the configured matching rules, the requested track remains unmatched.


The matcher should not select a weak candidate simply to increase the number of matched tracks.


An unmatched result is preferable to a confidently wrong playlist entry.


Unmatched tracks feed downstream workflows such as:


      • Unmatched reporting.
      • Alias analysis.
      • Lidarr diagnostics.
      • Lidarr search requests.

This allows the application to improve playlist completeness without weakening the core matching criteria.


10.13 Unique Artist Statistics
Where meaningful, matching summaries may include the number of unique requested artists represented
in the workload.


For example:


  Playlist Entries : 100
  Unique Artists   : 64


                                                      28

  Matched Tracks   : 72
  Unmatched Tracks : 28


Unique artist counts can provide useful context, particularly for:


      • XMPlaylist imports.
      • Large playlist imports.
      • Lidarr workloads.
      • Matching analytics.

A playlist containing 100 tracks from five artists represents a different workload from one containing 100
tracks from 90 artists.


The statistic should be included where it provides useful operational context rather than mechanically
added to every report.


10.14 Matching Independence
The matching engine is intentionally designed to operate without requiring live Plex network access.


Its inputs are:


  Playlist Entries
         +
  Search Index
         +
  Matching Configuration
         +
  Artist Aliases


Its outputs are match results.


This makes matching behavior:


      • Faster.
      • Easier to test.
      • More deterministic.
      • Less dependent on network availability.

Live Plex access becomes necessary later when accepted cached records must be resolved into Plex objects
for playlist modification.


                                                      29

10.15 Testing the Matcher
Matching behavior should be protected by focused regression tests.


Important cases include:


     • Exact matches.
     • Unicode and accented characters.
     • Artist aliases.
     • Case differences.
     • Metadata normalization.
     • Unrelated titles remaining unmatched.
     • Known regression cases.

When a real-world playlist exposes incorrect matching behavior, the preferred workflow is:


  Observed Match Problem
          |
          v
  Create Reproducible Test Case
          |
          v
  Confirm Test Fails
          |
          v
  Modify Matching Logic
          |
          v
  Confirm Targeted Test Passes
          |
          v
  Run Full Regression Suite


This prevents solving one metadata problem at the expense of previously correct behavior.


10.16 Matching Design Principle
The matching subsystem follows a general hierarchy:


  Known Equivalence
        |
        v
  Exact Normalized Match
        |


                                                    30

        v
  Strong Candidate Match
        |
        v
  Weighted Fuzzy Match
        |
        v
  Controlled Fallback
        |
        v
  Unmatched


The matcher should become more permissive only as stronger evidence fails.


At every stage, the system should preserve enough information to explain the final result.


The governing principle is:


       Prefer an explainable unmatched result over an unexplained incorrect match.


Detailed matching algorithms, normalization rules, scoring implementation, and alias internals should be
documented separately in:


docs/subsystems/matching.md


and:


docs/subsystems/aliases.md


                                                     31


11. Artist Alias System
Music metadata frequently represents the same artist using different names.


Examples may include:


  The Doobie Brothers
  Doobie Brothers


or:


  Bob Marley and the Wailers
  Bob Marley & The Wailers


These differences may be semantically insignificant to a person but can affect automated track matching.


The artist alias system provides explicit knowledge about artist names that should be considered
equivalent.


Configured aliases are maintained in:


resources/aliases.txt


The alias system works with the matching engine but remains a distinct concern.


Normalization handles predictable textual differences.


Fuzzy matching evaluates similarity.


Aliases represent known equivalence.


11.1 Purpose of Artist Aliases
An artist alias provides the matcher with information that cannot always be inferred safely from
normalization alone.


Conceptually:


  Playlist Artist
        |


                                                     1

        v
  Alias Lookup
        |
        +----> Alias Found ----> Canonical Artist
        |
          +----> No Alias -------> Original Artist


The resulting artist name can then participate in normal candidate selection and matching.


Aliases allow known metadata differences to be handled explicitly rather than making the entire matching
algorithm more permissive.


This reduces the risk of introducing false-positive matches while solving known metadata inconsistencies.


11.2 Alias Configuration
Aliases are stored in:


resources/aliases.txt


The file is user-maintained reference data rather than application source code.


Aliases should represent intentional equivalence between artist names.


They should not be added merely because two names appear similar.


For example, the purpose of an alias is to express:


       These names refer to the same artist for the purposes of this music library.


The detailed file syntax and maintenance procedures should be documented in:


docs/subsystems/aliases.md


11.3 Alias Normalization
Alias comparison follows the same general normalization principles used by the matching system.


Differences in capitalization alone should not cause an otherwise valid alias to fail.


For example:


                                                        2

  The Doobie Brothers


and:


  the doobie brothers


should not be considered different solely because of letter case.


Alias processing should remain consistent with the broader matching architecture so that an alias does not
behave differently from ordinary artist comparison for superficial metadata differences.


11.4 Alias Usage
An alias being present in resources/aliases.txt does not necessarily mean that it contributes to
every matching session.


The application distinguishes between:


       • An alias that is configured.
       • An alias that is used during the current execution.
       • An alias that has been used successfully during previous executions.

This distinction is important when evaluating whether an alias remains useful.


For example, an alias may not be used during a particular run simply because no playlist entry required it.


That does not mean the alias is obsolete.


11.5 Persistent Alias Usage History
Alias effectiveness is tracked across executions using persistent application state.


The configured runtime database associated with this function records historical alias usage.


The current alias-usage database is:

cache/alias_usage.db


Persistent history allows the application to distinguish between:


  Configured Alias
        |


                                                       3

          +----> Never Observed
          |
          +----> Previously Used
          |
          +----> Used During Current Run


This provides better information than evaluating aliases from a single playlist execution.


Detailed database behavior is discussed in Section 15.


11.6 Artist Inventory Export
The alias subsystem supports exporting artist information from the Plex library for analysis.


The purpose is to make it easier to identify metadata patterns that may require aliases.


For example, a user may discover that the Plex library contains:


  Doobie Brothers


while external playlists commonly request:


  The Doobie Brothers


The inventory provides source material for identifying these differences systematically rather than waiting
for every difference to appear as an unmatched track.


11.7 Alias Suggestions
Alias analysis can propose potential artist aliases.


A suggestion should include enough information to support human review.


Conceptually:


  Requested Artist
        |
        v
  Compare Against Plex Artists
        |


                                                       4

        v
  Potential Alias
        |
        +----> Confidence
        |
        +----> Reason
        |
        v
  Human Review


Suggested aliases are not automatically assumed to be correct.


Artist identity is sometimes ambiguous, and automatically creating aliases could introduce incorrect
matches throughout the system.


The human remains responsible for deciding whether a suggested equivalence should become configured
alias knowledge.


11.8 Alias Import Workflow
The alias-analysis workflow supports a review-and-import model.


A generated CSV may contain a status or action field such as:


  ADD


Rows explicitly approved for addition can then be incorporated into the alias configuration.


This workflow provides a controlled path from:


  Observed Metadata Difference
          |
          v
  Alias Suggestion
          |
          v
  Human Review
          |
          v
  Approved ADD
          |


                                                      5

          v
  Alias Configuration


The goal is to make alias maintenance scalable without removing human judgment from artist identity
decisions.


11.9 Alias Audit
Alias auditing evaluates the configured alias set.


An audit may identify conditions such as:


     • Aliases that have demonstrated historical usage.
     • Aliases that have not yet been observed in matching.
     • Aliases whose configured relationship can no longer be resolved as expected.

Audit status should be interpreted in the context of persistent usage history rather than a single execution.


For example, an alias that was useful six months ago should not become "unused" merely because today's
playlist did not require it.


11.10 Alias Design Principle
Aliases represent explicit library knowledge.


The governing principle is:


       Use aliases to document known equivalence rather than weakening matching rules globally.


This keeps exceptions visible, maintainable, and auditable.


Detailed alias formats, commands, analysis procedures, and persistence behavior belong in:


docs/subsystems/aliases.md


12. Plex Integration
Plex is the authoritative media system used by Plex Playlist Importer.


The importer reads Plex library metadata, maintains a local matching cache derived from that metadata,
resolves accepted matches back to live Plex objects, and creates or modifies Plex playlists.


                                                      6

Plex-specific communication is primarily encapsulated in:


plex_playlist/plex_client.py


The objective of this boundary is to prevent Plex API behavior from becoming embedded throughout the
application.


12.1 Plex Responsibilities
Within the overall system, Plex is responsible for:


      • Maintaining the music library.
      • Scanning media directories.
      • Maintaining Plex media metadata.
      • Providing live media objects.
      • Storing Plex playlists.

Plex Playlist Importer is responsible for:


      • Determining which requested tracks correspond to Plex tracks.
      • Resolving those matches to live Plex objects.
      • Requesting the appropriate Plex playlist operation.

The importer does not replace Plex library management.


12.2 Plex Connection
The application connects to Plex using configuration values such as:


      • Plex server URL.
      • Authentication token.
      • Music library name.

These values are maintained in config.ini .


Authentication secrets should not be exposed in normal logs, reports, or diagnostic output.


A successful server connection alone is not sufficient to establish that the application can perform its
required Plex operations.


The configured music library must also be available.


                                                       7

12.3 Music Library Selection
Plex Playlist Importer operates against the configured Plex music library.


The library name is treated as configuration because Plex installations may use different names.


For example:


  Music


The application should verify that the configured library exists and is accessible before treating Plex as fully
available for importer operations.


This allows the application to distinguish between:


  Plex server reachable


and:


  Plex server reachable and configured music library available


The second condition is the meaningful health state for this application.


12.4 Plex and the Local Cache
Plex provides authoritative library metadata during a cache refresh.


The relationship is:


  Plex Music Library
        |
        | Retrieve Metadata
        v
  Local Plex Cache
        |
        | Load
        v
  Search Index


After the cache has been populated, most matching work can occur without repeated Plex API access.


                                                       8

This separation improves performance and provides limited resiliency during Plex outages.


It does not make the cache authoritative.


12.5 Live Plex Object Resolution
The matching engine returns cached Plex track records.


Before those records can be used to modify a Plex playlist, they must be resolved back to live Plex media
objects.


Conceptually:


  Matched Cached Track
          |
          v
  Plex Identifier
          |
          v
  Live Plex Lookup
             |
             +----> Found ------> Plex Track Object
             |
             +----> Missing ----> Stale Cache Reference


This step validates that the matched item still exists at the point where a Plex action is required.


12.6 Stale Plex References
A track may exist in the local cache but no longer exist in Plex.


This is an expected consequence of maintaining a local cache of an independently changing media library.


The application should handle this condition gracefully.


Where safe, it should:


      • Identify the stale item.
      • Record or report the condition.
      • Skip the missing Plex object.
      • Continue resolving other matched tracks.

A stale item should not normally cause the entire application to terminate with a raw Plex exception.


                                                        9

The event also provides useful information that the local cache may need to be refreshed.


12.7 Playlist Creation
When the target playlist does not exist and playlist modification is requested, the application can create a
Plex playlist using successfully resolved Plex track objects.


Only tracks that:


    1. Successfully matched against the local search index, and
    2. Successfully resolved to live Plex objects

can be added to the Plex playlist.


Unmatched tracks and stale cache references are not converted into invalid playlist entries.


12.8 Playlist Update
Update mode is intended to maintain an existing playlist while avoiding unnecessary duplicate additions
according to configured playlist behavior.


Conceptually:


  Existing Plex Playlist
          +
  Newly Matched Tracks
          |
          v
  Duplicate Evaluation
          |
          v
  Add Eligible Tracks


The application can report information such as:


  Requested       : 41
  Already present : 2
  Added           : 39
  Final playlist : 65


This provides visibility into the difference between tracks requested by the current execution and tracks
actually added to Plex.


                                                      10

12.9 Playlist Replacement
Replacement mode treats the newly resolved track collection as the desired playlist contents.


The existing playlist contents are replaced according to the implemented Plex playlist workflow.


Replacement should remain an explicit operation because its semantics differ materially from incremental
update.


12.10 Playlist Order
The importer should preserve source order where the playlist operation and source semantics make order
meaningful.


The application should not automatically sort tracks by:


      • Artist.
      • Album.
      • Title.

For XMPlaylist sources, unique tracks are retained according to the ingestion behavior rather than being
deliberately alphabetically sorted.


Users may choose random playback within Plex, but that preference should not cause the importer to
rewrite the natural source order.


12.11 Plex Unavailability
Plex unavailability does not necessarily prevent every application function.


If a usable local cache exists, the importer may still be able to:


      • Parse input.
      • Retrieve XMPlaylist data.
      • Perform matching.
      • Generate reports.
      • Identify unmatched tracks.
      • Perform requested Lidarr processing.

The application cannot modify a Plex playlist while Plex is unavailable.


This should be reported as a controlled operational limitation.


                                                        11

For example:


  Matching completed using local Plex cache.
  Plex playlist update skipped because Plex was unavailable.


12.12 Plex Design Principle
The Plex integration follows two related rules:


       Plex is authoritative for the media library.


and:


       Match locally when possible; resolve against Plex when Plex action is required.


This boundary allows the application to improve performance and resiliency without attempting to become
a second media-library authority.


Detailed Plex client behavior should be documented in:


docs/subsystems/plex.md


13. Lidarr Integration
Lidarr integration provides optional processing for tracks that the Plex matching engine cannot find in the
current Plex library cache.


The integration allows the importer to investigate whether missing music is known to Lidarr and, when
explicitly requested, ask Lidarr to search for an appropriate album.


Low-level Lidarr communication is primarily encapsulated in:


plex_playlist/lidarr_client.py


Higher-level diagnostic and acquisition workflows use that client to process unmatched tracks.


Lidarr integration is optional.


A normal Plex playlist import should not require Lidarr to be installed or available.


                                                      12

13.1 Purpose of Lidarr Integration
An unmatched Plex track can represent several different conditions.


For example:


  Requested Track
        |
        v
  Not Found in Plex
        |
        +----> Artist not known to Lidarr
        |
        +----> Artist known but not managed
        |
        +----> Album known but file missing
        |
        +----> Track known but file missing
        |
        +----> Search previously requested
        |
        +----> Media acquired but Plex/cache not yet updated


Without additional analysis, all of these conditions appear simply as "unmatched."


Lidarr integration provides additional diagnostic information and, when requested, can initiate acquisition
workflows.


13.2 Lidarr Check Mode
The --lidarr-check option performs non-search diagnostic processing for unmatched tracks.


Depending on available Lidarr metadata, the application may determine information such as:


     • Whether the artist can be identified.
     • Whether the artist is already managed by Lidarr.
     • Whether a relevant album can be identified.
     • Whether the track is known.
     • Whether a corresponding media file is available.

The purpose of check mode is visibility.


It does not itself request a new Lidarr search.


                                                     13

13.3 Lidarr Search Mode
The --lidarr-search option allows the importer to request active album searches for eligible
unmatched tracks.


This is a live operation.


If Lidarr finds a suitable release and the configured download workflow accepts it, media may be
downloaded as a result.


This remains true when the importer is executed with --dry-run .


The --dry-run option prevents Plex playlist modification; it does not convert an explicitly requested
Lidarr search into a simulation.


Users and developers should therefore treat:


  --lidarr-search


as an active acquisition request.


13.4 Artist Resolution
Before album-level processing can occur, the application attempts to resolve the requested artist through
Lidarr.


The workflow may include:


      • Artist lookup.
      • MusicBrainz identifier discovery.
      • Detection of an already managed artist.
      • Identification of the corresponding Lidarr artist record.

Artist resolution should avoid unnecessarily creating duplicate managed artists.


External identifiers such as MusicBrainz IDs provide stronger identity information than artist-name
similarity alone when available.


13.5 Album and Track Identification
After resolving the artist, the integration evaluates available album and track information.


                                                       14

The objective is to determine whether the requested track corresponds to media already known to Lidarr
and whether the associated file is present.


This allows the application to distinguish between conditions such as:


  Track Found; File Available


and:


  Track Found; File Missing


These conditions have different operational implications.


A missing Plex match does not necessarily mean the media is unavailable to the broader system.


13.6 Album-Level Search
Lidarr acquisition searches operate at the album level.


Multiple unmatched tracks may therefore correspond to the same album search.


The importer should avoid requesting the same album search repeatedly within one processing workload.


Conceptually:


  Track A ----

  Track B ------> Same Album ----> One Album Search
               /
  Track C ----/


This reduces unnecessary API calls and duplicate Lidarr work.


13.7 Asynchronous Search Behavior
A Lidarr search request is asynchronous.


The following events are distinct:


                                                     15

  Importer Requests Search
            |
            v
  Lidarr Accepts Command
            |
            v
  Lidarr Searches Indexers
            |
               +----> No Results
               |
               +----> Results Rejected
               |
               +----> Release Downloaded
               |
               +----> Search Fails


A successfully queued search does not mean that media has been acquired.


Likewise, a completed Lidarr search command does not guarantee that a file was downloaded.


The importer must preserve this distinction in status reporting.


13.8 Acquisition Status
Lidarr diagnostic results use acquisition status information to describe the outcome of search-related
processing.


Examples of meaningful conceptual states include:


     • Search queued.
     • Search completed with file available.
     • Search completed without file.
     • Search failed.
     • Search skipped because of retry policy.

The exact constants and status names belong to implementation-level documentation.


The Developer Guide's concern is that search-command status and media-acquisition status are separate
concepts.


13.9 Search History and Retry Policy
Repeatedly requesting the same unsuccessful Lidarr search wastes API calls and indexer resources.


                                                     16

The application therefore maintains persistent Lidarr search history.


The configured runtime database associated with Lidarr search history records information used by the
retry policy.


The exact database filename and location should be documented from the current application
configuration.


The retry policy can use information such as:


     • Whether a search was previously requested.
     • When it was requested.
     • How many requests have occurred.
     • Whether enough time has passed to search again.

Conceptually:


  Unmatched Track
        |
        v
  Previous Eligible Search?
        |
     YES|         NO
        |          |
        v          v
  Retry Window   Search May
  Expired?       Be Requested
        |
    +---+---+
    |       |
   NO      YES
    |       |
    v       v
  Skip    Search May
  Search Be Requested


This allows repeated scheduled importer executions without repeatedly issuing the same search request
every time.


13.10 Remembering Failed Searches
The retry design may preserve failed search history according to configuration.


                                                     17

Remembering an unsuccessful search can be valuable because immediate repetition is unlikely to produce
a different result.


At the same time, permanently suppressing future searches would prevent the application from benefiting
when new releases later become available.


The retry interval provides a balance between those concerns.


13.11 Lidarr and Plex Synchronization
After Lidarr acquires media, Plex Playlist Importer does not force an immediate Plex library scan and
rematch cycle.


The intended workflow is:


  Importer
     |
     | Request Album Search
     v
  Lidarr
     |
     | Acquire Media
     v
  Media Library
     |
     | Existing Library Integration
     v
  Plex
     |
     | Library Scan / Update
     v
  Plex Library
     |
     | Later Importer Execution
     v
  Updated Plex Cache / Match


This is a deliberate separation-of-responsibilities decision.


Lidarr and Plex already provide mechanisms for managing media acquisition and library synchronization.


The importer should not duplicate or tightly couple itself to that workflow.


                                                       18

A later importer execution can discover the newly available track after Plex and the local cache have been
updated.


This architectural decision should be preserved in an ADR.


13.12 Lidarr Failure Isolation
Because Lidarr is optional, a Lidarr failure should not normally invalidate matching work already completed.


For example, if Lidarr becomes unavailable while processing unmatched tracks:


      • Existing match results remain valid.
      • Plex playlist processing may continue if Plex is available.
      • Reports should identify the Lidarr failure.
      • Runtime health should mark Lidarr appropriately.

The current implementation may stop the remaining Lidarr processing when a request-level failure occurs.


Finer-grained per-track Lidarr error isolation is a future development item and should not be documented
as currently implemented behavior.


13.13 Lidarr Logging
Lidarr processing can generate a large number of API requests when many tracks are unmatched.


Low-level API request messages are useful for debugging but can clutter normal operational output.


Current logging behavior should be documented according to the released implementation.


A future development cycle is expected to improve Lidarr operational visibility using progress-oriented
output such as processed-item counts while moving lower-level request detail to DEBUG logging.


Until that functionality is released, it should remain identified as future behavior rather than current
functionality.


13.14 Lidarr Design Principle
Lidarr integration follows the principle:


       Investigate and request acquisition of missing media without making media acquisition part
       of the core playlist-import transaction.


                                                        19

A Plex playlist import should not wait indefinitely for a download to complete.


Acquisition happens independently.


The playlist becomes more complete on later executions as newly acquired media becomes available in
Plex.


Detailed Lidarr workflows, diagnostic fields, retry configuration, and status definitions belong in:


docs/subsystems/lidarr.md


14. XMPlaylist Integration
XMPlaylist integration allows SiriusXM channel history to act as a dynamic playlist source.


Instead of reading a static playlist file, the application retrieves recently played tracks from a selected
XMPlaylist station and converts those plays into the same common playlist-entry model used by file-based
imports.


Low-level XMPlaylist API communication is primarily implemented in:


plex_playlist/xmplaylist_client.py


Higher-level ingestion behavior is implemented in:


plex_playlist/xmplaylist_source.py


Persistent ingestion state is managed in:


plex_playlist/xmplaylist_state.py


User station preferences are maintained separately from core system configuration in the resources
directory.


The exact station-preference filename should reflect the currently released implementation.


14.1 Purpose of XMPlaylist Integration
The objective is to maintain Plex playlists that represent the music currently being played by selected
SiriusXM channels.


A typical operational model is:


                                                      20

  SiriusXM Channel
        |
        v
  XMPlaylist History
        |
        v
  Unique Recent Tracks
        |
        v
  Plex Matching
        |
        v
  Plex Playlist


The importer may be executed periodically for multiple stations.


Each execution retrieves enough history to discover new tracks while respecting API request limits and
configured processing targets.


14.2 Station Resolution
Users identify an XMPlaylist station by channel number.


For example:


  --xmstation 72


The application resolves the channel number to XMPlaylist station metadata.


That metadata may include information such as:


     • Channel number.
     • Station name.
     • XMPlaylist station identifier.

For example:


  Channel : 72
  Station : 50s Gold


The resolved station information is then used for history requests and playlist naming.


                                                     21

14.3 Default Plex Playlist Naming
When no station-specific playlist-name override is configured, XMPlaylist-generated Plex playlists use the
standard naming convention:


  Ch <channel number> - <station name>


For example:


  Ch 72 - 50s Gold


This provides predictable naming without requiring every station to be individually configured.


Station preferences may override the default playlist name when required.


14.4 Station Preferences
XMPlaylist station preferences are user operational data and are intentionally maintained separately from
 config.ini .


The design principle is:


        config.ini contains system and application configuration; station preferences describe
       how individual user-selected stations should behave.


The station-preference file belongs in:


resources/


A station entry may define values such as:


      • Channel number.
      • Playlist-name behavior.
      • Other supported station-specific preferences.

A playlist value of:


  default


indicates that the standard:


                                                        22

  Ch <channel number> - <station name>


naming convention should be used.


A configured name can override that default.


The exact current file format and supported fields should be documented in:


docs/subsystems/xmplaylist.md


or the appropriate user configuration reference.


14.5 History Window
XMPlaylist ingestion operates within a configurable history window expressed in hours.


For example:


  --xmhours 168


represents a seven-day history window.


The history window defines the oldest play that is relevant to the current ingestion workload.


It does not necessarily mean that every track within the entire window must be retrieved during one
execution.


The amount of work performed during one execution is also controlled by request and track limits.


14.6 API Request Budget
XMPlaylist API access is constrained by a configurable maximum request budget.


For example:


  --xm-max-requests 8


The request budget prevents one execution from consuming an uncontrolled number of API requests.


                                                     23

Request accounting includes the API work defined by the current ingestion implementation, including
station resolution where applicable.


When the request budget is exhausted before the requested history window is fully processed, ingestion
can stop with partial backfill state preserved for a later execution.


14.7 Unique Track Target
The application can limit one XMPlaylist execution by the number of unique tracks retrieved.


For example:


  --xm-max-tracks 100


This option allows one execution to retrieve multiple pages of history until approximately the requested
workload has been accumulated, subject to other limits.


The important distinction is:


       The unique-track target controls tracks returned by the ingestion process; it does not change
       the number of tracks returned by an individual XMPlaylist API response.


The importer continues requesting history pages until a stopping condition is reached.


This allows a scheduled execution to retrieve more useful playlist material than would be available from
only one API page.


14.8 Deduplication Before Track Counting
SiriusXM channels may play the same song multiple times within the selected history window.


The purpose of the generated Plex playlist is to contain unique tracks rather than preserve every broadcast
occurrence.


Deduplication therefore occurs before evaluating the unique-track target.


For example:


  API Plays Retrieved
  -------------------
  Track A


                                                     24

  Track B
  Track C
  Track A
  Track D
  Track E


represents:


  5 Unique Tracks


not six.


If the target is five unique tracks, the duplicate occurrence of Track A does not count toward the target.


This behavior allows the track target to represent the actual number of distinct playlist candidates.


14.9 Natural Order
XMPlaylist ingestion does not deliberately sort tracks.


Unique tracks are retained according to the natural ingestion behavior, with first-seen order serving as an
implementation consequence of deduplication.


The application does not attempt to preserve:


      • Play count.
      • First-played statistics.
      • Last-played statistics.
      • Broadcast frequency.

The objective is to create a fresh collection of unique tracks from the selected history window.


14.10 Pagination
One XMPlaylist API history response may not contain enough data to satisfy the requested workload.


The ingestion process therefore supports retrieving multiple history pages.


Conceptually:


                                                      25

  History Page 1
        |
        v
  Unique Track Count < Target?
         |
        YES
         |
         v
  History Page 2
        |
        v
  Unique Track Count < Target?
        |
       YES
        |
        v
  Continue While Budget Allows


Pagination stops when one of the ingestion stopping conditions is reached.


14.11 Ingestion Stopping Conditions
An XMPlaylist ingestion run may stop because:


     • The unique-track target was reached.
     • The API request budget was reached.
     • The requested history window was fully processed.
     • No additional history cursor was available.
     • An API rate limit was encountered.
     • An unrecoverable XMPlaylist error occurred.

The stop reason should be observable.


For example:


  XMPlaylist ingestion:
  channel 72 50s Gold,
  100 unique tracks,
  6 requests,
  backfill partial;
  stop reason=TRACK_LIMIT_REACHED


This allows the operator to understand whether ingestion completed the history window or intentionally
stopped after reaching the requested workload.


                                                   26

14.12 Persistent Cursor State
When the request or track limit stops ingestion before the selected history window has been fully
processed, the application can preserve its position.


Persistent state allows the next execution to resume from the saved cursor rather than starting the same
backfill work again.


Conceptually:


  Execution 1
  -----------
  Page 1
  Page 2
  Page 3
  STOP: Track Target Reached
  Save Cursor
        |
        v
  Execution 2
  -----------
  Load Cursor
  Resume Page 4
  Page 5
  ...


This is especially useful when operating under API request constraints.


14.13 History Window Changes
Saved ingestion state is associated with the history-window assumptions under which it was created.


If the configured history window changes, previously saved backfill state may no longer represent the
desired retrieval boundary.


The application therefore resets the relevant saved ingestion state when the history window changes.


This prevents a cursor created for one window from incorrectly controlling ingestion for a materially
different window.


                                                     27

14.14 Rate Limits
XMPlaylist rate limiting is treated as an expected external-service condition.


When a rate limit is encountered, the application should:


      • Stop making additional requests.
      • Preserve usable partial results.
      • Preserve appropriate resume state.
      • Report the rate-limit condition.

A rate limit should not invalidate tracks that were already retrieved successfully.


The request-budget mechanism is intended to reduce the likelihood of reaching external service limits, but
the application must still handle a service-enforced limit when it occurs.


14.15 XMPlaylist and Dry-Run Behavior
XMPlaylist ingestion remains live when --dry-run is specified.


The --dry-run option prevents modification of the Plex playlist.


It does not prevent XMPlaylist from:


      • Resolving stations.
      • Retrieving history.
      • Consuming API requests.
      • Updating persistent ingestion state.
      • Updating history-related runtime data.

This distinction is important during testing and operation.


For example:


  --xmstation 72 --dry-run


does not mean:


  Simulate XMPlaylist API access


It means:


                                                       28

  Perform XMPlaylist ingestion and matching normally,
  but do not modify the target Plex playlist.


14.16 XMPlaylist Failure Isolation
XMPlaylist is required when XMPlaylist is the selected playlist source.


If the service cannot provide the requested source data and no usable result can be produced, that
particular import cannot proceed normally.


This differs from Lidarr, which is an optional downstream integration.


The distinction is:


  XMPlaylist Selected as Source
          |
          v
  Source Required for This Run


versus:


  File Playlist Source
          |
          v
  Lidarr Optional


Runtime health should reflect this difference.


14.17 XMPlaylist Design Principle
XMPlaylist ingestion balances three independent controls:


  History Window
        +
  API Request Budget
        +
  Unique Track Target


                                                      29

        =
  Work Performed During One Execution


The history window defines what data is relevant.


The request budget limits API consumption.


The unique-track target limits the desired amount of playlist material gathered during one execution.


Persistent cursor state allows useful work to continue across multiple executions when the complete
window cannot or should not be processed at once.


Detailed API behavior, station-preference syntax, state schema, pagination, and CLI options belong in:


docs/subsystems/xmplaylist.md


15. Persistent Application State
Plex Playlist Importer maintains several categories of information between executions.


Persistent state allows the application to remember information that would otherwise be lost when the
process exits.


The application uses embedded SQLite databases rather than requiring an external database server.


These databases support different operational purposes and should be understood according to the data
they own rather than simply as interchangeable .db files.


Current persistent categories include:


     • Plex library cache.
     • Artist alias usage history.
     • Lidarr search history.
     • XMPlaylist ingestion state and history.

Historical analytics may also be persisted through application-generated reporting data according to the
current implementation.


The current persistent database paths are:

cache/plex_library.db
cache/alias_usage.db
cache/lidarr_search_history.db
cache/xmplaylist_history.db

These paths should remain configurable where supported by the owning subsystem.


                                                    30

15.1 Why Persistent State Exists
Each category of persistent state solves a different problem.


  Plex Cache
      |
      +----> Avoid repeatedly retrieving the complete Plex library


  Alias Usage
      |
      +----> Remember which aliases have demonstrated value

  Lidarr Search History
      |
      +----> Avoid repeatedly requesting the same searches

  XMPlaylist State
      |
      +----> Resume incremental history ingestion


These are separate responsibilities.


The fact that each can be implemented using SQLite does not mean they represent the same type of data.


15.2 Rebuildable Data Versus Historical Knowledge
Persistent application data can be divided conceptually into two categories.


Rebuildable State

Data that can be recreated from an authoritative external source.


The primary example is the Plex library cache.


If the cache is deleted, it can be rebuilt by retrieving the Plex music library again.


The loss may cause inconvenience or require Plex availability, but the underlying media information still
exists in Plex.


Historical Knowledge

Data that represents what the importer has learned or done across previous executions.


                                                        31

Examples include:


      • Alias usage history.
      • Lidarr search history.
      • XMPlaylist cursor and ingestion state.

Deleting this information may not corrupt the application, but the historical context cannot necessarily be
reconstructed from the current state of an external service.


For example, deleting Lidarr search history may cause the importer to forget that it recently requested a
search.


Deleting XMPlaylist cursor state may cause ingestion to repeat previously processed history.


This distinction matters for:


      • Backup.
      • Recovery.
      • Migration.
      • Troubleshooting.


15.3 Plex Library Cache Database
The Plex cache database stores a local representation of relevant Plex music-library metadata.


Its responsibilities include:


      • Persisting Plex track records.
      • Recording cache metadata.
      • Recording the last successful refresh.
      • Supporting cache age evaluation.
      • Providing the source data for the in-memory search index.

The configured path is defined in config.ini .


The cache is rebuildable because Plex remains authoritative.


However, deleting the cache may temporarily prevent matching if Plex is unavailable when the application
next runs.


15.4 Artist Alias Usage Database
Alias usage persistence records historical information about configured artist aliases.


                                                     32

Its purpose is to support questions such as:


      • Has this alias ever contributed to a successful match?
      • Is this alias currently unused or merely not required by today's playlist?
      • Which aliases provide demonstrated value?

This data represents application history rather than a copy of an external authoritative source.


The alias definitions themselves remain in:


resources/aliases.txt


The database records usage knowledge about those definitions.


The distinction is:


  resources/aliases.txt
          |
          +----> What aliases are configured

  Alias Usage Database
          |
          +----> What the application has observed about those aliases


15.5 Lidarr Search History Database
Lidarr search history records information about acquisition searches requested by the importer.


Its purpose is to support retry policy and prevent repeated search requests during frequent scheduled
executions.


Information may include:


      • Search identity.
      • Previous request time.
      • Request count.
      • Other information required by retry behavior.

This database does not replace Lidarr's own state.


Lidarr remains authoritative for:


      • Managed artists.
      • Albums.


                                                        33

      • Search commands.
      • Download activity.
      • Media acquisition.

The importer database remembers what the importer has requested so that it can make better decisions
during future runs.


15.6 XMPlaylist State and History Database
XMPlaylist persistence supports incremental ingestion.


Its responsibilities may include:


      • Station-specific ingestion state.
      • Saved history cursor.
      • History-window information.
      • Oldest processed timestamp.
      • Backfill completion state.
      • Persisted track-history information required by the ingestion workflow.

This state allows the importer to resume work across executions while respecting API request and unique-
track limits.


Unlike the Plex cache, this data represents the importer's progress through an external historical data
stream.


Deleting it may cause previously processed XMPlaylist history to be retrieved again.


15.7 Database Initialization
Each persistence subsystem should own initialization of its database structures.


Callers should not need to create SQLite tables manually.


Conceptually:


  Application Starts
        |
        v
  Subsystem Required?
        |
       YES
        |


                                                     34

        v
  Initialize Persistent Store
        |
        +----> Database Exists ----> Validate / Use
        |
          +----> Database Missing ---> Create Required Schema


This supports first-run behavior and self-contained deployment.


15.8 Schema Versioning
Persistent database structures may need to evolve as application functionality changes.


Where schema changes are required, the application should manage them deliberately.


A schema version allows the application to distinguish between:


     • A current database.
     • An older compatible database.
     • A database requiring migration.
     • An unsupported database structure.

Schema changes should avoid silently destroying historical state.


Where practical, migrations should preserve existing information.


Migration behavior should be protected by automated tests.


15.9 SQLite Operational Behavior
SQLite provides persistent relational storage without requiring:


     • A separate database server.
     • Database service management.
     • Network database connectivity.
     • Additional authentication infrastructure.

This fits the application's self-contained deployment model.


Individual persistence modules may use SQLite features such as:


     • Write-Ahead Logging.
     • Busy timeouts.
     • Transactional updates.


                                                     35

The specific settings should be appropriate to each subsystem's access pattern.


The application architecture does not require every persistent data category to share one database file.


Separate databases may improve:


      • Logical ownership.
      • Backup choices.
      • Troubleshooting.
      • Schema independence.
      • Future migration.


15.10 Database Locations
Runtime database paths should be configurable or consistently located according to the application's
directory structure.


Where the current release uses paths such as:


  cache/<database>.db


the exact filenames should be documented in the configuration reference.


The Developer Guide should explain the purpose of each database.


docs/configuration.md should document the exact configured path and configuration key.


Subsystem documentation should describe the detailed schema and lifecycle where necessary.


This separation prevents hard-coded filenames in architectural documentation from becoming inaccurate if
deployment paths later change.


15.11 Backup Considerations
Not all databases have equal backup value.


The Plex library cache is rebuildable.


Historical state may be more valuable to preserve.


A backup strategy should therefore prioritize data according to recoverability.


                                                     36

Conceptually:


                            Can Be Rebuilt?
                                 |
                    +----------+----------+
                    |                     |
                   YES                    NO /
                    |                 Not Easily
                  |                             |
                  v                             v
           Plex Library Cache             Historical State
                                          - Alias Usage
                                          - Lidarr Search History
                                          - XMPlaylist State


A future containerized deployment should make persistent application directories externally mountable so
that runtime state survives container replacement.


Containerization is a future deployment item and should not be interpreted as current functionality.


15.12 Resetting Persistent State
Deleting or resetting persistent state should be treated according to the subsystem involved.


Resetting the Plex cache means:


       Rebuild the local representation of Plex.


Resetting Lidarr search history means:


       Forget previous importer search requests.


Resetting alias usage means:


       Forget historical evidence of alias effectiveness.


Resetting XMPlaylist state means:


       Forget previous ingestion progress and potentially repeat history retrieval.


These operations have different consequences and should not be represented as one generic "clear
database" action.


                                                       37

15.13 Persistence and Failure Isolation
A failure in one persistent subsystem should not automatically imply corruption or failure of another.


For example:


       • An XMPlaylist state database problem should not invalidate the Plex library cache.
       • Alias usage persistence failure should not change the configured aliases in resources/
        aliases.txt .
       • Lidarr search-history failure should not imply that Lidarr itself is unavailable.

Keeping logical ownership clear allows failures to be diagnosed at the correct boundary.


15.14 Persistence Design Principle
The application's persistence strategy follows two related principles:


        Persist information when remembering it improves future behavior.


and:


        Keep authoritative external data distinct from local application knowledge.


Plex metadata can be cached because Plex remains authoritative.


Lidarr search history is maintained because the importer needs to remember its own previous actions.


XMPlaylist state is maintained because the importer needs to remember its progress.


Alias usage is maintained because the importer needs to remember what it has learned about configured
aliases.


Understanding those distinctions is more important than the fact that the underlying storage technology is
SQLite.


Detailed database schemas and subsystem-specific persistence behavior belong in the corresponding
subsystem documentation.


                                                         38


16. Configuration Architecture
Plex Playlist Importer separates long-lived application configuration from execution-specific command-line
options and user-maintained operational reference data.


This separation keeps configuration responsibilities clear and reduces the need to modify application
source code for normal operational changes.


The primary configuration file is:


config.ini


Additional user-maintained resources are stored under:


resources/


Examples include:


      • resources/aliases.txt
      • resources/xmstations.ini

Command-line options provide execution-specific behavior and overrides.


The general model is:


  Application Defaults
          |
          v
  config.ini
          |
          v
  Resource Files
          |
          v
  Command-Line Options
          |
          v
  Effective Runtime Configuration


Not every setting follows the same precedence path, but the principle is consistent:


       Persistent behavior belongs in configuration. One-time actions belong on the command line.


                                                      1

16.1 Purpose of config.ini
config.ini contains application and system configuration that is expected to remain stable across
multiple executions.


Examples include:


     • Plex connection information.
     • Plex authentication.
     • Plex music-library selection.
     • Matching thresholds.
     • Matching weights.
     • Metadata-normalization behavior.
     • Cache configuration.
     • Report locations.
     • Logging configuration.
     • Lidarr connection settings.
     • Lidarr retry behavior.
     • XMPlaylist integration defaults.

Configuration should be grouped logically by subsystem.


A subsystem should read only the configuration it requires rather than depend on unrelated sections.


16.2 Configuration Sections
The current configuration is organized into sections that correspond to major application responsibilities.


Examples include:


  [plex]

  [matching]

  [cache]

  [reports]

  [logging]

  [playlist]

  [lidarr]


                                                      2

  [xmplaylist]


The exact set of sections may evolve as functionality changes.


The important design principle is that configuration organization should reflect logical ownership.


Matching configuration belongs with matching.


Cache configuration belongs with the cache subsystem.


Integration credentials belong with the integration that consumes them.


16.3 Matching Configuration
Matching behavior is intentionally configurable because music libraries and source metadata differ.


Current matching configuration can include settings such as:


     • Acceptance threshold.
     • Worker or thread count.
     • Artist preference behavior.
     • Metadata-stripping options.
     • Weighted scoring values.

Examples of configurable matching weights include:


     • Artist.
     • Album artist.
     • Title.
     • Combined metadata.

The matcher should receive effective configuration values rather than directly parse configuration files
throughout the matching code.


This keeps configuration loading separate from matching behavior.


16.4 Cache Configuration
Cache configuration controls how the local Plex library cache behaves.


                                                      3

Settings may include:


     • Whether caching is enabled.
     • Database path.
     • Refresh-on-start behavior.
     • Maximum cache age.

For example, the configuration may contain a database setting such as:


  database = cache/plex_library.db


The exact filename and path should reflect the released config.ini .


The cache subsystem should treat this path as configuration rather than hard-code it.


16.5 Reporting Configuration
Reporting settings define where generated output is written.


Examples may include:


     • Playlist match CSV.
     • Unmatched-track CSV.
     • Lidarr report.
     • Other currently implemented reports.

Only report types available in the released application should be documented as current functionality.


Planned dashboard or HTML presentation features should remain in roadmap or future-architecture
documentation until released.


16.6 Logging Configuration
Logging settings may define:


     • Log level.
     • Log directory.
     • Log filename.

For example:


                                                     4

  level = INFO
  directory = logs
  filename = playlist_import.log


The logging subsystem should own interpretation of these settings.


Individual modules should use the configured logging infrastructure rather than independently create their
own file handlers or output conventions.


16.7 Playlist Configuration
Playlist-related settings control behavior associated with playlist construction.


Examples include:


      • Duplicate handling.
      • Order behavior where configurable.

The current application preserves source order unless a specific workflow defines otherwise.


Configuration should not be used to silently change semantics that users would reasonably consider
destructive.


16.8 Lidarr Configuration
Lidarr configuration may include:


      • Base URL.
      • API key.
      • Retry interval.
      • Search-history behavior.
      • Other integration-specific settings.

Credentials should be treated as secrets.


They should not be:


      • Written to logs.
      • Included in reports.
      • Committed to public source-control repositories.

The application should validate required Lidarr configuration only when Lidarr functionality is requested or
enabled.


                                                       5

A missing Lidarr configuration should not prevent a normal Plex-only import.


16.9 XMPlaylist Configuration
XMPlaylist configuration may define defaults such as:


      • History window.
      • Maximum API requests per run.
      • Unique-track target.
      • Other integration-specific settings.

Execution-specific command-line options may override these defaults where supported.


For example:


  --xmhours
  --xm-max-requests
  --xm-max-tracks


The effective runtime values should be observable so that an operator can understand what limits
governed a particular ingestion run.


16.10 Resource Files
Some user-maintained operational data does not belong in config.ini .


Examples include:


Artist Aliases

Stored in:


resources/aliases.txt


This file represents user-maintained artist-equivalence knowledge.


XMPlaylist Station Preferences

Stored under:


resources/


                                                        6

Station preferences are stored in:

resources/xmstations.ini


Station preferences are separated from config.ini because they represent per-station user choices
rather than core system configuration.


This separation allows the station list to grow without turning the main configuration file into a large
operational data store.


16.11 Command-Line Options
Command-line options are intended for:


     • Selecting an input source.
     • Selecting a Plex playlist.
     • Choosing a one-time operation.
     • Requesting cache refresh.
     • Enabling Lidarr check or search behavior.
     • Selecting an XMPlaylist station.
     • Overriding XMPlaylist workload limits.
     • Enabling dry-run behavior.

The command line should not become a second configuration file.


Settings that users repeatedly provide on every execution should be considered candidates for persistent
configuration when appropriate.


16.12 Configuration Precedence
Where both persistent configuration and command-line overrides exist, the precedence should be
predictable.


Conceptually:


  Application Default
        |
        v
  config.ini Value
        |
        v
  Command-Line Override
        |


                                                       7

        v
  Effective Runtime Value


The exact precedence rules should be documented in:


docs/configuration.md


A developer adding a new configuration option should explicitly decide:


     • Whether a default exists.
     • Whether it belongs in config.ini .
     • Whether it can be overridden on the command line.
     • How the effective value is reported.


16.13 Configuration Validation
Configuration should be validated before the application reaches the operation that depends on it.


Examples include:


     • Missing Plex URL.
     • Missing Plex token.
     • Invalid matching threshold.
     • Invalid database path.
     • Invalid numeric API limits.
     • Missing Lidarr credentials when Lidarr is explicitly requested.

Validation should produce a clear application-level message rather than an unrelated downstream
exception.


16.14 Configuration and Secrets
Authentication tokens and API keys are operational secrets.


They should be excluded from:


     • Source control.
     • Reports.
     • Diagnostic output.
     • Exception messages where practical.

Example configuration files intended for public distribution should use placeholders rather than real
credentials.


                                                      8

16.15 Configuration Design Principle
The configuration architecture follows two rules:


        Stable behavior belongs in configuration.


and:


        Execution-specific actions belong on the command line.


Operational reference data such as aliases and station preferences should remain separate when they have
their own lifecycle and maintenance workflow.


Detailed configuration keys, defaults, and examples belong in:


docs/configuration.md


17. Reporting and Analytics
Plex Playlist Importer treats reporting as part of normal application behavior.


The application should not merely perform work.


It should provide enough information to understand:


       • What was requested.
       • What succeeded.
       • What did not succeed.
       • Why a match was accepted.
       • Why a track remained unmatched.
       • What optional integrations did.
       • What operational limitations occurred.

Reporting serves both immediate operational review and longer-term analysis.


17.1 Reporting Categories
Application output can be divided conceptually into several categories.


Operational Reports

Describe the results of the current execution.


                                                      9

Examples include:


     • Playlist match report.
     • Unmatched-track report.
     • Lidarr diagnostic report.

Diagnostic Information

Helps explain unexpected or noteworthy behavior.


Examples include:


     • Match reasons.
     • Confidence values.
     • Metadata warnings.
     • Stale Plex-cache references.

Historical Analytics

Preserve trends or aggregate information across executions.


Examples may include:


     • Match rates.
     • Unmatched rates.
     • Unique artist counts.
     • Alias effectiveness.

Runtime Status

Provides machine-readable or concise summary information about the most recent execution.


These categories may use different files or persistence mechanisms because they serve different audiences.


17.2 Playlist Match Report
The playlist match report records the outcome of matching requested tracks against the Plex library.


A useful match report may include information such as:


     • Original artist.
     • Original title.
     • Matched Plex artist.
     • Matched Plex title.
     • Match score.
     • Confidence label.


                                                    10

     • Match reason.
     • Match notes.

The report should preserve original input values so that the user can compare:


  Requested


against:


  Matched


without reconstructing the original playlist source.


17.3 Unmatched-Track Report
Unmatched tracks should be reported explicitly.


An unmatched report provides a focused list of tracks that require further attention.


These tracks may later be:


     • Reviewed manually.
     • Evaluated for alias opportunities.
     • Checked through Lidarr.
     • Requested through Lidarr search.

Separating unmatched tracks from the full match report makes remediation easier.


17.4 Lidarr Reporting
When Lidarr processing is requested, the application produces information describing the outcome of that
processing.


Examples may include:


     • Requested artist.
     • Requested track.
     • Plex match notes.
     • Lidarr artist status.
     • Album information.
     • Search status.
     • Acquisition-related information.


                                                       11

The report should preserve the distinction between:


     • A search being queued.
     • A search completing.
     • A file actually becoming available.

These are separate events.


17.5 Match Reasons and Confidence
Reporting should expose enough information to make matching decisions reviewable.


For example:


  Requested:
  The Doobie Brothers - Listen to the Music

  Matched:
  Doobie Brothers - Listen to the Music

  Reason:
  Artist alias applied; exact normalized title match

  Confidence:
  High


This is more useful than:


  Matched: Yes


Explainability allows users to trust strong matches and investigate questionable ones.


17.6 Metadata Warnings
A successful match may still produce a warning.


Examples may include:


     • Artist metadata differs.
     • Album artist was used.
     • Fallback logic was required.
     • A stale cache record was encountered later.


                                                      12

Warnings should not automatically be treated as failures.


They indicate that the application completed the requested operation but detected something worth
reviewing.


17.7 Alias Reporting
Alias-related reporting may support:


      • Suggested aliases.
      • Approved additions.
      • Alias audit.
      • Historical alias usage.

The purpose is to make the alias system maintainable over time.


Alias reports should help answer:


      • Which aliases have been useful?
      • Which aliases have never been observed?
      • Which configured aliases no longer resolve as expected?
      • Which new aliases may improve matching?


17.8 Match Analytics
Historical analytics provide context beyond one execution.


Examples include:


      • Total entries processed.
      • Match percentage.
      • Unmatched percentage.
      • Normal versus fallback matches.
      • Unique artists.
      • Confidence distributions.

Analytics are useful for identifying trends.


For example:


  Match rate declines after adding a new playlist source.


or:


                                                    13

  Fallback matches increase after a normalization change.


Such trends may reveal problems that are not obvious from one execution.


17.9 Latest-Run Status
The application may maintain concise information describing the most recent execution.


This information can support:


     • Manual inspection.
     • Scheduled-job monitoring.
     • Future operational dashboard functionality.

Current machine-readable status should document only fields actually produced by the released
implementation.


Future dashboard presentation should not be described as current functionality until implemented.


17.10 Report Timing
Reports should be generated at points in the lifecycle that preserve useful information even if a later
operation fails.


For example, match results should be available before the final Plex playlist modification.


This means:


  Matching Completed
        |
        v
  Match Reports Written
        |
        v
  Live Plex Resolution
        |
        v
  Playlist Modification


If Plex later becomes unavailable, the matching work and diagnostic information are still preserved.


                                                      14

17.11 Reports Versus Logs
Reports and logs serve different purposes.


Reports answer:


       What was the result?


Logs answer:


       What happened while the application was running?


A user reviewing unmatched tracks should not need to parse a log file.


A developer diagnosing an HTTP failure should not expect the playlist match CSV to contain a complete
request trace.


The two forms of output should complement one another.


17.12 Reporting Design Principle
The reporting architecture follows the principle:


       A result should be understandable without reading the source code.


Reports should make application decisions visible, while logs provide the operational detail required to
diagnose how those decisions were reached.


18. Logging and Observability
Logging provides the chronological operational record of an application execution.


It complements reports by showing what the application did while processing the workload.


Logging is initialized through:


plex_playlist/logging_config.py


The exact implementation may evolve, but logging should remain centralized and consistent across
subsystems.


                                                     15

18.1 Purpose of Logging
Logs should make it possible to understand:


     • When an execution started.
     • What major processing stage was active.
     • Which components were available.
     • Whether the cache was used or refreshed.
     • How many entries were loaded.
     • Whether optional integrations were invoked.
     • What warnings occurred.
     • Whether the final operation succeeded.

Logs are particularly important for unattended scheduled execution.


18.2 Logging Levels
The application should use standard logging levels consistently.


DEBUG

Detailed implementation and diagnostic information.


Examples:


     • Low-level API requests.
     • Candidate scoring details.
     • Internal state transitions.
     • Pagination details.

INFO

Normal operational progress.


Examples:


     • Cache loaded.
     • Search index built.
     • Playlist loaded.
     • Matching completed.
     • Lidarr workflow started.
     • Playlist updated.

WARNING

Unexpected but recoverable conditions.


                                                     16

Examples:


      • Plex unavailable but cache usable.
      • Stale cached track reference.
      • Optional integration unavailable.
      • Individual malformed playlist record skipped.

ERROR

A significant operation failed.


Examples:


      • Required playlist source unavailable.
      • Cache unavailable when no Plex connection exists.
      • Plex playlist modification failed.

Logging levels should help operators identify severity without reading every line.


18.3 Console Versus File Logging
Console output should prioritize useful operational progress.


File logs may contain additional detail needed for troubleshooting.


The same event should not be emitted repeatedly at multiple levels without purpose.


Normal console output should avoid becoming overwhelmed by low-level API request information.


Where detailed request tracing is useful, DEBUG logging is the appropriate destination.


18.4 Progress-Oriented Logging
Long-running operations should provide progress at a meaningful level.


Examples include:


  Search index ready (55,982 tracks)
  Playlist loaded: 429 entries
  Matching completed: 391 matched, 38 unmatched


Progress messages should help an operator determine that the application is still functioning.


                                                        17

They should not require exposing every internal method call.


18.5 Component Availability
Component state should be logged explicitly where relevant.


For example:


  Plex       : AVAILABLE
  Lidarr     : AVAILABLE
  XMPlaylist : NOT_CONFIGURED


This gives context to later behavior.


A skipped Lidarr workflow means something different when Lidarr is:


  NOT_CONFIGURED


than when it is:


  UNAVAILABLE


18.6 Cache Observability
Cache behavior should be visible.


Useful events include:


      • Cache database opened.
      • Cache empty.
      • Cache age.
      • Cache stale.
      • Cache refresh requested.
      • Cache refresh completed.
      • Track count after refresh.
      • Search index built.

This information helps distinguish matching problems from stale-library problems.


                                                    18

18.7 Matching Observability
The default log should summarize matching rather than print detailed candidate scoring for every track.


Useful summary information includes:


     • Number of entries processed.
     • Number matched.
     • Number unmatched.
     • Fallback-match count where implemented.
     • Warnings.

Detailed scoring belongs at DEBUG level or in reports where appropriate.


18.8 Lidarr Observability
Lidarr processing can involve many API calls.


Current released behavior should be documented accurately.


The long-term operational goal is to make INFO logging progress-oriented while reserving low-level request
details for DEBUG.


Future improvements should not be presented as already implemented.


The important design rule is:


       Normal logs should explain progress; debug logs should explain implementation detail.


18.9 XMPlaylist Observability
XMPlaylist ingestion should expose enough information to explain the work performed.


Useful information includes:


     • Channel number.
     • Station name.
     • History window.
     • API request count.
     • Unique-track count.
     • Stop reason.
     • Whether ingestion is complete or partial.

For example:


                                                    19

  XMPlaylist ingestion:
  channel 72,
  100 unique tracks,
  6 requests,
  stop reason=TRACK_LIMIT_REACHED


This is particularly important because one execution may intentionally stop before processing the entire
available history.


18.10 Sensitive Data
Logs must not expose secrets.


This includes:


     • Plex authentication tokens.
     • Lidarr API keys.
     • Other service credentials.

Diagnostic logging should redact or omit sensitive values.


A developer should assume that logs may eventually be shared for troubleshooting.


18.11 End-of-Run Summary
A completed execution should provide a concise operational summary.


Conceptually:


  Entries processed : 100
  Matched           : 72
  Unmatched         : 28
  Plex playlist          : Updated
  Lidarr                  : Available
  XMPlaylist              : Not configured
  Warnings                : 1


The exact fields depend on the requested workflow.


The summary should describe outcome rather than repeat the entire log.


                                                     20

18.12 Logging Design Principle
Logging follows the principle:


       Make normal operation easy to follow and exceptional behavior easy to diagnose.


A log should not be so quiet that an operator cannot understand progress.


It should not be so verbose that important events disappear inside routine noise.


Detailed logging behavior and troubleshooting guidance belong in:


docs/logging.md


19. Runtime Health and Resiliency
Plex Playlist Importer depends on several local and external components.


Not all components are required for every execution.


The application therefore evaluates health in terms of both:


     • Component availability.
     • The requirements of the current operation.

This allows useful work to continue when possible without pretending that unavailable functionality
succeeded.


19.1 Component Health States
A simple conceptual health model includes:


  AVAILABLE
  UNAVAILABLE
  NOT_CONFIGURED


These states should remain distinct.


AVAILABLE

The component is configured and usable.


                                                     21

UNAVAILABLE

The component is expected or configured but cannot currently be used.


NOT_CONFIGURED

The component is not configured for use.


NOT_CONFIGURED is not necessarily an error.


For an optional integration such as Lidarr, it may represent a perfectly valid deployment.


19.2 Required Versus Optional Components
Whether a component failure is fatal depends on the requested workflow.


Examples:


Plex

Required for:


       • Creating a Plex playlist.
       • Updating a Plex playlist.
       • Replacing a Plex playlist.
       • Refreshing the Plex cache.

Potentially not required for:


       • Matching against an existing usable cache.
       • Generating match reports.
       • Performing Lidarr analysis.

Lidarr

Optional unless the user explicitly requests Lidarr processing.


XMPlaylist

Required when XMPlaylist is selected as the playlist source.


Not required for file-based imports.


This dependency model should be evaluated per execution rather than globally.


                                                      22

19.3 Plex Unavailable with Usable Cache
One important resiliency scenario is:


  Plex       : UNAVAILABLE
  Plex Cache : USABLE


In this state, the application may still be able to:


      • Parse input.
      • Build the search index.
      • Match tracks.
      • Generate reports.
      • Process unmatched tracks through Lidarr.

The application cannot safely modify the Plex playlist.


The execution may therefore complete partially with a clear warning.


19.4 Plex Unavailable without Usable Cache
If both Plex and the local cache are unavailable, the application has no authoritative or cached library data
against which to match.


Conceptually:


  Plex       : UNAVAILABLE
  Plex Cache : EMPTY / UNAVAILABLE


Matching cannot proceed.


This is a fatal limitation for normal playlist importing.


The application should stop with a clear explanation.


19.5 Lidarr Unavailability
Lidarr is an optional integration.


If Lidarr is unavailable during a normal Plex import that did not require Lidarr, the import should continue
normally.


                                                        23

If the user explicitly requested:


  --lidarr-check


or:


  --lidarr-search


the application should report that the requested Lidarr portion could not be completed.


Existing matching results should remain valid.


Where possible, Plex playlist processing should continue independently.


19.6 XMPlaylist Unavailability
XMPlaylist is different from Lidarr when it is selected as the playlist source.


If the user requests:


  --xmstation <channel>


and XMPlaylist cannot provide source data, the application may have no playlist workload to process.


In that case, the requested import cannot proceed normally.


Usable partial data already retrieved before a later failure may be preserved according to the current
ingestion implementation.


19.7 Rate Limiting
External rate limiting is an expected operational condition.


The application should not treat a rate limit as an internal software defect.


When rate limiting occurs, the application should:


      • Stop additional requests.
      • Preserve valid completed work.
      • Preserve state required for later continuation where supported.


                                                        24

      • Report the limiting condition.

This is particularly important for XMPlaylist ingestion.


19.8 Timeout and Network Failure
Network-dependent operations may fail because of:


      • Timeout.
      • DNS failure.
      • Connection refusal.
      • Remote service restart.
      • Temporary network interruption.

Expected network errors should be converted into component-level operational failures where practical.


For example:


  Lidarr unavailable: connection timed out


is preferable during normal operation to an uncontrolled stack trace from the HTTP client.


Unexpected exceptions should still remain visible during development and testing.


19.9 Stale Cache Resiliency
A stale or inconsistent cache should be handled according to the point at which the inconsistency is
discovered.


A stale-by-age cache may trigger refresh behavior.


A cached track that no longer exists in Plex may be discovered only during live object resolution.


In that case, the application should isolate the affected track where safe rather than fail the entire playlist
operation.


This allows:


  100 matched cached tracks
  1 stale Plex reference
  99 valid Plex objects


                                                       25

to result in a controlled 99-track playlist operation rather than a complete application failure.


The stale condition should still be reported.


19.10 Partial Success
The application should distinguish full success from useful partial success.


Examples include:


Full Success

Matching completed and requested Plex playlist modification succeeded.


Success with Warnings

Playlist modification succeeded but one or more recoverable conditions occurred.


Partial Success

Matching and reporting completed, but Plex playlist modification was skipped because Plex was
unavailable.


Failed Execution

The requested source could not be loaded or no usable Plex library data existed.


These distinctions are more operationally useful than a binary success/failure model.


19.11 Health and Exit Behavior
Runtime health reporting and process exit status should complement one another.


A non-zero exit status may be appropriate when the requested primary operation could not be completed.


Warnings associated with optional components should not necessarily cause the entire execution to be
treated as failed.


The exact exit-code policy should be documented once formally defined and stabilized.


                                                       26

19.12 Scheduled Execution
Resiliency becomes especially important when the application runs unattended.


A scheduled execution should:


      • Complete as much safe work as possible.
      • Preserve useful reports.
      • Record component health.
      • Avoid uncontrolled tracebacks for expected operational failures.
      • Produce an outcome that can be interpreted later.

The future production model depends on this behavior.


Containerization and a health dashboard remain future deployment items and should not be treated as
current capabilities.


19.13 Resiliency Design Principle
The resiliency model follows the principle:


       Fail only the work that cannot safely continue.


An unavailable optional integration should not invalidate unrelated successful work.


An unavailable required source should stop the workflow that depends on it.


A temporary Plex outage should not erase the value of local matching when a usable cache exists.


20. Error Handling
Error handling defines how the application converts failures into controlled behavior.


The objective is not to hide errors.


The objective is to distinguish expected operational conditions from programming defects.


Expected failures should be understandable to operators.


Unexpected failures should remain visible to developers.


                                                     27

20.1 Expected Operational Errors
Examples include:


     • Playlist file not found.
     • Unsupported playlist format.
     • Plex unavailable.
     • Lidarr unavailable.
     • XMPlaylist unavailable.
     • External API timeout.
     • API rate limit.
     • Stale Plex cache reference.
     • Missing individual Plex track during live resolution.
     • Malformed playlist record.

These conditions may be undesirable, but they are foreseeable.


They should normally be handled without exposing raw implementation exceptions to the end user.


20.2 Programming Errors
Programming errors include defects such as:


     • Incorrect assumptions about object structure.
     • Invalid internal state.
     • Unexpected None values.
     • Logic errors.
     • Unhandled schema incompatibilities.

These should not be silently converted into generic warnings.


During development and testing, they should remain visible so they can be corrected.


Error handling that catches every exception indiscriminately can make the application appear resilient while
actually hiding defects.


20.3 Handle Errors at the Narrowest Practical Boundary
Errors should generally be handled by the subsystem that best understands their meaning.


For example:


                                                      28

  HTTP Timeout
        |
        v
  Lidarr Client
        |
        v
  Lidarr Unavailable Result
        |
        v
  Application Workflow


The top-level application should not need to interpret a low-level socket exception to understand that Lidarr
is unavailable.


Likewise:


  Plex Object Missing
        |
        v
  Plex Resolution Layer
        |
        v
  Stale Cache Reference
        |
        v
  Skip / Report


This keeps subsystem-specific failure semantics close to the subsystem.


20.4 Input Errors
Input validation errors should be expressed in user-facing terms.


Prefer:


  Playlist file not found: playlist.txt


over:


  FileNotFoundError: [Errno 2] ...


                                                     29

Prefer:


  Unsupported playlist format: .xyz


over allowing the parser to fail indirectly.


Individual malformed records may be skipped when safe, but the skip should be observable.


20.5 External Service Errors
External service clients should translate expected communication failures into meaningful integration-level
results.


Examples include:


  Plex unavailable
  Lidarr request timed out
  XMPlaylist rate limit reached


The application can then decide whether the current workflow can continue.


This creates a clean separation between:


  What failed?


and:


  Does that failure stop this execution?


20.6 Per-Item Error Isolation
Where practical, one problematic item should not invalidate unrelated items.


Examples include:


       • One malformed playlist line.
       • One stale Plex track.
       • One failed live Plex object lookup.


                                                    30

The application should continue processing the remaining workload when doing so is safe.


This principle should not be overextended.


If a shared dependency fails globally, repeatedly attempting every remaining item may provide no value.


20.7 Lidarr Error Isolation
Current Lidarr processing may stop remaining Lidarr work when a request-level failure occurs.


More granular per-track Lidarr failure isolation is a future improvement.


Until implemented, documentation should describe the current behavior accurately rather than imply full
per-item isolation.


This is an example of the project's general rule against documenting planned behavior as current
functionality.


20.8 Stale Plex Item Example
A useful example of controlled error handling is a stale Plex cache reference.


Conceptually:


  Cached Match Accepted
        |
        v
  Resolve Live Plex Object
        |
        v
  Object Missing
        |
        v
  Classify as Stale Cache Reference
        |
        v
  Log Warning
        |
        v
  Record Condition
        |


                                                     31

        v
  Continue with Remaining Tracks


The missing Plex item is an expected operational inconsistency between two independently changing data
stores.


It should not normally be treated as an application crash.


20.9 Error Messages
Useful error messages should answer:


     • What failed?
     • What was the application trying to do?
     • Can the application continue?
     • What should the operator investigate?

For example:


  Plex unavailable. Matching completed using the local cache,
  but playlist update was skipped.


is more useful than:


  Connection failed.


Context matters.


20.10 Tracebacks
Raw Python tracebacks are valuable during development.


They are generally not appropriate as the primary user-facing response to expected runtime conditions.


The application should suppress or translate tracebacks only for errors it intentionally understands and
handles.


Unexpected exceptions should still produce enough diagnostic information to support debugging.


The goal is controlled error handling, not error concealment.


                                                     32

20.11 Error Reporting and Logs
User-facing messages and logs may provide different levels of detail.


For example:


Console:


  Lidarr unavailable: request timed out.


DEBUG log:


  Detailed request URL, timeout location, exception type, and call context


Sensitive data must still be protected.


This allows normal operation to remain readable while preserving enough diagnostic information for
troubleshooting.


20.12 Error Handling and Transactions
Operations that replace or update persistent state should avoid leaving partially written results when failure
occurs.


Where appropriate, SQLite transactions should be used to preserve consistency.


Examples include:


     • Replacing Plex cache contents.
     • Updating persistent ingestion state.
     • Recording related history changes.

The persistence subsystem should own its transactional behavior.


Callers should not need to manually coordinate low-level database consistency.


20.13 Error Handling Design Principle
The application follows three related rules:


       Expected failures should become controlled application behavior.


                                                     33

      Unexpected programming defects should remain visible.


      One failure should affect only the work that can no longer be performed safely.


These rules support both operational resilience and maintainable software.


Detailed subsystem-specific error behavior belongs in the relevant subsystem documentation.


                                                   34


21. Testing Strategy
Automated testing is a core part of the Plex Playlist Importer development process.


The application integrates with several independently changing systems and processes data where small
behavioral changes can produce results that appear valid while still being incorrect.


Examples include:


     • Matching the wrong Plex track.
     • Failing to match a track that previously matched.
     • Requesting the same Lidarr album search repeatedly.
     • Incorrectly classifying a completed Lidarr search as a successful acquisition.
     • Reprocessing XMPlaylist history unnecessarily.
     • Breaking compatibility with an existing persistent database.

For these reasons, testing should verify behavior rather than merely confirm that code executes without
raising an exception.


The project uses pytest for automated testing.


Tests are maintained under:


tests/


21.1 Testing Objectives
The test suite should protect the behaviors that users and other subsystems depend upon.


The primary objectives are:


     • Prevent regressions.
     • Verify subsystem boundaries.
     • Validate known edge cases.
     • Protect persistence compatibility.
     • Confirm failure behavior.
     • Make refactoring safer.

A passing test suite does not guarantee that the application is defect-free.


It provides evidence that previously defined and tested behavior remains intact.


                                                      1

21.2 Unit Tests
Unit tests should verify behavior at the smallest practical component boundary.


Examples include:


     • Metadata normalization.
     • Artist alias handling.
     • Playlist parsing.
     • Match scoring.
     • Match classification.
     • Cache state evaluation.
     • Lidarr acquisition-status classification.
     • XMPlaylist deduplication.
     • XMPlaylist stopping conditions.

Unit tests should avoid unnecessary dependence on live external services.


Where practical, inputs and expected outputs should be deterministic.


21.3 Pure Matching Tests
The matching engine is particularly well suited to focused testing because matching can operate against
local data without requiring a live Plex server.


A matching test can provide:


  Requested Playlist Entry
          +
  Known Plex Track Records
          +
  Matching Configuration
          +
  Optional Aliases
          |
          v
  Expected Match Result


Important cases include:


     • Exact artist and title.
     • Case differences.
     • Unicode characters.
     • Accented characters.


                                                     2

     • Artist aliases.
     • Album-artist behavior.
     • Normalization rules.
     • Fuzzy matches.
     • Fallback matches.
     • Clearly unrelated tracks remaining unmatched.

Matching tests should verify not only that a track matched, but that it matched the correct track for the
correct reason where practical.


21.4 Regression Tests
When a real-world problem is discovered, the preferred correction process is:


  Observe Defect
        |
        v
  Create Reproducible Test
        |
        v
  Confirm Test Fails
        |
        v
  Correct Implementation
        |
        v
  Confirm Targeted Test Passes
        |
        v
  Run Full Test Suite


The new test then becomes part of the permanent regression suite.


This converts operational experience into long-term protection against recurrence.


A defect should not be considered fully corrected until the behavior that exposed it can be reproduced and
protected by a test where practical.


21.5 Parser Tests
Each supported playlist format should have tests covering:


     • Valid input.


                                                      3

     • Invalid input.
     • Missing required fields.
     • Header behavior where applicable.
     • Order preservation.
     • Unicode data.
     • Representative real-world examples.

Adding support for a new playlist format should include parser tests before the format is considered
complete.


21.6 Cache Tests
Cache tests should verify behavior such as:


     • Empty database initialization.
     • Track replacement.
     • Metadata updates.
     • Track count.
     • Cache age.
     • Fresh versus stale classification.
     • Search-index loading.

Where database schema compatibility is important, tests should also verify that existing supported
database structures continue to operate after application changes.


21.7 Persistence Compatibility Tests
Persistent databases survive individual application executions and may survive multiple software upgrades.


Changes to database schemas therefore require additional care.


Compatibility tests should verify:


     • Current schema initialization.
     • Supported older-schema behavior.
     • Schema migration where implemented.
     • Preservation of historical data.
     • Correct behavior after migration.

A database migration that works only with a newly created empty database is not sufficient.


Existing application state must be considered.


                                                     4

21.8 Lidarr Tests
Lidarr tests should isolate the application from a live Lidarr server where practical.


Mocked responses can verify:


      • Artist resolution.
      • Managed-artist detection.
      • Album identification.
      • Track identification.
      • File-availability classification.
      • Search queue behavior.
      • Search completion behavior.
      • Search failure behavior.
      • Multiple tracks mapping to one album search.
      • Retry-history behavior.

A particularly important distinction to test is:


  Search Command Completed


versus:


  Media File Available


These conditions are not equivalent.


21.9 XMPlaylist Tests
XMPlaylist tests should verify both API interpretation and ingestion behavior.


Important cases include:


      • Station resolution.
      • History-page parsing.
      • Pagination.
      • Deduplication.
      • Unique-track counting.
      • Request limits.
      • Track limits.
      • Cursor persistence.
      • Resume behavior.
      • History-window changes.


                                                       5

     • Rate-limit handling.

The tests should confirm that duplicate broadcast plays do not incorrectly count toward the configured
unique-track target.


21.10 Mocking External Services
Automated tests should not normally depend on:


     • A live Plex server.
     • A live Lidarr server.
     • XMPlaylist API availability.

External services introduce:


     • Network dependency.
     • Authentication dependency.
     • Rate limits.
     • Unpredictable data changes.
     • Slow test execution.

Mocks and controlled fixtures allow tests to verify application behavior consistently.


Live integration testing remains valuable, but it serves a different purpose from the routine automated
regression suite.


21.11 Live Integration Testing
Live testing verifies assumptions that mocks cannot fully reproduce.


Examples include:


     • Plex API behavior.
     • Playlist creation and update.
     • Real library metadata.
     • Lidarr API compatibility.
     • XMPlaylist response behavior.
     • Network timeout behavior.

Live tests should be deliberate rather than required for every development cycle.


They may have real side effects.


For example:


                                                       6

  --lidarr-search


can result in media acquisition.


Likewise, XMPlaylist testing consumes real API requests and may update persistent ingestion state.


The --dry-run option prevents Plex playlist modification but does not make all integrations simulated.


21.12 Test Data
Test data should be:


     • Small enough to understand.
     • Large enough to represent the behavior being tested.
     • Stable.
     • Free of credentials.
     • Independent of a specific developer's local environment.

Where real-world examples reveal important edge cases, they should be reduced to the smallest useful
reproducible fixture.


21.13 Running Tests
The standard test suite can be executed using pytest .


For example:


  python -m pytest


A specific test module can be run during focused development:


  python -m pytest tests/test_lidarr_reporting.py -v


Before a development change is considered complete, the full relevant regression suite should pass.


Before a release, the complete automated test suite should pass.


                                                    7

21.14 Failed Tests
A failed test should be investigated before changing the expected result.


When a test fails, one of several things may be true:


      • The implementation contains a regression.
      • The test contains an incorrect assumption.
      • The intended behavior has deliberately changed.
      • The test fixture no longer represents the supported interface.

Changing a test merely to make the suite pass removes its value.


If intended behavior changes, both the implementation and the test should be updated deliberately, with
the reason documented where significant.


21.15 Testing Design Principle
The testing strategy follows the principle:


       Every significant defect is an opportunity to make the application permanently harder to
       break in the same way.


Tests preserve lessons learned during development.


The test suite is therefore part of the project's technical history, not merely a release gate.


Detailed testing procedures and test-environment requirements may be maintained in:


docs/testing.md


22. Adding and Modifying Functionality
New functionality should fit the existing architecture rather than bypass it.


The project is designed around subsystem boundaries so that changes to one integration or input format
do not unnecessarily affect unrelated components.


Before modifying the application, a developer should first determine which subsystem owns the behavior.


                                                        8

22.1 Identify the Correct Boundary
A change should be made as close as practical to the component responsible for that behavior.


Examples:


  New playlist format
       -> Parser subsystem

  New normalization rule
      -> Normalization subsystem

  New matching strategy
      -> Matcher

  New Plex API behavior
      -> Plex client

  New Lidarr API behavior
      -> Lidarr client

  New XMPlaylist ingestion behavior
       -> XMPlaylist client/source/state

  New persistent history
      -> Owning subsystem persistence layer


The top-level application should coordinate these components rather than absorb their internal logic.


22.2 Preserve the Common Data Model
New external sources should generally convert their data into existing application models.


For example:


  New Playlist Source
        |
        v
  Source-Specific Parsing
        |
        v
  Playlist Entry
        |


                                                     9

        v
  Existing Matching Pipeline


A new source should not require a separate matching engine unless the underlying problem is genuinely
different.


This preserves consistency across input sources.


22.3 Avoid Source-Specific Matching Logic
The matcher should not need to know whether a playlist entry came from:


     • TXT.
     • CSV.
     • TSV.
     • M3U.
     • XMPlaylist.
     • A future source.

If a new source requires special matching behavior, first determine whether the problem is actually a
metadata-normalization issue or a missing field in the common data model.


Source-specific exceptions inside the matcher should be treated cautiously because they increase coupling.


22.4 Extend Clients at Integration Boundaries
External service behavior should remain encapsulated in service clients.


For example, if a new Lidarr API endpoint is required:


  Application Workflow
        |
        v
  Lidarr Client Method
        |
        v
  Lidarr API


The workflow should not directly construct HTTP requests.


                                                     10

This allows:


      • Authentication.
      • Timeouts.
      • Error translation.
      • Logging.
      • API compatibility.

to remain centralized.


22.5 Preserve Failure Isolation
New integrations and features should define their failure boundaries.


A developer should ask:


      • Is this component required for the current operation?
      • Can useful work continue if it fails?
      • What state has already been safely produced?
      • What should be reported?
      • Should the process exit as failed, partial, or successful with warnings?

Failure behavior should be designed along with successful behavior.


It should not be added only after production failures occur.


22.6 Persistent State Changes
Before adding persistent state, determine:


      • Why the information must survive execution.
      • Which subsystem owns it.
      • Whether it can be rebuilt.
      • Whether losing it changes behavior.
      • Whether it requires backup.
      • Whether schema versioning is needed.

Persistent state should not be added simply because SQLite makes it easy to store information.


The application should persist data when remembering it improves future behavior.


                                                       11

22.7 Schema Changes
A database schema change should include:


    1. A clear reason for the change.
    2. Schema-version consideration.
    3. Migration behavior where required.
    4. Compatibility tests.
    5. Documentation updates.
    6. Changelog entry.

Existing databases should be treated as user data.


A developer should not assume every application upgrade begins with an empty database.


22.8 Configuration Changes
When adding a configuration option, define:


     • Default value.
     • Configuration section.
     • Data type.
     • Validation rules.
     • Whether it is required.
     • Whether a command-line override exists.
     • Precedence behavior.

The new setting should be documented in:


docs/configuration.md


If the option materially changes architecture or operational behavior, the Developer Guide or an ADR may
also require an update.


22.9 Command-Line Changes
New CLI options should have a clear operational purpose.


Before adding an option, consider whether the behavior belongs in:


     • Persistent configuration.
     • A resource file.
     • A one-time CLI action.


                                                     12

CLI names should remain consistent with existing conventions.


Removing or renaming a CLI option can break:


     • User scripts.
     • Scheduled jobs.
     • Container commands.

Such changes should therefore be treated as compatibility changes.


22.10 Logging Changes
New functionality should provide enough logging to make its progress and failures understandable.


Normal operation should use INFO-level messages selectively.


Detailed internal activity should use DEBUG.


Recoverable problems should use WARNING.


Failures that prevent required work should use ERROR.


A new feature should not flood normal logs with one INFO message per low-level API request when a
higher-level progress message would communicate the operation more effectively.


22.11 Reporting Changes
If a feature makes a decision that users may need to review later, consider whether that decision belongs in
a report.


Examples include:


     • Match classification.
     • Acquisition status.
     • Alias suggestion.
     • Skipped item.
     • Partial ingestion.

Logs describe execution.


Reports describe results.


A developer should choose the appropriate output rather than placing all information in one channel.


                                                     13

22.12 Testing Requirements
New functionality should include tests appropriate to its risk.


At minimum, consider:


     • Normal behavior.
     • Boundary conditions.
     • Invalid input.
     • External-service failure.
     • Persistence behavior.
     • Compatibility with existing functionality.

Bug fixes should include regression tests where practical.


22.13 Documentation Requirements
A feature is not complete when only the code is finished.


Depending on the change, documentation updates may include:


     • README.md
     • Developer Guide
     • docs/configuration.md
     • docs/playlist-formats.md
     • Subsystem documentation
     • ADR
     • Changelog
     • Project history

Not every change requires every document to be updated.


Documentation should be updated where the reader's understanding or operational behavior has changed.


22.14 Architectural Decisions
Changes that establish or materially alter a long-term architectural principle should be documented using
an Architecture Decision Record.


Examples include:


     • Licensing choice.
     • External-service responsibility boundaries.
     • Persistence architecture.


                                                      14

     • Deployment architecture.
     • Major integration strategy.

An ADR should explain:


     • Context.
     • Decision.
     • Rationale.
     • Consequences.
     • Alternatives considered.
     • Future reconsideration conditions.

Decisions should be documented as close as practical to the time they are finalized.


22.15 Avoid Speculative Complexity
The application should not become more complicated merely to handle hypothetical edge cases that have
not demonstrated practical value.


When an unusual condition is identified, consider:


     • Has this occurred in real usage?
     • Does the current behavior create an actual problem?
     • Can the issue be addressed later without breaking compatibility?

If the answer supports deferral, document the observation if necessary and wait for operational evidence.


The governing principle is:


       Solve demonstrated problems without closing the door on reasonable future changes.


22.16 Modification Design Principle
Changes should preserve the qualities the architecture is intended to provide:


     • Clear ownership.
     • Testability.
     • Explainability.
     • Failure isolation.
     • Backward compatibility where practical.
     • Operational visibility.

A feature that works but bypasses these principles creates future maintenance cost.


                                                     15

23. Versioning and Release Management
Versioning provides a shared language for describing the state of the application.


It allows developers and users to identify:


      • Which functionality is present.
      • Which fixes have been applied.
      • Which documentation corresponds to the code.
      • Whether a change may affect compatibility.

The project should maintain explicit version identifiers as it evolves.


23.1 Version Structure
The project currently uses version identifiers in the general form:


  MAJOR.MINOR.PATCH


For example:


  2.4.0
  2.4.1


Conceptually:


MAJOR

Represents a substantial application generation or compatibility boundary.


MINOR

Represents a meaningful development cycle or feature release.


PATCH

Represents corrections, compatibility fixes, and smaller refinements within a minor release.


The project's practical release history should determine version increments rather than applying semantic-
versioning terminology mechanically.


                                                       16

23.2 Development Cycles
Development work may be grouped into planned version cycles.


For example:


  v2.4.0
       |
       +----> Planned feature set
       +----> Testing
       +----> Documentation
       +----> Release

  v2.4.1
      |
      +----> Follow-up improvements
      +----> Logging refinements
      +----> Compatibility fixes


Grouping work into cycles prevents unrelated changes from accumulating indefinitely in one release.


23.3 Patch Releases
A patch release may include:


     • Defect corrections.
     • Compatibility fixes.
     • Logging refinements.
     • Documentation corrections.
     • Low-risk behavioral adjustments.

A patch should not silently introduce a major compatibility break.


If a correction changes externally visible behavior, the change should be documented.


23.4 Compatibility Patches
Occasionally, a release may expose a compatibility problem that requires a focused correction.


A compatibility patch should:


    1. Identify the broken compatibility assumption.
    2. Correct the smallest practical scope.


                                                       17

    3. Add regression protection.
    4. Run the full relevant test suite.
    5. Document the correction.

Compatibility patches should avoid unrelated feature development.


This keeps the risk of the corrective release controlled.


23.5 Changelog
User-visible changes should be recorded in the project changelog.


A changelog entry should focus on what changed from the user's or operator's perspective.


Useful categories may include:


      • Added.
      • Changed.
      • Fixed.
      • Removed.
      • Deprecated.

Internal refactoring that produces no observable change does not always require a prominent changelog
entry.


Significant architectural refactoring may still belong in project history or developer documentation.


23.6 Project History
The changelog and project history serve different purposes.


The changelog answers:


       What changed between releases?


Project history answers:


       How did the application arrive at its current design?


Project history can preserve context such as:


      • Major development phases.
      • Integration sequencing.
      • Architectural transitions.


                                                       18

      • Important lessons.
      • Retired approaches.

This context can help future maintainers understand why the current architecture exists.


23.7 Architecture Decision Records
ADRs preserve individual significant decisions.


The relationship is:


  Changelog
      -> What changed?

  Project History
      -> How did the project evolve?

  ADR
        -> Why was this specific decision made?

  Developer Guide
        -> How is the current system designed?


These documents complement one another rather than duplicate the same information.


23.8 Documentation Version Alignment
Documentation should describe the released application version with which it is associated.


The documentation should not present unreleased roadmap functionality as current behavior.


When functionality changes:


  Code Change
      |
      v
  Tests
      |
      v
  Documentation Update
      |
      v


                                                    19

  Changelog
      |
      v
  Release


Documentation updates should be part of the development cycle, not a later cleanup activity.


23.9 Release Readiness
Before a release is considered ready, the project should verify:


     • Planned scope is complete or explicitly deferred.
     • Relevant automated tests pass.
     • Known regressions are addressed.
     • Configuration changes are documented.
     • Database compatibility has been considered.
     • User documentation is current.
     • Developer documentation is current where architecture changed.
     • Changelog is updated.
     • Version identifier is correct.

Live integration testing should be performed when the release changes behavior involving external
services.


23.10 Release Scope Discipline
Not every discovered issue must be fixed in the current release.


When a new issue is found late in a development cycle, consider:


     • Is it a regression introduced by this release?
     • Does it prevent safe operation?
     • Does fixing it introduce additional risk?
     • Can it be deferred to the next development cycle?

A known low-priority improvement may be safer to defer than to destabilize an otherwise complete release.


23.11 Versioning Design Principle
Versioning follows the principle:


       A version should identify a coherent, testable, and documentable state of the application.


                                                      20

The version number is not merely a label.


It represents a point at which code, tests, configuration, and documentation should describe the same
system.


24. Project Directory and Repository Structure
The repository structure should make the purpose of files discoverable without requiring detailed
knowledge of the codebase.


At a high level, the project separates:


      • Application entry points.
      • Python package code.
      • Configuration.
      • User-maintained resources.
      • Runtime state.
      • Reports.
      • Logs.
      • Tests.
      • Documentation.

A conceptual project structure is:


  plex-playlist-importer/
  |
  +-- playlist_import_v2.py
  +-- config.ini
  +-- README.md
  +-- LICENSE
  +-- NOTICE
  +-- CHANGELOG.md
+-- PROJECT_HISTORY.md
+-- CONTRIBUTING.md
  |
  +-- plex_playlist/
  |   +-- models.py
  |   +-- normalization.py
  |   +-- matcher.py
  |   +-- parser.py
  |   +-- cache.py
  |   +-- plex_client.py
  |   +-- lidarr_client.py
  |   +-- xmplaylist_client.py
  |   +-- xmplaylist_source.py
  |   +-- xmplaylist_state.py


                                                    21

  |   +-- logging_config.py
  |
  +-- resources/
  |   +-- aliases.txt
  |   +-- xmstations.ini
  |
  +-- cache/
  |   +-- plex_library.db
|   +-- alias_usage.db
|   +-- lidarr_search_history.db
|   +-- xmplaylist_history.db
  |
  +-- reports/
  |   +-- <generated reports and runtime status>
  |
  +-- logs/
  |   +-- <application logs>
  |
  +-- tests/
  |   +-- <pytest test modules and fixtures>
  |
  +-- docs/
      +-- developer-guide.md
      +-- documentation-standards.md
      +-- configuration.md
      +-- playlist-formats.md
      +-- testing.md
      +-- logging.md
            |
      +-- adr/
      |   +-- ADR-001-...
      |   +-- ADR-002-...
      |
      +-- subsystems/
          +-- matching.md
          +-- aliases.md
          +-- plex.md
          +-- lidarr.md
          +-- xmplaylist.md


This diagram is conceptual.


The final documented repository tree should be verified against the actual released repository so that
obsolete or planned files are not presented as current.


                                                     22

24.1 Root Directory
The repository root contains the files required to understand, configure, and launch the application.


Examples include:


playlist_import_v2.py

The primary application entry point.


Its role should be application orchestration rather than implementation of every subsystem.


config.ini

Primary system and application configuration.


README.md

High-level project introduction, installation, and basic use.


LICENSE

Apache License 2.0 license text.


NOTICE

Project notice information appropriate to the licensing and distribution model.


CHANGELOG.md

Release-oriented record of user-visible changes.


24.2 plex_playlist/
The plex_playlist/ package contains application implementation modules.


Each module should have a clear responsibility.


Examples include:


models.py

Common application data models.


                                                       23

 normalization.py

Metadata-normalization behavior used by matching.


 matcher.py

Track matching and matching-session behavior.


 parser.py

Playlist file parsing.


 cache.py

Plex library cache and search-index persistence behavior.


 plex_client.py

Plex service integration.


 lidarr_client.py

Low-level Lidarr service integration.


 xmplaylist_client.py

Low-level XMPlaylist API integration.


 xmplaylist_source.py

XMPlaylist history-to-playlist ingestion behavior.


 xmplaylist_state.py

Persistent XMPlaylist ingestion state.


 logging_config.py

Centralized logging initialization and configuration.


The repository may contain additional modules as functionality evolves.


The actual source tree remains authoritative.


                                                        24

24.3 resources/
The resources/ directory contains user-maintained operational reference data.


Examples include:


     • Artist aliases.
     • XMPlaylist station preferences.

These files are distinct from application source code and core system configuration.


They represent information that users may reasonably maintain as the application operates.


24.4 cache/
The cache/ directory contains embedded runtime database files where configured by the application.


These databases may support:


     • Plex library caching.
     • Alias usage history.
     • Lidarr search history.
     • XMPlaylist state and history.

The exact filenames should be documented from the released configuration and implementation.


Developers should understand the difference between rebuildable cache data and historical application
state before deleting files from this directory.


The directory name cache/ does not imply that every database stored within it is disposable.


24.5 reports/
The reports/ directory contains generated application output.


Examples may include:


     • Playlist match reports.
     • Unmatched-track reports.
     • Lidarr reports.
     • Match analytics.
     • Latest-run status.

Generated reports should generally not be treated as application source files.


                                                     25

Retention requirements may vary according to operational use.


24.6 logs/
The logs/ directory contains application log files according to logging configuration.


Logs are runtime operational data.


They may contain information useful for:


     • Troubleshooting.
     • Development.
     • Operational review.

They should not contain authentication secrets.


24.7 tests/
The tests/ directory contains automated test modules and supporting fixtures.


Test organization should generally reflect the subsystem or behavior being tested.


A developer investigating a subsystem should be able to identify the relevant tests without searching the
entire repository manually.


24.8 docs/
The docs/ directory contains detailed project documentation.


The documentation structure separates different purposes.


Developer Guide

Explains the current application architecture and development model.


Documentation Standards

Defines the purpose, audience, tone, and maintenance rules for the documentation library.


Configuration Reference

Documents supported configuration values.


                                                    26

Playlist Formats

Documents user-facing input format requirements.


Testing

Documents test procedures and development testing practices.


Logging

Documents operational logging and troubleshooting.


Project History

Preserves the evolution and context of the project.


24.9 docs/adr/
The ADR directory contains Architecture Decision Records.


Each ADR documents a significant architectural decision.


ADR filenames should include:


     • Sequential identifier.
     • Short descriptive title.

For example:


  ADR-001-apache-2-license.md


Once accepted, an ADR should normally remain as a historical record even if the decision is later
superseded.


A later ADR can document the replacement decision.


24.10 docs/subsystems/
Subsystem documentation contains implementation-level information that would make the Developer
Guide too detailed.


                                                      27

Examples include:


      • Matching algorithms.
      • Alias file behavior.
      • Plex client behavior.
      • Lidarr diagnostics and acquisition workflow.
      • XMPlaylist pagination and state management.

The relationship is:


  README
     |
     v
  High-Level User Understanding
     |
     v
  Developer Guide
     |
     v
  Architecture and Application Flow
     |
     v
  Subsystem Documentation
     |
     v
  Detailed Implementation Behavior


This allows readers to stop at the level of detail appropriate to their task.


24.11 Runtime Directories and Source Control
Runtime-generated data should be handled carefully in source control.


Examples include:


      • Logs.
      • Reports.
      • SQLite databases.
      • Local configuration containing credentials.

These files may require exclusion through .gitignore depending on their purpose.


Template or example configuration files intended for distribution should not contain real credentials.


                                                        28

User-maintained resources may require a deliberate policy depending on whether they are considered:


     • Project defaults.
     • Examples.
     • Local user customization.


24.12 Repository Structure Design Principle
The repository follows the principle:


       A file's location should provide a useful first clue about its purpose.


Source code, configuration, runtime state, reports, tests, and documentation should remain
distinguishable.


A clean repository structure reduces the amount of project-specific knowledge required to begin
maintaining the application.


25. Developer Workflow
The developer workflow describes the expected path from identifying a change through integrating it into a
release.


The objective is to make changes deliberate, testable, documented, and recoverable.


The workflow should remain lightweight enough for a small project while preserving practices that become
increasingly valuable as the application grows.


25.1 Begin with the Problem
Development should begin by defining the problem rather than immediately changing code.


Questions include:


     • What behavior is incorrect or missing?
     • Is this a demonstrated problem or a hypothetical one?
     • Which subsystem owns the behavior?
     • Is the current behavior intentional?
     • Does an existing ADR explain the decision?
     • What user or operational outcome should change?

Understanding the problem first reduces unnecessary code changes.


                                                       29

25.2 Preserve the "Why"
When a change is proposed, the reason matters.


For example:


  Change:
  Do not force a Plex scan immediately after a Lidarr acquisition request.

  Why:
  Lidarr and Plex already own media acquisition and library synchronization.
  The importer should not tightly couple itself to that workflow.


The implementation may change over time.


The reason helps future maintainers decide whether the original decision still applies.


Significant reasons belong in:


     • Code comments where implementation-specific.
     • ADRs where architectural.
     • Project history where evolutionary.
     • Documentation where operationally relevant.


25.3 Reproduce Before Correcting
For defects, reproduce the behavior before changing the implementation where practical.


The preferred workflow is:


  Problem Report
        |
        v
  Reproduce
        |
        v
  Identify Owning Subsystem
        |
        v
  Create Regression Test
        |
        v


                                                     30

  Confirm Failure
        |
        v
  Implement Correction


This prevents developers from correcting an assumed cause rather than the actual defect.


25.4 Make Focused Changes
A development change should address a defined purpose.


Avoid combining:


     • Unrelated refactoring.
     • New features.
     • Compatibility fixes.
     • Formatting changes.

into one corrective patch when they can reasonably remain separate.


Focused changes are easier to:


     • Review.
     • Test.
     • Revert.
     • Document.
     • Troubleshoot.


25.5 Run Targeted Tests
During development, run the tests most closely related to the change.


For example:


  python -m pytest tests/test_lidarr_reporting.py -v


Targeted tests provide fast feedback.


They do not replace the full regression suite.


                                                    31

25.6 Run the Full Test Suite
After targeted tests pass, run the complete automated suite before considering the change complete.


For example:


  python -m pytest


A change to one subsystem can expose an assumption in another.


The full suite provides broader regression protection.


25.7 Perform Live Testing Where Appropriate
Changes involving external-service behavior may require live validation.


Examples include:


      • Plex playlist operations.
      • Plex cache refresh.
      • Lidarr API compatibility.
      • XMPlaylist ingestion.

Live testing should be performed with awareness of side effects.


In particular:


      • --lidarr-search may trigger media acquisition.
      • XMPlaylist calls consume API requests and update ingestion state.
      • --dry-run prevents Plex playlist modification but does not make external integrations simulated.


25.8 Review Operational Output
A technically correct change can still produce poor operational behavior.


After testing, review:


      • Console output.
      • Log volume.
      • Warning clarity.
      • Report contents.
      • Latest-run status where applicable.


                                                     32

Ask:


       • Can an operator tell what happened?
       • Are routine details overwhelming important messages?
       • Are errors actionable?
       • Are secrets protected?

Observability is part of feature quality.


25.9 Update Documentation
Documentation should be updated during the same development cycle as the code change.


Determine which documents are affected.


Examples:


  New CLI Option
      -> README if commonly used
      -> configuration/usage documentation
        -> changelog

  New Architecture Decision
      -> ADR
      -> Developer Guide if current architecture changes

  New Playlist Format
      -> README
      -> playlist-formats.md
      -> parser tests
      -> changelog

  Subsystem Behavior Change
      -> subsystem documentation
      -> changelog where user-visible


Documentation should describe the code that is actually being released.


25.10 Update the Changelog
User-visible changes should be recorded before release.


The changelog should describe the result of the change rather than internal implementation details.


                                                    33

Prefer:


  Fixed Lidarr acquisition reporting so completed searches correctly
  identify when the requested track file becomes available.


over:


  Changed boolean assignment in build_lidarr_diagnostics().


The first describes why the change matters.


25.11 Review Architectural Impact
Before finalizing a significant change, consider whether it creates a new long-term design decision.


Questions include:


        • Did responsibility move between subsystems?
        • Was a new persistent store introduced?
        • Did an external-service boundary change?
        • Did failure behavior change materially?
        • Was a new deployment assumption introduced?

If so, an ADR may be appropriate.


25.12 Version the Change
Assign the change to the appropriate development or release cycle.


Examples include:


        • Current minor release.
        • Compatibility patch.
        • Next planned development cycle.
        • Future roadmap.

Not every worthwhile idea belongs in the current release.


Deferral is a valid engineering decision when it reduces risk or avoids speculative complexity.


                                                      34

25.13 Preserve a Stable Recovery Point
Before substantial changes, maintain a recoverable version of the known-good application.


Version control should provide the primary mechanism for this.


A stable release or tagged checkpoint allows development to proceed without depending on manually
reconstructed source files.


The objective is simple:


          A developer should always be able to identify and restore the last known-good state.


25.14 Release Review
Before finalizing a release, review the project as a complete package.


Verify:


      • Application version.
      • Automated tests.
      • Live integration tests where required.
      • Configuration compatibility.
      • Database compatibility.
      • README.
      • Developer Guide.
      • Subsystem documentation affected by the release.
      • ADRs.
      • Changelog.
      • Project history where appropriate.

This is the point where code and documentation are evaluated together.


25.15 Post-Release Issues
Problems discovered after release should be classified before work begins.


Examples:


Regression

Previously working behavior was broken by the release.


                                                       35

Usually receives high priority.


Compatibility Issue

The release conflicts with an existing supported environment or persistent state.


May require a focused compatibility patch.


Existing Defect

The problem existed before the current release.


Priority depends on impact.


Enhancement

The application works as designed, but improved behavior is desirable.


Can normally be scheduled into a future development cycle.


This classification helps prevent every newly discovered issue from destabilizing the current release.


25.16 Development Workflow Summary
The overall development cycle is:


  Understand the Problem
          |
          v
  Identify the Owning Subsystem
          |
          v
  Reproduce / Define Expected Behavior
          |
          v
  Create or Update Tests
          |
          v
  Implement Focused Change
          |
          v
  Run Targeted Tests
          |
          v


                                                      36

  Run Full Regression Suite
          |
          v
  Perform Live Testing if Required
          |
          v
  Review Logs and Reports
          |
          v
  Update Documentation
          |
          v
  Update Changelog / ADR if Required
          |
          v
  Version and Release


25.17 Developer Workflow Principle
The development workflow follows the principle:


       Understand why a change is needed, make the smallest coherent change, prove that it works,
       and preserve enough context for the next developer to understand why it exists.


Code explains what the application does.


Tests protect what it is expected to do.


Documentation explains how it works.


ADRs preserve why significant decisions were made.


Version history records when those changes became part of the application.


Together, they form the maintainable project.


                                                     37


26. Related Documentation
The Developer Guide provides the architectural and development-level view of Plex Playlist Importer.


It is not intended to contain every operational detail, file-format rule, configuration option, or historical
decision.


The project documentation is divided by purpose so that readers can move from general understanding to
the level of detail appropriate to their task.


26.1 README
README.md


The README is the primary entry point for users.


It explains:


      • What Plex Playlist Importer is.
      • Why it exists.
      • Major capabilities.
      • Installation.
      • Basic configuration.
      • Quick Start usage.
      • Supported input formats.
      • Optional integrations.
      • Current project status.
      • Roadmap.
      • Licensing.

The README introduces concepts.


The Developer Guide explains how those concepts are implemented and how they fit together
architecturally.


26.2 Documentation Standards
docs/documentation-standards.md


This document defines the project's documentation philosophy and conventions.


                                                        1

It explains:


      • Documentation principles.
      • Audience and purpose expectations.
      • Writing style.
      • README structure.
      • ADR standards.
      • Documentation workflow.
      • Review checklist.

Developers adding or modifying documentation should review these standards before creating new project
documents.


26.3 Configuration Reference
docs/configuration.md


The configuration reference documents the application's supported configuration values.


It should include:


      • Configuration sections.
      • Configuration keys.
      • Defaults.
      • Allowed values.
      • Data types.
      • Required settings.
      • Optional settings.
      • Command-line override behavior where applicable.
      • Configuration examples.

The Developer Guide explains the configuration architecture.


The configuration reference defines the actual settings.


26.4 Playlist Format Reference
docs/playlist-formats.md


This document defines the supported playlist input formats.


It should include:


      • TXT format.


                                                      2

      • CSV format.
      • TSV format.
      • M3U format.
      • M3U8 format.
      • Required fields.
      • Optional fields.
      • Header behavior.
      • Delimiters.
      • Encoding considerations where applicable.
      • Valid examples.
      • Invalid examples where useful.

When a new playlist format is added, this document should be updated along with parser tests and the
README Supported Input Formats section.


26.5 Architecture
docs/architecture.md


The architecture document provides a focused view of the system's high-level components and boundaries.


It should explain:


      • Major subsystems.
      • External integrations.
      • Persistent state.
      • Data flow.
      • Responsibility boundaries.

The Developer Guide contains architectural context as part of a broader development narrative.


The architecture document provides a more concentrated reference for readers who need the system-level
view without reading the entire Developer Guide.


26.6 Application Flow
docs/application-flow.md


The application-flow document describes end-to-end execution behavior.


It should explain how an execution moves through stages such as:


```text id="h85nza" Startup | v Configuration | v Component Initialization | v Cache Evaluation | v Playlist
Source | v Matching | v Optional Integrations | v Plex Playlist Operation | v Reports / Status


                                                       3

This document is particularly useful for developers and operators diagnosing
where a particular behavior occurs during execution.

---


## 26.7 Testing

`docs/testing.md`


The testing document provides practical guidance for running and maintaining the
test suite.

It should include:

- Test-environment setup.
- Running the complete suite.
- Running targeted tests.
- Test organization.
- Mocking conventions.
- Integration testing.
- Regression testing.
- Persistence compatibility testing.

The Developer Guide explains the testing philosophy.

The testing document provides the operational test reference.

---

## 26.8 Logging

`docs/logging.md`

The logging document provides detailed operational guidance for interpreting
application logs.


It should include:

- Log configuration.
- Log levels.
- Log locations.
- Common startup messages.
- Cache messages.
- Matching messages.
- Plex messages.
- Lidarr messages.
- XMPlaylist messages.


                                       4

  - Warning interpretation.
  - Troubleshooting examples.

  The Developer Guide explains the observability model.


  The logging document helps operators use it.

  ---


  ## 26.9 Subsystem Documentation

  `docs/subsystems/`

  Subsystem documentation provides deeper implementation detail for major
  components.

  Expected subsystem documents may include:

  ```text id="tj3p7l"
  docs/subsystems/
      matching.md
      aliases.md
      cache.md
      plex.md
      lidarr.md
      xmplaylist.md
      reporting.md
      analytics.md


The exact set of subsystem documents should reflect the implemented application.


A subsystem document may describe:


     • Internal responsibilities.
     • Important classes and functions.
     • Data structures.
     • Algorithms.
     • Persistence behavior.
     • Error behavior.
     • Extension points.
     • Test coverage.

Subsystem documents should not duplicate the full Developer Guide.


They exist for readers who need to go deeper into one specific area.


                                                     5

26.10 Architecture Decision Records
docs/adr/


Architecture Decision Records preserve significant project decisions and the reasoning behind them.


Each ADR explains:


     • Context.
     • Decision.
     • Rationale.
     • Alternatives considered.
     • Consequences.
     • Future reconsideration.

For example:


```text id="2cty2n" ADR-001 - Adopt Apache License 2.0


  Future ADRs may document decisions such as:

  - Self-contained deployment.
  - Native Plex/Lidarr synchronization.
  - Separation of responsibilities.
  - Documentation standards.

  Accepted ADRs should remain as historical records.

  If a decision changes, a new ADR should supersede the earlier one rather than
  rewriting the original reasoning.

  ---

  ## 26.11 Changelog

  `CHANGELOG.md`

  The changelog records release-oriented changes.

  It answers:

  > What changed between versions?

  Entries should focus on changes meaningful to users, operators, and developers.

  The changelog should not attempt to explain the full historical context behind


                                                     6

every change.

---

## 26.12 Project History


`PROJECT_HISTORY.md`

Project History preserves the evolution of Plex Playlist Importer.


It should include:

- Project origins.
- Foundational decisions.
- Major development phases.
- Significant milestones.
- Architectural evolution.
- Future direction.

It answers:

> How did the project arrive at its current state?

This differs from an ADR, which answers why one specific decision was made.

---

## 26.13 Contributing Guide

`CONTRIBUTING.md`

The contributing guide defines expectations for contributors.

It should include:

- Development setup.
- Contribution workflow.
- Testing expectations.
- Documentation expectations.
- Coding conventions where applicable.
- Pull-request expectations where applicable.
- ADR requirements for significant decisions.

The Developer Guide explains how the application is engineered.

The contributing guide explains how others should participate in changing it.

---


                                       7

## 26.14 License and Notice

`LICENSE`


`NOTICE`

The project is licensed under Apache License 2.0.


The `LICENSE` file contains the full license text.

The `NOTICE` file contains project identification and any attribution or notice
information required by the project's distribution model.

The reasoning behind the licensing choice is preserved in:

`docs/adr/ADR-001-apache-license-2.0.md`

---

## 26.15 Choosing the Right Document

A useful way to navigate the documentation library is to begin with the question
being asked.

```text id="kau5mo"
What is this project?
    -> README.md

How do I configure it?
    -> docs/configuration.md

What playlist formats are supported?
    -> docs/playlist-formats.md

How does the system work?
    -> docs/developer-guide.md


What are the major components?
    -> docs/architecture.md

What happens during one execution?
    -> docs/application-flow.md

How do I test it?
    -> docs/testing.md

How do I interpret logs?


                                       8

       -> docs/logging.md

  How does one subsystem work internally?
      -> docs/subsystems/


  Why was a significant decision made?
      -> docs/adr/

  What changed in a release?
       -> CHANGELOG.md

  How did the project evolve?
      -> PROJECT_HISTORY.md

  How do I contribute?
      -> CONTRIBUTING.md


26.16 Documentation Design Principle
The documentation library follows the principle:


       Put detailed information in the document whose audience and purpose best match the
       question.


The README introduces.


The Developer Guide explains.


Reference documentation defines.


Subsystem documentation drills down.


ADRs preserve decisions.


The changelog records releases.


Project History preserves evolution.


Together, these documents provide different views of the same project without requiring one document to
serve every reader.


                                                   9
