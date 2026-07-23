import playlist_import_v2 as app


def test_supported_tidal_diagnostics_remain_available():
    parser = app.build_parser()

    assert parser.parse_args(["--tidal-search", "Steely Dan", "Peg"]).tidal_search
    assert parser.parse_args(["--tidal-authorize"]).tidal_authorize is True
    assert parser.parse_args(["--tidal-authorize-write"]).tidal_authorize_write is True
    assert parser.parse_args(["--tidal-account-test"]).tidal_account_test is True
    assert parser.parse_args(["--tidal-write-test"]).tidal_write_test is True
    assert parser.parse_args(["--tidal-favorite-test"]).tidal_favorite_test is True
    assert parser.parse_args(["--tidal-favorite-cleanup"]).tidal_favorite_cleanup is True
