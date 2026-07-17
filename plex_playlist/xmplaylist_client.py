from __future__ import annotations

from dataclasses import dataclass
import logging
from time import perf_counter
from typing import Any

from plex_playlist.runtime import ComponentHealth
from urllib.parse import parse_qs, urlparse

import requests

logger = logging.getLogger("plex_playlist")


class XMPlaylistError(RuntimeError):
    """Raised when XMPlaylist returns invalid data or an HTTP failure."""


@dataclass(frozen=True, slots=True)
class XMPlaylistStation:
    id: str
    number: int
    name: str
    deeplink: str

    @property
    def plex_playlist_name(self) -> str:
        return f"Ch {self.number} - {self.name}"


@dataclass(frozen=True, slots=True)
class XMPlaylistPlay:
    id: str
    timestamp: str
    track_id: str
    title: str
    artists: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class XMPlaylistHistoryPage:
    station: XMPlaylistStation
    plays: tuple[XMPlaylistPlay, ...]
    next_cursor: str | None


class XMPlaylistClient:
    """Minimal client for the public XMPlaylist station endpoints."""

    def __init__(
        self,
        *,
        base_url: str = "https://xmplaylist.com",
        timeout_seconds: float = 20.0,
        user_agent: str = "plex-playlist-importer/1.0",
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        normalized_agent = str(user_agent or "").strip()
        if not normalized_agent:
            raise ValueError("user_agent must not be empty")

        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": normalized_agent,
        })
        self._stations_cache: list[XMPlaylistStation] | None = None

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        started = perf_counter()
        url = f"{self.base_url}/{path.lstrip('/')}"

        try:
            response = self.session.request(
                method,
                url,
                timeout=self.timeout_seconds,
                **kwargs,
            )

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "")
                suffix = (
                    f"; retry after {retry_after} seconds"
                    if retry_after
                    else ""
                )
                raise XMPlaylistError(
                    f"XMPlaylist rate limit exceeded{suffix}"
                )

            response.raise_for_status()

        except XMPlaylistError:
            raise
        except requests.RequestException as exc:
            raise XMPlaylistError(
                f"XMPlaylist request failed: {method} {path}: {exc}"
            ) from exc
        finally:
            logger.info(
                "XMPlaylist API %s %s completed in %.2f sec",
                method,
                path,
                perf_counter() - started,
            )

        if not response.content:
            raise XMPlaylistError(
                f"XMPlaylist returned an empty response for {path}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise XMPlaylistError(
                f"XMPlaylist returned invalid JSON for {path}"
            ) from exc

    def is_available(self) -> ComponentHealth:
        """Verify XMPlaylist reachability and station discovery."""

        try:
            stations = self.get_stations()
        except Exception as exc:
            return ComponentHealth.unavailable(str(exc))

        if not stations:
            return ComponentHealth.unavailable(
                "XMPlaylist returned no visible stations"
            )

        return ComponentHealth.available_health(
            f"station discovery available ({len(stations)} stations)"
        )

    def get_stations(self) -> list[XMPlaylistStation]:
        if self._stations_cache is not None:
            return list(self._stations_cache)

        payload = self._request("GET", "api/station")
        results = _results_list(payload, "station list")

        stations: list[XMPlaylistStation] = []
        for item in results:
            try:
                number = int(str(item.get("number", "")).strip())
            except (TypeError, ValueError):
                continue

            name = str(item.get("name", "") or "").strip()
            deeplink = str(item.get("deeplink", "") or "").strip().lower()
            station_id = str(item.get("id", "") or "").strip()

            if not name or not deeplink:
                continue

            stations.append(
                XMPlaylistStation(
                    id=station_id,
                    number=number,
                    name=name,
                    deeplink=deeplink,
                )
            )

        self._stations_cache = stations
        return list(stations)

    def resolve_station(self, station_number: int) -> XMPlaylistStation:
        normalized_number = int(station_number)
        matches = [
            station
            for station in self.get_stations()
            if station.number == normalized_number
        ]

        if not matches:
            raise XMPlaylistError(
                f"XMPlaylist station {normalized_number} was not found"
            )

        if len(matches) > 1:
            names = ", ".join(station.name for station in matches)
            raise XMPlaylistError(
                "XMPlaylist returned multiple visible stations for "
                f"channel {normalized_number}: {names}"
            )

        return matches[0]

    def get_history_page(
        self,
        station: XMPlaylistStation,
        *,
        last: str | None = None,
    ) -> XMPlaylistHistoryPage:
        params = {"last": last} if last else None
        payload = self._request(
            "GET",
            f"api/station/{station.deeplink}",
            params=params,
        )

        if not isinstance(payload, dict):
            raise XMPlaylistError(
                "XMPlaylist station history returned an unexpected response"
            )

        channel_payload = payload.get("channel")
        returned_station = (
            _parse_station(channel_payload)
            if isinstance(channel_payload, dict)
            else station
        )

        plays: list[XMPlaylistPlay] = []
        for item in _results_list(payload, "station history"):
            track = item.get("track")
            if not isinstance(track, dict):
                continue

            title = str(track.get("title", "") or "").strip()
            raw_artists = track.get("artists")
            if isinstance(raw_artists, list):
                artists = tuple(
                    str(value).strip()
                    for value in raw_artists
                    if str(value).strip()
                )
            elif isinstance(raw_artists, str):
                artists = (raw_artists.strip(),) if raw_artists.strip() else ()
            else:
                artists = ()

            timestamp = str(item.get("timestamp", "") or "").strip()
            if not title or not artists or not timestamp:
                continue

            plays.append(
                XMPlaylistPlay(
                    id=str(item.get("id", "") or ""),
                    timestamp=timestamp,
                    track_id=str(track.get("id", "") or ""),
                    title=title,
                    artists=artists,
                )
            )

        return XMPlaylistHistoryPage(
            station=returned_station,
            plays=tuple(plays),
            next_cursor=_cursor_from_next(payload.get("next")),
        )


def _results_list(
    payload: Any,
    description: str,
) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise XMPlaylistError(
            f"XMPlaylist {description} returned an unexpected response"
        )

    results = payload.get("results")
    if not isinstance(results, list):
        raise XMPlaylistError(
            f"XMPlaylist {description} did not contain a results list"
        )

    return [item for item in results if isinstance(item, dict)]


def _parse_station(item: dict[str, Any]) -> XMPlaylistStation:
    try:
        number = int(str(item.get("number", "")).strip())
    except (TypeError, ValueError) as exc:
        raise XMPlaylistError(
            "XMPlaylist channel payload has an invalid station number"
        ) from exc

    name = str(item.get("name", "") or "").strip()
    deeplink = str(item.get("deeplink", "") or "").strip().lower()
    if not name or not deeplink:
        raise XMPlaylistError(
            "XMPlaylist channel payload is missing name or deeplink"
        )

    return XMPlaylistStation(
        id=str(item.get("id", "") or ""),
        number=number,
        name=name,
        deeplink=deeplink,
    )


def _cursor_from_next(value: Any) -> str | None:
    if value is None:
        return None

    next_url = str(value).strip()
    if not next_url:
        return None

    query = parse_qs(urlparse(next_url).query)
    cursors = query.get("last", [])
    if not cursors:
        raise XMPlaylistError(
            "XMPlaylist next URL did not contain a last cursor"
        )

    cursor = str(cursors[0]).strip()
    return cursor or None
