# Lidarr Integration

Plex Playlist Importer (PPI) can optionally integrate with Lidarr to help locate music that is requested by a playlist but is not currently available in the Plex music library.

Lidarr integration is optional. PPI can operate normally without Lidarr.

## Overview

PPI's Lidarr integration provides two related functions:

* Determine whether an unmatched track or its artist/album can be identified in Lidarr.
* Request a Lidarr search for music that is missing from Plex.

Lidarr acquisition is intentionally asynchronous.

PPI does **not** wait for Lidarr to download an album, wait for Plex to import it, and then attempt to rematch the track during the same PPI execution.

Instead, the normal workflow is:

```text
PPI finds track missing from Plex
        ↓
PPI identifies the track/album in Lidarr
        ↓
PPI optionally requests a Lidarr search
        ↓
Lidarr performs its normal asynchronous acquisition process
        ↓
Lidarr/Plex integration updates the Plex library
        ↓
A later PPI run finds the newly available Plex track
```

This keeps PPI independent from the download and Plex-library-refresh lifecycle.

---

# Requirements

To use the Lidarr integration, you need:

* A working Lidarr installation.
* Network connectivity from PPI to Lidarr.
* A Lidarr API key.
* Lidarr integration enabled in PPI's `config.ini`.

Lidarr must already be configured with the indexers, download clients, root folders, quality profiles, and other settings required for its normal operation.

PPI does not configure or manage those components.

---

# PPI Configuration

The Lidarr configuration is located in the `[lidarr]` section of `config.ini`.

A typical configuration is:

```ini
[lidarr]

enabled = true

url = http://10.0.10.12:8686

api_key = LIDARR_API_KEY_HERE

remember_failed_searches = true
retry_search_after_days = 7
search_history_database = cache/lidarr_search_history.db

timeout_seconds = 20
```

## enabled

```ini
enabled = true
```

Enables Lidarr integration.

Set this to `false` if Lidarr should not participate in PPI processing.

---

# Lidarr URL

```ini
url = http://10.0.10.12:8686
```

Specifies the URL PPI uses to communicate with Lidarr.

Replace the example address with the address appropriate for your environment.

The PPI host must be able to reach this address.

---

# API Key

```ini
api_key = LIDARR_API_KEY_HERE
```

Enter the API key from your Lidarr installation.

The API key can be found in Lidarr under:

```text
Settings > General > Security
```

Treat the API key as a private credential.

Do not publish a populated `config.ini` containing your actual API key in a public source-code repository.

---

# timeout_seconds

```ini
timeout_seconds = 20
```

Controls the HTTP timeout used when PPI communicates with Lidarr.

The current example configuration uses 20 seconds.

---

# Lidarr Operating Modes

PPI provides two command-line modes for Lidarr processing:

```text
--lidarr-check
```

and:

```text
--lidarr-search
```

They serve different purposes.

## --lidarr-check

`--lidarr-check` performs a non-destructive Lidarr lookup for tracks that remain unmatched after Plex matching.

Example:

```text
python playlist_import_v2.py playlist.txt --playlist "My Playlist" --lidarr-check
```

This mode can be used to determine whether PPI can identify the missing music through Lidarr without requesting an active search.

It is useful for:

* Testing Lidarr connectivity.
* Evaluating unmatched tracks.
* Reviewing what PPI can identify in Lidarr.
* Troubleshooting matching behavior without initiating downloads.

## --lidarr-search

`--lidarr-search` performs the Lidarr lookup and may request an active Lidarr search for eligible missing music.

Example:

```text
python playlist_import_v2.py playlist.txt --playlist "My Playlist" --lidarr-search
```

PPI submits the search request to Lidarr and continues processing.

It does not wait for the search to finish.

---

# Asynchronous Search Behavior

A successful PPI search request means that Lidarr accepted the request.

It does **not** mean that Lidarr successfully found or downloaded the requested album.

For example, Lidarr may accept a search request and later report:

```text
Searching indexers for [Sam Cooke - Shake (1965)].
No results found
Album search completed. 0 reports downloaded
```

This is normal Lidarr behavior when none of the configured indexers can provide an acceptable release.

PPI does not treat the absence of an available release as an application failure.

The search request itself was successfully handed to Lidarr.

---

# No Immediate Plex Rematch

PPI deliberately does not wait for Lidarr acquisition and then refresh Plex during the same run.

There are several reasons for this:

* Lidarr searches are asynchronous.
* Downloads can take an unpredictable amount of time.
* A requested release may not exist on the configured indexers.
* Download clients may queue the request.
* Lidarr may reject available releases because of quality or profile rules.
* Plex library updates occur independently.

If Lidarr successfully acquires an album, the existing Lidarr-to-Plex workflow can update the Plex music library.

On a later scheduled PPI execution, the Plex cache/library will contain the new track and PPI can match it normally.

---

# Search History

PPI maintains Lidarr search history in:

```text
cache/lidarr_search_history.db
```

This prevents PPI from repeatedly requesting the same unsuccessful search on every scheduled run.

The behavior is controlled by:

```ini
remember_failed_searches = true
retry_search_after_days = 7
```

## remember_failed_searches

```ini
remember_failed_searches = true
```

Enables tracking of previously requested Lidarr searches.

This is recommended for normal scheduled operation.

Without search history, a persistently unavailable album could generate another Lidarr search every time the playlist is processed.

## retry_search_after_days

```ini
retry_search_after_days = 7
```

Controls how long PPI waits before allowing another eligible search attempt for an item already recorded in the search history.

The current example uses seven days.

This gives Lidarr's indexers time to change while preventing unnecessary repeated search requests.

---

# Search Eligibility

PPI only dispatches tracks to Lidarr after they remain unmatched by Plex.

Lidarr processing therefore supplements the normal Plex matching process rather than replacing it.

PPI attempts to identify the appropriate artist and album information required by Lidarr.

Depending on the result, a track may be:

* Identified in Lidarr.
* Eligible for an active search.
* Already covered by previous search history.
* Unable to be resolved sufficiently for a Lidarr search.
* Unavailable from the configured indexers after Lidarr performs the search.

---

# Lidarr Reports

PPI can produce a Lidarr unmatched report containing information about tracks that were not found in Plex and were evaluated through the Lidarr integration.

The default report configuration is:

```ini
[reports]

lidarr = lidarr_unmatched_report.csv
```

A command can also specify the report explicitly:

```text
python playlist_import_v2.py playlist.txt \
    --playlist "My Playlist" \
    --lidarr-search \
    --lidarr-report reports/lidarr_unmatched_report.csv
```

On Windows PowerShell, for example:

```text
python playlist_import_v2.py playlist.txt --playlist "My Playlist" --lidarr-search --lidarr-report reports\lidarr_unmatched_report.csv
```

The Lidarr report is useful for reviewing:

* The original unmatched artist and track.
* Plex matching information.
* Whether Lidarr identified the music.
* Whether an active search was requested.
* Search-history behavior.
* Diagnostic information explaining the result.

The report's Plex-specific diagnostic field is labeled:

```text
plex match notes
```

to distinguish Plex matching information from the Lidarr result.

---

# Understanding a Lidarr Search Result

It is important to distinguish between three different events:

### PPI submitted the search

PPI successfully asked Lidarr to perform a search.

This confirms that the PPI-to-Lidarr integration worked.

### Lidarr searched its indexers

Lidarr contacted its configured indexers and evaluated available releases.

This occurs asynchronously after PPI submits the request.

### Lidarr acquired the album

Lidarr found an acceptable release, sent it to the download client, completed the acquisition, and imported the album.

Only this final outcome makes the music available for eventual Plex import.

Therefore:

```text
SEARCH_QUEUED
```

should not be interpreted as:

```text
DOWNLOAD_COMPLETE
```

---

# Example: Successful Later Acquisition

A track may initially be missing from Plex and dispatched to Lidarr.

For example:

```text
Nicolette Larson - Lotta Love
```

may initially be reported as unmatched.

If Lidarr later obtains the required album and Plex imports it, a future PPI execution can find the track in the Plex library.

At that point the track is handled as a normal Plex match and no longer requires Lidarr processing.

This is the expected lifecycle of the integration.

---

# Example: Album Unavailable

A search may be accepted by Lidarr but produce no releases.

For example:

```text
Sam Cooke - Shake
```

may result in Lidarr reporting:

```text
Searching indexers for [Sam Cooke - Shake (1965)].
No results found
Album search completed. 0 reports downloaded
```

Performing the same search manually through the Lidarr interface may produce the same result.

In this situation, PPI has completed its responsibility successfully.

The album is simply unavailable through the currently configured Lidarr indexers.

A later retry may succeed if indexer availability changes.

---

# Relationship with TIDAL

Lidarr and TIDAL solve different problems.

Lidarr attempts to acquire music that can eventually become part of the local Plex library.

TIDAL provides a companion streaming source for tracks that are not currently available locally.

When both integrations are enabled, PPI can use its external unmatched processing to evaluate music that Plex could not resolve.

A Lidarr search does not block PPI from continuing its other processing.

Likewise, PPI does not wait for Lidarr to finish an acquisition before proceeding.

This is intentional because Lidarr searches and downloads can take considerably longer than a normal PPI execution.

---

# Scheduled Operation

Lidarr integration is designed to work with scheduled PPI execution.

For example, a scheduled playlist import can use:

```text
--lidarr-search
```

to allow eligible missing music to be submitted to Lidarr automatically.

Search history prevents the same unresolved item from being submitted on every execution.

With:

```ini
retry_search_after_days = 7
```

a frequently scheduled PPI job does not automatically translate into a Lidarr search for the same missing album on every run.

---

# Failure Handling

PPI is designed so that failure of an optional external service does not unnecessarily corrupt the rest of the playlist workflow.

If Lidarr is unavailable or a request times out, PPI reports the problem rather than assuming that the requested music was successfully processed.

Plex matching and other applicable PPI processing remain separate from Lidarr acquisition.

A failed Lidarr request does not mean that the Plex playlist itself is invalid.

---

# Troubleshooting

## PPI cannot connect to Lidarr

Verify:

```ini
enabled = true
```

and confirm:

```ini
url
api_key
timeout_seconds
```

Check that the PPI host can reach the configured Lidarr address.

Also verify the API key against the value shown under:

```text
Settings > General > Security
```

## PPI says the search was queued but nothing downloaded

This is not necessarily an error.

Open Lidarr and inspect the search/activity history for the artist or album.

Lidarr may have:

* Found no releases.
* Rejected available releases.
* Encountered an indexer problem.
* Queued a download that has not completed.
* Encountered a download-client problem.

PPI only requests the search. Lidarr remains responsible for acquisition.

## The same missing track is not searched again

Check:

```ini
remember_failed_searches = true
retry_search_after_days = 7
```

PPI may be intentionally suppressing another search because the previous attempt is still inside the retry interval.

## Lidarr downloaded the album but PPI still reports the track missing

Confirm that Plex has imported the new music.

PPI does not immediately rematch a Lidarr acquisition during the same execution that requested it.

A subsequent PPI run should use the updated Plex library/cache and attempt the match again.

If Plex has the track but PPI still cannot match it, troubleshoot the normal Plex matching process rather than Lidarr acquisition.

## Lidarr reports "No results found"

This normally means the configured indexers returned no acceptable releases.

The same result should generally be reproducible using Lidarr's manual interactive search.

This is an availability issue rather than a PPI integration failure.

---

# Search History Database

The Lidarr search-history database is operational state:

```text
cache/lidarr_search_history.db
```

It should normally be preserved across PPI runs.

Deleting it removes PPI's memory of previous Lidarr search attempts and may cause previously searched items to become eligible for another search.

Routine database trimming is not currently required.

---

# Backup

The following Lidarr-specific PPI state should be included with normal PPI application backups:

```text
cache/lidarr_search_history.db
```

For an Unraid installation under:

```text
/mnt/user/appdata/plex-playlist-importer
```

the database is included when the PPI application directory is protected by the normal appdata backup process.

Other platforms should include the PPI application and cache directories in their normal backup strategy as appropriate.

---

# Platform Support

PPI is written in Python and is not limited to Unraid.

The Lidarr integration can be used on any operating system capable of running PPI and reaching the configured Lidarr server.

Unraid is the developer's current preferred production platform, but it is not a requirement for PPI or Lidarr integration.
