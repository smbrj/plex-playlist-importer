from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
import re
from typing import Iterable

from plex_playlist.models import LibraryTrack
from plex_playlist.normalization import normalize_artist
from plex_playlist.alias_usage import AliasUsageStore


CONFIDENCE_ORDER = {
    "VERY HIGH": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
}


@dataclass(frozen=True, slots=True)
class ArtistInventoryRow:
    artist: str
    normalized_artist: str
    album_count: int
    track_count: int
    first_letter: str


@dataclass(frozen=True, slots=True)
class AliasSuggestionRow:
    requested_artist: str
    suggested_plex_artist: str
    confidence: str
    reason: str
    exists_in_plex: bool
    existing_alias: bool
    action: str = "REVIEW"


def export_plex_artists_csv(
    tracks: Iterable[LibraryTrack],
    output_path: Path,
) -> list[ArtistInventoryRow]:
    artist_albums: dict[str, set[str]] = {}
    track_counts: Counter[str] = Counter()

    for track in tracks:
        artist = str(track.artist or "").strip()
        if not artist:
            continue
        artist_albums.setdefault(artist, set()).add(
            str(track.album or "").strip()
        )
        track_counts[artist] += 1

    rows = [
        ArtistInventoryRow(
            artist=artist,
            normalized_artist=normalize_artist(artist),
            album_count=len({
                album for album in artist_albums[artist] if album
            }),
            track_count=track_counts[artist],
            first_letter=artist[:1].upper(),
        )
        for artist in sorted(artist_albums, key=str.casefold)
    ]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "Artist",
            "Normalized Artist",
            "Album Count",
            "Track Count",
            "First Letter",
        ])
        for row in rows:
            writer.writerow([
                row.artist,
                row.normalized_artist,
                row.album_count,
                row.track_count,
                row.first_letter,
            ])

    return rows


def suggest_aliases_csv(
    *,
    unmatched_csv: Path,
    tracks: Iterable[LibraryTrack],
    aliases_path: Path,
    output_path: Path,
) -> list[AliasSuggestionRow]:
    plex_artists = sorted({
        str(track.artist or "").strip()
        for track in tracks
        if str(track.artist or "").strip()
    }, key=str.casefold)

    existing_aliases = load_alias_file(aliases_path)
    requested_artists = _read_requested_artists(unmatched_csv)

    rows: list[AliasSuggestionRow] = []
    for requested in sorted(requested_artists, key=str.casefold):
        suggestion = _best_alias_candidate(requested, plex_artists)
        if suggestion is None:
            continue

        candidate, confidence, reason = suggestion
        rows.append(
            AliasSuggestionRow(
                requested_artist=requested,
                suggested_plex_artist=candidate,
                confidence=confidence,
                reason=reason,
                exists_in_plex=True,
                existing_alias=requested in existing_aliases,
            )
        )

    rows.sort(
        key=lambda row: (
            CONFIDENCE_ORDER.get(row.confidence, 99),
            row.requested_artist.casefold(),
        )
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "Requested Artist",
            "Suggested Plex Artist",
            "Confidence",
            "Reason",
            "Exists in Plex",
            "Existing Alias",
            "Action",
        ])
        for row in rows:
            writer.writerow([
                row.requested_artist,
                row.suggested_plex_artist,
                row.confidence,
                row.reason,
                "Yes" if row.exists_in_plex else "No",
                "Yes" if row.existing_alias else "No",
                row.action,
            ])

    return rows


def import_approved_aliases(
    *,
    suggestions_csv: Path,
    aliases_path: Path,
) -> dict[str, int]:
    existing = load_alias_file(aliases_path)
    added = 0
    skipped_existing = 0
    ignored = 0
    invalid = 0

    with Path(suggestions_csv).open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            action = str(row.get("Action", "") or "").strip().upper()
            if action != "ADD":
                ignored += 1
                continue

            requested = str(
                row.get("Requested Artist", "") or ""
            ).strip()
            target = str(
                row.get("Suggested Plex Artist", "") or ""
            ).strip()

            if not requested or not target or requested == target:
                invalid += 1
                continue

            if requested in existing:
                skipped_existing += 1
                continue

            existing[requested] = target
            added += 1

    write_alias_file(aliases_path, existing)

    return {
        "added": added,
        "skipped_existing": skipped_existing,
        "ignored": ignored,
        "invalid": invalid,
        "total": len(existing),
    }


def audit_aliases_csv(
    *,
    aliases_path: Path,
    tracks: Iterable[LibraryTrack],
    output_path: Path,
    usage_store: AliasUsageStore | None = None,
    review_after_days: float = 90.0,
) -> list[dict[str, str | int]]:
    aliases = load_alias_file(aliases_path)
    plex_artists = {
        str(track.artist or "").strip()
        for track in tracks
        if str(track.artist or "").strip()
    }

    if usage_store is not None:
        usage_store.initialize()
        usage_store.sync_aliases(aliases)

    rows: list[dict[str, str | int]] = []
    for alias, target in sorted(
        aliases.items(),
        key=lambda item: item[0].casefold(),
    ):
        entry = usage_store.get(alias) if usage_store is not None else None
        target_exists = target in plex_artists
        status = AliasUsageStore.classify(
            entry=entry,
            target_exists=target_exists,
            review_after_days=review_after_days,
        )

        rows.append({
            "Alias": alias,
            "Target Artist": target,
            "Target Exists in Plex": "Yes" if target_exists else "No",
            "Usage Count": entry.use_count if entry else 0,
            "Run Count": entry.run_count if entry else 0,
            "First Used UTC": entry.first_used_utc if entry else "",
            "Last Used UTC": entry.last_used_utc if entry else "",
            "Last Source": entry.last_source if entry else "",
            "Last Playlist": entry.last_playlist if entry else "",
            "Status": status,
        })

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "Alias",
        "Target Artist",
        "Target Exists in Plex",
        "Usage Count",
        "Run Count",
        "First Used UTC",
        "Last Used UTC",
        "Last Source",
        "Last Playlist",
        "Status",
    ]
    with output_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return rows


def load_alias_file(path: Path) -> dict[str, str]:
    path = Path(path)
    if not path.exists():
        return {}

    aliases: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        alias, target = line.split("=", 1)
        alias = alias.strip()
        target = target.strip()
        if alias and target:
            aliases[alias] = target
    return aliases


def write_alias_file(path: Path, aliases: dict[str, str]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Plex Playlist Importer Artist Aliases",
        "# Managed by --import-aliases",
        f"# Entries: {len(aliases)}",
        "",
    ]
    lines.extend(
        f"{alias} = {target}"
        for alias, target in sorted(
            aliases.items(),
            key=lambda item: item[0].casefold(),
        )
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_requested_artists(path: Path) -> set[str]:
    path = Path(path)
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return set()

        candidates = [
            "Requested Artist",
            "Artist",
            "requested_artist",
            "artist",
        ]
        selected = next(
            (name for name in candidates if name in reader.fieldnames),
            None,
        )
        if selected is None:
            raise ValueError(
                "Unable to locate an artist column in unmatched CSV"
            )

        return {
            str(row.get(selected, "") or "").strip()
            for row in reader
            if str(row.get(selected, "") or "").strip()
        }


def _best_alias_candidate(
    requested: str,
    plex_artists: list[str],
) -> tuple[str, str, str] | None:
    requested_norm = normalize_artist(requested)
    if not requested_norm:
        return None

    best: tuple[float, str, str, str] | None = None
    for candidate in plex_artists:
        if candidate == requested:
            continue

        confidence, reason, score = _grade_candidate(
            requested,
            candidate,
        )
        if confidence is None:
            continue

        rank = (
            -CONFIDENCE_ORDER[confidence],
            score,
            candidate,
            reason,
        )
        if best is None or rank[:2] > best[:2]:
            best = (rank[0], rank[1], candidate, f"{confidence}|{reason}")

    if best is None:
        return None

    candidate = best[2]
    confidence, reason = best[3].split("|", 1)
    return candidate, confidence, reason


def _grade_candidate(
    requested: str,
    candidate: str,
) -> tuple[str | None, str, float]:
    req = normalize_artist(requested)
    cand = normalize_artist(candidate)

    if _without_leading_the(req) == _without_leading_the(cand):
        return "VERY HIGH", "Leading article difference only", 1.0

    req_amp = _normalize_ampersand(req)
    cand_amp = _normalize_ampersand(cand)
    if req_amp == cand_amp:
        return "VERY HIGH", "Ampersand vs. and difference only", 0.99

    req_punct = _letters_numbers(req_amp)
    cand_punct = _letters_numbers(cand_amp)
    if req_punct == cand_punct:
        return "VERY HIGH", "Punctuation or spacing difference only", 0.98

    req_tokens = _meaningful_tokens(req)
    cand_tokens = _meaningful_tokens(cand)
    if req_tokens and req_tokens == cand_tokens:
        return "HIGH", "Normalized token match", 0.96

    if (
        req_tokens
        and cand_tokens
        and (
            req_tokens.issubset(cand_tokens)
            or cand_tokens.issubset(req_tokens)
        )
    ):
        ratio = len(req_tokens & cand_tokens) / max(
            len(req_tokens),
            len(cand_tokens),
        )
        if ratio >= 0.66:
            return "MEDIUM", "Partial artist-name overlap", ratio

    similarity = SequenceMatcher(None, req, cand).ratio()
    if similarity >= 0.88:
        return "HIGH", "Strong normalized name similarity", similarity
    if similarity >= 0.76:
        return "MEDIUM", "Moderate normalized name similarity", similarity
    if similarity >= 0.62:
        return "LOW", "Weak similarity; manual verification required", similarity

    return None, "", similarity


def _without_leading_the(value: str) -> str:
    return re.sub(r"^the\s+", "", value).strip()


def _normalize_ampersand(value: str) -> str:
    return re.sub(r"\s+(?:&|and)\s+", " and ", value).strip()


def _letters_numbers(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _meaningful_tokens(value: str) -> set[str]:
    stop = {"the", "and", "a", "an"}
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if token not in stop
    }


