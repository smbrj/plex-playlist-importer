from plex_playlist.runtime import ComponentHealth, HealthState


def test_health_states_are_explicit() -> None:
    health = ComponentHealth.available_health("ok")
    assert health.available is True
    assert health.state == HealthState.AVAILABLE

    disabled = ComponentHealth.disabled()
    assert disabled.available is False
    assert disabled.state == HealthState.DISABLED
    assert disabled.checked is False
