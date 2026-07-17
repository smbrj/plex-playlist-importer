"""
User-maintained resource file loaders.

Resource files contain editable application data such as:
- artist aliases
- future version mappings
- future stopword lists
"""

from __future__ import annotations

import logging
from pathlib import Path


logger = logging.getLogger("plex_playlist")


def load_mapping_file(path: Path) -> dict[str, str]:
    """
    Load a simple key=value mapping file.

    Blank lines and lines beginning with '#' are ignored.
    Invalid lines are skipped with a warning.
    """

    path = Path(path)

    if not path.exists():
        logger.warning(
            "Resource file not found: %s; continuing with an empty mapping",
            path,
        )
        return {}

    mappings: dict[str, str] = {}

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                logger.warning(
                    "Ignoring invalid resource line %d in %s: %s",
                    line_number,
                    path,
                    line,
                )
                continue

            key, value = line.split("=", 1)

            key = key.strip()
            value = value.strip()

            if not key or not value:
                logger.warning(
                    "Ignoring incomplete resource line %d in %s",
                    line_number,
                    path,
                )
                continue

            mappings[key] = value

    return mappings


def load_artist_aliases(path: Path) -> dict[str, str]:
    """
    Load artist alias mappings.

    Expected format:
        alias = canonical artist
    """

    aliases = load_mapping_file(path)

    logger.info(
        "Loaded %d artist aliases from %s",
        len(aliases),
        path,
    )

    return aliases