from __future__ import annotations
import csv, json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

@dataclass(slots=True)
class RunAnalytics:
    run_timestamp_utc: str
    source: str
    playlist: str
    requested_tracks: int
    normal_matches: int
    fallback_matches: int
    alias_matches: int
    unmatched_tracks: int
    metadata_warnings: int
    match_percent: float
    lidarr_searches_queued: int
    lidarr_searches_suppressed: int
    lidarr_retries_queued: int
    lidarr_tracks_available: int
    run_duration_seconds: float
    cache_refresh_performed: bool
    stale_plex_matches: int
    playlist_skip_reason: str
    plex_cache_age_hours: float | None
    plex_cache_track_count: int
    plex_state: str
    xmplaylist_state: str
    lidarr_state: str
    tidal_state: str
    playlist_state: str
    run_result: str

    @classmethod
    def create(cls, **kwargs):
        # Backward-compatible defaults for fields introduced by stale Plex
        # cache hardening. Older callers and tests do not need to supply them.
        kwargs.setdefault("stale_plex_matches", 0)
        kwargs.setdefault("playlist_skip_reason", "")

        requested = int(kwargs["requested_tracks"])
        matched = int(kwargs["normal_matches"]) + int(kwargs["fallback_matches"])
        kwargs["match_percent"] = round((matched / requested) * 100, 2) if requested else 0.0
        kwargs["run_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
        return cls(**kwargs)

FIELDS = list(RunAnalytics.__dataclass_fields__)

def append_match_analytics_csv(item: RunAnalytics, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _migrate_csv_schema_if_needed(path)

    new_file = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(asdict(item))


def _migrate_csv_schema_if_needed(path: Path) -> None:
    """
    Rewrite an existing analytics CSV when new fields are introduced.

    Existing rows are preserved and newly introduced columns are left blank.
    """

    if not path.exists() or path.stat().st_size == 0:
        return

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        existing_fields = list(reader.fieldnames or [])
        if existing_fields == FIELDS:
            return
        rows = list(reader)

    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                field: row.get(field, "")
                for field in FIELDS
            })

    temporary.replace(path)

def write_latest_run_json(item: RunAnalytics, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(asdict(item), indent=2) + "\n", encoding="utf-8")
    temp.replace(path)

def count_lidarr_states(rows: Iterable[object]) -> dict[str, int]:
    counts = {"queued": 0, "suppressed": 0, "retries": 0, "available": 0}
    for row in rows:
        status = str(getattr(row, "acquisition_status", "") or "")
        if status == "SEARCH_QUEUED":
            counts["queued"] += 1
        elif status == "SEARCH_RECENTLY_REQUESTED":
            counts["suppressed"] += 1
        elif status == "SEARCH_RETRY_QUEUED":
            counts["retries"] += 1
        elif status in {"TRACK_ALREADY_AVAILABLE", "SEARCH_COMPLETED_FILE_AVAILABLE"}:
            counts["available"] += 1
    return counts
