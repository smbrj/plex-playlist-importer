import playlist_import_v2 as app


def test_parser_accepts_tidal_favorite_test():
    args = app.build_parser().parse_args(["--tidal-favorite-test"])
    assert args.tidal_favorite_test is True
