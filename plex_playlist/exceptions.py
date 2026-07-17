"""
Custom exceptions used throughout the application.
"""


class PlaylistImporterError(Exception):
    """Base application exception."""


class ConfigError(PlaylistImporterError):
    """Invalid configuration."""


class PlexConnectionError(PlaylistImporterError):
    """Unable to connect to Plex."""


class PlexLibraryError(PlaylistImporterError):
    """Music library not found."""


class PlaylistError(PlaylistImporterError):
    """Playlist operation failed."""


class MatchingError(PlaylistImporterError):
    """Matching engine failure."""


class CacheError(PlaylistImporterError):
    """Cache failure."""


class LidarrError(PlaylistImporterError):
    """Lidarr API failure."""