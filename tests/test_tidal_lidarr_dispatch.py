from pathlib import Path


def test_lidarr_and_tidal_share_post_plex_dispatch_pool():
    source = Path("playlist_import_v2.py").read_text(encoding="utf-8")
    start = source.index("def main(")

    dispatch = source.index("External unmatched dispatch pool:", start)
    lidarr = source.index("run_lidarr_diagnostics(", start)
    tidal = source.index("run_tidal_unmatched_resolution(", start)

    assert dispatch < lidarr
    assert dispatch < tidal
