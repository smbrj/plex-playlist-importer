# XMPlaylist Integration

Plex Playlist Importer (PPI) can optionally integrate with XMPlaylist to automatically build Plex playlists from recent SiriusXM channel history.

Unlike importing a traditional playlist file, XMPlaylist allows PPI to build and maintain a continuously refreshed playlist using songs that have recently aired on a SiriusXM channel.

XMPlaylist integration is optional. PPI can operate normally without it.

---

# Overview

The XMPlaylist integration retrieves recently played songs from a SiriusXM channel using the XMPlaylist API.

For each configured station, PPI:

* Retrieves the channel's recent play history.
* Removes duplicate songs.
* Preserves the order in which songs are first encountered.
* Matches each unique song against the Plex music library.
* Builds or updates the corresponding Plex playlist.
* Optionally uses Lidarr and/or TIDAL for tracks that are not available locally.

The objective is **not** to reproduce the SiriusXM channel exactly.

Instead, PPI creates a refreshed collection of unique music that reflects recent channel programming while avoiding excessive duplicate songs.

---

# Requirements

To use the XMPlaylist integration you need:

* An XMPlaylist account.
* A valid XMPlaylist API key.
* A properly configured `xmstations.ini`.
* Internet connectivity.
* XMPlaylist integration configured in `config.ini`.

---

# Configuration

XMPlaylist configuration is located in the `[xmplaylist]` section of `config.ini`.

A typical configuration is:

```ini
[xmplaylist]

base_url = https://xmplaylist.com
timeout_seconds = 20
user_agent = plex-playlist-importer/1.0

state_database = cache/xmplaylist_history.db

history_hours = 168

max_requests_per_run = 8

max_tracks_per_run = 100
```

## base_url

Specifies the XMPlaylist API endpoint.

The default value should normally not be changed.

---

## timeout_seconds

HTTP timeout used for XMPlaylist requests.

The current example uses:

```text
20 seconds
```

---

## user_agent

User-Agent string sent to the XMPlaylist service.

The default value should normally not be modified.

---

## state_database

```text
cache/xmplaylist_history.db
```

Stores the local XMPlaylist ingestion state.

This database contains the cursor information used to continue incremental history collection between PPI executions.

---

## history_hours

```text
history_hours = 168
```

Defines how much SiriusXM channel history PPI attempts to maintain.

The default example retains:

```text
168 hours (7 days)
```

Increasing this value generally produces larger playlists with greater variety.

Reducing it produces playlists that more closely reflect recent channel programming.

---

## max_requests_per_run

Limits the number of XMPlaylist API requests performed during a single execution.

This provides a simple way to remain within the practical limits of the XMPlaylist API.

If additional history remains after the request limit is reached, PPI records its current position and continues during a future execution.

---

## max_tracks_per_run

Limits the maximum number of unique tracks retained for the playlist.

This prevents playlists from growing indefinitely while still providing substantial variety.

---

# Station Profiles

Stations are configured in:

```text
xmstations.ini
```

Each station profile contains the information required to retrieve SiriusXM channel history and determine the Plex playlist name.

Each configured station is processed independently.

---

# Understanding the Rolling History Model

One of the most important concepts of the XMPlaylist integration is that PPI is **not attempting to duplicate SiriusXM's live playlist exactly**.

Instead, PPI continuously builds a collection of unique songs that have recently appeared on the channel.

For example:

```text
Song A
Song B
Song A
Song C
Song D
Song B
```

becomes:

```text
Song A
Song B
Song C
Song D
```

The resulting Plex playlist remains representative of recent channel programming without repeatedly adding songs that receive frequent airplay.

This design keeps playlists fresh while providing significantly more listening variety than simply replaying the exact SiriusXM history.

---

# Playlist Construction

For each configured station PPI performs the following steps:

1. Retrieve channel history.
2. Continue from the previously stored cursor.
3. Remove duplicate songs.
4. Match songs against Plex.
5. Process unmatched songs through optional Lidarr and/or TIDAL integration.
6. Update the Plex playlist.

Play counts, first-played timestamps, and last-played timestamps are not retained.

Only the unique music is preserved.

---

# Incremental Operation

The first execution may require several API requests to build the desired history window.

Subsequent executions usually require far fewer requests because PPI resumes from the previously stored cursor.

This significantly reduces API traffic during normal scheduled operation.

---

# State Database

PPI stores XMPlaylist state in:

```text
cache/xmplaylist_history.db
```

The state database records the ingestion cursor for each configured station.

Deleting this database causes PPI to rebuild history from the beginning during the next execution.

Routine deletion is not recommended.

---

# First Run

During the initial execution PPI may require multiple API requests before sufficient channel history has been collected.

This is expected.

Depending on the configured request limit, the first execution may only partially populate the desired history window.

Subsequent executions continue automatically until the requested history has been collected.

---

# Backfill Operation

Once PPI has caught up with the desired history window, log messages similar to the following may appear:

```text
XMPlaylist ingestion:
channel 14 The Bridge,
100 unique tracks,
6 requests,
backfill complete;
stop reason=TRACK_LIMIT_REACHED
```

This is **normal**.

It indicates that:

* The desired rolling history has already been collected.
* PPI reached the configured request limit.
* No additional historical data was available or required during this execution.

This message should not normally be interpreted as an application error.

---

# XMPlaylist API Rate Limits

The XMPlaylist API has practical request limits.

For smaller station collections, processing every configured station during a single execution may be acceptable.

For larger station collections, repeatedly requesting every station during one execution may eventually encounter API rate limiting.

PPI therefore recommends:

* Using `--all-xmprofiles` only for relatively small station collections (approximately four stations or fewer).
* Splitting larger collections into multiple scheduled jobs.

This approach reduces API load while allowing each station to be refreshed on a regular schedule.

---

# Scheduling

XMPlaylist integration is intended to run under a scheduler such as:

* Unraid User Scripts
* cron
* Windows Task Scheduler
* Any comparable scheduling system

The exact scheduler is not important.

The recommended approach is to process a manageable number of stations during each scheduled execution.

A production example is:

```bash
#!/bin/bash

set -uo pipefail

cd /mnt/user/appdata/plex-playlist-importer || exit 1

stations=(24 25 26)

for station in "${stations[@]}"; do

    echo "Processing station $station..."

    if ./venv/bin/python ./playlist_import_v2.py \
        --xmstation "$station" \
        --xm-max-tracks 150 \
        --update; then

        cp "./reports/unmatched.csv" "./reports/unmatched-${station}.csv"

        echo "✓ Station $station completed"

    else

        echo "✗ Station $station failed" >&2

    fi

done

echo "All stations processed."
```

Each station executes independently.

A warning or failure for one station does not prevent later stations from running.

This approach has proven effective for larger station collections while remaining within normal XMPlaylist API limits.

---

# Operational Messages

Typical log messages include:

## Initial backfill

```text
Beginning history backfill...
```

Occurs during the first collection of station history.

---

## Partial backfill

```text
stop reason=REQUEST_LIMIT_REACHED
```

The configured request limit was reached before the desired history window was fully collected.

The next scheduled execution continues automatically.

---

## Backfill complete

```text
backfill complete;
stop reason=TRACK_LIMIT_REACHED
```

Normal operational message indicating that PPI has already caught up with the configured history window.

---

## Playlist updated

A successful playlist update indicates that Plex processing completed normally after XMPlaylist ingestion.

---

# Relationship with Lidarr and TIDAL

XMPlaylist supplies the source material for the playlist.

After unique songs have been collected:

* Plex matching is attempted first.
* Lidarr may optionally process tracks unavailable in Plex.
* TIDAL may optionally supply companion-playlist tracks that remain unavailable locally.

XMPlaylist itself is not responsible for external music acquisition.

---

# Troubleshooting

## Empty playlist

Verify:

* Station configuration.
* XMPlaylist API credentials.
* Internet connectivity.
* Plex connectivity.

---

## Playlist contains fewer songs than expected

Check:

```text
history_hours
max_requests_per_run
max_tracks_per_run
```

A newly configured station may require several scheduled executions before the desired history window has been collected.

---

## API rate limiting

If API rate-limit messages occur regularly:

* Reduce the number of stations processed during a single execution.
* Split stations across multiple scheduled jobs.
* Avoid using `--all-xmprofiles` for large station collections.

---

## Rebuilding history

Deleting:

```text
cache/xmplaylist_history.db
```

forces PPI to rebuild the rolling history from the beginning.

This should normally only be performed intentionally.

---

# Backup

The following files should be included in normal PPI backups:

```text
cache/xmplaylist_history.db
xmstations.ini
```

For an Unraid installation under:

```text
/mnt/user/appdata/plex-playlist-importer
```

these files are automatically included when the application directory is protected by the normal appdata backup process.

---

# Platform Support

PPI is written in Python and is not limited to Unraid.

The XMPlaylist integration can be used on any operating system capable of running the supported Python environment and satisfying PPI's dependencies.

Unraid is the developer's current preferred production platform, but it is not required for using PPI or the XMPlaylist integration.
