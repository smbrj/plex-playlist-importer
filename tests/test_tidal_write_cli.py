import playlist_import_v2 as app


def test_parser_accepts_tidal_authorize_write():
    args = app.build_parser().parse_args(["--tidal-authorize-write"])
    assert args.tidal_authorize_write is True


def test_parser_accepts_tidal_write_test():
    args = app.build_parser().parse_args(["--tidal-write-test"])
    assert args.tidal_write_test is True
