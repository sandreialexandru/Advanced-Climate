"""Vacation start / end for Advanced Climate."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import AdvancedClimateConfigEntry
from .entity import HouseEntity
from .house import House


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdvancedClimateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up datetime entities."""
    house = entry.runtime_data
    async_add_entities([VacationDateTime(house, "start"), VacationDateTime(house, "end")])


class VacationDateTime(HouseEntity, DateTimeEntity):
    """Vacation start or end."""

    def __init__(self, house: House, which: str) -> None:
        """Initialize."""
        super().__init__(house, f"vacation_{which}")
        self.which = which

    @property
    def native_value(self) -> datetime | None:
        """Value."""
        return self.house.vacation_start if self.which == "start" else self.house.vacation_end

    async def async_set_value(self, value: datetime) -> None:
        """Set the value."""
        value = dt_util.as_local(value)
        if self.which == "start":
            await self.house.async_set_vacation(value, None, partial=True)
        else:
            await self.house.async_set_vacation(None, value, partial=True)
