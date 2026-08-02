# TIDAL Integration

Plex Playlist Importer (PPI) can optionally integrate with TIDAL to provide access to tracks that are not available in the local Plex music library.

TIDAL integration is optional. PPI can operate normally with Plex alone or with other optional integrations without enabling TIDAL.

## Overview

PPI uses TIDAL as a companion to the local Plex music library.

When processing a playlist:

* Tracks available in Plex are placed in the Plex playlist.
* Tracks that cannot be matched in Plex can be searched for in TIDAL.
* Successfully matched TIDAL tracks are placed in a TIDAL companion playlist.
* PPI can also add tracks that it places in a companion playlist to the user's TIDAL favorites.
* The Plex and TIDAL playlists use the same playlist name.

For example, if PPI processes a playlist named:

```text
Ch 14 - The Bridge
```

tracks available locally are maintained in the Plex playlist named `Ch 14 - The Bridge`, while tracks supplied by TIDAL are maintained in the TIDAL companion playlist with the same name.

PPI does not download TIDAL subscription content into Plex.

---

# Requirements

To use the TIDAL integration, you need:

* A TIDAL account with a paid subscription.
* A TIDAL developer application.
* The application's client ID and client secret.
* TIDAL integration enabled in PPI's `config.ini`.
* Initial user authorization completed successfully.

---

# Creating a TIDAL Developer Application

Sign in to the TIDAL developer dashboard using your TIDAL account and create an application.

The application name is not used by PPI for API authentication and does not need to have a particular value. `ppi` is a suggested application name for clarity.

Configure the application with this redirect URI:

```text
http://127.0.0.1:8765/callback
```

PPI has been developed and validated using the following TIDAL application scopes:

```text
collection.read
collection.write
entitlements.read
playlists.read
playlists.write
recommendations.read
search.read
search.write
user.read
```

The `playback` scope is not required by PPI.

After saving the application configuration, allow some time for the new application credentials and permissions to propagate through TIDAL's systems. In testing, newly created credentials have sometimes required a few hours before they worked reliably.

Record the application's:

```text
client_id
client_secret
```

and store them securely.

Do not publish these credentials or commit a populated `config.ini` containing them to a public source-code repository.

---

# PPI Configuration

The TIDAL configuration is located in the `[tidal]` section of `config.ini`.

A typical configuration is:

```ini
[tidal]

enabled = true
allow_explicit = true

client_id = CLIENT_ID_HERE
client_secret = CLIENT_SECRET_HERE

country_code = US
timeout = 20

hydration_delay_seconds = 0.25

user_token_file = cache/tidal_user_tokens.json
redirect_uri = http://127.0.0.1:8765/callback
authorization_timeout_seconds = 180

cache_enabled = true
cache_database = cache/tidal_search_cache.db
state_database = cache/tidal_state.db
cache_max_age_hours = 24

quality_preference = DOLBY_ATMOS,HIRES_LOSSLESS,LOSSLESS,HIGH,LOW
```

## enabled

```ini
enabled = true
```

Enables TIDAL integration.

Set this to `false` if TIDAL should not participate in normal PPI processing.

## allow_explicit

```ini
allow_explicit = true
```

Controls whether PPI may select TIDAL tracks marked as explicit by TIDAL.

When set to:

```text
true
```

explicit and non-explicit recordings may be considered.

When set to:

```text
false
```

explicit recordings are rejected during TIDAL candidate selection.

The explicit-content policy is included in PPI's TIDAL search-cache key so a result obtained under one policy does not incorrectly satisfy a lookup performed under the other policy.

## client_id and client_secret

```ini
client_id = CLIENT_ID_HERE
client_secret = CLIENT_SECRET_HERE
```

Credentials assigned to the application created in the TIDAL developer dashboard.

These values should be treated as private credentials.

## country_code

```ini
country_code = US
```

Specifies the TIDAL catalog country used for API requests.

Catalog availability can vary by country.

## timeout

```ini
timeout = 20
```

HTTP timeout, in seconds, used for TIDAL catalog API requests.

## hydration_delay_seconds

```ini
hydration_delay_seconds = 0.25
```

Controls the delay between TIDAL candidate-detail requests.

TIDAL search results may initially contain incomplete metadata. PPI retrieves additional track information for title-matching candidates before making its final matching decision. Sending these detail requests too quickly can cause TIDAL to respond with HTTP `429 Too Many Requests`.

A default delay of:

```text
0.25 seconds
```

has been validated to reduce these rate-limit responses.

This delay applies only between candidate hydration/detail requests. It does not intentionally delay unrelated TIDAL operations.

The default should normally be left unchanged.

If repeated HTTP 429 responses occur during TIDAL candidate hydration, increasing this value may reduce the request rate.

## user_token_file

```ini
user_token_file = cache/tidal_user_tokens.json
```

Stores the TIDAL user authorization tokens used by PPI.

This file should be treated as private application data and should not be committed to a public repository.

## redirect_uri

```ini
redirect_uri = http://127.0.0.1:8765/callback
```

OAuth callback address used during TIDAL user authorization.

The value configured here must match the redirect URI configured for the TIDAL developer application.

## authorization_timeout_seconds

```ini
authorization_timeout_seconds = 180
```

Controls how long PPI waits for completion of the interactive authorization process.

## cache_enabled

```ini
cache_enabled = true
```

Enables PPI's TIDAL catalog search cache.

Caching reduces unnecessary TIDAL API searches and helps reduce API traffic.

## cache_database

```ini
cache_database = cache/tidal_search_cache.db
```

SQLite database containing cached TIDAL catalog search results.

## state_database

```ini
state_database = cache/tidal_state.db
```

SQLite database containing PPI's TIDAL companion-playlist and ownership state.

This state is important for safe reconciliation of TIDAL playlists and favorites.

Do not manually synchronize this database between separate PPI installations or operating systems.

Each independent PPI installation should maintain its own TIDAL state.

## cache_max_age_hours

```ini
cache_max_age_hours = 24
```

Controls how long a TIDAL search result remains valid in the search cache.

The current default is 24 hours.

## quality_preference

```ini
quality_preference = DOLBY_ATMOS,HIRES_LOSSLESS,LOSSLESS,HIGH,LOW
```

Defines PPI's preferred TIDAL recording qualities in descending order.

When multiple otherwise acceptable recordings are available, PPI uses this preference to select among them.

The configured values reflect quality metadata returned by the TIDAL API. They may not use exactly the same terminology displayed by TIDAL's web or desktop applications.

For example, a recording displayed differently in the TIDAL user interface may be returned through the API with:

```text
HIRES_LOSSLESS,LOSSLESS
```

---

# Initial TIDAL Authorization

TIDAL playlist and favorites operations require authorization to the user's TIDAL account.

After configuring the developer application and entering the credentials in `config.ini`, complete PPI's TIDAL user authorization process.

PPI uses the configured local callback:

```text
http://127.0.0.1:8765/callback
```

During authorization, the user signs in to TIDAL and grants the permissions requested by the registered application.

The resulting authorization information is stored in:

```text
cache/tidal_user_tokens.json
```

PPI can subsequently refresh its authorization without requiring interactive login for every run.

The refresh-token request includes the configured TIDAL `client_id`.

---

# Matching Behavior

TIDAL processing occurs after PPI has attempted to match the requested track against the Plex library.

Only tracks that remain unmatched in Plex are candidates for TIDAL catalog resolution.

PPI evaluates TIDAL candidates using artist and track-title information and applies its recording-version and explicit-content rules before selecting a track.

Album name is useful diagnostic metadata but is not required to establish the TIDAL artist/title match.

PPI accepts appropriate studio recordings and supported recording variations while rejecting unsuitable candidates such as live, demo, acoustic, instrumental, or other non-studio versions when they do not satisfy the matching policy.

Configured artist aliases may also participate in matching.

---

# Candidate Hydration

TIDAL catalog searches can return candidates with incomplete metadata.

For candidates whose titles are relevant to the requested track, PPI retrieves the full track details before making the final matching decision. This process is referred to as candidate hydration.

Hydration can provide metadata such as:

* Artist
* Album
* Recording quality
* Explicit-content status
* Recording version

PPI deliberately limits hydration to title-relevant candidates rather than retrieving details for every search result.

Candidate hydration requests are paced using:

```ini
hydration_delay_seconds = 0.25
```

to reduce the chance of triggering TIDAL API rate limits.

---

# Hydration Failures and HTTP 429 Responses

TIDAL may occasionally reject candidate-detail requests with:

```text
HTTP 429 Too Many Requests
```

A candidate whose detail request fails may not contain enough artist or album metadata for PPI to safely determine whether it is a valid match.

PPI treats this situation as **inconclusive**, rather than as a confirmed TIDAL catalog miss.

For example:

```text
TIDAL resolution inconclusive: Ozzy Osbourne - Bark At The Moon;
candidate hydration failed for track(s) ...;
NO_MATCH was not cached
```

When this occurs:

* PPI does not accept the incomplete candidate.
* The hydration failure is included in the unmatched diagnostic report.
* PPI does **not** write a negative `NO_MATCH` result to the TIDAL search cache.
* A later PPI run is therefore allowed to search TIDAL again.

This prevents a temporary API or rate-limit failure from becoming a persistent false-negative result.

---

# TIDAL Search Cache

PPI stores TIDAL catalog results in:

```text
cache/tidal_search_cache.db
```

Both successful matches and confirmed catalog misses may be cached.

With the default configuration, entries expire after:

```text
24 hours
```

A cached result reduces unnecessary repeated API traffic.

A cached negative result may appear in the log as:

```text
TIDAL no match: Artist - Track (cache)
```

A fresh API lookup appears as:

```text
TIDAL no match: Artist - Track (api)
```

Hydration failures are not stored as negative cache results.

The PPI housekeeping utility can remove expired TIDAL search-cache entries.

---

# Companion Playlists

When PPI finds a suitable TIDAL match for a track that is unavailable in Plex, it maintains a TIDAL companion playlist.

The companion uses the same playlist name requested for Plex.

PPI can:

* Create the companion playlist.
* Reuse an existing PPI companion playlist.
* Add newly required TIDAL tracks.
* Avoid adding duplicate tracks.
* Track playlist membership in its local state database.
* Add companion tracks to the user's TIDAL favorites.
* Reconcile tracks that are no longer required.

Playlist and favorite state are tracked independently.

---

# TIDAL Favorites

Tracks added to a PPI companion playlist may also be added to the user's TIDAL favorites.

PPI records whether it can establish that a favorite was created by PPI.

This ownership information is important when a track later becomes stale.

PPI will not automatically delete a favorite that it cannot prove it owns.

This protects favorites that may have been added manually by the user or by another application.

---

# Plex-to-TIDAL Reconciliation Safety

PPI uses a conservative handoff policy when moving responsibility for a track between Plex and TIDAL.

Destructive TIDAL reconciliation is deferred until the corresponding Plex playlist update has completed successfully.

Before removing a stale TIDAL track, PPI verifies the final Plex playlist state when the handoff depends on a Plex replacement.

If the final Plex playlist does not contain the expected replacement, destructive TIDAL removal is suppressed.

This protects against losing a track from both services because of a failed Plex update or playlist-trimming operation.

---

# Multiple PPI Installations

Each PPI installation maintains its own local TIDAL state.

For example, a Windows development installation and an Unraid production installation can both use the same TIDAL account while maintaining different:

```text
cache/tidal_state.db
```

databases.

These databases should **not** be synchronized between installations.

Because each installation can only prove ownership based on its own recorded history, one installation may encounter a track or favorite created by another installation and classify it as user-owned or externally owned.

This is expected conservative behavior.

Using different test playlist names between development and production installations is recommended.

---

# TIDAL Reports

PPI produces timestamped TIDAL diagnostic reports in the configured reports directory.

## Matched report

Successful TIDAL catalog matches are written to files using the naming convention:

```text
tidal-matched-MMDDHHMM.csv
```

Example:

```text
tidal-matched-07251755.csv
```

These reports identify the TIDAL track selected for an unmatched Plex track.

## Unmatched report

TIDAL catalog misses and rejected candidates are written to:

```text
tidal-unmatched-MMDDHHMM.csv
```

Example:

```text
tidal-unmatched-07251625.csv
```

The unmatched report is intended primarily for troubleshooting cases where a track can be found manually in TIDAL but PPI did not select it.

Candidate-level information includes:

```text
requested_artist
requested_title
search_title
search_source
candidate_count
candidate_number
tidal_url
candidate_artist
candidate_title
candidate_album
candidate_quality
available_candidate_qualities
candidate_explicit
decision
rejection_reason
```

Typical rejection reasons include:

```text
artist metadata missing
artist mismatch
track mismatch
non-studio recording
explicit content rejected by configuration
```

If no candidates are returned by the TIDAL API, the report records:

```text
NO_CANDIDATES
```

If PPI encounters an existing negative cache entry, candidate details from the original API lookup are not retained. The report therefore records:

```text
CACHED_NO_MATCH
```

with an explanation that candidate diagnostics are unavailable from the cached result.

If candidate hydration fails, the affected candidate is reported as:

```text
INCONCLUSIVE_HYDRATION
```

and the failed result is not negative-cached.

---

# Understanding TIDAL Quality Information

PPI reports the quality metadata supplied by the TIDAL API.

Examples include:

```text
DOLBY_ATMOS
HIRES_LOSSLESS
LOSSLESS
HIGH
LOW
```

Some tracks may advertise more than one quality tag:

```text
HIRES_LOSSLESS,LOSSLESS
```

PPI does not currently report an exact bitrate, sample rate, or bit depth from this catalog-search path.

The quality terminology displayed in the TIDAL website or application may differ from the API quality tags reported by PPI.

---

# Troubleshooting

## Track exists in TIDAL but PPI reports no match

Check the most recent:

```text
tidal-unmatched-*.csv
```

Find the requested artist and track and review:

```text
candidate_artist
candidate_title
candidate_album
candidate_quality
decision
rejection_reason
```

The report should indicate whether the candidate was rejected because of metadata, artist/title matching, recording version, explicit-content policy, or candidate hydration.

## Report shows CACHED_NO_MATCH

PPI reused a previous negative search result.

Candidate-level information is not retained for negative cache entries.

The entry will become eligible for another API search after the configured cache lifetime expires.

## Report shows INCONCLUSIVE_HYDRATION

PPI found a potentially relevant search candidate but could not retrieve enough track detail to safely evaluate it.

The result is deliberately not negative-cached.

A later run will be able to retry the TIDAL lookup.

Repeated occurrences accompanied by HTTP 429 responses may indicate that candidate-detail requests are arriving too quickly.

The default:

```ini
hydration_delay_seconds = 0.25
```

should normally be sufficient. If repeated 429 responses continue, the value can be increased to further reduce the request rate.

## TIDAL authorization fails

Verify:

* `client_id`
* `client_secret`
* TIDAL developer-application permissions
* Redirect URI
* TIDAL subscription status

The configured redirect URI must match:

```text
http://127.0.0.1:8765/callback
```

if that is the value used in `config.ini`.

Newly created TIDAL developer credentials may require some time to propagate before they work reliably.

## PPI refuses to remove a TIDAL favorite

PPI uses conservative ownership tracking.

If PPI cannot prove that it originally created the favorite, it preserves the favorite rather than risk deleting user-owned content.

This behavior is intentional.

---

# Backup and Housekeeping

Important TIDAL runtime data is stored below PPI's `cache` directory, including:

```text
tidal_user_tokens.json
tidal_search_cache.db
tidal_state.db
```

The state and authorization files should be included in normal application backups.

For an Unraid installation under:

```text
/mnt/user/appdata/plex-playlist-importer
```

these files are included when the PPI application directory is protected by the normal appdata backup process.

PPI also provides housekeeping utilities for removing expired TIDAL search-cache entries and old timestamped reports.

Housekeeping recognizes both current report names:

```text
tidal-matched-*.csv
tidal-unmatched-*.csv
```

and the older legacy matched-report pattern:

```text
tidal-matched=*.csv
```

so reports created before the filename change can age out normally.

---

# Platform Support

PPI is written in Python and is not limited to Unraid.

TIDAL integration can be used on any operating system capable of running the supported Python environment and satisfying PPI's dependencies.

Unraid is the developer's current preferred production platform, but it is not a requirement for using PPI or its TIDAL integration.
