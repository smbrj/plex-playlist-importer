from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests

from plex_playlist.normalization import normalize_title


AUTH_URL = "https://auth.tidal.com/v1/oauth2/token"
API_BASE_URL = "https://openapi.tidal.com/v2"


class TidalError(RuntimeError):
    """Base error for supported TIDAL client failures."""


class TidalAuthenticationError(TidalError):
    """Raised when client-credentials authentication fails."""


class TidalRequestError(TidalError):
    """Raised when a TIDAL API request fails."""


@dataclass(frozen=True)
class TidalTrackCandidate:
    track_id: str
    artist: str
    title: str
    album: str
    quality: str | None = None
    version: str = ""
    explicit: bool = False


@dataclass(frozen=True)
class TidalHydrationFailure:
    track_id: str
    error: str


class TidalClient:
    """Minimal read-only client for Phase 1 TIDAL catalogue access."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        country_code: str = "US",
        timeout: float = 20.0,
        session: requests.Session | None = None,
        auth_url: str = AUTH_URL,
        api_base_url: str = API_BASE_URL,
        hydration_delay_seconds: float = 0.25,
    ) -> None:
        if not client_id.strip():
            raise ValueError("TIDAL client_id is required")
        if not client_secret.strip():
            raise ValueError("TIDAL client_secret is required")

        self.client_id = client_id
        self.client_secret = client_secret
        self.country_code = country_code.strip().upper() or "US"
        self.timeout = timeout
        self.session = session or requests.Session()
        self.auth_url = auth_url.rstrip("/")
        self.api_base_url = api_base_url.rstrip("/")
        if hydration_delay_seconds < 0:
            raise ValueError("TIDAL hydration_delay_seconds cannot be negative")
        self.hydration_delay_seconds = float(hydration_delay_seconds)

        self._access_token: str | None = None
        self._token_expires_at: float = 0.0
        self.last_hydration_failures: tuple[TidalHydrationFailure, ...] = ()

    def _get_access_token(self) -> str:
        # Refresh a little early to avoid expiring during a request.
        if self._access_token and time.time() < self._token_expires_at - 30:
            return self._access_token

        basic = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode("utf-8")
        ).decode("ascii")

        try:
            response = self.session.post(
                self.auth_url,
                headers={"Authorization": f"Basic {basic}"},
                data={"grant_type": "client_credentials"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TidalAuthenticationError(
                f"TIDAL authentication request failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise TidalAuthenticationError(
                f"TIDAL authentication failed with HTTP {response.status_code}"
            )

        try:
            payload = response.json()
            token = str(payload["access_token"])
            expires_in = int(payload.get("expires_in", 300))
        except (KeyError, TypeError, ValueError) as exc:
            raise TidalAuthenticationError(
                "TIDAL authentication response was missing token data"
            ) from exc

        self._access_token = token
        self._token_expires_at = time.time() + max(expires_in, 1)
        return token

    def search_tracks(self, artist: str, title: str) -> list[TidalTrackCandidate]:
        query = f"{artist} {title}".strip()
        if not query:
            return []

        token = self._get_access_token()
        encoded_query = quote(query, safe="")
        url = f"{self.api_base_url}/searchResults/{encoded_query}"

        try:
            response = self.session.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.api+json",
                },
                params={
                    "countryCode": self.country_code,
                    "include": "tracks,artists,albums",
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TidalRequestError(f"TIDAL track search failed: {exc}") from exc

        if response.status_code >= 400:
            detail = ""
            try:
                payload = response.json()
                detail = str(payload)[:500]
            except (ValueError, TypeError):
                detail = str(getattr(response, "text", ""))[:500]

            suffix = f": {detail}" if detail else ""
            raise TidalRequestError(
                f"TIDAL track search failed with HTTP "
                f"{response.status_code}{suffix}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise TidalRequestError("TIDAL returned invalid JSON") from exc

        sparse_candidates = _parse_search_candidates(payload)

        requested_title_key = normalize_title(title)
        hydrated: list[TidalTrackCandidate] = []
        hydration_failures: list[TidalHydrationFailure] = []
        self.last_hydration_failures = ()

        hydration_count = 0
        for candidate in sparse_candidates:
            if normalize_title(candidate.title) != requested_title_key:
                hydrated.append(candidate)
                continue

            if hydration_count > 0 and self.hydration_delay_seconds > 0:
                time.sleep(self.hydration_delay_seconds)
            hydration_count += 1

            try:
                hydrated.append(self.get_track(candidate.track_id))
            except TidalRequestError as exc:
                # Preserve the sparse search result for diagnostics, but record
                # that the catalogue lookup is incomplete. Callers must not
                # negative-cache a NO_MATCH derived from incomplete hydration.
                hydration_failures.append(
                    TidalHydrationFailure(
                        track_id=candidate.track_id,
                        error=str(exc),
                    )
                )
                hydrated.append(candidate)

        self.last_hydration_failures = tuple(hydration_failures)
        return hydrated


    def get_track(self, track_id: str) -> TidalTrackCandidate:
        """Retrieve one track with artist and album relationships included."""
        token = self._get_access_token()
        url = f"{self.api_base_url}/tracks/{quote(str(track_id), safe='')}"

        try:
            response = self.session.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.api+json",
                },
                params={
                    "countryCode": self.country_code,
                    "include": "artists,albums",
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TidalRequestError(
                f"TIDAL track detail request failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise TidalRequestError(
                f"TIDAL track detail failed with HTTP {response.status_code}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise TidalRequestError(
                "TIDAL track detail returned invalid JSON"
            ) from exc

        return _parse_track_document(payload, expected_id=str(track_id))


def _resource_map(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    resources: dict[tuple[str, str], dict[str, Any]] = {}
    for resource in payload.get("included", []) or []:
        rtype = str(resource.get("type", ""))
        rid = str(resource.get("id", ""))
        if rtype and rid:
            resources[(rtype, rid)] = resource
    return resources


def _relationship_ids(
    resource: dict[str, Any],
    relationship_name: str,
) -> list[tuple[str, str]]:
    relationships = resource.get("relationships") or {}
    relationship = relationships.get(relationship_name) or {}
    data = relationship.get("data")

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []

    result: list[tuple[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        rtype = str(item.get("type", ""))
        rid = str(item.get("id", ""))
        if rtype and rid:
            result.append((rtype, rid))
    return result


def _first_related_attribute(
    track: dict[str, Any],
    resource_map: dict[tuple[str, str], dict[str, Any]],
    relationship_name: str,
    attribute_name: str,
) -> str:
    for key in _relationship_ids(track, relationship_name):
        related = resource_map.get(key)
        if not related:
            continue
        value = (related.get("attributes") or {}).get(attribute_name)
        if value:
            return str(value)
    return ""


def _candidate_quality(attributes: dict[str, Any]) -> str | None:
    media_tags = attributes.get("mediaTags")
    if isinstance(media_tags, list) and media_tags:
        return ",".join(str(item) for item in media_tags)

    # Backward-tolerant fallbacks for older response shapes.
    for key in ("audioQuality", "quality", "mediaMetadata"):
        value = attributes.get(key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, dict):
            for nested_key in ("audioQuality", "quality", "tags"):
                nested = value.get(nested_key)
                if isinstance(nested, str) and nested:
                    return nested
                if isinstance(nested, list) and nested:
                    return ",".join(str(item) for item in nested)
    return None


def _parse_track_document(
    payload: dict[str, Any],
    *,
    expected_id: str,
) -> TidalTrackCandidate:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise TidalRequestError("TIDAL track detail response had no track data")

    track_id = str(data.get("id", "")).strip()
    if not track_id:
        track_id = expected_id

    attributes = data.get("attributes") or {}
    resources = _resource_map(payload)

    artist = _first_related_attribute(
        data, resources, "artists", "name"
    )
    album = _first_related_attribute(
        data, resources, "albums", "title"
    )

    return TidalTrackCandidate(
        track_id=track_id,
        artist=artist,
        title=str(attributes.get("title", "")).strip(),
        album=album,
        quality=_candidate_quality(attributes),
        version=str(attributes.get("version", "") or "").strip(),
        explicit=attributes.get("explicit") is True,
    )



def _parse_search_candidates(
    payload: dict[str, Any],
) -> list[TidalTrackCandidate]:
    resources = _resource_map(payload)

    tracks: list[dict[str, Any]] = [
        resource
        for (rtype, _), resource in resources.items()
        if rtype in {"tracks", "track"}
    ]

    # Some JSON:API responses can place the requested resource directly in data.
    direct_data = payload.get("data")
    if isinstance(direct_data, list):
        tracks.extend(
            item
            for item in direct_data
            if isinstance(item, dict)
            and str(item.get("type", "")) in {"tracks", "track"}
        )

    seen: set[str] = set()
    candidates: list[TidalTrackCandidate] = []

    for track in tracks:
        track_id = str(track.get("id", "")).strip()
        if not track_id or track_id in seen:
            continue

        attributes = track.get("attributes") or {}
        title = str(attributes.get("title", "")).strip()

        artist = _first_related_attribute(
            track, resources, "artists", "name"
        )
        album = _first_related_attribute(
            track, resources, "albums", "title"
        )

        # Be tolerant if the schema embeds these directly.
        artist = artist or str(attributes.get("artist", "")).strip()
        album = album or str(attributes.get("album", "")).strip()

        if not title:
            continue

        seen.add(track_id)
        candidates.append(
            TidalTrackCandidate(
                track_id=track_id,
                artist=artist,
                title=title,
                album=album,
                quality=_candidate_quality(attributes),
                version=str(attributes.get("version", "") or "").strip(),
                explicit=attributes.get("explicit") is True,
            )
        )

    return candidates
