from plex_playlist.models import LibraryTrack
from plex_playlist.search_index import SearchIndex


def make_track(
    rating_key: int,
    *,
    artist: str = "Artist",
    album_artist: str | None = None,
    album: str = "Album",
    title: str = "Title",
    guid: str | None = None,
) -> LibraryTrack:
    return LibraryTrack(
        rating_key=rating_key,
        guid=guid,
        artist=artist,
        album_artist=album_artist if album_artist is not None else artist,
        album=album,
        title=title,
        duration=None,
        year=None,
    )


def keys(items):
    return [item.rating_key for item in items]


def test_build_preserves_all_tracks_and_count():
    tracks = [make_track(1), make_track(2, title="Other")]
    index = SearchIndex.build(tracks)
    assert index.all_tracks == tracks
    assert index.track_count == 2


def test_artist_lookup_is_normalized():
    index = SearchIndex.build([
        make_track(1, artist="Beyoncé"),
        make_track(2, artist="Other"),
    ])
    assert keys(index.artist_matches("BEYONCE")) == [1]


def test_title_lookup_is_normalized():
    index = SearchIndex.build([
        make_track(1, title="What's Going On"),
        make_track(2, title="Other"),
    ])
    assert keys(index.title_matches("whats going on")) == [1]


def test_album_lookup_is_normalized():
    index = SearchIndex.build([
        make_track(1, album="Abbey Road"),
        make_track(2, album="Other"),
    ])
    assert keys(index.album_matches("abbey-road")) == [1]


def test_album_artist_lookup_is_preindexed_and_normalized():
    index = SearchIndex.build([
        make_track(1, artist="Guest", album_artist="The Band"),
        make_track(2, artist="Guest 2", album_artist="Other"),
    ])
    assert "theband" in index.by_album_artist
    assert keys(index.album_artist_matches("The Band")) == [1]


def test_artist_title_lookup_returns_duplicate_versions():
    index = SearchIndex.build([
        make_track(1, artist="Artist", title="Song", album="Original"),
        make_track(2, artist="Artist", title="Song", album="Greatest Hits"),
    ])
    assert keys(index.artist_title_matches("artist", "song")) == [1, 2]


def test_guid_lookup_returns_track():
    index = SearchIndex.build([make_track(1, guid="plex://track/one")])
    assert index.guid_match("plex://track/one").rating_key == 1


def test_blank_guid_is_not_indexed():
    index = SearchIndex.build([
        make_track(1, guid=""),
        make_track(2, guid=None),
    ])
    assert index.by_guid == {}
    assert index.guid_match("") is None


def test_duplicate_guid_last_track_wins():
    index = SearchIndex.build([
        make_track(1, guid="same-guid"),
        make_track(2, guid="same-guid"),
    ])
    assert index.guid_match("same-guid").rating_key == 2


def test_missing_exact_lookups_return_empty_or_none():
    index = SearchIndex.build([make_track(1)])
    assert index.artist_matches("Missing") == []
    assert index.title_matches("Missing") == []
    assert index.album_matches("Missing") == []
    assert index.album_artist_matches("Missing") == []
    assert index.artist_title_matches("Missing", "Missing") == []
    assert index.guid_match("missing") is None


def test_title_token_one_token_requires_that_token():
    index = SearchIndex.build([
        make_track(1, title="Satisfaction"),
        make_track(2, title="Paint It Black"),
    ])
    assert keys(index.title_token_matches("Satisfaction")) == [1]


def test_title_token_two_tokens_requires_one_overlap():
    index = SearchIndex.build([
        make_track(1, title="Rolling Stone"),
        make_track(2, title="Rolling Thunder"),
        make_track(3, title="Paint Black"),
    ])
    assert set(keys(index.title_token_matches("Rolling Stone"))) == {1, 2}


def test_title_token_four_tokens_requires_two_overlap():
    index = SearchIndex.build([
        make_track(1, title="One Two Three Four"),
        make_track(2, title="One Two Other"),
        make_track(3, title="One Other"),
    ])
    assert set(keys(index.title_token_matches("One Two Three Four"))) == {1, 2}


def test_title_token_lookup_deduplicates_track_across_tokens():
    index = SearchIndex.build([make_track(1, title="One Two Three")])
    assert keys(index.title_token_matches("One Two Three")) == [1]


def test_title_token_lookup_empty_or_stopwords_only_returns_empty():
    index = SearchIndex.build([make_track(1, title="The Song")])
    assert index.title_token_matches("") == []
    assert index.title_token_matches("the an a") == []


def test_title_token_matching_uses_normalized_tokens():
    index = SearchIndex.build([make_track(1, title="Beyoncé Dreams")])
    assert keys(index.title_token_matches("Beyonce Dreams")) == [1]


def test_build_accepts_generator():
    index = SearchIndex.build(
        make_track(i, title=f"Song {i}") for i in range(1, 4)
    )
    assert index.track_count == 3


def test_empty_index_is_safe():
    index = SearchIndex.build([])
    assert index.track_count == 0
    assert index.all_tracks == []
    assert index.artist_matches("anything") == []
    assert index.album_artist_matches("anything") == []
    assert index.title_token_matches("anything") == []
