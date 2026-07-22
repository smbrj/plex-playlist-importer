from pathlib import Path

from plex_playlist.parser import parse_playlist_file


def test_parse_m3u8_extinf(tmp_path: Path):
    source = tmp_path / "playlist.m3u8"
    source.write_text(
        "#EXTM3U\n"
        "#EXTINF:123,The Beatles - Something\n"
        "file:///music/beatles/something.flac\n",
        encoding="utf-8",
    )

    entries = parse_playlist_file(source)

    assert len(entries) == 1
    assert entries[0].artist == "The Beatles"
    assert entries[0].title == "Something"
    assert entries[0].sequence == 1


def test_m3u8_is_treated_like_m3u(tmp_path: Path):
    body = (
        "#EXTM3U\n"
        "#EXTINF:200,Steely Dan - Peg\n"
        "file:///music/steely-dan/peg.flac\n"
    )

    m3u = tmp_path / "one.m3u"
    m3u8 = tmp_path / "one.m3u8"
    m3u.write_text(body, encoding="utf-8")
    m3u8.write_text(body, encoding="utf-8")

    m3u_entries = parse_playlist_file(m3u)
    m3u8_entries = parse_playlist_file(m3u8)

    assert [(e.artist, e.title) for e in m3u8_entries] == [
        (e.artist, e.title) for e in m3u_entries
    ]
