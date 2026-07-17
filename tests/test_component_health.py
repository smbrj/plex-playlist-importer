from unittest.mock import Mock, patch
from plex_playlist.plex_client import PlexClient


@patch("plex_playlist.plex_client.PlexServer")
def test_plex_is_available_checks_music_library(mock_server) -> None:
    library = Mock()
    library.type = "artist"
    server = Mock()
    server.library.section.return_value = library
    mock_server.return_value = server
    client = PlexClient("http://plex", "token", "Music")
    health = client.is_available()
    assert health.available is True
    server.library.section.assert_called_once_with("Music")


@patch("plex_playlist.plex_client.PlexServer")
def test_plex_is_unavailable_when_library_missing(mock_server) -> None:
    mock_server.side_effect = RuntimeError("library missing")
    client = PlexClient("http://plex", "token", "Music")
    health = client.is_available()
    assert health.available is False
    assert "library missing" in health.detail
