# Analytics

**Document Version:** 1.0  
**Status:** Approved  
**Last Updated:** 2026-07-21  
**Primary Audience:** Developers and Operators  
**Depends On:** reporting.md  
**Related Documents:** runtime.md, matching.md, aliases.md, lidarr.md, xmplaylist.md, testing.md, deployment.md  
**Snapshot:** 012

---

# Purpose

The analytics subsystem preserves operational history across importer runs.

Current outputs are:

```text
reports/match_analytics.csv
reports/latest_run.json
```

The CSV provides historical run-level analytics. The JSON provides the most recent operational state.

Analytics summarize runtime outcomes rather than replacing track reports or logs.

# Analytics Versus Reporting

Reports answer what happened to individual tracks or one workflow.

Analytics answer how the importer performed during a run and how behavior changes over time.

# Historical CSV

`match_analytics.csv` appends one summarized row per run.

Useful information may include requested, matched and unmatched counts; matching paths; alias-assisted results; cache state; component health; playlist operation; runtime duration; and overall status.

Historical schema changes must preserve existing rows where practical. Older rows should not receive fabricated values for fields that did not yet exist.

# Latest-Run JSON

`latest_run.json` represents the most recent execution and is overwritten by newer run data.

It is intended for machine-readable status, future health monitoring, and the planned dashboard.

# Match and Method Counts

Analytics should preserve both overall match counts and enough method/reason information to distinguish exact/normal, fallback, alias-assisted, and unmatched behavior where available.

The same match percentage can represent very different matching quality, so method information is operationally useful.

# Alias Analytics

Persistent alias usage helps identify aliases that actually contribute to matching.

The existence of an alias in `resources/aliases.txt` does not prove operational value.

# Cache and Component Health

Analytics may include cache age, freshness, refresh state, Plex availability, Lidarr state, XMPlaylist state, and future TIDAL state.

Component health should remain separate from overall run status because optional component failures do not necessarily invalidate the full run.

# Playlist Operation

Matching success and Plex playlist-operation success are separate concepts.

Analytics should distinguish matching completion from actual playlist creation/update/replacement, dry-run, skip, or unavailable outcomes.

# Runtime Integration

Analytics are produced from runtime results and may be written during normal, dry-run, degraded Plex, and XMPlaylist workflows where the runtime reaches analytics generation.

They should remain useful for both file-based and XMPlaylist-based imports.

# Multi-Profile Runs

`--all-xmprofiles` creates both per-profile and aggregate process perspectives.

Current analytics semantics should be reviewed and directly tested so unattended monitoring can distinguish these levels clearly.

# Lidarr and TIDAL

Lidarr analytics should summarize run-level outcomes without duplicating the detailed Lidarr report.

TIDAL fields should be defined only after TIDAL behavior is implemented. Existing history compatibility must be preserved.

# Analytics Are Not Logs

Logs provide chronological diagnostics and exceptions.

Track reports explain individual matching outcomes.

Analytics provide structured run summaries and trends.

# Persistence and Configuration

Analytics normally live under `reports/` and should be persistent in the future container deployment.

The Configuration Audit should verify that analytics paths and settings are actually consumed as documented and that parent directories are handled consistently.

# Current Testing

Current analytics tests are in:

```text
tests/test_analytics.py
```

Recorded coverage includes output generation, count calculation, and existing CSV schema migration.

# Additional Testing

Future tests should verify:

- CSV append and history preservation.
- CSV schema migration.
- `latest_run.json` content.
- JSON overwrite behavior.
- Missing optional component fields.
- Parent-directory creation.
- Analytics write-failure handling.
- Multi-profile per-profile versus aggregate semantics.

# Failure Isolation

Analytics write failures must be logged and visible.

They should not incorrectly imply that a previously completed external operation, such as a successful Plex playlist update, did not occur.

The exact warning/failure classification should be explicit and regression-tested.

# Future Dashboard

The future dashboard should consume existing analytics and runtime status outputs rather than create a parallel monitoring system.

Likely sources are:

```text
reports/latest_run.json
reports/match_analytics.csv
RunStatus-derived information
```

`latest_run.json` supports current-state views. The CSV supports historical trends.

The dashboard should remain optional and logically separable from importer execution.

# Container and Scheduling Considerations

Analytics files should reside on persistent container storage.

Scheduled execution increases their value because no operator is present to observe console output.

Overlapping runs could contend for analytics files, so the future single-instance/overlap decision should include analytics writers.

Atomic replacement of `latest_run.json` may be evaluated if it becomes a health-monitoring dependency.

# Retention and Recovery

Analytics are valuable historical data but are not required for core importer function.

If lost, importer operation continues but historical trends are lost.

No retention policy is currently required, though long-term container operation may later justify one.

# Operational Improvement Review

After TIDAL integration and before finalizing containerization, review analytics accumulated during real-world use.

Add metrics only when they answer demonstrated operational questions such as run duration, recurring degraded integrations, stale-cache use, or unmatched trends.

# Post-Documentation Cleanup

Carry forward:

- Review current CSV schema against runtime data.
- Verify `latest_run.json` fields against `RunStatus`.
- Confirm analytics configuration usage.
- Add direct JSON/overwrite/optional-field/directory/write-failure tests.
- Clarify and test multi-profile analytics semantics.
- Verify failure handling does not misrepresent completed work.
- Ensure the dashboard reuses existing analytics/status outputs.
- Preserve compatibility when future TIDAL fields are introduced.

# Design Principle

> Record enough history to understand importer behavior over time, but add metrics only when they answer a useful operational question.
