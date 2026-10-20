"""Select for Advanced Climate: the global mode."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AdvancedClimateConfigEntry
from .const import MODES
from .entity import HouseEntity
from .house import House


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdvancedClimateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up selects."""
    house = entry.runtime_data
    async_add_entities([ModeSelect(house)])


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
