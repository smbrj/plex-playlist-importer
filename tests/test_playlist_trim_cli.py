from pathlib import Path

SOURCE = Path("playlist_import_v2.py").read_text(encoding="utf-8")


def test_parser_defines_trim_with_config_fallback_semantics():
    assert '"--trim"' in SOURCE
    assert 'type=int' in SOURCE
    assert 'default=None' in SOURCE
    assert 'cfg.getint("playlist", "trim", fallback=0)' in SOURCE
