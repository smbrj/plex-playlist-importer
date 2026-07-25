# Plex Playlist Importer --- Installation and Production Operations

This document contains installation and operational procedures that have
been verified for the Plex Playlist Importer (PPI) production
environment.

It intentionally does not document unverified or deferred procedures
such as installing or updating PPI from GitHub.

## Platform Support

PPI is written in Python and is not dependent on Unraid. It can run on
any operating system that provides a compatible Python environment and
access to the services configured for PPI.

The procedures in this document focus on **Unraid because it is the
developer's current preferred and verified production platform**, not
because Unraid is a PPI requirement.

PPI is also actively developed and tested on Windows. Installation and
scheduling procedures vary by operating system, but the core application
is platform independent.

## 1. Verified Production Environment

The verified production deployment runs on Unraid with the PPI
application tree located at:

``` text
/mnt/user/appdata/plex-playlist-importer
```

All PPI directories and files reside beneath this root.

The verified Unraid Python runtime is Python 3.11.15. PPI is installed
into a Python virtual environment (`venv`) beneath the application root.

The production PPI files are owned by `nobody:users` (UID 99, GID 100).
In the verified environment, directories use mode `777` and files use
mode `755` to remain compatible with other applications under
`/mnt/user/appdata`.

Unraid User Scripts executes scheduled PPI jobs as `root`.

## 2. Unraid Prerequisites

From the Unraid GUI:

1.  Open **Apps**.
2.  Search for **User Scripts**.
3.  Select **Actions → Install**.
4.  Search for **Python 3 for UNRAID**.
5.  Select **Actions → Install**.

Verify Python from an Unraid terminal:

``` bash
python --version
```

The production environment used to validate PPI reports:

``` text
Python 3.11.15
```

This is a tested version, not a declared minimum Python version.

## 3. Python Virtual Environment

Assuming PPI is already present at the verified application root:

``` bash
cd /mnt/user/appdata/plex-playlist-importer
python -m venv venv
source venv/bin/activate
```

The shell prompt should indicate that the virtual environment is active.

Install PPI's dependencies:

``` bash
pip install -r requirements.txt
```

When interactive setup or testing is complete, exit the virtual
environment with:

``` bash
deactivate
```

Scheduled User Scripts do not need to activate the virtual environment.
They can invoke its Python interpreter directly:

``` bash
./venv/bin/python ./playlist_import_v2.py ...
```

## 4. Initial Configuration

PPI includes `config.example.ini`. Create the working `config.ini` from
this example and supply the required local values.

The current example configuration uses `config_version = 3` and contains
sections for Plex, TIDAL, Lidarr, XMPlaylist, analytics, alias
intelligence, matching, cache, playlist behavior, reports, artist
aliases, and logging.

For initial Plex validation, configure the Plex server URL,
authentication token, and music library name:

``` ini
[plex]
url = http://PLEX_SERVER:32400
token = PLEX_TOKEN_HERE
library = Music
```

The example configuration stores the Plex library cache at:

``` text
cache/plex_library.db
```

and uses a 12-hour maximum cache age. fileciteturn11file0L1-L1

## 5. Initial Plex Validation

Before configuring the optional integrations, perform a simple manual
file-based playlist import using a small `playlist.txt`.

This validates the basic chain:

``` text
Python / venv
    ↓
PPI dependencies
    ↓
config.ini
    ↓
Plex connectivity
    ↓
track matching
    ↓
Plex playlist operation
```

A successful basic Plex import establishes that the core PPI
installation is operational before XMPlaylist, Lidarr, or TIDAL are
introduced.

## 6. Optional Integrations

XMPlaylist, Lidarr, and TIDAL are optional integrations. Their detailed
configuration and operation will be documented separately in:

``` text
docs/XMPLAYLIST.md
docs/LIDARR.md
docs/TIDAL.md
```

The sections below contain only the TIDAL setup and XMPlaylist
production practices that were specifically validated during production
deployment.

## 7. TIDAL Developer Application Setup

TIDAL integration requires a valid paid TIDAL subscription and a TIDAL
developer application.

Create the application through the TIDAL developer dashboard.

A suggested application name is:

``` text
PPI
```

The exact developer-application name is not required by PPI.

Configure this redirect URI:

``` text
http://127.0.0.1:8765/callback
```

Enable these scopes:

``` text
collection.read
collection.write
playlists.read
playlists.write
user.read
```

Record the generated:

``` text
Client ID
Client Secret
```

and store them securely.

Configure the corresponding PPI settings:

``` ini
[tidal]
enabled = true
client_id = CLIENT_ID_HERE
client_secret = CLIENT_SECRET_HERE
redirect_uri = http://127.0.0.1:8765/callback
```

The current example configuration also places the TIDAL user tokens,
search cache, and authoritative ownership/state database beneath the PPI
`cache` directory:

``` text
cache/tidal_user_tokens.json
cache/tidal_search_cache.db
cache/tidal_state.db
```

It currently uses a 24-hour TIDAL search-cache maximum age.
fileciteturn11file0L1-L1

Newly created or modified TIDAL developer-app settings may not become
usable immediately. If authorization fails despite correct credentials
and redirect URI, allow some time for the changes to propagate through
TIDAL's systems and retry.

### TIDAL production ownership

PPI stores TIDAL playlist/favorite ownership information locally in:

``` text
cache/tidal_state.db
```

Only one PPI installation should be treated as authoritative for
production TIDAL write operations.

The verified deployment uses the Unraid production database as the
authoritative TIDAL state. Development environments should not attempt
to synchronize their TIDAL state database with production.

The Windows development environment uses a separate test playlist name:

``` text
test-playlist
```

TIDAL favorites remain account-wide, so destructive TIDAL testing from
development environments should still be performed deliberately.

If an installation sees a TIDAL favorite but cannot prove that its own
PPI state created it, conservative reconciliation behavior such as
`KEEP_FAVORITE_USER_OWNED` is expected. PPI preserves the favorite
rather than deleting user data whose ownership it cannot prove.

## 8. XMPlaylist Production Scheduling

XMPlaylist jobs may be scheduled using the Unraid **User Scripts**
plugin or any scheduler appropriate for the operating system running
PPI.

The `--all-xmprofiles` option is supported and processes all enabled
XMPlaylist profiles sequentially. A verified production run successfully
processed 11 enabled profiles in a single execution.

XMPlaylist may impose API request restrictions depending on request
volume and timing. The number of profiles that can be processed
successfully in one execution should not be treated as a fixed PPI
limit. If an XMPlaylist rate-limit response is encountered, divide the
profiles into smaller groups and schedule those groups separately or at
different times.

PPI's XMPlaylist integration is intended to provide fresh playlist
content and variety. It does not require near-real-time synchronization
with a SiriusXM channel. Choose a scheduling frequency appropriate for
how often you want the resulting Plex playlists refreshed while
remaining within any external XMPlaylist API restrictions.

### Reports when using `--all-xmprofiles`

Standard fixed-name reports are regenerated as each profile is
processed. For example, the configured `reports/unmatched.csv` is
overwritten by subsequent profiles. After an `--all-xmprofiles`
execution completes, a fixed-name report therefore represents the most
recently processed profile rather than an aggregate report for every
profile.

If persistent per-station unmatched reports are required, process
stations individually or in scheduled groups and copy or rename the
report after each station. The Unraid User Scripts template below
demonstrates this approach.

## 9. Unraid User Scripts Template

Each station must execute independently. A failure for one station must
not prevent subsequent stations in the same job from running.

The approved production template is:

``` bash
#!/bin/bash

set -uo pipefail

cd /mnt/user/appdata/plex-playlist-importer || exit 1

stations=(24 25 26)
failures=0

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
        failures=$((failures + 1))
    fi
done

echo "All stations processed."

if (( failures > 0 )); then
    echo "Completed with $failures failed station(s)." >&2
    exit 1
fi

exit 0
```

Change only the `stations=(...)` array for each production job.

The script deliberately does not use `set -e`. Each station is attempted
even when an earlier station fails. After all stations have run, the
wrapper returns a non-zero status if any station failed.

The per-station copy of `unmatched.csv` preserves the latest unmatched
report for each channel before the next station overwrites the standard
report.

## 10. Expected Operational Conditions

The following XMPlaylist message is normal:

``` text
backfill complete; stop reason=TRACK_LIMIT_REACHED
```

It means the configured track target was reached and processing stopped
normally.

XMPlaylist API rate limiting when too many stations are processed
together is also an expected external limitation in the verified
environment. Reduce the number of stations per batch rather than
treating this condition as a reason to redesign PPI.

TIDAL messages such as:

``` text
TIDAL reconciliation plan: KEEP=...
```

and counters showing existing playlist/favorite entries generally
indicate idempotent synchronization rather than a fault.

`KEEP_FAVORITE_USER_OWNED` is a conservative ownership/safety decision,
not a synchronization failure.

A run ending with:

``` text
Result : COMPLETED WITH WARNINGS
```

should be reviewed, but does not automatically mean that the Plex
playlist operation failed.

For an individual User Scripts station, any non-zero PPI exit causes the
wrapper to report that station as failed while continuing to the next
station.

## 11. Backup and Recovery

The verified Unraid system uses the **Appdata Backup** plugin to back up
`/mnt/user/appdata` nightly to a separate RAID array.

Because PPI resides entirely under:

``` text
/mnt/user/appdata/plex-playlist-importer
```

the application tree benefits from the same backup process.

This includes application files, configuration, virtual environment,
caches, state databases, reports, logs, aliases, and TIDAL token/state
files that reside beneath the application root.

Restore operations are handled by the Unraid Appdata Backup plugin.

No separate PPI backup subsystem is required for this deployment.

## 12. Retention Policy

The approved production retention policy is:

``` text
Historical/timestamped reports     retain approximately 35 days
Per-run historical logs            retain approximately 35 days
Per-station unmatched reports      keep latest / overwrite
latest_run.json                     keep latest / overwrite
match_analytics.csv                 retain
Plex cache                          application managed
XMPlaylist state                    application managed / self-pruning
Alias usage database                retain
Lidarr search history               retain
TIDAL state database                retain; never age-prune
TIDAL search cache                  remove expired rows periodically
```

The 35-day period is intended to preserve at least two execution cycles
if production scheduling moves to twice monthly.

PPI does not contain a general-purpose retention engine. Housekeeping is
deliberately handled externally.

## 13. Housekeeping Scripts

Operational housekeeping utilities reside in:

``` text
scripts/
```

The approved utilities are:

``` text
scripts/cleanup_files.sh
scripts/cleanup_files.ps1
scripts/cleanup_tidal_cache.py
```

### Linux / Unraid file cleanup

Preview:

``` bash
./scripts/cleanup_files.sh --dry-run
```

Run:

``` bash
./scripts/cleanup_files.sh
```

The script removes only old timestamped artifacts covered by the
retention policy, including per-run logs and timestamped TIDAL matched
reports.

### Windows PowerShell file cleanup

Preview:

``` powershell
.\scripts\cleanup_files.ps1 -DryRun
```

Run:

``` powershell
.\scripts\cleanup_files.ps1
```

The PowerShell script implements the same file-retention policy as the
Unraid Bash script.

### TIDAL search-cache cleanup

The TIDAL cache housekeeping utility is Python and is cross-platform.

Preview:

``` bash
./scripts/cleanup_tidal_cache.py --dry-run
```

Run:

``` bash
./scripts/cleanup_tidal_cache.py
```

An optional manual VACUUM is available:

``` bash
./scripts/cleanup_tidal_cache.py --vacuum
```

Routine VACUUM is not required.

The utility removes only expired rows from `tidal_search_cache.db`. It
does not modify `tidal_state.db`.

The production dry-run and cleanup were validated against a live cache
containing 1,084 rows. Of those, 554 were expired; cleanup removed those
rows and a subsequent dry run reported 530 total rows and zero expired
rows.

A monthly Unraid housekeeping job has been scheduled.

## 14. Database and Cache Housekeeping Policy

The database audit established:

-   **Plex library cache:** no external cleanup required.
-   **XMPlaylist history/state:** application managed and self-pruning.
-   **Alias usage:** bounded by the alias inventory; retain.
-   **Lidarr search history:** one evolving record per searched album
    rather than an event log; retain.
-   **TIDAL state:** authoritative safety/ownership state; never
    age-prune.
-   **TIDAL search cache:** disposable TTL cache; expired rows may be
    periodically removed.

Do not synchronize SQLite state databases between production and
development systems.

## 15. Operational Principle

PPI production operation favors simple, observable external scheduling
and housekeeping:

``` text
PPI performs playlist/import logic
Unraid User Scripts performs scheduling
Unraid Appdata Backup performs backup/recovery
small scripts perform housekeeping
```

This keeps operational responsibilities separate and avoids embedding
platform-specific scheduling, backup, or retention machinery inside PPI.
