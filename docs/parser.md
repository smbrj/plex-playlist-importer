# Parser Subsystem

**Document Version:** 1.0  
**Status:** Approved  
**Last Updated:** 2026-07-21  
**Primary Audience:** Developers  
**Depends On:** configuration.md  
**Related Documents:** normalization.md, matching.md, models.py  
**Snapshot:** 005

---

# 1. Purpose and Scope

The parser subsystem converts supported external playlist files into the application's standard `PlaylistEntry` representation.

Its primary purpose is to isolate file-format handling from the rest of the matching pipeline.

The parser is responsible for:

- Detecting the supported input format from the file extension.
- Reading playlist files safely.
- Extracting artist and title fields.
- Ignoring unusable individual rows where appropriate.
- Preserving source file and source line information.
- Creating ordered `PlaylistEntry` objects.
- Rejecting unsupported file formats.
- Rejecting missing or invalid input paths.

The parser is not responsible for:

- Artist or title normalization.
- Alias resolution.
- Plex matching.
- Fuzzy scoring.
- Deduplication policy.
- Playlist modification.
- Lidarr processing.
- XMPlaylist ingestion.

The parser boundary is:

```text
External Playlist File
        |
        v
parser.py
        |
        v
PlaylistEntry objects
(models.py)
        |
        v
Normalization / Matching Pipeline
```

The central design principle is:

> File-format differences should end at the parser boundary.

Once an entry becomes a `PlaylistEntry`, downstream matching should not need to know whether it originated from TXT, CSV, TSV, or M3U input.

---

# 2. Supported Input Formats

The current parser supports:

```text
.txt
.csv
.tsv
.m3u
```

The parser selects the implementation based on the lowercase file extension.

Conceptually:

```text
Input File
    |
    v
Read Extension
    |
    +---------+---------+---------+---------+
    |         |         |         |
   .txt      .csv      .tsv      .m3u
    |         |         |         |
    v         v         v         v
 parse_txt  parse_csv  parse_tsv parse_m3u
    |         |         |         |
    +---------+---------+---------+
              |
              v
       PlaylistEntry list
```

Unsupported extensions are rejected with a `ValueError`.

---

# 3. Parser Entry Point

The primary entry point is:

```python
parse_playlist_file(path)
```

Implementation:

```text
plex_playlist/parser.py
```

The function accepts either:

```text
str
Path
```

and returns:

```text
list[PlaylistEntry]
```

Before parsing, the function verifies that:

- The path exists.
- The path refers to a file.
- The file extension is supported.

If the file does not exist, `FileNotFoundError` is raised.

If the path exists but is not a file, `ValueError` is raised.

If the extension is unsupported, `ValueError` is raised with the supported extension list.

---

# 4. PlaylistEntry Contract

All parser implementations produce `PlaylistEntry` defined in `plex_playlist/models.py`.

The current model contains:

```text
sequence
artist
title
line_number
source
```

Conceptually:

```text
Source File Record
      |
      v
Parser
      |
      v
PlaylistEntry
      |
      +-- sequence
      +-- artist
      +-- title
      +-- line_number
      +-- source
```

`PlaylistEntry` is immutable through the use of a frozen dataclass.

This provides a stable application-level contract between parsing and downstream processing.

---

# 5. Sequence Numbers

The parser assigns a sequential application sequence number to each valid parsed entry.

The assigned sequence is based on the number of successfully parsed entries:

```text
first valid entry   -> sequence 1
second valid entry  -> sequence 2
third valid entry   -> sequence 3
```

Invalid or skipped input lines do not create gaps in the resulting sequence.

Original line location is retained separately through `line_number`.

---

# 6. Source Line Tracking

Each parsed `PlaylistEntry` records `line_number`, which identifies the physical line in the source file that produced the entry.

This distinction is important because `sequence` represents logical playlist order, while `line_number` supports traceability back to the original source file.

---

# 7. Source File Tracking

Each parsed entry also retains `source` as a `Path`.

This allows downstream reporting or diagnostics to identify the originating playlist file.

The parser therefore preserves enough provenance to answer:

```text
Which file did this entry come from?
Which line produced it?
```

without carrying format-specific parser details into later stages.

---

# 8. TXT Parsing

TXT files are parsed using `parse_txt()`.

Accepted examples include:

```text
001. Aretha Franklin - Respect
12 - Fleetwood Mac - Dreams
Prince - Purple Rain
```

The required logical format is:

```text
Artist - Title
```

with the delimiter `" - "` including surrounding spaces.

---

# 9. TXT Sequence Prefix Removal

Before splitting artist and title, TXT parsing removes a leading numeric sequence or track-number prefix.

Examples:

```text
1. Artist - Title
01 Artist - Title
001. Artist - Title
12 - Artist - Title
```

are reduced to:

```text
Artist - Title
```

The helper responsible for this behavior is `_strip_track_number()`.

The numeric prefix is not preserved as the resulting `PlaylistEntry.sequence`.

The parser assigns its own contiguous sequence number based on successfully parsed entries.

---

# 10. TXT Invalid-Line Behavior

TXT parsing skips lines that cannot produce both an artist and title.

Skipped examples include:

```text
blank line
This line has no delimiter
 - Missing Artist
Missing Title - 
```

Invalid individual lines do not cause the entire playlist parse to fail.

This allows partially imperfect source files to remain usable.

---

# 11. CSV Parsing

CSV input is handled by `parse_csv()`, which delegates to the shared `_parse_delimited()` helper using `delimiter=","`.

Expected logical format:

```text
Artist,Title
```

A header row is optional.

---

# 12. CSV Header Handling

The parser recognizes conventional artist/title header names.

Artist header values currently recognized include:

```text
artist
requested artist
```

Title header values include:

```text
title
track
track title
song
song title
requested title
```

Header detection is case-insensitive through `casefold()`.

---

# 13. CSV Without Header

CSV files do not require a header.

The first valid row becomes sequence 1 and subsequent valid rows are numbered sequentially.

---

# 14. Additional CSV Columns

CSV input may contain more than two columns.

Only the first two columns are interpreted as artist and title.

Additional columns are ignored by the parser.

---

# 15. TSV Parsing

TSV input is handled by `parse_tsv()` using the same shared delimited parser as CSV, with a tab delimiter.

The same header detection and invalid-row handling used for CSV also apply to TSV.

---

# 16. Unicode Handling

TXT, CSV, TSV, and M3U files are opened using:

```text
encoding = utf-8-sig
errors = replace
```

`utf-8-sig` allows UTF-8 files containing a Byte Order Mark to be parsed without exposing the BOM as part of the first field.

Unicode artist names are supported.

Invalid byte sequences are replaced rather than causing parsing to fail.

---

# 17. CSV and TSV Reader Behavior

CSV and TSV parsing use Python's standard `csv.reader`.

Files are opened with `newline=""`.

Rows containing fewer than two columns are ignored.

Rows containing an empty artist or empty title are also ignored.

---

# 18. M3U Parsing

Extended M3U input is handled by `parse_m3u()`.

The parser uses `#EXTINF` metadata records.

The parser extracts the `Artist - Title` metadata from `#EXTINF` records.

---

# 19. M3U Media Paths

The actual media path following an `#EXTINF` line is not used for matching.

The matching pipeline operates from artist and title rather than from source filesystem paths.

This is an intentional parser boundary.

---

# 20. M3U Metadata Processing

For each M3U line, the parser:

- Ignores non-`#EXTINF` lines.
- Requires a comma.
- Extracts metadata after the comma.
- Requires `" - "`.
- Splits artist and title.
- Rejects empty artist/title fields.
- Creates a `PlaylistEntry`.

The source line number recorded for an M3U entry is the line containing `#EXTINF`, not the following media path.

---

# 21. Delimiter Behavior

TXT and M3U use `" - "` as the artist/title separator.

Only the first delimiter occurrence is used.

CSV and TSV use their respective structured delimiters and do not rely on `" - "`.

---

# 22. Whitespace Handling

Parsed artist and title values are stripped of leading and trailing whitespace.

Whitespace normalization beyond leading and trailing trimming is not a parser responsibility.

More advanced textual normalization belongs to `normalization.py`.

---

# 23. Invalid Record Philosophy

The parser distinguishes between file-level failure and record-level invalid input.

File-level failures are generally raised as errors.

Examples:

- File does not exist.
- Path is not a regular file.
- Unsupported file extension.

Record-level problems are generally skipped.

Examples:

- Missing delimiter.
- Empty artist.
- Empty title.
- Too few CSV/TSV columns.
- Invalid M3U metadata line.

This design allows imperfect playlist files to produce useful results without hiding fundamental input-file errors.

---

# 24. Validation Helper

The module contains `validate_tracks()`.

This helper returns only entries containing both a non-empty artist and title.

The individual parsers already enforce these requirements.

Therefore, `validate_tracks()` is retained primarily for callers that perform validation independently of the built-in parser flow.

---

# 25. Debug Helper

The module also contains `debug_print_tracks()`.

This helper prints a limited sample of parsed playlist entries.

Default limit:

```text
10 entries
```

This helper is diagnostic and is not part of the normal parsing pipeline.

---

# 26. Relationship to Normalization

The parser intentionally performs only limited cleanup.

It handles:

- File decoding.
- Structural field extraction.
- Leading/trailing whitespace removal.
- TXT numeric-prefix removal.
- Header recognition.

It does not perform advanced normalization such as:

- Remaster suffix handling.
- Live-version normalization.
- Featured-artist normalization.
- Case normalization for matching.
- Punctuation normalization.
- Alias substitution.

Those responsibilities belong downstream.

---

# 27. Relationship to Matching

For file-based playlist input, the orchestrator performs:

```text
Input File
    |
    v
parse_playlist_file()
(parser.py)
    |
    v
list[PlaylistEntry]
    |
    v
run_matcher_entries()
    |
    v
match_playlist()
(matcher.py)
```

The matcher receives the same `PlaylistEntry` model regardless of file format.

---

# 28. Relationship to XMPlaylist

XMPlaylist does not use the file parser.

Instead, `xmplaylist_source.py` produces `PlaylistEntry` objects directly.

Both paths converge on the same model before matching.

---

# 29. Error Handling

The parser explicitly raises errors for unsupported or invalid file-level input.

Malformed individual records do not normally raise exceptions.

They are skipped.

---

# 30. Testing

Parser behavior is covered by:

```text
tests/test_parser.py
```

Current verified tests include:

- Numbered TXT parsing.
- TXT invalid-line skipping.
- CSV with header.
- CSV without header.
- TSV delimiter and Unicode handling.
- Extended M3U parsing.
- Unsupported extension rejection.
- Missing-file rejection.

Representative command:

```bash
python -m pytest tests/test_parser.py -v
```

Before significant parser changes:

```bash
python -m pytest -v
```

---

# 31. Current Test Examples

Verified parser tests cover numbered TXT, invalid TXT rows, CSV with/without header, Unicode TSV input, and extended M3U metadata parsing.

The parser preserves title metadata such as remaster text and leaves interpretation of such text to downstream normalization/matching.

---

# 32. Parser Design Characteristics

The parser subsystem is intentionally simple.

Its design favors:

- Predictable supported formats.
- Small format-specific parsers.
- Shared CSV/TSV logic.
- Source traceability.
- Tolerance of invalid individual records.
- Strict rejection of invalid file-level input.
- Minimal transformation before normalization.
- A common downstream data model.

---

# 33. Post-Documentation Technical Review Candidates

Potential review candidates include:

## 33.1 Silent Invalid-Line Skipping

Optional logging or reporting of skipped lines may improve troubleshooting.

## 33.2 Input-Encoding Policy

Replacement characters can conceal encoding problems; future diagnostics may be useful.

## 33.3 Header Recognition

Additional real-world header aliases may be added if justified.

## 33.4 Additional Formats

Additional formats should be added only where there is a clear use case and should continue producing the same `PlaylistEntry` model.

---

# 34. Future Considerations

Potential future parser improvements include:

- Optional invalid-row diagnostics.
- Summary counts of parsed versus skipped records.
- More explicit encoding diagnostics.
- Additional recognized header labels.
- Additional supported formats where justified.
- Dedicated parser-health metrics for future dashboard use.

Future parser changes should preserve the architectural rule:

> The parser should convert external file structure into clean `PlaylistEntry` objects while leaving normalization, matching, and acquisition decisions to downstream subsystems.
