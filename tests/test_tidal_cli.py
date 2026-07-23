from pathlib import Path

import playlist_import_v2 as app


def test_parser_accepts_tidal_search():
    args = app.build_parser().parse_args(
        ["--tidal-search", "Steely Dan", "Peg"]
    )
    assert args.tidal_search == ["Steely Dan", "Peg"]
    assert args.input_file is None
