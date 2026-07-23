from pathlib import Path
import playlist_import_v2 as app


def test_marker_round_trip(tmp_path: Path):
    marker = tmp_path / "cache" / "tidal_favorite_test_state.json"
    app._write_tidal_favorite_test_marker(
        marker,
        track_id="317688870",
    )
    assert marker.exists()
    app._clear_tidal_favorite_test_marker(marker)
    assert not marker.exists()


def test_parser_accepts_tidal_favorite_cleanup():
    args = app.build_parser().parse_args(["--tidal-favorite-cleanup"])
    assert args.tidal_favorite_cleanup is True
