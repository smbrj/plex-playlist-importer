"""
matcher.py

Threaded indexed matcher for Plex Playlist Importer V2.

This module contains no Plex API calls.

The matcher operates entirely against the persistent SearchIndex
loaded from the SQLite cache.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from time import perf_counter

from rapidfuzz import fuzz

from plex_playlist.models import (
    ConfidenceLevel,
    LibraryTrack,
    MatchingConfig,
    MatchingSession,
    MatchResult,
    MatchScore,
    PlaylistEntry,
)

from plex_playlist.normalization import (
    artist_lookup_names,
    canonical_artist_key,
    normalize_key,
    normalize_title,
)

from plex_playlist.search_index import SearchIndex



logger = logging.getLogger(__name__)

def _log_diagnostics(lines: list[str]) -> None:
    if lines:
        logger.info("\n%s", "\n".join(lines))

def _log_trace(lines: list[str]) -> None:
    if lines:
        logger.info("\n%s", "\n".join(lines))

def _finish_trace(
    lines: list[str],
    *,
    enabled: bool,
    entry_start: float,
    decision_start: float,
    decision: str,
) -> None:
    if not enabled:
        return

    decision_ms = (perf_counter() - decision_start) * 1000
    total_ms = (perf_counter() - entry_start) * 1000

    lines.append(
        f"  decision           : {decision:<12} ({decision_ms:.3f} ms)"
    )
    lines.append(
        f"  total entry        : {total_ms:.3f} ms"
    )

    _log_trace(lines)


# ----------------------------------------------------------
# Diagnostics
# ----------------------------------------------------------


@dataclass(slots=True)
class EntryDiagnostics:
    """
    Useful debug information for one playlist entry.
    """

    candidate_count: int = 0
    best_artist_score: float = 0.0
    best_title_score: float = 0.0
    best_combined_score: float = 0.0


def _version_rank(
    track: LibraryTrack,
    config: MatchingConfig,
) -> int:
    """
    Lower rank is preferred.
    """

    version = getattr(track, "version", "studio")

    try:
        return config.preferred_versions.index(version)
    except ValueError:
        return len(config.preferred_versions)

# ----------------------------------------------------------
# Public API
# ----------------------------------------------------------


def match_playlist(
    playlist: list[PlaylistEntry],
    index: SearchIndex,
    config: MatchingConfig,
) -> MatchingSession:
    """
    Match every playlist entry against the SearchIndex.

    This function performs no matching itself—it simply dispatches work
    to worker threads and collects the MatchResult objects.
    """

    session = MatchingSession(
        threshold=config.threshold,
        workers=config.workers,
    )

    start = perf_counter()

    logger.info("Matching %d playlist entries...", len(playlist))

    with ThreadPoolExecutor(max_workers=config.workers) as executor:

        futures = [
            executor.submit(
                _match_entry,
                entry,
                index,
                config,
            )
            for entry in playlist
        ]

        session.results = [
            future.result()
            for future in futures
        ]

 
    session.elapsed_seconds = perf_counter() - start

    logger.info(
        "Matcher finished in %.2f sec",
        session.elapsed_seconds,
    )

    return session

# ----------------------------------------------------------
# Worker
# ----------------------------------------------------------


def _match_entry(
    entry: PlaylistEntry,
    index: SearchIndex,
    config: MatchingConfig,
) -> MatchResult:
    """
    Match a single playlist entry against the SearchIndex.

    Returns one MatchResult.
    """
    debug_lines: list[str] = []
    trace_lines: list[str] = [
        f"TRACE:",
        f"ENTRY: {entry.artist} - {entry.title}",
    ]

    entry_start = perf_counter()
    stage_start = entry_start

    diagnostics = EntryDiagnostics()

    candidates, candidate_source = _candidate_set(
        entry,
        index,
        config,
    )

    trace_lines.append(
        f"  candidate source   : {candidate_source}"
    )

    raw_ms = (perf_counter() - stage_start) * 1000
    stage_start = perf_counter()

    trace_lines.append(
        f"  raw candidates     : {len(candidates):<4} ({raw_ms:.3f} ms)"
    )

    candidates = _prioritize_candidates(
        entry,
        candidates,
        config,
    )

    prioritized_ms = (perf_counter() - stage_start) * 1000
    stage_start = perf_counter()

    trace_lines.append(
        f"  prioritized        : {len(candidates):<4} ({prioritized_ms:.3f} ms)"
    )

    candidates, fallback_mode = _eligible_candidates(
        entry,
        candidates,
        config,
    )
    eligible_ms = (perf_counter() - stage_start) * 1000
    stage_start = perf_counter()

    trace_lines.append(
        f"  eligible           : {len(candidates):<4} ({eligible_ms:.3f} ms)"
    )

    trace_lines.append(
        f"  fallback_mode      : {fallback_mode}"
    )
    
    required_title_score = (
        config.fallback_title_score
        if fallback_mode
        else config.min_title_score
    )

    
    candidates = [
        track for track in candidates
        if _title_similarity(entry, track) >= required_title_score
    ]

    title_gate_ms = (perf_counter() - stage_start) * 1000
    stage_start = perf_counter()

    trace_lines.append(
        f"  title gated        : {len(candidates):<4} ({title_gate_ms:.3f} ms)"
    )

    candidates = _deduplicate_candidates(
        candidates,
        config,
    )

    dedupe_ms = (perf_counter() - stage_start) * 1000

    trace_lines.append(
        f"  deduped            : {len(candidates):<4} ({dedupe_ms:.3f} ms)"
    )

    total_ms = (perf_counter() - entry_start) * 1000

    trace_lines.append(
        f"  pipeline total     : {total_ms:.3f} ms"
    )


    diagnostics.candidate_count = len(candidates)

    debug_lines.append(
        f"ENTRY: {entry.artist} - {entry.title} | candidates={diagnostics.candidate_count}"
    )

    if fallback_mode:
        debug_lines.append("MODE: FALLBACK")

    #
    # Nothing even remotely similar exists.
    #

    if not candidates:
        if config.debug:
            _log_diagnostics(debug_lines)

        _finish_trace(
            trace_lines,
            enabled=config.trace,
            entry_start=entry_start,
            decision_start=perf_counter(),
            decision="unmatched",
        )

        return MatchResult(
            requested=entry,
            matched=None,
            score=MatchScore(
                artist=0.0,
                album_artist=0.0,
                title=0.0,
                combined=0.0,
            ),
            confidence=ConfidenceLevel.NONE,
            reason="No candidates",
        )
       
       
    best_track: LibraryTrack | None = None
    best_score: MatchScore | None = None

   
    #
    # Score every candidate.
    #

    scoring_start = perf_counter()
    top_candidates: list[tuple[float, LibraryTrack]] = []

    for candidate in candidates:

        score = _score(
            entry,
            candidate,
            config,
        )

        top_candidates.append((score.combined, candidate))

        if (
            best_score is None
            or score.combined > best_score.combined
        ):
            best_track = candidate
            best_score = score

            diagnostics.best_artist_score = score.artist
            diagnostics.best_title_score = score.title
            diagnostics.best_combined_score = score.combined

            scoring_ms = (perf_counter() - scoring_start) * 1000
   

    #
    # Sort highest scores first
    #

    sorting_start = perf_counter()

    top_candidates.sort(
        key=lambda x: (
            x[0],
            -_version_rank(x[1], config),
        ),
        reverse=True,
    )

    sorting_ms = (perf_counter() - sorting_start) * 1000

    trace_lines.append(
        f"  scoring            : {len(candidates):<4} ({scoring_ms:.3f} ms)"
    )

    trace_lines.append(
        f"  sorting            : {len(top_candidates):<4} ({sorting_ms:.3f} ms)"
    )

    #
    # Print top five candidates
    #

    debug_lines.append("TOP CANDIDATES:")
    debug_lines.append("  score  | version    | artist                 | title")

    for score_value, track in top_candidates[:5]:
        debug_lines.append(
       #     f"  {score_value:6.1f} | {track.artist:<22} | {track.title}"
            f"  {score_value:6.1f} | {track.version:<10} | {track.artist:<22} | {track.title}"
        )


    #
    # Safety
    #

    decision_start = perf_counter()

    if best_track is None or best_score is None:

        _finish_trace(
            trace_lines,
            enabled=config.trace,
            entry_start=entry_start,
            decision_start=decision_start,
            decision="error",
        )

        if config.debug:
            _log_diagnostics(debug_lines)
        return MatchResult(
            requested=entry,
            matched=None,
            score=MatchScore(
                artist=0.0,
                album_artist=0.0,
                title=0.0,
                combined=0.0,
            ),
            confidence=ConfidenceLevel.NONE,
            reason="Internal matcher error",
        )

    debug_lines.append(
        f"BEST: {best_track.artist:<22} | {best_track.title:<40} | {best_score.combined:.1f}"
    )

    #
    # Fallback Various Artists mode
    #

    if fallback_mode:
        fallback_title_score = best_score.title
        required_score = 95.0


        if fallback_title_score < required_score:
           
            _finish_trace(
                trace_lines,
                enabled=config.trace,
                entry_start=entry_start,
                decision_start=decision_start,
                decision="rejected",
            )
            if config.debug:
                _log_diagnostics(debug_lines)
            return MatchResult(
                requested=entry,
                matched=None,
                score=best_score,
                confidence=ConfidenceLevel.NONE,
                reason=(
                    f"Fallback title score {fallback_title_score:.1f} "
                    f"below required {required_score:.1f}"
                ),
            )

        if config.debug:
            _log_diagnostics(debug_lines)

        _finish_trace(
            trace_lines,
            enabled=config.trace,
            entry_start=entry_start,
            decision_start=decision_start,
            decision="fallback",
        )      

        return MatchResult(
            requested=entry,
            matched=best_track,
            score=best_score,
            confidence=ConfidenceLevel.FALLBACK,
            reason=(
                f"Fallback Various Artists match; "
                f"title score {fallback_title_score:.1f}"

                
            ),
    
        )

   

    #
    # Normal artist match mode
    #

    required_score = config.threshold

    if best_score.combined < required_score:
        if config.debug:
             _log_diagnostics(debug_lines)
        return MatchResult(
            requested=entry,
            matched=None,
            score=best_score,
            confidence=ConfidenceLevel.NONE,
            reason=(
                f"Best score {best_score.combined:.1f} "
                f"below required {required_score:.1f}"
            ),
        )
    if config.debug:
        _log_diagnostics(debug_lines)

    _finish_trace(
        trace_lines,
        enabled=config.trace,
        entry_start=entry_start,
        decision_start=decision_start,
        decision="matched",
    )   
    return MatchResult(
        requested=entry,
        matched=best_track,
        score=best_score,
        confidence=_confidence(best_score.combined),
        reason="",
    )

    
# ----------------------------------------------------------
# Candidate selection
# ----------------------------------------------------------


def _candidate_set(
    entry: PlaylistEntry,
    index: SearchIndex,
    config: MatchingConfig,
) -> tuple[list[LibraryTrack], str]:
    """
    Build a focused candidate set and report the discovery path used.

    Search order:
        1. Exact artist + title, including configured aliases
        2. Exact-title candidates intersected with artist candidates
        3. Token-title candidates intersected with artist candidates
        4. Exact-title or token-title candidates for Various Artists fallback
    """

    lookup_artists = artist_lookup_names(
        entry.artist,
        config.artist_aliases,
    )

    
    #
    # 1. Exact artist + title fast path.
    #

    exact_artist_title: dict[int, LibraryTrack] = {}

    for artist_name in lookup_artists:
        for track in index.artist_title_matches(
            artist_name,
            entry.title,
        ):
            exact_artist_title[track.rating_key] = track

    if exact_artist_title:
        source = (
            "exact artist+title"
            if len(lookup_artists) == 1
            else "alias artist+title"
        )

        return list(exact_artist_title.values()), source

    #
    # Build requested/alias artist bucket.
    #

    artist_candidates: dict[int, LibraryTrack] = {}

    for artist_name in lookup_artists:
        for track in index.artist_matches(artist_name):
            artist_candidates[track.rating_key] = track

    artist_matches = list(artist_candidates.values())
    artist_rating_keys = set(artist_candidates)

    #
    # 2. Exact-title lookup.
    #

    exact_title_matches = index.title_matches(entry.title)

    if artist_matches and exact_title_matches:
        artist_exact_title = [
            track
            for track in exact_title_matches
            if track.rating_key in artist_rating_keys
        ]

        if artist_exact_title:
            source = (
                "artist intersect exact title"
                if len(lookup_artists) == 1
                else "alias artist intersect exact title"
            )

            return artist_exact_title, source

    #
    # Do not return here when exact-title intersection is empty.
    # A stripped/remastered title may still resolve through token lookup.
    #

    #
    # 3. Token-title lookup.
    #

    token_matches = index.title_token_matches(entry.title)

    if artist_matches:
        artist_token_matches = [
            track
            for track in token_matches
            if track.rating_key in artist_rating_keys
        ]

        if artist_token_matches:
            source = (
                "artist intersect token title"
                if len(lookup_artists) == 1
                else "alias artist intersect token title"
            )

            return artist_token_matches, source

        #
        # Requested artist exists, but neither exact nor tokenized title
        # lookup found a plausible title belonging to that artist.
        #

        return [], "artist found; no title match"

    #
    # 4. Requested artist is absent. Preserve title candidates so
    # _eligible_candidates() can evaluate Various Artists fallback.
    #

    fallback_candidates: dict[int, LibraryTrack] = {}

    for track in exact_title_matches:
        fallback_candidates[track.rating_key] = track

    for track in token_matches:
        fallback_candidates[track.rating_key] = track

    if fallback_candidates:
        source = (
            "exact title"
            if exact_title_matches
            else "token title"
        )

        return list(fallback_candidates.values()), source

    return [], "no candidates"

# ----------------------------------------------------------
# Candidate prioritization
# ----------------------------------------------------------

def _prioritize_candidates(
    entry: PlaylistEntry,
    candidates: list[LibraryTrack],
    config: MatchingConfig,
) -> list[LibraryTrack]:
    """
    Priority:
      1. Exact or alias-equivalent artist
      2. Various Artists
      3. Everything else
    """

    wanted_artist = canonical_artist_key(
        entry.artist,
        config.artist_aliases,
    )

    exact_artist: list[LibraryTrack] = []
    various_artists: list[LibraryTrack] = []
    remaining: list[LibraryTrack] = []

    for track in candidates:
        artist = canonical_artist_key(
            track.artist,
            config.artist_aliases,
        )

        if artist == wanted_artist:
            exact_artist.append(track)

        elif _is_various_artist(track):
            various_artists.append(track)

        else:
            remaining.append(track)

    return exact_artist + various_artists + remaining

def _deduplicate_candidates(
    candidates: list[LibraryTrack],
    config: MatchingConfig,
) -> list[LibraryTrack]:
    """
    Collapse duplicate logical tracks.

    Duplicates are grouped by:
      artist + title + version

    This preserves distinct versions such as studio vs live.
    """

    grouped: dict[tuple[str, str, str], LibraryTrack] = {}

    for track in candidates:
        key = (
            normalize_key(track.artist),
            normalize_key(track.title),
            getattr(track, "version", "studio"),
        )

        existing = grouped.get(key)

        if existing is None:
            grouped[key] = track
            continue

        grouped[key] = _prefer_track(existing, track, config)

    return list(grouped.values())


def _prefer_track(
    current: LibraryTrack,
    candidate: LibraryTrack,
    config: MatchingConfig,
) -> LibraryTrack:
    """
    Choose one representative from duplicate logical tracks.
    """

    current_rank = _version_rank(current, config)
    candidate_rank = _version_rank(candidate, config)

    if candidate_rank < current_rank:
        return candidate

    if candidate_rank > current_rank:
        return current

    # Stable fallback: lower rating_key wins.
    if candidate.rating_key < current.rating_key:
        return candidate

    return current


def _eligible_candidates(
    entry: PlaylistEntry,
    candidates: list[LibraryTrack],
    config: MatchingConfig,
) -> tuple[list[LibraryTrack], bool]:
    """
    Enforce artist policy with alias equivalence.
    """

    wanted_artist = canonical_artist_key(
        entry.artist,
        config.artist_aliases,
    )

    exact_artist = [
        track
        for track in candidates
        if canonical_artist_key(
            track.artist,
            config.artist_aliases,
        ) == wanted_artist
    ]

    if exact_artist:
        return exact_artist, False

    various = [
        track
        for track in candidates
        if _is_various_artist(track)
    ]

    if various:
        return various, True

    return [], False

def _is_various_artist(track: LibraryTrack) -> bool:
    return normalize_key(track.artist) == "variousartists"


# ----------------------------------------------------------
# Scoring
# ----------------------------------------------------------

def _score(
    entry: PlaylistEntry,
    track: LibraryTrack,
    config: MatchingConfig,
) -> MatchScore:
    """
    Compute the weighted fuzzy score for one candidate.

    Scores are all 0–100.
    """
    entry_artist = canonical_artist_key(
        entry.artist,
        config.artist_aliases,
    )

    track_artist = canonical_artist_key(
        track.artist,
        config.artist_aliases,
    )

    track_album_artist = canonical_artist_key(
        track.album_artist,
        config.artist_aliases,
    )

    entry_title = normalize_title(entry.title)
    track_title = normalize_title(track.title)


    artist_score = fuzz.ratio(
        entry_artist,
        track_artist,
    )

    album_artist_score = fuzz.ratio(
        entry_artist,
        track_album_artist,
    )

    title_score = max(
        fuzz.ratio(
            entry_title,
            track_title,
        ),
        fuzz.token_sort_ratio(
            entry_title,
            track_title,
        ),
        fuzz.token_set_ratio(
            entry_title,
            track_title,
        ),
    )

    #
    # Bonus for exact normalized title
    #

    #if normalize_key(entry.title) == normalize_key(track.title):
    #   title_score = 100.0
    if entry_title == track_title:
        title_score = 100.0

    #
    # Bonus for exact normalized artist
    #

    if entry_artist == track_artist:
        artist_score = 100.0

    combined = (
        artist_score * config.artist_weight
        + album_artist_score * config.album_artist_weight
        + title_score * config.title_weight
    )

    #
    # Small bonus if both artist and title are exact.
    #

    if (
        artist_score == 100
        and title_score == 100
    ):
        combined += (
            100 * config.combined_weight
        )

    return MatchScore(
        artist=artist_score,
        album_artist=album_artist_score,
        title=title_score,
        combined=min(100.0, combined),
    )

def _format_match(track: LibraryTrack) -> str:
    return (
        f"{track.artist} | "
        f"{track.title} | "
        f"{track.version} | "
        f"rk={track.rating_key}"
    )

# ----------------------------------------------------------
# Weed out similar titles that are clearly not the same song.
# ----------------------------------------------------------

def _title_similarity(
    entry: PlaylistEntry,
    track: LibraryTrack,
) -> float:
    entry_title = normalize_title(entry.title)
    track_title = normalize_title(track.title)

    return max(
        fuzz.ratio(entry_title, track_title),
        fuzz.token_sort_ratio(entry_title, track_title),
        fuzz.token_set_ratio(entry_title, track_title),
    )

# ----------------------------------------------------------
# Confidence helper
# ----------------------------------------------------------


def _confidence(score: float) -> ConfidenceLevel:
    """
    Convert a numeric score into a confidence level.
    """

    if score >= 99:
        return ConfidenceLevel.EXACT

    if score >= 95:
        return ConfidenceLevel.HIGH

    if score >= 90:
        return ConfidenceLevel.GOOD

    if score >= 85:
        return ConfidenceLevel.WEAK

    return ConfidenceLevel.NONE


# ----------------------------------------------------------
# Compatibility wrapper
# ----------------------------------------------------------


