# Checkpoint-021a — TIDAL refresh-token client identification

## Live failure

TIDAL returned:

```text
HTTP 400
invalid_request
Missing parameters: client_id
```

during access-token refresh.

## Fix

`refresh_user_tokens()` now requires and submits:

```text
grant_type=refresh_token
refresh_token=<stored refresh token>
client_id=<configured TIDAL client id>
```

`TidalUserTokenProvider` now stores the configured client ID and supplies it
whenever an expired access token is refreshed.

All production provider construction sites read `client_id` from `[tidal]`.

No client secret is sent during refresh.

## Token rotation

If TIDAL returns a replacement refresh token, it is stored.

If TIDAL omits a replacement refresh token, PPI retains the previous refresh
token through the existing fallback behavior.

## Scope

CP021 handoff ordering and reconciliation logic are unchanged.

## Validation

```powershell
python -m pytest tests/test_tidal_refresh_auth.py tests/test_tidal_user_auth.py -v
python -m pytest -v
```

Then:

```powershell
python playlist_import_v2.py --tidal-account-test
```

If successful, retry:

```powershell
python playlist_import_v2.py tidal-test.txt --playlist test-tidal
```
