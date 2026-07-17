from plex_playlist.analytics import RunAnalytics


def test_stale_cache_fields_are_present():
    item = RunAnalytics.create(
        source="XMPlaylist Ch 24",
        playlist="Ch 24 - Radio Margaritaville",
        requested_tracks=1,
        normal_matches=1,
        fallback_matches=0,
        alias_matches=0,
        unmatched_tracks=0,
        metadata_warnings=0,
        lidarr_searches_queued=0,
        lidarr_searches_suppressed=0,
        lidarr_retries_queued=0,
        lidarr_tracks_available=0,
        run_duration_seconds=1.0,
        cache_refresh_performed=False,
        stale_plex_matches=1,
        playlist_skip_reason="STALE_PLEX_CACHE",
        plex_cache_age_hours=1.0,
        plex_cache_track_count=10,
        plex_state="AVAILABLE",
        xmplaylist_state="AVAILABLE",
        lidarr_state="AVAILABLE",
        tidal_state="NOT_CONFIGURED",
        playlist_state="SKIPPED",
        run_result="COMPLETED WITH WARNINGS",
    )

    assert item.stale_plex_matches == 1
    assert item.playlist_skip_reason == "STALE_PLEX_CACHE"
