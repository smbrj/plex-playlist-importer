from pathlib import Path

import pytest

from playlist_import_v2 import build_parser, resolve_alias_suggestion_inputs
from plex_playlist.alias_intelligence import suggest_aliases_csv
from plex_playlist.models import LibraryTrack


def track(artist: str, key: int) -> LibraryTrack:
    return LibraryTrack(
        rating_key=key,
        guid="",
        artist=artist,
        album_artist=artist,
        album="Album",
        title="Track",
        duration=None,
        year=None,
        version="studio",
        file_path="",
    )


def write_unmatched(path: Path, *artists: str) -> None:
    rows = "".join(f"{artist},Song\n" for artist in artists)
    path.write_text(
        "Requested Artist,Requested Title\n" + rows,
        encoding="utf-8",
    )


def test_parser_preserves_default_no_argument_behavior() -> None:
    args = build_parser().parse_args(["--suggest-aliases"])
    assert args.suggest_aliases == []


def test_parser_accepts_multiple_alias_input_patterns() -> None:
    args = build_parser().parse_args([
        "--suggest-aliases",
        "reports/unmatched-1.csv",
        "reports/unmatched-*.csv",
    ])
    assert args.suggest_aliases == [
        "reports/unmatched-1.csv",
        "reports/unmatched-*.csv",
    ]


def test_resolve_uses_default_when_no_explicit_inputs(tmp_path: Path) -> None:
    default = tmp_path / "unmatched.csv"
    write_unmatched(default, "Doobie Brothers")

    assert resolve_alias_suggestion_inputs([], default_path=default) == [
        default.resolve()
    ]


def test_resolve_expands_sorts_and_deduplicates_patterns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = tmp_path / "unmatched-1.csv"
    second = tmp_path / "unmatched-2.csv"
    write_unmatched(first, "Doobie Brothers")
    write_unmatched(second, "Stills")
    monkeypatch.chdir(tmp_path)

    result = resolve_alias_suggestion_inputs(
        ["unmatched-*.csv", "unmatched-1.csv"],
        default_path=tmp_path / "unused.csv",
    )

    assert result == [first.resolve(), second.resolve()]


def test_resolve_rejects_pattern_with_no_matches(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="matched no files"):
        resolve_alias_suggestion_inputs(
            [str(tmp_path / "missing-*.csv")],
            default_path=tmp_path / "unused.csv",
        )


def test_resolve_rejects_non_csv_input(tmp_path: Path) -> None:
    text_file = tmp_path / "unmatched.txt"
    text_file.write_text("x", encoding="utf-8")

    with pytest.raises(RuntimeError, match="must be a CSV"):
        resolve_alias_suggestion_inputs(
            [str(text_file)],
            default_path=tmp_path / "unused.csv",
        )


def test_suggestions_combine_multiple_files_and_deduplicate_artists(
    tmp_path: Path,
) -> None:
    first = tmp_path / "unmatched-1.csv"
    second = tmp_path / "unmatched-2.csv"
    write_unmatched(first, "Doobie Brothers", "Doobie Brothers")
    write_unmatched(second, "Doobie Brothers")

    output = tmp_path / "aliases_suggested.csv"
    rows = suggest_aliases_csv(
        unmatched_csv=[first, second],
        tracks=[track("The Doobie Brothers", 1)],
        aliases_path=tmp_path / "aliases.txt",
        output_path=output,
    )

    assert len(rows) == 1
    assert rows[0].requested_artist == "Doobie Brothers"
    assert rows[0].suggested_plex_artist == "The Doobie Brothers"
    assert output.exists()
