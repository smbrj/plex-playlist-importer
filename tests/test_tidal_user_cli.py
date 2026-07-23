import playlist_import_v2 as app


def test_parser_accepts_tidal_authorize():
    args = app.build_parser().parse_args(["--tidal-authorize"])
    assert args.tidal_authorize is True


def test_parser_accepts_tidal_account_test():
    args = app.build_parser().parse_args(["--tidal-account-test"])
    assert args.tidal_account_test is True
