from plex_playlist.matcher import match_playlist
from plex_playlist.models import (
    ConfidenceLevel,
    LibraryTrack,
    MatchingConfig,
    PlaylistEntry,
)
from plex_playlist.search_index import SearchIndex


def library_track(
    *,
    rating_key: int,
    artist: str,
    title: str,
    album: str,
    version: str = "studio",
) -> LibraryTrack:
    return LibraryTrack(
        rating_key=rating_key,
        guid=f"test://{rating_key}",
        artist=artist,
        album_artist=artist,
        album=album,
        title=title,
        duration=240_000,
        year=2000,
        version=version,
        file_path="",
    )


def test_exact_match_smoke() -> None:
    index = SearchIndex.build([
        library_track(
            rating_key=1,
            artist="Daft Punk",
            title="Harder Better Faster Stronger",
            album="Discovery",
        ),
        library_track(
            rating_key=2,
            artist="Radiohead",
            title="Paranoid Android",
            album="OK Computer",
        ),
    ])

    playlist = [
        PlaylistEntry(
            sequence=1,
            artist="Daft Punk",
            title="Harder Better Faster Stronger",
        )
    ]

    session = match_playlist(
        playlist=playlist,
        index=index,
        config=MatchingConfig(
            threshold=85,
            workers=1,
        ),
    )

    assert len(session.results) == 1

    result = session.results[0]

    assert result.matched is not None
    assert result.matched.rating_key == 1
    assert result.score.combined == 100.0
    assert result.confidence is ConfidenceLevel.EXACT


def test_unicode_accent_matching_smoke() -> None:
    index = SearchIndex.build([
        library_track(
            rating_key=10,
            artist="Mötley Crüe",
            title="Home Sweet Home",
            album="Theatre of Pain",
        )
    ])

    playlist = [
        PlaylistEntry(
            sequence=1,
            artist="Motley Crue",
            title="Home Sweet Home",
        )
    ]

    session = match_playlist(
        playlist=playlist,
        index=index,
        config=MatchingConfig(
            threshold=85,
            workers=1,
        ),
    )

    result = session.results[0]

    assert result.matched is not None
    assert result.matched.rating_key == 10
    assert result.score.artist == 100.0


def test_configured_artist_alias_smoke() -> None:
    index = SearchIndex.build([
        library_track(
            rating_key=20,
            artist="Electric Light Orchestra",
            title="Mr. Blue Sky",
            album="Out of the Blue",
        )
    ])

    playlist = [
        PlaylistEntry(
            sequence=1,
            artist="ELO",
            title="Mr. Blue Sky",
        )
    ]

    session = match_playlist(
        playlist=playlist,
        index=index,
        config=MatchingConfig(
            threshold=85,
            workers=1,
            artist_aliases={
                "ELO": "Electric Light Orchestra",
            },
        ),
    )

    result = session.results[0]

    assert result.matched is not None
    assert result.matched.rating_key == 20
    assert result.score.artist == 100.0


def test_unrelated_title_remains_unmatched() -> None:
    index = SearchIndex.build([
        library_track(
            rating_key=30,
            artist="Sam Cooke",
            title="Wonderful World",
            album="The Best of Sam Cooke",
        )
    ])

    playlist = [
        PlaylistEntry(
            sequence=1,
            artist="Sam Cooke",
            title="A Change Is Gonna Come",
        )
    ]

    session = match_playlist(
        playlist=playlist,
        index=index,
        config=MatchingConfig(
            threshold=85,
            workers=1,
        ),
    )

    result = session.results[0]

    assert result.matched is None
    assert result.confidence is ConfidenceLevel.NONE