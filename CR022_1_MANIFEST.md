# CR022.1 — FIFO Playlist Trim

Adds `[playlist] trim = 0` support and CLI `--trim N`.

- `0` = unlimited.
- Negative values are rejected.
- `--trim > 0` is rejected with `--replace` and `--sync`.
- CREATE/UPDATE perform the normal Plex operation first, then FIFO trim from the front.
- Duplicate playlist occurrences remain distinct.
- Existing oversized playlists are repaired even if the run adds no new tracks.
- Trim failure becomes a warning and does not roll back a successful update.
- Dry-run reports exact current/new-unique/after-update/remove/final counts without mutation.
- CP021 safety is preserved: destructive TIDAL handoff is filtered against the final post-trim Plex playlist membership.

Validation:
```powershell
python -m pytest tests/test_playlist_trim.py tests/test_playlist_trim_client.py tests/test_playlist_trim_cli.py tests/test_playlist_trim_handoff.py tests/test_playlist_trim_modes.py -v
python -m pytest -v
```

Suggested dry-run:
```powershell
python playlist_import_v2.py tidal-test.txt --playlist test-tidal --update --trim 1 --dry-run
```

## Configuration example

`config.example.ini` now includes:

```ini
[playlist]
trim = 0
```
