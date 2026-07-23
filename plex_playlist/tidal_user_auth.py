from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
import webbrowser
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Event
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import requests


AUTHORIZE_URL = "https://login.tidal.com/authorize"
TOKEN_URL = "https://auth.tidal.com/v1/oauth2/token"

READ_SCOPES = (
    "playlists.read",
    "collection.read",
    "user.read",
)

WRITE_SCOPES = (
    "playlists.read",
    "playlists.write",
    "collection.read",
    "collection.write",
    "user.read",
)


class TidalUserAuthError(RuntimeError):
    """Raised when TIDAL user authorization cannot be completed."""


@dataclass(frozen=True)
class TidalUserTokens:
    access_token: str
    refresh_token: str
    expires_at: float
    scope: str = ""
    token_type: str = "Bearer"

    def is_access_token_valid(self, *, skew_seconds: int = 60) -> bool:
        return bool(self.access_token) and time.time() < self.expires_at - skew_seconds


class TidalTokenStore:
    """Small local credential store for OAuth user tokens."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def save(self, tokens: TidalUserTokens) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(asdict(tokens), indent=2),
            encoding="utf-8",
        )
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def load(self) -> TidalUserTokens:
        if not self.path.exists():
            raise TidalUserAuthError(
                f"TIDAL user token store not found: {self.path}"
            )

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return TidalUserTokens(
                access_token=str(payload["access_token"]),
                refresh_token=str(payload.get("refresh_token", "")),
                expires_at=float(payload["expires_at"]),
                scope=str(payload.get("scope", "")),
                token_type=str(payload.get("token_type", "Bearer")),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise TidalUserAuthError(
                f"Invalid TIDAL token store: {self.path}"
            ) from exc


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def build_authorization_url(
    *,
    client_id: str,
    redirect_uri: str,
    scopes: tuple[str, ...] = READ_SCOPES,
    state: str,
    code_challenge: str,
) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def exchange_authorization_code(
    *,
    client_id: str,
    code: str,
    redirect_uri: str,
    code_verifier: str,
    timeout: float = 20.0,
    session: requests.Session | None = None,
) -> TidalUserTokens:
    session = session or requests.Session()
    try:
        response = session.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            },
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise TidalUserAuthError(
            f"TIDAL authorization-code exchange failed: {exc}"
        ) from exc

    return _parse_token_response(response)


def refresh_user_tokens(
    *,
    refresh_token: str,
    timeout: float = 20.0,
    session: requests.Session | None = None,
) -> TidalUserTokens:
    if not refresh_token:
        raise TidalUserAuthError(
            "No TIDAL refresh token is available; authorize again."
        )

    session = session or requests.Session()
    try:
        response = session.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise TidalUserAuthError(
            f"TIDAL refresh-token request failed: {exc}"
        ) from exc

    return _parse_token_response(
        response,
        fallback_refresh_token=refresh_token,
    )


def _parse_token_response(
    response: requests.Response,
    *,
    fallback_refresh_token: str = "",
) -> TidalUserTokens:
    if response.status_code >= 400:
        detail = ""
        try:
            detail = str(response.json())[:500]
        except (ValueError, TypeError):
            detail = str(getattr(response, "text", ""))[:500]
        suffix = f": {detail}" if detail else ""
        raise TidalUserAuthError(
            f"TIDAL token request failed with HTTP "
            f"{response.status_code}{suffix}"
        )

    try:
        payload: dict[str, Any] = response.json()
        access_token = str(payload["access_token"])
        refresh_token = str(
            payload.get("refresh_token") or fallback_refresh_token
        )
        expires_in = int(payload.get("expires_in", 3600))
    except (KeyError, TypeError, ValueError) as exc:
        raise TidalUserAuthError(
            "TIDAL token response was missing required fields."
        ) from exc

    return TidalUserTokens(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=time.time() + max(expires_in, 1),
        scope=str(payload.get("scope", "")),
        token_type=str(payload.get("token_type", "Bearer")),
    )


class TidalUserTokenProvider:
    """Loads persisted user tokens and refreshes access automatically."""

    def __init__(
        self,
        *,
        store: TidalTokenStore,
        timeout: float = 20.0,
        session: requests.Session | None = None,
    ) -> None:
        self.store = store
        self.timeout = timeout
        self.session = session or requests.Session()

    def access_token(self) -> str:
        tokens = self.store.load()
        if tokens.is_access_token_valid():
            return tokens.access_token

        refreshed = refresh_user_tokens(
            refresh_token=tokens.refresh_token,
            timeout=self.timeout,
            session=self.session,
        )
        self.store.save(refreshed)
        return refreshed.access_token


class _CallbackHandler(BaseHTTPRequestHandler):
    callback_result: dict[str, str] = {}
    callback_event: Event | None = None

    def do_GET(self) -> None:  # noqa: N802
        query = parse_qs(urlparse(self.path).query)
        result = {
            key: values[0]
            for key, values in query.items()
            if values
        }
        type(self).callback_result = result

        body = (
            "TIDAL authorization received. "
            "You may close this browser window and return to PPI."
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

        if type(self).callback_event is not None:
            type(self).callback_event.set()

    def log_message(self, fmt: str, *args: object) -> None:
        return


def authorize_interactively(
    *,
    client_id: str,
    redirect_uri: str,
    token_store: TidalTokenStore,
    timeout_seconds: int = 180,
    request_timeout: float = 20.0,
    scopes: tuple[str, ...] = READ_SCOPES,
) -> TidalUserTokens:
    parsed = urlparse(redirect_uri)
    if parsed.scheme != "http" or parsed.hostname not in {
        "127.0.0.1",
        "localhost",
    }:
        raise TidalUserAuthError(
            "Phase 2 authorization currently requires a loopback redirect URI "
            "using http://127.0.0.1:<port>/... or http://localhost:<port>/..."
        )
    if parsed.port is None:
        raise TidalUserAuthError(
            "TIDAL redirect_uri must include an explicit local port."
        )

    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(24)
    url = build_authorization_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scopes=scopes,
        state=state,
        code_challenge=challenge,
    )

    callback_event = Event()
    _CallbackHandler.callback_event = callback_event
    _CallbackHandler.callback_result = {}

    server = HTTPServer((parsed.hostname, parsed.port), _CallbackHandler)
    server.timeout = 1

    print("Opening TIDAL authorization in your browser...")
    print(f"Redirect URI: {redirect_uri}")
    print("If the browser does not open, use this URL:")
    print(url)

    webbrowser.open(url)

    deadline = time.time() + timeout_seconds
    try:
        while time.time() < deadline and not callback_event.is_set():
            server.handle_request()
    finally:
        server.server_close()

    if not callback_event.is_set():
        raise TidalUserAuthError(
            "Timed out waiting for the TIDAL authorization callback."
        )

    result = _CallbackHandler.callback_result
    if result.get("state") != state:
        raise TidalUserAuthError("TIDAL authorization state mismatch.")
    if "error" in result:
        raise TidalUserAuthError(
            f"TIDAL authorization was rejected: {result.get('error')}"
        )

    code = result.get("code", "")
    if not code:
        raise TidalUserAuthError(
            "TIDAL authorization callback did not contain a code."
        )

    tokens = exchange_authorization_code(
        client_id=client_id,
        code=code,
        redirect_uri=redirect_uri,
        code_verifier=verifier,
        timeout=request_timeout,
    )
    token_store.save(tokens)
    return tokens
