from pathlib import Path

import pytest

from plex_playlist.parser import parse_playlist_file


def write_file(
    path: Path,
    content: str,
) -> Path:
    path.write_text(
        content,
        encoding="utf-8",
    )

    return path


def test_parse_numbered_txt(
    tmp_path: Path,
) -> None:
    source = write_file(
        tmp_path / "playlist.txt",
        (
            "001. Aretha Franklin - Respect\n"
            "002. Fleetwood Mac - Dreams (2001 Remaster)\n"
        ),
    )

    entries = parse_playlist_file(source)

    assert len(entries) == 2

    assert entries[0].sequence == 1
    assert entries[0].artist == "Aretha Franklin"
    assert entries[0].title == "Respect"
    assert entries[0].line_number == 1
    assert entries[0].source == source

    assert entries[1].sequence == 2
    assert entries[1].artist == "Fleetwood Mac"
    assert entries[1].title == "Dreams (2001 Remaster)"


def test_parse_txt_ignores_invalid_lines(
    tmp_path: Path,
) -> None:
    source = write_file(
        tmp_path / "playlist.txt",
        (
            "\n"
            "This line has no delimiter\n"
            "Prince - Purple Rain\n"
            " - Missing Artist\n"
            "Missing Title - \n"
        ),
    )

    entries = parse_playlist_file(source)

    assert len(entries) == 1
    assert entries[0].artist == "Prince"
    assert entries[0].title == "Purple Rain"
    assert entries[0].line_number == 3


def test_parse_csv_with_header(
    tmp_path: Path,
) -> None:
    source = write_file(
        tmp_path / "playlist.csv",
        (
            "Artist,Title\n"
            "Queen,Bohemian Rhapsody\n"
            "Eagles,Hotel California\n"
        ),
    )

    entries = parse_playlist_file(source)

    assert [
        (entry.artist, entry.title)
        for entry in entries
    ] == [
        ("Queen", "Bohemian Rhapsody"),
        ("Eagles", "Hotel California"),
    ]


def test_parse_csv_without_header(
    tmp_path: Path,
) -> None:
    source = write_file(
        tmp_path / "playlist.csv",
        (
            "Queen,Bohemian Rhapsody\n"
            "Eagles,Hotel California\n"
        ),
    )

    entries = parse_playlist_file(source)

    assert len(entries) == 2
    assert entries[0].sequence == 1
    assert entries[1].sequence == 2


def test_parse_tsv_preserves_tab_delimiter(
    tmp_path: Path,
) -> None:
    source = write_file(
        tmp_path / "playlist.tsv",
        (
            "Artist\tTitle\n"
            "Mötley Crüe\tHome Sweet Home\n"
            "Sinéad O'Connor\tNothing Compares 2 U\n"
        ),
    )

    entries = parse_playlist_file(source)

    assert len(entries) == 2
    assert entries[0].artist == "Mötley Crüe"
    assert entries[0].title == "Home Sweet Home"
    assert entries[1].artist == "Sinéad O'Connor"


def test_parse_m3u_extinf(
    tmp_path: Path,
) -> None:
    source = write_file(
        tmp_path / "playlist.m3u",
        (
            "#EXTM3U\n"
            "#EXTINF:-1,Queen - Bohemian Rhapsody\n"
            "/music/Queen/Bohemian Rhapsody.flac\n"
            "#EXTINF:295,Eagles - Hotel California\n"
            "/music/Eagles/Hotel California.mp3\n"
        ),
    )

    entries = parse_playlist_file(source)

    assert [
        (entry.artist, entry.title)
        for entry in entries
    ] == [
        ("Queen", "Bohemian Rhapsody"),
        ("Eagles", "Hotel California"),
    ]

    assert entries[0].line_number == 2
    assert entries[1].line_number == 4


def test_unsupported_extension_is_rejected(
    tmp_path: Path,
) -> None:
    source = write_file(
        tmp_path / "playlist.json",
        "{}",
    )

    with pytest.raises(
        ValueError,
        match="Unsupported playlist format",
    ):
        parse_playlist_file(source)


def test_missing_file_is_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        parse_playlist_file(
            tmp_path / "missing.txt"
        )