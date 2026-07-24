from pathlib import Path
SOURCE=Path('playlist_import_v2.py').read_text(encoding='utf-8')

def test_replace_sync_rejection_present():
    assert '--trim cannot currently be used with --replace or --sync' in SOURCE

def test_update_then_trim_then_tidal_execute_order():
    main=SOURCE[SOURCE.index('def main()'):]
    update=main.index('plex.update_playlist(')
    trim=main.index('plex.trim_playlist_fifo(',update)
    tidal=main.index('executor.execute(safe_pending_decisions)',trim)
    assert update < trim < tidal
