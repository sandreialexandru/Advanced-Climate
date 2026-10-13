"""Diagnostics for Advanced Climate."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import AdvancedClimateConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AdvancedClimateConfigEntry
) -> dict[str, Any]:
    """Return configuration, state and the last decisions of every room."""
    house = entry.runtime_data
    return {
        "options": dict(entry.options),
        "rooms": {
            sub.subentry_id: {"title": sub.title, "data": dict(sub.data)}
            for sub in entry.subentries.values()
        },
        "state": house.diagnostics(),
    }
