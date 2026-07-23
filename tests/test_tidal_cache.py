from datetime import datetime, timedelta, timezone

from plex_playlist.tidal_cache import TidalSearchCache
from plex_playlist.tidal_client import TidalTrackCandidate


NOW = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)


def candidate():
    return TidalTrackCandidate(
        track_id="317688870",
        artist="Steely Dan",
        title="Peg",
        album="Aja",
        quality="HIRES_LOSSLESS,LOSSLESS",
    )


def test_match_round_trip(tmp_path):
    cache = TidalSearchCache(tmp_path / "tidal.db", max_age_hours=24)
    cache.initialize()
    cache.put_match("Steely Dan", "Peg", candidate(), now=NOW)

    result = cache.get("Steely Dan", "Peg", now=NOW + timedelta(hours=1))

    assert result.found is True
    assert result.matched.track_id == "317688870"


def test_no_match_round_trip(tmp_path):
    cache = TidalSearchCache(tmp_path / "tidal.db", max_age_hours=24)
    cache.initialize()
    cache.put_no_match("Nobody", "Nothing", now=NOW)

    result = cache.get("Nobody", "Nothing", now=NOW + timedelta(hours=1))

    assert result.found is True
    assert result.matched is None


def test_expired_entry_becomes_cache_miss(tmp_path):
    cache = TidalSearchCache(tmp_path / "tidal.db", max_age_hours=24)
    cache.initialize()
    cache.put_match("Steely Dan", "Peg", candidate(), now=NOW)

    result = cache.get("Steely Dan", "Peg", now=NOW + timedelta(hours=25))

    assert result.found is False
    assert result.matched is None
