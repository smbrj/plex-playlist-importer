from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any
from uuid import uuid4

import requests

from plex_playlist.tidal_user_auth import TidalUserTokenProvider


API_BASE_URL = "https://openapi.tidal.com/v2"


class TidalAccountError(RuntimeError):
    """Raised when a user-context TIDAL API request fails."""


@dataclass(frozen=True)
class TidalUserPlaylist:
    playlist_id: str
    name: str


@dataclass(frozen=True)
class TidalPlaylistRelationshipItem:
    item_type: str
    item_id: str
    meta: dict[str, Any]


@dataclass(frozen=True)
class TidalAccountSummary:
    playlists: tuple[TidalUserPlaylist, ...]
    favorite_track_count: int


class TidalAccountClient:
    """User-context TIDAL API client with explicit playlist mutation methods."""

    def __init__(
        self,
        *,
        token_provider: TidalUserTokenProvider,
        country_code: str = "US",
        timeout: float = 20.0,
        session: requests.Session | None = None,
        api_base_url: str = API_BASE_URL,
        rate_limit_retries: int = 3,
        rate_limit_fallback_seconds: float = 5.0,
    ) -> None:
        self.token_provider = token_provider
        self.country_code = country_code.strip().upper() or "US"
        self.timeout = timeout
        self.session = session or requests.Session()
        self.api_base_url = api_base_url.rstrip("/")
        self.rate_limit_retries = max(int(rate_limit_retries), 0)
        self.rate_limit_fallback_seconds = max(
            float(rate_limit_fallback_seconds),
            0.1,
        )

    def _headers(self, *, idempotency_key: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.token_provider.access_token()}",
            "Accept": "application/vnd.api+json",
        }
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    def _response_error(self, response: requests.Response, url: str) -> TidalAccountError:
        detail = ""
        try:
            detail = str(response.json())[:500]
        except (ValueError, TypeError):
            detail = str(getattr(response, "text", ""))[:500]
        suffix = f": {detail}" if detail else ""
        return TidalAccountError(
            f"TIDAL account request failed with HTTP "
            f"{response.status_code} for {url}{suffix}"
        )

    def _retry_after_seconds(
        self,
        response: requests.Response,
        attempt: int,
    ) -> float:
        headers = getattr(response, "headers", {}) or {}
        raw = headers.get("Retry-After")
        if raw is not None:
            try:
                return max(float(raw), 0.1)
            except (TypeError, ValueError):
                pass
        return self.rate_limit_fallback_seconds * (2 ** attempt)

    def _request_with_rate_limit_retry(
        self,
        request_func,
        url: str,
        **kwargs,
    ):
        attempt = 0
        while True:
            response = request_func(url, **kwargs)
            if response.status_code != 429:
                return response
            if attempt >= self.rate_limit_retries:
                return response
            time.sleep(self._retry_after_seconds(response, attempt))
            attempt += 1

    def _get_json(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        try:
            response = self._request_with_rate_limit_retry(
                self.session.get,
                url,
                headers=self._headers(),
                params=params,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TidalAccountError(
                f"TIDAL account request failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise self._response_error(response, url)

        try:
            payload = response.json()
        except ValueError as exc:
            raise TidalAccountError(
                "TIDAL account API returned invalid JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise TidalAccountError(
                "TIDAL account API returned an unexpected document."
            )
        return payload

    def _resolve_next_url(self, next_url: str | None) -> str:
        if not next_url:
            return ""

        value = str(next_url).strip()
        if value.startswith("http://") or value.startswith("https://"):
            return value

        if value.startswith("/"):
            value = value[1:]

        return f"{self.api_base_url}/{value}"

    def create_playlist(
        self,
        name: str,
        *,
        description: str = "",
        access_type: str = "UNLISTED",
    ) -> TidalUserPlaylist:
        playlist_name = name.strip()
        if not playlist_name:
            raise ValueError("TIDAL playlist name must not be empty")

        url = f"{self.api_base_url}/playlists"
        payload = {
            "data": {
                "type": "playlists",
                "attributes": {
                    "name": playlist_name,
                    "description": description,
                    "accessType": access_type,
                },
            }
        }
        try:
            response = self._request_with_rate_limit_retry(
                self.session.post,
                url,
                headers={
                    **self._headers(idempotency_key=str(uuid4())),
                    "Content-Type": "application/vnd.api+json",
                },
                params={"countryCode": self.country_code},
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TidalAccountError(
                f"TIDAL playlist create request failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise self._response_error(response, url)

        try:
            document = response.json()
            data = document["data"]
            attributes = data.get("attributes") or {}
            return TidalUserPlaylist(
                playlist_id=str(data["id"]),
                name=str(attributes.get("name", playlist_name)).strip(),
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise TidalAccountError(
                "TIDAL playlist create response was invalid."
            ) from exc

    def get_playlist(self, playlist_id: str) -> TidalUserPlaylist:
        url = f"{self.api_base_url}/playlists/{playlist_id}"
        payload = self._get_json(
            url,
            params={"countryCode": self.country_code},
        )
        try:
            data = payload["data"]
            attributes = data.get("attributes") or {}
            return TidalUserPlaylist(
                playlist_id=str(data["id"]),
                name=str(attributes.get("name", "")).strip(),
            )
        except (KeyError, TypeError) as exc:
            raise TidalAccountError(
                "TIDAL playlist response was invalid."
            ) from exc

    def delete_playlist(self, playlist_id: str) -> None:
        url = f"{self.api_base_url}/playlists/{playlist_id}"
        try:
            response = self._request_with_rate_limit_retry(
                self.session.delete,
                url,
                headers=self._headers(idempotency_key=str(uuid4())),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TidalAccountError(
                f"TIDAL playlist delete request failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise self._response_error(response, url)

    def list_playlist_relationship_items(
        self,
        playlist_id: str,
    ) -> list[TidalPlaylistRelationshipItem]:
        value = str(playlist_id).strip()
        if not value:
            raise ValueError("TIDAL playlist ID must not be empty")

        url = f"{self.api_base_url}/playlists/{value}/relationships/items"
        params: dict[str, str] | None = {
            "countryCode": self.country_code,
        }
        items: list[TidalPlaylistRelationshipItem] = []

        while url:
            payload = self._get_json(url, params=params)
            params = None

            data = payload.get("data", []) or []
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue

                    item_type = str(item.get("type", "")).strip()
                    item_id = str(item.get("id", "")).strip()
                    if not item_type or not item_id:
                        continue

                    raw_meta = item.get("meta")
                    meta = dict(raw_meta) if isinstance(raw_meta, dict) else {}

                    items.append(
                        TidalPlaylistRelationshipItem(
                            item_type=item_type,
                            item_id=item_id,
                            meta=meta,
                        )
                    )

            links = payload.get("links") or {}
            url = self._resolve_next_url(links.get("next"))

        return items

    def list_playlist_track_ids(self, playlist_id: str) -> set[str]:
        return {
            item.item_id
            for item in self.list_playlist_relationship_items(playlist_id)
            if item.item_type == "tracks"
        }

    def add_playlist_tracks(
        self,
        playlist_id: str,
        track_ids: list[str] | tuple[str, ...],
    ) -> None:
        playlist_value = str(playlist_id).strip()
        if not playlist_value:
            raise ValueError("TIDAL playlist ID must not be empty")

        unique_ids: list[str] = []
        seen: set[str] = set()
        for raw in track_ids:
            value = str(raw).strip()
            if not value or value in seen:
                continue
            seen.add(value)
            unique_ids.append(value)

        if not unique_ids:
            return

        url = (
            f"{self.api_base_url}/playlists/"
            f"{playlist_value}/relationships/items"
        )
        payload = {
            "data": [
                {
                    "type": "tracks",
                    "id": track_id,
                }
                for track_id in unique_ids
            ]
        }

        try:
            response = self._request_with_rate_limit_retry(
                self.session.post,
                url,
                headers={
                    **self._headers(idempotency_key=str(uuid4())),
                    "Content-Type": "application/vnd.api+json",
                },
                params={"countryCode": self.country_code},
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TidalAccountError(
                f"TIDAL playlist item add request failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise self._response_error(response, url)

    def remove_playlist_tracks(
        self,
        playlist_id: str,
        track_ids: list[str] | tuple[str, ...],
    ) -> None:
        playlist_value = str(playlist_id).strip()
        if not playlist_value:
            raise ValueError("TIDAL playlist ID must not be empty")

        requested: list[str] = []
        seen: set[str] = set()
        for raw in track_ids:
            value = str(raw).strip()
            if not value or value in seen:
                continue
            seen.add(value)
            requested.append(value)

        if not requested:
            return

        requested_set = set(requested)
        relationship_items = self.list_playlist_relationship_items(
            playlist_value
        )

        delete_data: list[dict[str, Any]] = []
        found_ids: set[str] = set()

        for item in relationship_items:
            if item.item_type != "tracks":
                continue
            if item.item_id not in requested_set:
                continue

            if not item.meta:
                raise TidalAccountError(
                    "TIDAL playlist relationship item is missing required "
                    f"meta for track {item.item_id}; refusing to synthesize "
                    "a destructive DELETE payload."
                )

            delete_data.append(
                {
                    "type": item.item_type,
                    "id": item.item_id,
                    "meta": item.meta,
                }
            )
            found_ids.add(item.item_id)

        missing = [track_id for track_id in requested if track_id not in found_ids]
        if missing:
            raise TidalAccountError(
                "Requested TIDAL playlist track(s) were not present in the "
                "server relationship response: "
                + ", ".join(missing)
            )

        url = (
            f"{self.api_base_url}/playlists/"
            f"{playlist_value}/relationships/items"
        )
        payload = {"data": delete_data}

        try:
            response = self._request_with_rate_limit_retry(
                self.session.delete,
                url,
                headers={
                    **self._headers(idempotency_key=str(uuid4())),
                    "Content-Type": "application/vnd.api+json",
                },
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TidalAccountError(
                f"TIDAL playlist item remove request failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise self._response_error(response, url)

    def list_owned_playlists(self) -> list[TidalUserPlaylist]:
        url = f"{self.api_base_url}/playlists"
        params: dict[str, str] | None = {
            "filter[owners.id]": "me",
            "countryCode": self.country_code,
        }
        playlists: list[TidalUserPlaylist] = []

        while url:
            payload = self._get_json(url, params=params)
            params = None

            for item in payload.get("data", []) or []:
                if not isinstance(item, dict):
                    continue
                attributes = item.get("attributes") or {}
                playlists.append(
                    TidalUserPlaylist(
                        playlist_id=str(item.get("id", "")),
                        name=str(attributes.get("name", "")).strip(),
                    )
                )

            links = payload.get("links") or {}
            next_url = links.get("next")
            url = self._resolve_next_url(next_url)

        return playlists

    def list_favorite_track_ids(self) -> set[str]:
        """Return all track IDs currently present in the user's favorites."""
        url = (
            f"{self.api_base_url}"
            "/userCollectionTracks/me/relationships/items"
        )
        params: dict[str, str] | None = {
            "countryCode": self.country_code,
        }
        track_ids: set[str] = set()

        while url:
            payload = self._get_json(url, params=params)
            params = None

            data = payload.get("data", []) or []
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    if str(item.get("type", "")) != "tracks":
                        continue
                    track_id = str(item.get("id", "")).strip()
                    if track_id:
                        track_ids.add(track_id)

            links = payload.get("links") or {}
            url = self._resolve_next_url(links.get("next"))

        return track_ids

    def is_favorite_track(self, track_id: str) -> bool:
        value = str(track_id).strip()
        if not value:
            raise ValueError("TIDAL track ID must not be empty")
        return value in self.list_favorite_track_ids()

    def add_favorite_track(self, track_id: str) -> None:
        value = str(track_id).strip()
        if not value:
            raise ValueError("TIDAL track ID must not be empty")

        url = (
            f"{self.api_base_url}"
            "/userCollectionTracks/me/relationships/items"
        )
        payload = {
            "data": [
                {
                    "type": "tracks",
                    "id": value,
                }
            ]
        }

        try:
            response = self._request_with_rate_limit_retry(
                self.session.post,
                url,
                headers={
                    **self._headers(idempotency_key=str(uuid4())),
                    "Content-Type": "application/vnd.api+json",
                },
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TidalAccountError(
                f"TIDAL favorite-track add request failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise self._response_error(response, url)

        # TIDAL may return HTTP 200 with skipped items in meta. Treat a skipped
        # NOT_FOUND result as a failed mutation; ALREADY_PRESENT is acceptable.
        try:
            document = response.json()
        except ValueError:
            document = {}

        if isinstance(document, dict):
            meta = document.get("meta") or {}
            skipped = meta.get("skipped") or []
            for item in skipped:
                if not isinstance(item, dict):
                    continue
                if str(item.get("id", "")) != value:
                    continue
                reason = str(item.get("reason", "")).upper()
                if reason == "NOT_FOUND":
                    raise TidalAccountError(
                        f"TIDAL track {value} was not found while adding favorite."
                    )

    def remove_favorite_track(self, track_id: str) -> None:
        value = str(track_id).strip()
        if not value:
            raise ValueError("TIDAL track ID must not be empty")

        url = (
            f"{self.api_base_url}"
            "/userCollectionTracks/me/relationships/items"
        )
        payload = {
            "data": [
                {
                    "type": "tracks",
                    "id": value,
                }
            ]
        }

        try:
            response = self._request_with_rate_limit_retry(
                self.session.delete,
                url,
                headers={
                    **self._headers(idempotency_key=str(uuid4())),
                    "Content-Type": "application/vnd.api+json",
                },
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TidalAccountError(
                f"TIDAL favorite-track remove request failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise self._response_error(response, url)

    def count_favorite_tracks(self) -> int:
        url = (
            f"{self.api_base_url}"
            "/userCollectionTracks/me/relationships/items"
        )
        params: dict[str, str] | None = {
            "countryCode": self.country_code,
        }
        count = 0

        while url:
            payload = self._get_json(url, params=params)
            params = None
            data = payload.get("data", []) or []
            if isinstance(data, list):
                count += len(data)

            links = payload.get("links") or {}
            next_url = links.get("next")
            url = self._resolve_next_url(next_url)

        return count

    def summary(self) -> TidalAccountSummary:
        return TidalAccountSummary(
            playlists=tuple(self.list_owned_playlists()),
            favorite_track_count=self.count_favorite_tracks(),
        )
