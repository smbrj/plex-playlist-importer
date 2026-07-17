# Plex Playlist Importer

A command-line playlist importer and matcher for Plex Music.

The application reads playlist definitions from TXT, CSV, TSV, or M3U
files, searches a Plex Music library for the best matching tracks,
writes detailed match diagnostics, and can create or modify a Plex
playlist.

This document describes the current **V3 baseline**. The executable
remains named `playlist_import_v2.py` because the filename was retained
from the earlier V2 rewrite.

> **Baseline status:** TXT, CSV, TSV, and M3U dry runs are verified and
> the automated suite currently reports `13 passed`, and the live Plex write path has been validated for CREATE, UPDATE, REPLACE, and additive SYNC.

## Contents

-   Overview
-   Current baseline
-   Requirements and installation
-   Directory structure
-   Configuration
-   Artist aliases
-   Input formats
-   Command-line usage and options
-   Playlist modes
-   Application flow
-   Matching and normalization
-   Cache
-   Reports and filename diagnostics
-   Duplicate reporting
-   Logging
-   Testing and baseline verification
-   Troubleshooting
-   Maintenance notes
-   Known limitations
-   Future work

## Overview

The application is divided into layers:

1.  Configuration loads Plex, matching, cache, report, alias, logging,
    and playlist settings.
2.  Plex I/O reads library metadata and performs playlist changes.
3.  SQLite caching stores a local materialized representation of the
    Plex library.
4.  Parsing converts supported files into ordered playlist entries.
5.  Normalization creates stable Unicode-aware comparison forms.
6.  Search indexing builds fast in-memory candidate lookup structures.
7.  Matching discovers candidates, applies gates, scores candidates, and
    selects a result.
8.  Reporting writes unmatched and full match reports and identifies
    metadata concerns.
9.  Playlist application resolves accepted matches back to Plex objects
    and applies the selected mode.

The CLI orchestrator should remain orchestration-only. Matching logic
belongs in the package modules.

## Current Baseline

The current baseline has been exercised against a Plex Music library
containing approximately **55,982 tracks**.

  Format     Entries   Normal   Fallback   Unmatched   Warnings
  -------- --------- -------- ---------- ----------- ----------
  TXT              9        5          3           1          3
  CSV              7        7          0           0          0
  TSV              7        7          0           0          0
  M3U              2        2          0           0          1

Automated baseline:

``` text
............. [100%]
13 passed
```

Expected TXT baseline:

``` text
Normal matches   : 5
Fallback matches : 3
Unmatched        : 1
Metadata Warnings: 3
Total            : 9
```

The TXT case exercises exact matching, remaster-title normalization,
token candidate discovery, `Various Artists` fallback handling, filename
diagnostics, and a legitimate unmatched entry.


## Live Plex Integration Validation

The V3 write path has been validated against a live Plex Media Server
using a disposable audio playlist.

| Test | Verified behavior | Result |
| --- | --- | --- |
| CREATE when absent | Created five tracks in input order | PASS |
| CREATE when present | Rejected with a clear error; existing playlist unchanged | PASS |
| UPDATE | Skipped three existing tracks, added two new tracks, preserved order | PASS |
| REPLACE | Removed seven existing tracks, added three requested tracks in order | PASS |
| SYNC | Skipped two existing tracks, added two missing tracks, retained an omitted existing track | PASS |
| Rating-key resolution | Resolved accepted matches with Plex rating keys before mutation | PASS |
| Duplicate-name protection | Exact-title lookup rejects ambiguous duplicate playlists | PASS |

Observed validated summaries:

``` text
Playlist create summary:
  Added     : 5
  Final     : 5
```

``` text
Playlist update summary:
  Requested       : 5
  Already present : 3
  Added           : 2
  Final playlist  : 7
```

``` text
Playlist replace summary:
  Removed         : 7
  Added           : 3
  Final playlist  : 3
```

``` text
Playlist sync summary:
  Requested       : 4
  Already present : 2
  Added           : 2
  Final playlist  : 5
```

## Features

Current implemented capabilities include:


✓ SQLite search index
✓ Intelligent multi-stage matching
✓ Artist alias support
✓ Version-aware matching
✓ Filename diagnostics
✓ Metadata diagnostics
✓ Dry-run mode
✓ CSV reports
✓ CREATE playlists
✓ UPDATE playlists
✓ REPLACE playlists
✓ SYNC playlists
✓ Playlist order preservation
✓ Automatic duplicate prevention
✓ Refreshable cache
✓ Threaded matching
✓ TXT, CSV, TSV, and M3U parsing.
✓ Optional media file paths in reports.
✓ Duplicate logical-track reports.
✓ Debug candidate diagnostics.
✓ Trace pipeline/timing diagnostics.
✓ Pytest regression tests.

## Requirements

Minimum software:

-   Python **3.10 or newer**
-   Plex Media Server
-   A Plex Music library
-   Network access to the Plex server
-   A valid Plex authentication token

The baseline development environment has been exercised with Python 3.12
on Windows. SQLite is supplied by Python's standard library.

The current `requirements.txt` specifies:

  Package        Minimum   Purpose
  -------------- --------- -----------------------
  `plexapi`      4.17.0    Plex access
  `rapidfuzz`    3.9.0     Fuzzy comparison
  `tqdm`         4.66.0    Progress support
  `rich`         13.9.0    Console support
  `jinja2`       3.1.4     Reporting support
  `pandas`       2.2.3     CSV/DataFrame support
  `sqlalchemy`   2.0.36    Optional ORM support
  `typer`        0.15.1    CLI-related support
  `pytest`       8.3.4     Testing
  `mypy`         1.14.0    Type checking
  `black`        24.10.0   Formatting
  `ruff`         0.8.4     Linting

Not every dependency is used directly by every current execution path.
The requirements file represents the current project/development
environment.

## Installation

From the project directory:

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Configure `config.ini`:

``` ini
[plex]
url = http://YOUR-PLEX-SERVER:32400
token = YOUR_PLEX_TOKEN
library = Music
```

Never commit a real Plex token to a public repository.

Verify the installation:

``` powershell
python -m pytest -q
```

Perform an initial dry run:

``` powershell
python playlist_import_v2.py playlist.txt `
    --playlist "Test Playlist" `
    --dry-run
```

A dry run performs parsing, index loading, matching, diagnostics, and
report generation, but returns before Plex playlist changes.

## Directory Structure

``` text
Plex-playlist-importer/
|
|-- playlist_import_v2.py       Main CLI orchestrator
|-- config.ini                  Local runtime configuration
|-- requirements.txt            Dependency requirements
|-- README.md                   Project/support documentation
|
|-- plex_playlist/
|   |-- __init__.py
|   |-- cache.py                SQLite library cache
|   |-- logging_config.py       Logging initialization
|   |-- matcher.py              Candidate processing and decisions
|   |-- models.py               Shared models and enums
|   |-- normalization.py        Unicode and metadata normalization
|   |-- parser.py               TXT/CSV/TSV/M3U parsers
|   |-- plex_client.py          Plex I/O and playlist operations
|   |-- reporting.py            Match, unmatched, and duplicate reports
|   |-- resources.py            External resource loading
|   `-- search_index.py         In-memory lookup indexes
|
|-- resources/
|   `-- aliases.txt             Artist alias mappings
|
|-- cache/
|   `-- plex_library.db         Generated SQLite library cache
|
|-- logs/
|   |-- debug.log               Historical/debug log when retained
|   |-- importer.log            Historical/importer log when retained
|   `-- runs/                   Per-run text diagnostics
|
|-- reports/                    Report destination directory
`-- tests/                      Automated tests
```

Legacy files removed during baseline cleanup and not part of the current
architecture:

``` text
filename_diagnostics.py
config.py
logging_utils.py
test_e2e_mock.py
utils.py
```

The former track-number parsing helper from root `utils.py` was moved
into parser ownership before the baseline was frozen.

Some source docstrings and the executable filename still contain `V2`
terminology. These are historical naming artifacts.

## Configuration

The default configuration file is `config.ini`.

Select another file with:

``` powershell
python playlist_import_v2.py playlist.txt `
    --playlist "Classic Rock" `
    --config config-testing.ini `
    --dry-run
```

Relative alias and cache paths are resolved relative to the directory
containing the selected configuration file.

Representative configuration:

``` ini
[plex]
url = http://YOUR-PLEX-SERVER:32400
token = YOUR_PLEX_TOKEN
library = Music

[matching]
threshold = 85
threads = 8
preferred_versions = studio,remaster,stereo,single,album,live,acoustic,demo,alternate,instrumental,radio,extended,edit,mono
artist_weight = 0.25
album_artist_weight = 0.15
title_weight = 0.45
combined_weight = 0.15
min_title_score = 80
fallback_title_score = 95

[cache]
enabled = true
database = cache/plex_library.db
refresh_on_start = false
max_age_hours = 24

[reports]
unmatched = unmatched.csv
output_path = reports/
path = reports/
include_file_paths = false

[artist_aliases]
enabled = true
file = resources/aliases.txt

[logging]
debug = false
trace = true
level = INFO
directory = logs
filename = playlist_import.log

[playlist]
duplicates = skip
preserve_order = true
```

### `[plex]`

  Setting     Required   Description
  ----------- ---------- -----------------------------------------------------
  `url`       Yes        Plex server URL
  `token`     Yes        Plex authentication token
  `library`   No         Music library section; CLI code defaults to `Music`

### `[matching]`

  Setting                  Description
  ------------------------ ------------------------------------
  `threshold`              Configured overall match threshold
  `threads`                Configured worker count
  `preferred_versions`     Recording preference order
  `artist_weight`          Artist score weight
  `album_artist_weight`    Album-artist score weight
  `title_weight`           Title score weight
  `combined_weight`        Combined artist/title score weight
  `min_title_score`        Normal title gate
  `fallback_title_score`   Stricter fallback title gate

Baseline weights total `1.00`:

``` text
artist             0.25
album artist       0.15
title              0.45
combined           0.15
```

### `[cache]`

  Setting              Description
  -------------------- --------------------------------
  `enabled`            Cache policy configuration
  `database`           SQLite database path
  `refresh_on_start`   Refresh policy configuration
  `max_age_hours`      Cache-age policy configuration

**Current behavior:** cache use is explicitly controlled by
`--no-cache`, and refresh by `--refresh-cache` or an empty cache. Do not
assume every cache policy field is automatically enforced by the current
orchestrator.

### `[reports]`

`include_file_paths` is actively read by the CLI. When false, the
report's `File Path` column is blank.

The CLI currently passes `--unmatched` and `--report` paths directly to
the report writers.

### `[artist_aliases]`

``` ini
[artist_aliases]
enabled = true
file = resources/aliases.txt
```

The aliases file is intentionally external to preserve `config.ini` as
application configuration rather than metadata storage.

### `[logging]`

Intended diagnostic combinations:

``` text
debug=true,  trace=false  -> inspect candidates and scores
debug=false, trace=true   -> inspect pipeline and timing
```

### `[playlist]`

The configuration currently contains duplicate and order policies:

``` ini
duplicates = skip
preserve_order = true
```

Support personnel should verify active implementation paths before
assuming every configuration field changes runtime behavior.

## Artist Aliases

Aliases allow different artist names to resolve to the same canonical
artist key.

Conceptual example:

``` text
ELO = Electric Light Orchestra
```

A request for:

``` text
ELO - Mr. Blue Sky
```

can resolve against Plex metadata for:

``` text
Electric Light Orchestra - Mr. Blue Sky
```

The alias path may be absolute or relative. Relative paths are resolved
from the configuration file's directory.

Alias mappings participate in matching canonicalization and metadata
diagnostics.

If the alias file is unavailable, the resource loader can continue with
an empty mapping and log a warning. Matching then proceeds without alias
assistance.

## Supported Playlist Formats

Supported extensions:

``` text
.txt
.csv
.tsv
.m3u
```

Currently supported:

TXT

Artist - Title

Number. Artist - Title

CSV

Artist,Title

Artist,Title,Album

Artist,Title,Album,Year

TSV

Artist<TAB>Title

Whitespace and extra delimiters are ignored.


An unrecognized extension currently falls back to TXT parsing.

Accepted entries become ordered `PlaylistEntry` records containing at
least:

``` text
sequence
artist
title
```

Sequence numbers begin at `1` and are assigned to accepted entries.

### TXT

Format:

``` text
Artist - Title
```

Leading numeric sequence/track numbers are supported:

``` text
1. Aretha Franklin - Respect
2. Bob Dylan - Like a Rolling Stone
3. Marvin Gaye - What's Going On
```

Numbers are optional:

``` text
Aretha Franklin - Respect
Bob Dylan - Like a Rolling Stone
```

The delimiter is a hyphen surrounded by spaces: `-`. Only the first
delimiter separates artist and title.

Required fields: artist and title. Blank or unparseable lines are
skipped.

### CSV

The first two columns are:

``` text
Artist,Title
```

Example:

``` csv
Bob Dylan,Like a Rolling Stone
The Rolling Stones,Satisfaction
John Lennon,Imagine
Marvin Gaye,What's Going On
```

    Position Field    Required
  ---------- -------- ----------
           1 Artist   Yes
           2 Title    Yes

Rows with fewer than two columns or a blank artist/title are skipped.
Additional columns may exist; matching input uses the first two.

**Header note:** the current parser treats rows positionally. Do not add
an `Artist,Title` header unless header detection is explicitly
implemented and tested.

### TSV

Format:

``` text
Artist<TAB>Title
```

Example:

``` text
Bob Dylan   Like a Rolling Stone
The Rolling Stones  Satisfaction
John Lennon Imagine
```

The separator must be an actual tab character. The first two fields are
artist and title.

### M3U

The current parser uses `#EXTINF` metadata:

``` text
#EXTM3U

#EXTINF:-1,Queen - Bohemian Rhapsody
Queen - Bohemian Rhapsody.mp3

#EXTINF:-1,Eagles - Hotel California
Eagles - Hotel California.flac
```

It extracts `Artist - Title` from the text after the first comma on an
`#EXTINF` line.

The media path line is not the matching source. Matching is driven by
`#EXTINF` metadata.

## Command-Line Usage

General form:

``` powershell
python playlist_import_v2.py INPUT_FILE `
    --playlist "PLAYLIST NAME" `
    [OPTIONS]
```

`INPUT_FILE` is positional and `--playlist` is required by the current
argument parser.

### Dry run

``` powershell
python playlist_import_v2.py playlist.txt `
    --playlist "Classic Rock" `
    --dry-run
```

### Create

``` powershell
python playlist_import_v2.py playlist.txt `
    --playlist "Classic Rock"
```

### Update

``` powershell
python playlist_import_v2.py playlist.txt `
    --playlist "Classic Rock" `
    --update
```

### Replace

``` powershell
python playlist_import_v2.py playlist.txt `
    --playlist "Classic Rock" `
    --replace
```

### Sync

``` powershell
python playlist_import_v2.py playlist.txt `
    --playlist "Classic Rock" `
    --sync
```

### Refresh cache

``` powershell
python playlist_import_v2.py playlist.txt `
    --playlist "Classic Rock" `
    --refresh-cache `
    --dry-run
```

### Bypass cache

``` powershell
python playlist_import_v2.py playlist.txt `
    --playlist "Classic Rock" `
    --no-cache `
    --dry-run
```

### Custom reports

``` powershell
python playlist_import_v2.py playlist.txt `
    --playlist "Classic Rock" `
    --unmatched reports\classic-rock-unmatched.csv `
    --report reports\classic-rock-report.csv `
    --dry-run
```

### Duplicate report

``` powershell
python playlist_import_v2.py playlist.txt `
    --playlist "Dedupe Report" `
    --dedupe `
    --output reports\duplicates.csv
```

The input file and playlist name are still required by argparse even
though `--dedupe` exits before playlist parsing and matching.

## Command-Line Options

  Argument/Option     Required   Default                 Description
  ------------------- ---------- ----------------------- -----------------------------------------
  `input_file`        Yes        None                    Playlist input file
  `--playlist`        Yes        None                    Plex playlist name
  `--config`          No         `config.ini`            INI configuration file
  `--dry-run`         No         Off                     Match/report without playlist changes
  `--update`          No         Off                     UPDATE mode
  `--replace`         No         Off                     REPLACE mode
  `--sync`            No         Off                     SYNC mode
  `--refresh-cache`   No         Off                     Reload Plex and replace cached tracks
  `--no-cache`        No         Off                     Build the index directly from Plex
  `--unmatched`       No         `unmatched.csv`         Unmatched CSV path
  `--report`          No         `playlist_report.csv`   Full match CSV path
  `--dedupe`          No         Off                     Write duplicate library report and exit
  `--output`          No         `duplicates.csv`        Duplicate report path

Mode selection precedence is:

``` text
--update
--replace
--sync
CREATE default
```

The arguments are not currently mutually exclusive. Specify no more than
one mode option.

## Playlist Modes

### CREATE

CREATE is the default.

If the named playlist does not exist, it is created with the accepted
tracks in input order.

If an exact-title playlist already exists, CREATE is rejected safely:

``` text
Playlist 'NAME' already exists. Use --update, --replace, or --sync.
```

The existing playlist is not modified.

Playlist lookup uses exact-title validation. If multiple exact-title
playlists exist, the operation is rejected rather than selecting one
arbitrarily.

Successful CREATE operations log:

``` text
Playlist create summary:
  Added     : 5
  Final     : 5
```

### UPDATE

`--update` appends only requested tracks whose Plex rating keys are not
already present.

The importer filters existing rating keys before calling Plex rather
than relying on Plex to suppress duplicates.

New tracks retain input order. Existing playlist order is unchanged.

Successful UPDATE operations log:

``` text
Playlist update summary:
  Requested       : 5
  Already present : 3
  Added           : 2
  Final playlist  : 7
```

If the playlist does not exist, it is created.

### REPLACE

`--replace`:

1.  reads the current playlist contents;
2.  removes all existing playlist items;
3.  adds the accepted tracks in input order.

Successful REPLACE operations log:

``` text
Playlist replace summary:
  Removed         : 7
  Added           : 3
  Final playlist  : 3
```

If the playlist does not exist, it is created.

### SYNC

Current `--sync` behavior:

1.  reads rating keys already in the playlist;
2.  skips requested tracks already present;
3.  appends only missing requested tracks in input order;
4.  leaves existing tracks that are absent from the input untouched.

Successful SYNC operations log:

``` text
Playlist sync summary:
  Requested       : 4
  Already present : 2
  Added           : 2
  Final playlist  : 5
```

Current V3 SYNC is therefore **additive synchronization**, not an exact
mirror.

## Application Flow

``` text
Command line
    |
    v
Load configuration
    |
    +--> Plex settings
    +--> MatchingConfig
    +--> artist aliases
    `--> report file-path policy
    |
    v
Initialize SQLite cache schema
    |
    v
Connect PlexClient
    |
    +--> --dedupe?
    |       +--> load cached tracks
    |       +--> write duplicate CSV
    |       `--> exit
    |
    v
Load search index
    |
    +--> --no-cache
    |       +--> load Plex library
    |       `--> build SearchIndex directly
    |
    `--> cache path
            +--> refresh requested or cache empty?
            |       +--> load Plex library
            |       `--> replace cached tracks
            `--> load cache and build SearchIndex
    |
    v
Parse input
    |
    v
Match entries
    |
    v
Log summary and write reports
    |
    +--> --dry-run? --> exit
    |
    v
Select PlaylistMode
    |
    v
Resolve accepted rating keys to Plex objects
    |
    v
Apply playlist operation
```

Reports are generated **before** the dry-run return. Dry runs are
therefore useful for parser, candidate, match, metadata, cache, and
performance review.

## Matching and Normalization

The matcher works with shared data models instead of raw Plex objects:

``` text
PlaylistEntry
    |
    v
SearchIndex candidate discovery
    |
    v
prioritization
    |
    v
eligibility
    |
    v
title gate
    |
    v
logical deduplication
    |
    v
weighted scoring
    |
    v
version preference / sorting
    |
    v
decision
    |
    v
MatchResult
```

A `MatchingSession` contains all results for the requested playlist.

### Unicode folding

Normalization:

-   translates typographic quotes/apostrophes;
-   translates common Unicode dash variants;
-   translates selected non-decomposing letters;
-   applies NFKD decomposition;
-   removes combining marks;
-   applies case folding.

Examples:

``` text
Beyoncé         -> beyonce
Mötley Crüe     -> motley crue
What’s Going On -> what's going on
```

Selected translations include:

``` text
æ -> ae
œ -> oe
ø -> o
ł -> l
đ -> d
ð -> d
þ -> th
ß -> ss
```

Original display metadata remains available for reports.

### Artist normalization

Artist normalization applies general normalization and removes
collaboration suffixes beginning with markers such as:

``` text
feat
ft
featuring
```

Aliases are applied through canonical artist keys.

### Title normalization

Title normalization folds Unicode, removes selected recording/version
noise, converts punctuation to token boundaries, treats underscores as
separators, and collapses whitespace.

This helps compare:

``` text
What's Going On
What’s Going On

Dreams
Dreams (2001 Remaster)

Strawberry Fields Forever
Strawberry Fields Forever (Remastered 2009)
```

### Candidate discovery

Trace output can identify sources such as:

``` text
exact artist+title
exact title
artist intersect token title
token title
artist found; no title match
```

The matcher avoids scoring the entire Plex library for each request.

Exact normalized artist/title lookup is the narrowest path. Versioned
titles may use artist/title-token intersection. Strong exact-title
candidates can support fallback handling when Plex artist metadata is
generic.

### Title gates

Normal candidate processing uses:

``` ini
min_title_score = 80
```

Fallback processing uses the stricter:

``` ini
fallback_title_score = 95
```

Candidate discovery alone does not mean a track is accepted.

### Weighted score

Baseline weights:

``` text
Artist score         25%
Album artist score   15%
Title score          45%
Combined score       15%
```

The full report exposes all component scores and the combined score.

### Version classification

Current version categories include:

``` text
studio
live
remaster
mono
stereo
single
album
acoustic
demo
alternate
instrumental
radio
extended
edit
```

Recognized indicators include live/concert, remaster, mono, stereo,
single version/edit, album version, acoustic/unplugged, demo,
alternate/take/session, instrumental, radio edit/version,
extended/12-inch/club mix, and edit markers.

No marker defaults to `studio`.

The order of `preferred_versions` is significant and helps choose among
otherwise strong versions.

### Fallback matching

Fallback matching supports strong-title cases with unreliable artist
metadata.

Example:

``` text
Requested Artist: Nirvana
Requested Title : Smells Like Teen Spirit
Plex Artist      : Various Artists
Plex Title       : Smells Like Teen Spirit
```

Fallbacks are explicitly labeled and receive diagnostic warnings. They
are not silently presented as normal exact matches.

## SQLite Library Cache

Default configured database:

``` text
cache/plex_library.db
```

Current cached track fields include:

``` text
rating_key
guid
artist
artist_key
album_artist
album_artist_key
album
album_key
title
title_key
duration
year
version
file_path
```

The cache also has a metadata table. Current schema version:

``` text
5
```

Metadata can include:

``` text
schema_version
last_refresh
```

SQLite is initialized with WAL journal mode and a 5000 ms busy timeout.
Indexes exist for `artist_key` and `title_key`.

If the cache is empty, a cached run loads Plex and replaces the cache
contents.

Use `--refresh-cache` after meaningful Plex library changes:

-   tracks added or removed;
-   artist/album/title metadata changed;
-   media reorganized and filename paths need refreshing.

Use `--no-cache` to load Plex directly and build an in-memory search
index.

A full Plex refresh can take minutes for a large library; loading the
SQLite-backed index normally takes only a few seconds.

## Reports

Normal matching runs generate reports before the dry-run boundary.

Default paths:

``` text
unmatched.csv
playlist_report.csv
```

### `unmatched.csv`

Fields:

  Field        Description
  ------------ ------------------------------------
  `Sequence`   Parsed sequence
  `Artist`     Requested artist
  `Title`      Requested title
  `Reason`     Why no accepted match was produced

### `playlist_report.csv`

Current fields:

  Field                    Description
  ------------------------ -------------------------------------------------
  `Sequence`               Requested sequence
  `Requested Artist`       Input artist
  `Requested Title`        Input title
  `Matched Artist`         Plex artist
  `Matched Album Artist`   Plex album artist
  `Matched Title`          Plex title
  `Matched Album`          Plex album
  `Matched Version`        Classified selected-track version
  `Selected Version`       Selected version
  `Rating Key`             Plex rating key
  `Match Type`             Confidence-derived type, Fallback, or Unmatched
  `Confidence`             Confidence enum name
  `Artist Score`           One-decimal artist score
  `Title Score`            One-decimal title score
  `Album Artist Score`     One-decimal album-artist score
  `Combined Score`         One-decimal combined score
  `File Path`              Media path when enabled
  `Filename Artist`        Diagnostic artist parsed from filename
  `Filename Title`         Diagnostic title parsed from filename
  `Metadata Warnings`      Semicolon-separated warnings
  `Reason`                 Matcher decision reason

By default:

``` ini
include_file_paths = false
```

The `File Path` column remains blank. Set it to `true` when full media
paths are required.

## Filename Diagnostics

Filename diagnostics are **reporting-only**. They do not affect
candidate discovery, scores, gates, or selected tracks.

A filename can be parsed when its stem follows:

``` text
Artist - Title
```

Leading track/sequence numbers are removed.

Examples:

``` text
009. Public Enemy - Fight The Power (From Do The Right Thing Soundtrack).flac
003. Nirvana - Smells Like Teen Spirit.flac
008. Missy Elliott - Get Ur Freak On.flac
```

Current warnings include:

``` text
Matched artist is Various Artists
Matched album artist is Various Artists
Fallback match; verify artist metadata
Matched artist differs from requested artist
Filename artist differs from Plex artist
Filename title differs from Plex title
```

Artist comparisons are alias-aware. Title comparisons use normalized
titles.

A warning does not automatically mean the match is wrong. It identifies
metadata worth reviewing.

Files such as:

``` text
01_Respect.flac
108. Like a Rolling Stone.flac
02. Dreams (2001 Remaster).flac
```

do not contain both artist and title in the expected filename pattern,
so filename artist/title columns remain blank. This is expected.

## Duplicate Library Report

`--dedupe` analyzes cached Plex library tracks rather than the requested
playlist.

Duplicates are grouped by:

``` text
normalized artist
+ normalized title
+ classified version
```

Only groups with more than one track are written.

Fields:

``` text
Artist
Title
Version
Duplicate Type
Likely Action
Duplicate Count
Album Count
Duration Spread
Rating Keys
Albums
Durations
Years
```

Duplicate types:

``` text
Same Album
Different Album
Different Version
Multiple Copies
```

Diagnostic actions include:

``` text
Review/delete duplicate
Review carefully
Inspect manually
Usually keep
Review
```

The report never deletes Plex tracks.

## Logging

A normal run logs a summary such as:

``` text
--------------------------------------
Matching summary:
  Normal matches   : 5
  Fallback matches : 3
  Unmatched        : 1
  Metadata Warnings: 3
  Total            : 9
```

### Debug mode

``` ini
debug = true
trace = false
```

Use for candidate and score diagnostics.

### Trace mode

``` ini
debug = false
trace = true
```

Use for candidate-source, pipeline-count, decision, and timing
diagnostics.

Example:

``` text
TRACE:
ENTRY: The Beatles - Strawberry Fields Forever (Remastered 2009)
  candidate source   : artist intersect token title
  raw candidates     : 8
  prioritized        : 8
  eligible           : 8
  fallback_mode      : False
  title gated        : 8
  deduped            : 8
  pipeline total     : ...
  scoring            : 8
  sorting            : 8
  decision           : matched
  total entry        : ...
```

Historical files under `logs/` may contain old development failures. Do
not treat an old stack trace as a current defect without reproducing it
against the current baseline.

## Testing

Run all tests:

``` powershell
python -m pytest -q
```

Current expectation:

``` text
............. [100%]
13 passed
```

Recommended change workflow:

``` text
1. Make one focused change.
2. Run python -m pytest -q.
3. Run the TXT baseline dry run.
4. Compare the matching summary.
5. Inspect changed playlist_report.csv rows.
6. If parser-related, run the affected format baseline.
7. Commit only after every intentional result change is explained.
```

Run the full suite after changes to parsing, normalization, aliases,
indexing, matching, scoring, version classification, cache
schema/loading, reporting helpers used by match results, or shared
models.

## Baseline Verification

### TXT

``` powershell
python playlist_import_v2.py playlist.txt `
    --playlist "Baseline TXT" `
    --dry-run
```

Expected:

``` text
Normal matches   : 5
Fallback matches : 3
Unmatched        : 1
Metadata Warnings: 3
Total            : 9
```

Known baseline entries include:

``` text
Aretha Franklin - Respect
Public Enemy - Fight The Power (From Do The Right Thing Soundtrack)
Sam Cooke - A Change Is Gonna Come
Bob Dylan - Like a Rolling Stone
Nirvana - Smells Like Teen Spirit
Marvin Gaye - What's Going On
The Beatles - Strawberry Fields Forever (Remastered 2009)
Missy Elliott - Get Ur Freak On
Fleetwood Mac - Dreams (2001 Remaster)
```

### CSV

``` powershell
python playlist_import_v2.py sample.csv `
    --playlist "Baseline CSV" `
    --dry-run
```

Expected: 7 normal, 0 fallback, 0 unmatched, 0 warnings.

### TSV

``` powershell
python playlist_import_v2.py sample.tsv `
    --playlist "Baseline TSV" `
    --dry-run
```

Expected: 7 normal, 0 fallback, 0 unmatched, 0 warnings.

### M3U

``` powershell
python playlist_import_v2.py sample.m3u `
    --playlist "Baseline M3U" `
    --dry-run
```

Expected: 2 normal, 0 fallback, 0 unmatched, 1 warning.

## Troubleshooting

### Alias resource not found

Check:

``` ini
[artist_aliases]
enabled = true
file = resources/aliases.txt
```

A relative alias path is resolved from the configuration file's
directory. The application can continue with an empty mapping, but
alias-assisted matches may change.

### A known track is unmatched

Use this order:

1.  Confirm the track exists in the configured Plex Music library.
2.  Run `--refresh-cache`.
3.  Inspect trace `candidate source`.
4.  Check whether the artist was found.
5.  Check title candidate discovery.
6.  Inspect `unmatched.csv`.
7.  Inspect normalization behavior.
8.  Check whether an artist alias is appropriate.
9.  Only then consider matching logic or threshold changes.

Do not immediately lower the global threshold. Candidate discovery and
title gating happen before final acceptance.

### `artist found; no title match`

Check requested spelling, Plex title metadata, version suffixes, Unicode
differences, and cache freshness.

### Unexpected `Various Artists` fallback

Review:

``` text
Requested Artist
Matched Artist
Matched Album Artist
Matched Title
Filename Artist
Filename Title
Metadata Warnings
Reason
```

A correct filename artist combined with `Various Artists` Plex metadata
often indicates a metadata problem rather than a matching problem.

### `File Path` is blank

Set:

``` ini
[reports]
include_file_paths = true
```

### Cache refresh is slow

A refresh calls Plex `searchTracks()` and materializes the full Music
library. On the approximately 55,982-track baseline library, observed
refreshes took minutes; cached index loads took a few seconds. This is
expected.

### SQLite schema error after development changes

The cache is derived data and can be rebuilt.

1.  Preserve the failing DB if needed for debugging.
2.  Verify the code/schema change.
3.  Remove or rename the generated cache DB.
4.  Run a controlled `--refresh-cache --dry-run`.
5.  Re-run tests and baseline verification.

### Long floating-point scores return

Current reporting formats scores to one decimal place, for example:

``` text
100.0
51.4
56.4
57.3
```

If long float representations return, inspect `reporting.py` and confirm
the score formatter is used for all score columns.

### A dry run changes Plex

The intended dry-run boundary returns before match resolution and
playlist update. Treat any dry-run mutation as a critical regression.

## Support and Maintenance Notes

Recommended source reading order:

``` text
1. playlist_import_v2.py
2. plex_playlist/models.py
3. plex_playlist/parser.py
4. plex_playlist/normalization.py
5. plex_playlist/search_index.py
6. plex_playlist/matcher.py
7. plex_playlist/reporting.py
8. plex_playlist/cache.py
9. plex_playlist/plex_client.py
```

  Module                    Primary Responsibility
  ------------------------- ---------------------------------------------
  `playlist_import_v2.py`   CLI orchestration
  `models.py`               Data contracts and enums
  `parser.py`               Input parsing
  `normalization.py`        Comparison forms and version classification
  `search_index.py`         Candidate lookup
  `matcher.py`              Candidate processing, scoring, decisions
  `reporting.py`            Reports and metadata diagnostics
  `cache.py`                SQLite persistence
  `plex_client.py`          Plex API and playlist mutation
  `resources.py`            External resource loading
  `logging_config.py`       Logging initialization

Architectural boundaries:

-   Do not put fuzzy matching logic in `plex_client.py`.
-   Do not put Plex API calls in `matcher.py`.
-   Filename diagnostics must not influence matching unless
    intentionally redesigned and regression-tested.
-   Preserve original display metadata separately from normalized
    comparison data.
-   Keep aliases in `resources/aliases.txt`, not inline in `config.ini`.
-   Use `pathlib.Path` for project path handling.
-   Treat cache data as rebuildable.
-   Generate reports before playlist mutation.
-   Add regression tests before broad matcher tuning.

For a support issue, collect:

``` text
Python version
Operating system
Plex Media Server version
Input format
Exact command
Relevant config sections with token removed
Whether --refresh-cache was used
Matching summary
Affected entries
Relevant playlist_report.csv rows
Relevant unmatched.csv rows
Trace or debug output
Full stack trace
```

Never include a real Plex token in a public issue or diagnostic bundle.

## Known Baseline Limitations

1.  The executable remains named `playlist_import_v2.py`.
2.  Some source docstrings still refer to V2.
3.  `--sync` is additive and does not remove tracks absent from the
    input.
4.  Playlist mode options are not mutually exclusive.
5.  `--playlist` and `input_file` remain required for `--dedupe`.
6.  Some configuration fields exist but are not fully enforced by the
    current orchestrator.
7.  Cache schema migration is limited; development schema changes may
    require a cache rebuild.
8.  Filename diagnostics only parse `Artist - Title` filename stems.
9.  Filename diagnostics are advisory and do not repair Plex metadata.
10. The older README's HTML-report claims do not describe the verified
    current baseline.
11. Live write-path validation has been completed for the controlled
    integration cases documented above, but broader production-library
    behavior should still be introduced cautiously.


## Baseline Change Policy

Before a matching change:

``` powershell
python -m pytest -q

python playlist_import_v2.py playlist.txt `
    --playlist "Baseline TXT" `
    --dry-run
```

After the change, repeat both commands and explain every intentional
result difference.

The baseline does not prevent improvements. It makes improvements
measurable.

## Project Status

``` text
V3 baseline cleanup complete
TXT parser baseline verified
CSV parser baseline verified
TSV parser baseline verified
M3U parser baseline verified
13 automated tests passing
Unicode/accent normalization active
External artist alias resource active
SQLite search cache active
Filename metadata diagnostics active
CSV match reporting active
Duplicate library reporting active
CREATE integration validated
Existing-playlist CREATE rejection validated
UPDATE integration and summary counts validated
REPLACE integration and summary counts validated
Additive SYNC integration and summary counts validated
Exact-title playlist lookup protection active
```

The current V3 baseline is integration-validated for the documented
controlled write-path scenarios.
