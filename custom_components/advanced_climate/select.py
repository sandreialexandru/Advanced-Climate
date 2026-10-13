"""Selects for Advanced Climate: global mode and room profile."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AdvancedClimateConfigEntry
from .const import MODES
from .entity import HouseEntity, RoomEntity
from .house import House
from .room import Room


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdvancedClimateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up selects."""
    house = entry.runtime_data
    async_add_entities([ModeSelect(house)])
    for room in house.rooms.values():
        async_add_entities([ProfileSelect(room)], config_subentry_id=room.id)


class ModeSelect(HouseEntity, SelectEntity):
    """Global mode: auto / vacation / off / summer."""

    _attr_options = list(MODES)

    def __init__(self, house: House) -> None:
        """Initialize."""
        super().__init__(house, "mode")

    @property
    def current_option(self) -> str:
        """Current mode."""
        return self.house.mode

    async def async_select_option(self, option: str) -> None:
        """Change the mode."""
        await self.house.async_set_mode(option)


class ProfileSelect(RoomEntity, SelectEntity):
    """Schedule profile: auto or a fixed profile."""

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "profile")

    @property
    def options(self) -> list[str]:
        """Auto plus the profile names."""
        return self.room.profile_options

    @property
    def current_option(self) -> str:
        """Selected profile."""
        return self.room.profile_select

    async def async_select_option(self, option: str) -> None:
        """Select a profile."""
        await self.room.async_set_profile(option)
