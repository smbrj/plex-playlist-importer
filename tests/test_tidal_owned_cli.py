import pytest
import playlist_import_v2 as app


def test_temporary_tidal_mark_test_owned_flag_is_removed():
    with pytest.raises(SystemExit) as exc:
        app.build_parser().parse_args(["--tidal-mark-test-owned"])
    assert exc.value.code == 2
