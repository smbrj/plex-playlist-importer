# Technical Cleanup Checkpoint-005

**Date:** 2026-07-22  
**Scope:** Add documented `.m3u8` playlist input support

## Production Change

`plex_playlist/parser.py` now recognizes `.m3u8` as a supported playlist
extension and dispatches it through the existing `parse_m3u()` implementation.

This brings the implementation into conformance with Documentation V1.0,
which already documented M3U8 support.

## Regression Coverage

Added `tests/test_m3u8_parser.py` covering:

- `.m3u8` EXTINF parsing.
- Equivalence between `.m3u` and `.m3u8` dispatch behavior.

## Required Validation After Extraction

Run:

```powershell
python -m pytest tests/test_m3u8_parser.py -v
python -m pytest -v
```

The full suite must remain green before Documentation V1.1 maintenance begins.
