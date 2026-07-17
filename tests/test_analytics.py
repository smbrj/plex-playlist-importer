from pathlib import Path
import csv, json
from plex_playlist.analytics import RunAnalytics, append_match_analytics_csv, write_latest_run_json, count_lidarr_states

class Row:
    def __init__(self, status): self.acquisition_status = status

def test_analytics_outputs(tmp_path: Path):
    item = RunAnalytics.create(
        source="XMPlaylist Ch 14", playlist="Ch 14 - The Bridge",
        requested_tracks=100, normal_matches=80, fallback_matches=10,
        alias_matches=5, unmatched_tracks=10, metadata_warnings=3,
        lidarr_searches_queued=1, lidarr_searches_suppressed=2,
        lidarr_retries_queued=0, lidarr_tracks_available=1,
        run_duration_seconds=112.345,
        cache_refresh_performed=False,
        plex_cache_age_hours=2.5, plex_cache_track_count=56250,
        plex_state="AVAILABLE", xmplaylist_state="AVAILABLE",
        lidarr_state="AVAILABLE", tidal_state="NOT_CONFIGURED",
        playlist_state="DRY RUN", run_result="SUCCESS",
    )
    csv_path = tmp_path / "history.csv"
    json_path = tmp_path / "latest.json"
    append_match_analytics_csv(item, csv_path)
    append_match_analytics_csv(item, csv_path)
    write_latest_run_json(item, json_path)
    with csv_path.open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert rows[0]["match_percent"] == "90.0"
    assert json.loads(json_path.read_text())["playlist"] == "Ch 14 - The Bridge"

def test_counts():
    rows = [Row("SEARCH_QUEUED"), Row("SEARCH_RECENTLY_REQUESTED"), Row("SEARCH_RETRY_QUEUED"), Row("TRACK_ALREADY_AVAILABLE")]
    assert count_lidarr_states(rows) == {"queued":1, "suppressed":1, "retries":1, "available":1}


def test_existing_csv_schema_is_migrated(tmp_path: Path):
    csv_path = tmp_path / "history.csv"
    csv_path.write_text(
        "run_timestamp_utc,source,playlist\n"
        "2026-07-16T00:00:00+00:00,old,Old Playlist\n",
        encoding="utf-8",
    )

    item = RunAnalytics.create(
        source="XMPlaylist Ch 14",
        playlist="Ch 14 - The Bridge",
        requested_tracks=10,
        normal_matches=8,
        fallback_matches=1,
        alias_matches=0,
        unmatched_tracks=1,
        metadata_warnings=0,
        lidarr_searches_queued=0,
        lidarr_searches_suppressed=0,
        lidarr_retries_queued=0,
        lidarr_tracks_available=0,
        run_duration_seconds=5.5,
        cache_refresh_performed=True,
        plex_cache_age_hours=0.0,
        plex_cache_track_count=100,
        plex_state="AVAILABLE",
        xmplaylist_state="AVAILABLE",
        lidarr_state="AVAILABLE",
        tidal_state="NOT_CONFIGURED",
        playlist_state="UPDATED",
        run_result="SUCCESS",
    )

    append_match_analytics_csv(item, csv_path)

    with csv_path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 2
    assert rows[0]["run_duration_seconds"] == ""
    assert rows[1]["run_duration_seconds"] == "5.5"
    assert rows[1]["cache_refresh_performed"] == "True"
