# Reporting Subsystem

**Document Version:** 1.0  
**Status:** Approved  
**Last Updated:** 2026-07-21  
**Primary Audience:** Developers and Operators  
**Depends On:** matching.md  
**Related Documents:** plex.md, lidarr.md, aliases.md, analytics.md, configuration.md  
**Snapshot:** 008

---

# 1. Purpose and Scope

The reporting subsystem provides persistent, human-readable output describing what the Plex Playlist Importer did during an execution and why individual tracks produced particular outcomes.

Reporting is an operational feature of the application rather than merely a debugging convenience.

The subsystem provides visibility into areas including:

- Playlist matching results.
- Unmatched tracks.
- Lidarr investigation and search outcomes.
- Duplicate-library analysis.
- Plex artist inventory.
- Artist-alias suggestions.
- Alias auditing.
- Other library-intelligence operations.

Reports allow an operator to inspect application behavior without examining source code or relying exclusively on log files.

The governing principle is:

> Important application decisions should be observable after the execution completes.

---

# 2. Responsibilities

The reporting subsystem is responsible for:

- Converting application results into persistent report files.
- Preserving requested artist/title information.
- Recording Plex match information.
- Recording match score and confidence information where applicable.
- Recording explanatory match reasons or notes.
- Separating matched and unmatched outcomes where appropriate.
- Producing Lidarr diagnostic information for unmatched tracks.
- Producing duplicate-library analysis.
- Producing artist and alias intelligence reports.
- Writing report files to configured or command-line-selected paths.
- Creating output that can be reviewed with ordinary spreadsheet tools.

The reporting subsystem is not responsible for determining match scores, selecting Plex candidates, performing normalization, searching Lidarr, modifying Plex playlists, refreshing the Plex cache, deciding XMPlaylist ingestion limits, maintaining application logs, or providing the future application-health dashboard.

---

# 3. Reporting Philosophy

Reports and logs serve related but different purposes.

Logs describe application execution as it happens.

Reports describe structured results that remain useful after execution.

A user investigating a particular track should normally be able to use the generated report rather than reconstructing the result from many log entries.

---

# 4. Current Report Format

The current released reporting model is primarily:

```text
CSV
```

CSV is intentionally used because it is human-readable, easy to archive, easy to inspect with a text editor, easy to open in spreadsheet applications, easy to process with scripts, suitable for filtering and sorting, and portable between Windows and Linux.

---

# 5. HTML Reporting

HTML reporting is **not currently implemented**.

The current released reporting model is CSV-based.

HTML reporting may be considered for a future release if it provides useful presentation or navigation capabilities beyond the existing CSV reports and planned operational dashboard.

Until such functionality is intentionally implemented and released:

- HTML output should not appear in current user procedures.
- Configuration should not imply that an HTML report will be generated.
- Dependencies related to HTML generation should not be interpreted as evidence of current functionality.
- Current documentation should describe CSV as the supported report format.

If HTML reporting is introduced in a future release, this document should be updated to describe its purpose, output location, configuration, and relationship to CSV reporting.

---

# 6. Primary Match Report

The primary playlist matching report is selected with:

```text
--report
```

The current default path is:

```text
playlist_report.csv
```

The full match report represents the outcome of the matching process for requested playlist entries.

---

# 7. Match Report Purpose

The full match report should provide enough information to determine:

- Which source entry was processed.
- Whether it matched Plex.
- Which Plex track was selected.
- The match score.
- The confidence classification.
- The reason for the match decision.
- Relevant source metadata.
- Relevant matched Plex metadata.

The reporting subsystem serializes values already determined by the matcher.

---

# 8. MatchResult as Reporting Source

The reporting subsystem consumes matching results rather than reproducing matching logic.

A report should reflect values already determined by the matcher, such as score, confidence, reason, and matched track.

This separation prevents report generation from independently interpreting whether a track should have matched.

---

# 9. Match Reason

The match reason is important for troubleshooting.

A numerical score alone may not explain why a particular candidate was selected or rejected.

The reason field can provide context concerning exact normalized matches, alias-assisted matching, candidate scoring, threshold failures, title-gate failures, and other matcher decisions.

---

# 10. Confidence Labels

Where the matching result provides a confidence classification, the report preserves it.

Confidence labels make it easier to distinguish high-confidence matches from borderline or lower-confidence matches without interpreting raw score values manually.

Confidence is generated by the matching subsystem and should not be recalculated by reporting code.

---

# 11. Unmatched Report

Tracks that do not receive an acceptable Plex match can be written separately through:

```text
--unmatched
```

The current default path is:

```text
unmatched.csv
```

This report provides a focused inventory of requested tracks requiring additional attention.

---

# 12. Purpose of the Unmatched Report

The unmatched report supports:

- Manual library review.
- Alias investigation.
- Lidarr investigation.
- Metadata troubleshooting.
- Identifying missing music.
- Feeding alias-suggestion tooling.

---

# 13. Full Report Versus Unmatched Report

The full match report provides the overall matching outcome for playlist entries.

The unmatched report provides a focused work list containing entries that could not be matched acceptably.

The unmatched report should not be treated as a replacement for the full match report.

---

# 14. Report Generation During Dry Run

The `--dry-run` option matches tracks and generates reports without changing Plex.

This makes dry-run mode useful for validating matching behavior before changing Plex.

---

# 15. Reporting During Plex Degradation

The application architecture allows useful work to continue when Plex modification is unavailable but a usable local cache exists.

The importer may still parse input, perform matching against cached metadata, generate reports, identify unmatched tracks, and perform optional downstream analysis where available.

The inability to modify Plex should not automatically prevent useful report generation.

---

# 16. Lidarr Report

Lidarr diagnostics use a separate report selected with:

```text
--lidarr-report
```

The current default path is:

```text
lidarr_unmatched_report.csv
```

The Lidarr report is implemented separately from the primary Plex matching report because it describes a different stage of processing.

---

# 17. Lidarr Report Purpose

The Lidarr report should provide enough information to understand the original unmatched track, relevant Plex match information, whether Lidarr resolution succeeded, whether a matching album was identified, whether an album search was requested, whether retry policy prevented another search, and relevant Lidarr status information.

The report must preserve the distinction between a search being requested and media actually being acquired.

---

# 18. Plex Match Notes in Lidarr Reporting

The Lidarr report includes a field identified as:

```text
plex match notes
```

This field belongs to the Plex matching context and should not be interpreted as describing Lidarr acquisition success.

---

# 19. Duplicate-Library Report

The importer supports:

```text
--dedupe
```

The output path is selected using:

```text
--output
```

with the current default:

```text
duplicates.csv
```

The duplicate report is generated from cached library tracks.

---

# 20. Duplicate Report Purpose

The duplicate report helps identify multiple Plex library records that represent the same or similar logical music.

The presence of multiple records is not automatically an error.

The report provides visibility so the operator can determine whether duplicates are intentional.

---

# 21. Plex Artist Inventory Report

The application provides:

```text
--export-artists
```

The output path is controlled through:

```text
--artists-output
```

with the current default:

```text
reports/plex_artists.csv
```

This report supports alias discovery and general library inspection.

---

# 22. Artist Inventory Purpose

The artist inventory allows the operator to inspect how artist names actually appear in Plex.

This is useful when diagnosing variations such as `Doobie Brothers` versus `The Doobie Brothers`.

---

# 23. Alias Suggestion Report

The application provides:

```text
--suggest-aliases
```

The current output option is:

```text
--alias-suggestions-output
```

with the default:

```text
reports/aliases_suggested.csv
```

This workflow uses unmatched data to identify possible alias relationships.

---

# 24. Alias Suggestion Review Workflow

Alias suggestions are intended for operator review before import into `resources/aliases.txt`.

This preserves a human-in-the-loop workflow rather than automatically changing artist equivalence rules.

---

# 25. Alias Audit Report

The application provides:

```text
--audit-aliases
```

The output path is controlled through:

```text
--alias-audit-output
```

with the current default:

```text
reports/alias_audit.csv
```

The audit provides visibility into configured aliases and observed use.

---

# 26. Reporting and Alias Intelligence

Alias-related reports answer different questions:

```text
plex_artists.csv
    = What artist names exist in Plex?

aliases_suggested.csv
    = What possible alias relationships should be reviewed?

alias_audit.csv
    = How are configured aliases resolving and being used?
```

---

# 27. Report Path Configuration

Reporting paths may come from application configuration or execution-specific command-line options depending on the workflow.

Persistent report-location preferences belong in configuration; execution-specific output overrides belong on the command line.

---

# 28. Current CLI Reporting Paths

Current command-line report/output controls include:

```text
--report
--unmatched
--lidarr-report
--output
--artists-output
--alias-suggestions-output
--alias-audit-output
```

---

# 29. Output Directory Handling

Report writers should ensure that required parent directories exist where the current implementation supports this behavior.

Where directory-creation behavior differs among report writers, it should be standardized during technical cleanup.

---

# 30. CSV Header Stability

CSV reports may be consumed by spreadsheet workflows, manual review, follow-on utilities, alias tooling, and future automation.

Report column names should therefore be treated as a lightweight interface.

Changes to headers should be deliberate and regression-tested where downstream tooling depends on them.

---

# 31. Example of Header Evolution

The Lidarr report previously used a generic `notes` field.

It was changed to:

```text
plex match notes
```

to make the field's responsibility explicit.

---

# 32. Report Ordering

Where reports correspond to playlist entries, source sequence should normally be preserved.

This makes it easier to compare the source playlist with the generated report.

---

# 33. Original Metadata Preservation

Reports should preserve human-readable original metadata wherever practical.

Normalized comparison strings are useful internally but are generally less useful as the primary report representation.

---

# 34. Matched Plex Metadata

For successful matches, the full report should expose enough Plex metadata to identify the selected library track and understand differences from requested metadata.

---

# 35. Reporting and Secrets

Reports must not contain authentication secrets such as Plex tokens, Lidarr API keys, or other service credentials.

---

# 36. Reporting and Logs

Reports should not duplicate the complete application log.

Reports contain structured results; logs contain execution history and diagnostics.

---

# 37. Reporting and Analytics

Operational reports describe a particular execution or analysis operation.

Historical analytics provide longer-lived aggregate information across executions.

Detailed analytics behavior belongs in `analytics.md`.

---

# 38. Reporting and Future Dashboard

The planned dashboard is not a replacement for persistent reports.

CSV reports remain useful for detailed track-level inspection, archival, spreadsheet analysis, troubleshooting, and external processing.

---

# 39. Failure Behavior

If a required report cannot be written because of an invalid path, permission failure, filesystem failure, or disk-space problem, the application should report the failure clearly.

It should not silently claim successful report generation.

---

# 40. Partial-System Failure

Reporting should preserve useful results even when optional external components fail.

A Lidarr failure should not prevent normal Plex matching reports from existing.

A Plex modification failure should not prevent report generation when matching can continue from a usable cache.

---

# 41. Current Test Coverage

Reporting-related coverage currently exists primarily through subsystem and integration tests rather than one comprehensive reporting test module.

A complete report-writer coverage audit should be performed during the later `testing.md` review.

---

# 42. Recommended Reporting Tests

Reporting tests should verify:

- Report file creation.
- Correct CSV headers.
- Matched-row serialization.
- Unmatched-row serialization.
- Empty-result behavior.
- Unicode output.
- Parent-directory creation.
- Stable source ordering.
- Confidence and reason serialization.
- Lidarr status serialization.
- Duplicate-report generation.
- Artist inventory generation.
- Alias suggestion output.
- Alias audit output.
- Proper CSV quoting.
- No credentials written to reports.

---

# 43. Post-Documentation Technical Review Candidates

## 43.1 Audit Reporting Test Coverage

Identify every current report writer and confirm direct test coverage.

## 43.2 Verify Report Directory Creation

Confirm that every report writer consistently creates required parent directories or fails with a clear diagnostic.

## 43.3 Verify Current [reports] Configuration Usage

Compare released `[reports]` settings against the actual orchestrator.

Unused or historical report settings should be implemented, deprecated, or removed.

## 43.4 Review HTML-Related Configuration and Dependencies

Verify that no active configuration keys, dependencies, comments, or documentation imply that HTML reporting is currently supported.

Remove obsolete items where appropriate.

Retain HTML reporting only as a future-release consideration unless and until it is intentionally implemented.

## 43.5 Define Report Schema Stability Expectations

Identify which CSV schemas function as internal interfaces and protect important headers with regression tests.

## 43.6 Standardize Report Failure Semantics

Review whether all report writers handle filesystem/write failures consistently.

A required report failure should not be silently ignored.

---

# 44. Operational Troubleshooting

When a report appears incomplete or incorrect:

1. Confirm the expected report option and output path.
2. Confirm the output directory exists or can be created.
3. Review application logs for report-write errors.
4. Confirm the matching session contains the expected entries.
5. Confirm matched versus unmatched classification.
6. Compare original source metadata.
7. Compare selected Plex metadata.
8. Review match score, confidence, and reason.
9. For Lidarr reports, distinguish Plex match notes from Lidarr status.
10. For alias reports, confirm the expected alias resource file was loaded.
11. Confirm the report is from the current execution.
12. Review filesystem permissions if the file was not updated.

---

# 45. Design Characteristics

The reporting subsystem is designed around:

- CSV-first operational output.
- Human-readable results.
- Spreadsheet compatibility.
- Separation from logging.
- Preservation of source metadata.
- Visibility into match decisions.
- Dedicated reports for specialized workflows.
- Graceful-degradation support.
- Configuration-driven output locations where applicable.
- Stable report schemas where downstream tooling depends on them.

---

# 46. Future Considerations

Potential future improvements include:

- More comprehensive direct report-writer tests.
- Formal report-schema definitions.
- Run identifiers or timestamps where useful.
- Standardized report metadata.
- Improved report-write failure handling.
- Optional HTML reporting in a future release if it provides clear value beyond CSV reporting and the planned dashboard.
- Dashboard links to current report artifacts.
- Historical report retention policy.
- Report-generation metrics.

Future changes should preserve the guiding principle:

> Reports should make application outcomes understandable without requiring the operator to inspect source code or reconstruct decisions from logs.
