# Deployment Architecture

**Document Version:** 1.0  
**Status:** Approved  
**Last Updated:** 2026-07-21  
**Primary Audience:** Developers and Operators  
**Depends On:** runtime.md  
**Related Documents:** README.md, configuration.md, testing.md, cache.md, reporting.md  
**Snapshot:** 011

---

# Purpose and Scope

This document defines the intended deployment architecture for the Plex Playlist Importer.

The application is currently a headless Python command-line application. The long-term production target is a Linux container on an Unraid server with persistent configuration, state, reports and logs; scheduled unattended execution; network access to Plex, Lidarr, XMPlaylist, and future TIDAL integration; and operational health visibility.

Containerization, scheduling, and the health dashboard are target-state functionality and are not yet considered completed current functionality.

# Deployment Principles

The target deployment should provide reliable unattended execution, minimal administration, persistent application data, predictable connectivity, simple upgrades and recovery, useful exit status, and graceful degradation.

> Use the simplest deployment architecture that provides reliable unattended operation, persistent state, safe upgrades, and clear health visibility.

# Current Development Environment

Development and testing primarily occur on Windows using PowerShell, Python, and pytest. The current runtime is already headless, CLI-driven, configuration-file driven, filesystem-report driven, and SQLite-state driven.

# Target Production Environment

The target is an Unraid-hosted Linux container. Production should not depend on Windows drive letters, Windows-specific paths, desktop sessions, PowerShell, or manually activated virtual environments.

# Container Runtime

The same Python orchestrator and subsystem modules should run in development and production. The image should contain Python, application code, and dependencies. User configuration and runtime state should live on persistent host-mounted storage.

# Persistent Data

Persistent storage should include:

```text
config.ini
resources/xmstations.ini
resources/aliases.txt
cache/plex_library.db
cache/lidarr_search_history.db
cache/xmplaylist_history.db
cache/alias_usage.db
reports/
logs/
```

The Plex cache is rebuildable but should normally persist. XMPlaylist state, Lidarr search history, and alias usage contain operational history that is useful to preserve.

# Recommended Persistent Layout

A practical host layout may resemble:

```text
/appdata/plex-playlist-importer/
    config/
    resources/
    cache/
    reports/
    logs/
```

Exact host and container mount points should be finalized during implementation.

# Logging

Current logging paths are tied to the process working directory and include hard-coded operational values. Logging should be made explicit and predictable for container deployment as part of the Configuration Audit.

# Secrets

Sensitive values such as the Plex token and Lidarr API key must not be embedded in the image or committed to a public repository. The current private `config.ini` approach is acceptable for the initial deployment if its persistent directory is protected. Container-native secret mechanisms may be considered later if they provide practical value.

# Networking

The container requires access to Plex and Lidarr on the local network and outbound internet access for XMPlaylist. TIDAL will add another external dependency when implemented. Stable hostnames, service names, or local DNS should be preferred over transient container IP addresses.

# Permissions

The container should not require unnecessary root privileges. Its runtime user must be able to read configuration/resources and read/write persistent databases, reports, and logs. PUID/PGID-style configuration may be evaluated for Unraid so files remain manageable from the host.

# Scheduling

Scheduled unattended execution is part of the target deployment.

The current working preference is **cron inside the container** under the KISS principle. The final scheduling decision is intentionally deferred until the containerization phase.

The station-profile model is well suited to scheduling through commands such as:

```text
--xmprofile <profile>
--all-xmprofiles
```

Scheduling frequency should reflect XMPlaylist history windows, API budgets, playlist freshness requirements, Lidarr retry policy, and expected runtime.

# cron.ini Evaluation

During containerization, evaluate a user-maintained `cron.ini` that can generate the actual crontab.

The evaluation should explicitly document advantages and disadvantages. Potential advantages include making scheduling more approachable for users unfamiliar with crontab syntax, centralized validation, and consistent command generation. Potential disadvantages include introducing another configuration format and translation layer that must itself be maintained and tested.

No final `cron.ini` design is specified by this document.

# Overlapping Runs

Scheduled execution introduces the possibility of overlapping runs. The current runtime does not document a global process lock.

Before unattended scheduling is finalized, evaluate whether a simple single-instance lock is required to protect SQLite state, reports, logs, XMPlaylist state, and Plex playlist operations.

# Exit Codes

Scheduled/container execution should preserve meaningful runtime exit codes:

| Exit Code | Meaning |
|---:|---|
| 0 | Normal success |
| 1 | Keyboard interruption |
| 2 | Dry run completed with warnings |
| 4 | Plex playlist operation skipped because Plex was unavailable |
| 5 | Playlist skipped for stale-cache safety or Plex resolution inconsistency |

Monitoring should distinguish fatal failure from completion with degraded functionality.

# Restart and Upgrade Model

Persistent mounted storage should survive container restart, recreation, and image upgrade. A normal upgrade should replace the image while mounting the same persistent application data.

Persistent SQLite schema changes must be tested against populated databases, not only new empty databases.

# Backup and Recovery

The persistent application-data directory should be included in the normal Unraid backup strategy.

At minimum, recovery should preserve:

```text
config.ini
resources/xmstations.ini
resources/aliases.txt
```

and persistent SQLite state where continuity matters.

The Plex library cache can be rebuilt from Plex. Loss of XMPlaylist or Lidarr history state loses operational continuity and may cause backfill or retry behavior to restart.

# Health Monitoring

The project's completion target includes an application-health dashboard.

Current health sources already include:

```text
RunStatus
logs
analytics
reports/latest_run.json
process exit code
```

A future dashboard should build on these sources and remain logically separable from the importer so dashboard failure cannot block scheduled imports.

A future container health model should consider the latest run result and age, persistent-storage accessibility, and configuration validity rather than merely checking whether a Python process exists.

# Time Zone, Locale, and Paths

The final container should use a predictable timezone and a UTF-8-capable environment.

Linux path case sensitivity and path portability must be validated. Python `Path` handling and portable relative paths should be preferred over Windows-specific path assumptions.

# Container Validation

Before production deployment, validate:

- Image build and Python startup.
- Dependency installation.
- Mounted configuration/resources.
- Persistent cache/state/reports/logs.
- Plex/Lidarr/XMPlaylist connectivity.
- Unicode handling.
- Exit-code propagation.
- Restart behavior.
- Existing SQLite database reuse.
- Scheduled execution.

Initial deployment should progress from diagnostic/read-only operations to dry run, report/log verification, controlled Plex connectivity testing, a disposable real playlist update, and only then scheduled execution.

# Upgrade and Rollback

Before replacing a production image:

1. Run the automated test suite.
2. Validate persistent-state migration behavior where relevant.
3. Back up persistent application data.
4. Deploy the new image.
5. Verify startup.
6. Run a controlled dry run.
7. Review logs and `latest_run.json`.
8. Resume scheduled execution.

Rollback to a previous known-good image should remain possible. Schema changes must therefore be deliberate, tested, documented, and backed up.

# Production Completion Criteria

The project completion target requires:

```text
Linux / Unraid container
        +
Scheduled imports
        +
Application health dashboard
```

Production readiness should also demonstrate persistent configuration/state, safe restart behavior, external-service connectivity, useful exit statuses, and a backup/recovery path.

# Known Deployment Work

Remaining target-state work includes:

- Build and validate the Linux/Unraid container.
- Finalize persistent volume mappings.
- Resolve logging paths for container operation.
- Finalize scheduling architecture.
- Evaluate `cron.ini`/crontab generation.
- Evaluate overlap/single-instance protection.
- Finalize secret handling.
- Validate Linux path/Unicode behavior.
- Validate exit-code propagation.
- Define backup/restore and upgrade/rollback procedures.
- Implement the health dashboard.

# Operational Improvement Review

After TIDAL integration and before finalizing containerization, review operational improvements identified through regular real-world use of the importer.

This review should occur before deployment behavior is frozen so useful operational lessons can be incorporated into the production container design.

# Deployment Design Principle

The deployment architecture should remain understandable to a single maintainer.

The goal is not to reproduce enterprise infrastructure unnecessarily.

> Use the simplest deployment architecture that provides reliable unattended operation, persistent state, safe upgrades, and clear health visibility.
