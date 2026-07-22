# Lidarr Integration Subsystem

## 1. Purpose and Scope

The Lidarr integration subsystem extends the Plex Playlist Importer workflow for requested tracks that cannot be matched to the Plex music library.

Its purpose is to determine whether missing music can be associated with an artist and album known to Lidarr and, when explicitly requested, initiate a Lidarr album search that may result in media acquisition.

Lidarr operates downstream of Plex matching.

A track reaches the Lidarr workflow because the matching subsystem could not identify an acceptable Plex library match.

The subsystem supports two distinct operating modes:

- **Lidarr check** — investigate unmatched tracks without initiating acquisition searches.
- **Lidarr search** — explicitly request Lidarr album searches for eligible unmatched tracks.

Lidarr searches are asynchronous.

A successfully submitted Lidarr search does not guarantee that an album will be found, downloaded, imported, or immediately available in Plex.

The governing architectural decision is:

`ADR-002 — Rely on Native Lidarr and Plex Library Synchronization`

---

## 2. Responsibilities

The Lidarr subsystem is responsible for:

- Receiving tracks that remain unmatched after Plex matching.
- Communicating with the configured Lidarr server.
- Determining whether relevant artist and album information can be resolved in Lidarr.
- Reporting Lidarr information for unmatched tracks.
- Initiating album searches when `--lidarr-search` is explicitly requested.
- Recording Lidarr search history.
- Applying configured retry policy to previously searched albums.
- Avoiding unnecessary repeated searches.
- Reporting Lidarr component health and failures.
- Preserving the distinction between a search request and successful media acquisition.

The Lidarr subsystem is not responsible for:

- Matching tracks against the Plex library.
- Downloading media directly.
- Selecting or managing indexers.
- Determining which release Lidarr downloads.
- Forcing Plex library scans.
- Waiting for Lidarr downloads to complete.
- Waiting for Plex to discover newly acquired media.
- Automatically refreshing the Plex cache after acquisition.
- Automatically rematching the track during the same run.

The responsibility boundary is:

```text
Plex Playlist Importer
        |
        | Request album search
        v
      Lidarr
        |
        | Search / acquire / import
        v
   Local Media
        |
        | Existing synchronization
        v
       Plex
        |
        | Discover / index
        v
Plex Playlist Importer
   (subsequent run)
```

---

## 3. Processing Flow

The Lidarr subsystem begins with tracks that remain unmatched after the normal Plex matching workflow.

The two primary modes share the initial investigation path and diverge when acquisition behavior is considered.

```text
Unmatched Playlist Entry
MatchResult / PlaylistEntry
(models.py)
        |
        v
Lidarr Option Requested?
playlist_import_v2.py
        |
        +-----------------------------+
        |                             |
        v                             v
--lidarr-check                  --lidarr-search
        |                             |
        +-------------+---------------+
                      |
                      v
              Lidarr Processing
              playlist_import_v2.py
                      |
                      v
              LidarrClient
              (lidarr_client.py)
                      |
                      v
               Lidarr Server
                      |
                      v
           Resolve Artist / Album
              LidarrClient
              (lidarr_client.py)
                      |
              +-------+-------+
              |               |
              v               v
         Resolved         Not Resolved
              |               |
              |               v
              |         Report Outcome
              |         lidarr_reporting.py
              |
              v
       Operating Mode?
              |
       +------+------+
       |             |
       v             v
--lidarr-check  --lidarr-search
       |             |
       v             v
Report Only     Search Eligibility
                     |
                     v
               Retry Policy
        lidarr_search_history.py
                     |
                     v
      cache/lidarr_search_history.db
                     |
              +------+------+
              |             |
              v             v
           Eligible      Suppressed
              |             |
              v             v
       Request Album     Report Prior /
          Search         Retry Status
              |
              v
       LidarrClient
       (lidarr_client.py)
              |
              v
         Lidarr API
              |
              v
      Search Request Submitted
              |
              v
     Record Search History
   lidarr_search_history.py
              |
              v
cache/lidarr_search_history.db
              |
              v
      Continue Without Waiting
       for Media Acquisition
```

The key boundary is that the importer submits a search request and continues.

It does not block while waiting to determine whether Lidarr ultimately acquires the album.

---

## 4. Lidarr Check Mode

Lidarr check mode is invoked with:

```text
--lidarr-check
```

Its purpose is to investigate unmatched tracks without intentionally initiating an album acquisition search.

Conceptually:

```text
Unmatched Track
      |
      v
--lidarr-check
      |
      v
Query Lidarr
(lidarr_client.py)
      |
      v
Resolve Available
Artist / Album Information
      |
      v
Lidarr Report
(lidarr_reporting.py)
```

This mode is useful for:

- Diagnosing why tracks remain unavailable.
- Determining whether Lidarr recognizes the artist.
- Determining whether a relevant album can be identified.
- Reviewing potential acquisition candidates before initiating searches.
- Testing Lidarr connectivity and integration behavior.

The check path should remain non-acquisitional.

It should not initiate an album search merely because Lidarr recognizes an artist or album.

---

## 5. Lidarr Search Mode

Lidarr search mode is invoked with:

```text
--lidarr-search
```

This mode allows the importer to initiate Lidarr album searches for eligible unmatched tracks.

Conceptually:

```text
Unmatched Track
      |
      v
--lidarr-search
      |
      v
Resolve Artist / Album
(lidarr_client.py)
      |
      v
Check Search History
(lidarr_search_history.py)
      |
      v
Apply Retry Policy
      |
  +---+---+
  |       |
  v       v
Search   Suppress
Allowed  Search
  |       |
  v       v
Lidarr   Report
Album    Status
Search
```

Unlike `--lidarr-check`, this mode can cause a real external action.

If Lidarr finds an acceptable release according to its own configuration and indexers, the album may be downloaded and imported.

This remains true when the importer is run with:

```text
--dry-run
```

The `--dry-run` option prevents Plex playlist modification.

It does not suppress an explicitly requested `--lidarr-search`.

Therefore:

```text
--dry-run
+
--lidarr-search
        |
        v
Plex Playlist Write
        |
      BLOCKED


Lidarr Album Search
        |
       LIVE
```

This behavior should remain consistent across the README, Developer Guide, CLI help, and subsystem documentation.

---

## 6. Unmatched Track Resolution

The Lidarr subsystem receives unmatched playlist entries rather than attempting to rematch the Plex library itself.

The general boundary is:

```text
Playlist Entry
      |
      v
Plex Matching
(matcher.py)
      |
  +---+---+
  |       |
  v       v
Matched  Unmatched
  |       |
  |       v
  |   Lidarr Workflow
  |   (when requested)
  |
  v
Plex Workflow
```

The Lidarr subsystem may use artist, title, album, or other available metadata to determine the appropriate Lidarr artist and album.

The quality of the available source metadata can therefore affect whether a useful Lidarr acquisition candidate can be identified.

A Lidarr resolution failure should not be treated as a Plex matching failure.

The track has already been classified as unmatched before Lidarr processing begins.

---

## 7. Album-Level Acquisition

Lidarr manages music primarily at the artist and album level.

The importer may begin with an unmatched individual track, but the actionable Lidarr operation is generally an album search.

Conceptually:

```text
Requested Track
Artist + Title
      |
      v
Identify Lidarr Artist
      |
      v
Identify Album
Containing Track
      |
      v
Album Search Request
      |
      v
Lidarr Acquisition Workflow
```

This distinction explains why Lidarr reports and logs may refer to an album rather than directly to the requested track.

For example, an unmatched track may result in a Lidarr search resembling:

```text
Searching indexers for [Artist - Album (Year)]
```

The importer requests the album search.

Lidarr determines whether any acceptable release is available.

---

## 8. Search Request Versus Acquisition

A submitted Lidarr search is not equivalent to successful acquisition.

The sequence is:

```text
Importer Requests Search
        |
        v
Lidarr Searches Indexers
        |
        +-------------------------+
        |                         |
        v                         v
Acceptable Release Found    No Acceptable Release
        |                         |
        v                         v
Download May Begin         No Download
        |
        v
Download May Complete
        |
        v
Lidarr May Import Album
        |
        v
Plex May Discover Media
```

Each stage is independent.

The importer does not control whether:

- An indexer returns results.
- A result satisfies Lidarr quality requirements.
- A download client accepts the release.
- The download completes.
- Lidarr imports the media successfully.
- Plex subsequently indexes the media.

Operationally, Lidarr log messages such as:

```text
Searching indexers for [Sam Cooke - Shake (1965)].
No results found.
Album search completed. 0 reports downloaded.
```

indicate that the search operation itself completed, but no release was acquired.

The importer should not interpret the completion of the search command as proof that media is now available.

---

## 9. Asynchronous Acquisition Boundary

The importer deliberately does not wait for Lidarr acquisition.

The current architecture is:

```text
Run N

Unmatched Track
      |
      v
Lidarr Search Requested
      |
      v
Search Submitted
      |
      v
Importer Continues / Completes


Between Runs

Lidarr
   |
   v
Possible Download
   |
   v
Media Import
   |
   v
Plex Library Synchronization


Run N+1

Plex Cache Refresh
      |
      v
Matching
      |
      v
Previously Missing Track
May Now Match
```

A real example observed during development involved:

```text
Nicolette Larson - Lotta Love
```

The track was initially unmatched.

Lidarr later acquired the relevant album, Plex subsequently updated its library, and a later importer run successfully matched the track.

This is the intended workflow.

The importer does not force the acquisition and Plex synchronization lifecycle into a single execution.

See ADR-002 for the architectural reasoning.

---

## 10. Search History

Lidarr search history is stored in:

```text
cache/lidarr_search_history.db
```

The database is managed by:

```text
lidarr_search_history.py
```

The current tables are:

```text
metadata
search_history
```

The search-history database records previous Lidarr search activity so that the application can make informed retry decisions.

Its purpose is to prevent scheduled importer runs from repeatedly requesting the same unsuccessful album search without regard to previous attempts.

---

## 11. Retry Policy

Retry behavior is controlled by the Lidarr search-history and retry-policy configuration.

The intended policy is:

- Search newly eligible items.
- Remember previous searches when configured.
- Suppress repeated searches until the configured retry interval has elapsed.
- Retry only when policy allows.

Conceptually:

```text
Eligible Album
      |
      v
Search History Lookup
lidarr_search_history.py
      |
      v
Previous Search?
      |
  +---+---+
  |       |
  No      Yes
  |       |
  v       v
Search   Retry Interval
Now      Elapsed?
          |
      +---+---+
      |       |
     Yes      No
      |       |
      v       v
    Search   Suppress
    Again    Search
```

Relevant `config.ini` settings should be shown here by their exact names when the configuration reference is finalized.

The policy should distinguish between:

- An item that has never been searched.
- An item whose previous search is still within the suppression interval.
- An item eligible for retry.
- An item whose failed-search history should or should not be remembered according to configuration.

Detailed setting descriptions belong in:

```text
docs/configuration.md
```

---

## 12. Search History Database

The Lidarr search-history database is:

```text
cache/lidarr_search_history.db
```

Owned by:

```text
lidarr_search_history.py
```

Tables:

```text
metadata
search_history
```

Unlike `cache/plex_library.db`, this database contains operational history that cannot necessarily be reconstructed from Lidarr.

Deleting it may cause the importer to lose knowledge of previous search attempts.

The consequence may be that albums are searched again sooner than intended.

For that reason, the database should be treated as persistent application state.

---

## 13. Lidarr Configuration

Lidarr behavior is controlled through the Lidarr-related settings in:

```text
config.ini
```

These settings include information required for:

- Lidarr server connectivity.
- Lidarr authentication.
- Search behavior.
- Retry policy.
- Search-history persistence.

Relevant CLI controls include:

```text
--lidarr-check
--lidarr-search
--lidarr-report
```

The exact current configuration keys and descriptions should be maintained in:

```text
docs/configuration.md
```

When configuration directly changes Lidarr processing flow, the relevant setting should also be identified in this subsystem document.

---

## 14. Lidarr Authentication

The application communicates with Lidarr using its configured API credentials.

The Lidarr API key should be treated as sensitive.

It should not be:

- Logged.
- Written to reports.
- Included in screenshots.
- Included in documentation examples.
- Committed to a public repository.

Future container deployment should preserve this security boundary.

---

## 15. Lidarr Reporting

Lidarr processing produces a dedicated report for unmatched-track investigation and acquisition status.

The report is implemented through:

```text
lidarr_reporting.py
```

A representative CLI option is:

```text
--lidarr-report reports/lidarr_unmatched_report.csv
```

The report should provide enough information to understand:

- The original unmatched track.
- Plex matching information where relevant.
- Whether Lidarr resolution succeeded.
- Whether an album search was requested.
- Whether retry policy suppressed the search.
- Relevant Lidarr status or outcome information.

The report should not imply that a submitted search guarantees successful acquisition.

The existing report field:

```text
plex match notes
```

should remain clearly associated with Plex matching rather than Lidarr acquisition.

---

## 16. Relationship to Plex

Lidarr and Plex have separate responsibilities.

```text
Lidarr
  =
Media Discovery
Acquisition
Import


Plex
  =
Media Library
Indexing
Playlist Destination


Plex Playlist Importer
  =
Playlist Ingestion
Matching
Acquisition Requests
Playlist Orchestration
```

The importer relies on the existing Lidarr-to-filesystem and filesystem-to-Plex synchronization process.

It does not attempt to replace that process.

After Lidarr acquisition:

1. Lidarr imports the media.
2. Plex discovers or is otherwise synchronized with the media.
3. The Plex cache is refreshed according to normal cache policy.
4. A later importer run may match the previously unavailable track.

---

## 17. Component Health and Failure Isolation

Lidarr is an optional integration.

A Lidarr failure should not necessarily invalidate work already completed by the parser, matcher, or Plex workflow.

Conceptually:

```text
Core Matching Complete
       |
       v
Lidarr Requested?
       |
   +---+---+
   |       |
  No      Yes
   |       |
   v       v
Continue  Lidarr Available?
            |
        +---+---+
        |       |
       Yes      No
        |       |
        v       v
      Process  Record Failure
              / Degraded Status
```

The application should preserve completed matching and reporting results when Lidarr is unavailable.

A Lidarr outage should be attributed to the Lidarr component rather than reported as a Plex or matching failure.

This follows ADR-007.

---

## 18. Failure Behavior

### Connection Failure

If Lidarr cannot be reached:

- Record the Lidarr component failure.
- Preserve completed matching work.
- Produce available reports.
- Do not claim that requested Lidarr processing completed successfully.

### Authentication Failure

If the Lidarr API key is invalid:

- Report authentication failure without exposing the key.
- Skip operations requiring Lidarr.

### Artist or Album Resolution Failure

If Lidarr cannot identify an appropriate artist or album:

- Record the unresolved status.
- Do not initiate an unrelated search.
- Preserve the original unmatched track information.

### Search Suppressed by Retry Policy

If search history indicates that an album is not yet eligible for another search:

- Do not submit a new search.
- Report the suppression or prior-search status.

This is expected behavior, not an external-service failure.

### Search Returns No Results

If Lidarr searches its indexers but finds no acceptable release:

- The request itself may still have completed successfully.
- The media remains unavailable.
- Search history should preserve the attempt according to policy.
- A later retry may occur if policy allows.

### Search Request Failure

If the API request to initiate the search fails:

- Record the Lidarr operation failure.
- Do not falsely record successful acquisition.
- Preserve enough context for troubleshooting.

---

## 19. Logging and Observability

Lidarr-related logging should make it possible to determine:

- Whether Lidarr processing was requested.
- Whether check or search mode was selected.
- Whether Lidarr connectivity succeeded.
- Whether artist resolution succeeded.
- Whether album resolution succeeded.
- Whether search history was consulted.
- Whether retry policy allowed or suppressed a search.
- Whether an album search was submitted.
- Whether an API failure occurred.
- Whether the run continued after a Lidarr failure.

Logs should preserve the distinction between:

```text
Search Request Submitted
```

and:

```text
Media Successfully Acquired
```

The importer normally knows the first.

It does not synchronously guarantee the second.

Sensitive API credentials must not be logged.

---

## 20. Testing

Lidarr integration has dedicated pytest coverage across client behavior, reporting, search history, retry policy, and compatibility/resiliency behavior.

### Current Test Coverage

Relevant pytest files recorded in the current project test suite include:

- `tests/test_lidarr_client.py`
  - Exercises Lidarr API client behavior.

- `tests/test_lidarr_reporting.py`
  - Exercises Lidarr report generation and report fields.

- `tests/test_lidarr_search_history.py`
  - Exercises persistent Lidarr search-history behavior.

- `tests/test_lidarr_retry_policy.py`
  - Exercises retry eligibility and search-suppression behavior.

Additional compatibility and resiliency coverage may exercise Lidarr behavior as part of broader application workflows.

### Running the Primary Lidarr Tests

```bash
python -m pytest \
  tests/test_lidarr_client.py \
  tests/test_lidarr_reporting.py \
  tests/test_lidarr_search_history.py \
  tests/test_lidarr_retry_policy.py -v
```

On Windows PowerShell:

```powershell
python -m pytest tests/test_lidarr_client.py tests/test_lidarr_reporting.py tests/test_lidarr_search_history.py tests/test_lidarr_retry_policy.py -v
```

Before finalizing significant Lidarr integration changes:

```bash
python -m pytest -v
```

### Regression Expectations

Regression tests should be added when practical for defects involving:

- Lidarr connectivity.
- Artist resolution.
- Album resolution.
- Check-versus-search behavior.
- Retry eligibility.
- Search-history persistence.
- Search suppression.
- Report output.
- API failures.
- Degraded operation when Lidarr is unavailable.

Tests should preserve the distinction between requesting a Lidarr search and confirming actual media acquisition.

---

## 21. Design Decisions and ADR References

### ADR-002 — Rely on Native Lidarr and Plex Library Synchronization

This is the primary architectural decision governing post-search behavior.

The importer does not force an immediate Plex refresh and rematch after requesting Lidarr acquisition.

### ADR-003 — Use Embedded SQLite for Local Persistence

Lidarr search history is stored locally using:

```text
cache/lidarr_search_history.db
```

### ADR-007 — Isolate Optional Integration Failures

Lidarr failure should not unnecessarily discard useful work completed by other subsystems.

### ADR-009 — Target Headless Containerized Deployment

Future Lidarr connectivity and persistent search history must work reliably from a Linux-based container hosted on an Unraid server.

---

## 22. Operational Notes

When troubleshooting a Lidarr-related issue, review the workflow in approximately this order:

1. Confirm whether `--lidarr-check` or `--lidarr-search` was requested.
2. Confirm Lidarr is running.
3. Confirm the configured Lidarr URL.
4. Confirm network connectivity from the application host.
5. Confirm the Lidarr API key.
6. Confirm the artist exists or can be resolved in Lidarr.
7. Confirm the relevant album can be identified.
8. Review `cache/lidarr_search_history.db`.
9. Determine whether retry policy suppressed the search.
10. Confirm whether an album search was actually submitted.
11. Review the Lidarr application logs to determine the indexer-search outcome.
12. Do not assume that "search completed" means media was downloaded.
13. If acquisition succeeded, allow the normal Lidarr/Plex synchronization process to occur.
14. Confirm Plex contains the acquired track.
15. Refresh the Plex cache according to normal cache policy or use `--refresh-cache` when an immediate refresh is specifically desired.
16. Run the importer again to determine whether the track now matches.

When Lidarr reports:

```text
No results found
Album search completed. 0 reports downloaded
```

the appropriate conclusion is:

> Lidarr completed the search request but did not find an acceptable release to download.

It is not evidence of an importer failure.

---

## 23. Search Retry Considerations

Repeatedly searching for an unavailable album on every scheduled importer run provides little benefit and may create unnecessary indexer activity.

The search-history and retry-policy mechanism exists to prevent this behavior.

The preferred operational model is:

```text
First Eligible Search
        |
        v
Record Attempt
        |
        v
Suppression Interval
        |
        v
Retry When Eligible
```

This allows unavailable media to be reconsidered later without repeatedly issuing identical searches.

The retry interval should balance:

- The likelihood that new releases become available.
- Importer scheduling frequency.
- Indexer load.
- External-service limits.
- Operational usefulness.

The exact policy remains configurable rather than hard-coded into the architecture.

---

## 24. Backup and Recovery

The Lidarr search-history database contains operational state:

```text
cache/lidarr_search_history.db
```

Unlike the Plex library cache, this database cannot necessarily be reconstructed from the current Lidarr library.

If lost, the importer may forget previous search attempts and repeat searches earlier than intended.

For future containerized deployment, this database should be stored on persistent storage outside the disposable container filesystem.

Its backup priority is therefore higher than:

```text
cache/plex_library.db
```

which can be rebuilt from Plex.

---

## 25. Future Considerations

Potential future improvements include:

- Improved acquisition-status visibility.
- Better differentiation between search-request status and eventual acquisition status.
- Additional retry-policy reporting.
- Operational dashboard visibility into Lidarr health and search history.
- More detailed acquisition statistics.
- Improved reporting of unresolved artists and albums.
- Container-specific Lidarr connectivity validation.

The application should continue to avoid becoming a replacement for Lidarr's own acquisition management.

The architectural boundary should remain:

```text
Importer
   |
   | Requests acquisition
   v
Lidarr
   |
   | Manages acquisition
   v
Media Library
   |
   | Existing synchronization
   v
Plex
   |
   | Becomes visible to importer
   v
Later Import Run
```

The guiding principle remains:

> Ask Lidarr to acquire missing media when explicitly requested, then allow Lidarr and Plex to perform their existing responsibilities before the importer looks for that media again.