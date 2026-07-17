from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class HealthState(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    DISABLED = "DISABLED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_REQUIRED = "NOT_REQUIRED"


@dataclass(slots=True)
class ComponentHealth:
    state: HealthState
    detail: str = ""
    checked: bool = True



    @property
    def available(self) -> bool:
        return self.state == HealthState.AVAILABLE

    @classmethod
    def available_health(cls, detail: str = "") -> "ComponentHealth":
        return cls(HealthState.AVAILABLE, detail, True)

    @classmethod
    def unavailable(cls, detail: str = "") -> "ComponentHealth":
        return cls(HealthState.UNAVAILABLE, detail, True)

    @classmethod
    def disabled(cls, detail: str = "disabled") -> "ComponentHealth":
        return cls(HealthState.DISABLED, detail, False)

    @classmethod
    def not_configured(
        cls,
        detail: str = "not configured",
    ) -> "ComponentHealth":
        return cls(HealthState.NOT_CONFIGURED, detail, False)

    @classmethod
    def not_required(
        cls,
        detail: str = "not required",
    ) -> "ComponentHealth":
        return cls(HealthState.NOT_REQUIRED, detail, False)
    
    def __post_init__(self):
        if isinstance(self.state, bool):
            self.state = (
                HealthState.AVAILABLE
                if self.state
                else HealthState.UNAVAILABLE
            )


@dataclass(slots=True)
class RunStatus:
    cache: ComponentHealth = field(
        default_factory=lambda: ComponentHealth.unavailable("not checked")
    )
    plex: ComponentHealth = field(
        default_factory=lambda: ComponentHealth.unavailable("not checked")
    )
    lidarr: ComponentHealth = field(
        default_factory=lambda: ComponentHealth.not_required()
    )
    xmplaylist: ComponentHealth = field(
        default_factory=lambda: ComponentHealth.not_required()
    )
    tidal: ComponentHealth = field(
        default_factory=lambda: ComponentHealth.not_configured()
    )
    cache_state: str = "UNKNOWN"
    cache_age_hours: float | None = None
    cache_track_count: int = 0
    cache_refreshed: bool = False
    playlist_state: str = "NOT REQUESTED"
    stale_plex_matches: int = 0
    playlist_skip_reason: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)
