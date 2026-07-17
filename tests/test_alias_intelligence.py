from pathlib import Path
import csv

from plex_playlist.alias_usage import AliasUsageStore
from plex_playlist.alias_intelligence import (
    export_plex_artists_csv,
    import_approved_aliases,
    suggest_aliases_csv,
    audit_aliases_csv,
)
from plex_playlist.models import LibraryTrack


def track(artist: str, album: str, title: str, key: int) -> LibraryTrack:
    return LibraryTrack(
        rating_key=key,
        guid="",
        artist=artist,
        album_artist=artist,
        album=album,
        title=title,
        duration=None,
        year=None,
        version="studio",
        file_path="",
    )


def test_export_artist_inventory(tmp_path: Path) -> None:
    output = tmp_path / "artists.csv"
    rows = export_plex_artists_csv(
        [
            track("The Doobie Brothers", "A", "One", 1),
            track("The Doobie Brothers", "B", "Two", 2),
        ],
        output,
    )
    assert len(rows) == 1
    assert rows[0].album_count == 2
    assert rows[0].track_count == 2


def test_suggests_leading_article_alias(tmp_path: Path) -> None:
    unmatched = tmp_path / "unmatched.csv"
    unmatched.write_text(
        "Requested Artist,Requested Title\n"
        "Doobie Brothers,Listen to the Music\n",
        encoding="utf-8",
    )
    output = tmp_path / "suggestions.csv"
    rows = suggest_aliases_csv(
        unmatched_csv=unmatched,
        tracks=[
            track(
                "The Doobie Brothers",
                "Toulouse Street",
                "Listen to the Music",
                1,
            )
        ],
        aliases_path=tmp_path / "aliases.txt",
        output_path=output,
    )
    assert rows[0].suggested_plex_artist == "The Doobie Brothers"
    assert rows[0].confidence == "VERY HIGH"


def test_imports_only_add_rows(tmp_path: Path) -> None:
    suggestions = tmp_path / "suggestions.csv"
    with suggestions.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "Requested Artist",
                "Suggested Plex Artist",
                "Action",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "Requested Artist": "Doobie Brothers",
            "Suggested Plex Artist": "The Doobie Brothers",
            "Action": "ADD",
        })
        writer.writerow({
            "Requested Artist": "Stills",
            "Suggested Plex Artist": "The Stills-Young Band",
            "Action": "REVIEW",
        })

    aliases = tmp_path / "aliases.txt"
    summary = import_approved_aliases(
        suggestions_csv=suggestions,
        aliases_path=aliases,
    )

    content = aliases.read_text(encoding="utf-8")
    assert "Doobie Brothers = The Doobie Brothers" in content
    assert "Stills = The Stills-Young Band" not in content
    assert summary["added"] == 1


def test_audit_uses_persistent_usage(tmp_path: Path) -> None:
    aliases = tmp_path / "aliases.txt"
    aliases.write_text(
        "Doobie Brothers = The Doobie Brothers\n"
        "Missing Artist = Missing Target\n",
        encoding="utf-8",
    )
    store = AliasUsageStore(tmp_path / "usage.db")
    store.initialize()
    store.record_run(
        usage_counts={"Doobie Brothers": 2},
        aliases={
            "Doobie Brothers": "The Doobie Brothers",
            "Missing Artist": "Missing Target",
        },
        source="test",
        playlist="test",
    )

    rows = audit_aliases_csv(
        aliases_path=aliases,
        tracks=[
            track(
                "The Doobie Brothers",
                "Toulouse Street",
                "Listen to the Music",
                1,
            )
        ],
        output_path=tmp_path / "audit.csv",
        usage_store=store,
        review_after_days=90,
    )

    by_alias = {row["Alias"]: row for row in rows}
    assert by_alias["Doobie Brothers"]["Status"] == "ACTIVE"
    assert by_alias["Doobie Brothers"]["Usage Count"] == 2
    assert by_alias["Missing Artist"]["Status"] == "BROKEN"
