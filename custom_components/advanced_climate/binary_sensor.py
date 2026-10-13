"""Binary sensors for Advanced Climate."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AdvancedClimateConfigEntry
from .entity import HouseEntity, RoomEntity
from .house import House
from .room import Room


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdvancedClimateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    house = entry.runtime_data
    async_add_entities(
        [
            HouseBinarySensor(house, "heating_season", lambda h: h.season_active),
            HouseBinarySensor(house, "outdoor_cutoff", lambda h: h.cutoff_active),
            HouseBinarySensor(
                house, "heat_demand", lambda h: h.heat_demand, BinarySensorDeviceClass.HEAT
            ),
        ]
    )
    for room in house.rooms.values():
        async_add_entities(
            [
                RoomBinarySensor(
                    room, "heat_demand", lambda r: r.heat_demand, BinarySensorDeviceClass.HEAT
                ),
                RoomBinarySensor(
                    room, "window_open", lambda r: r.window_open, BinarySensorDeviceClass.WINDOW
                ),
                OverrideBinarySensor(room),
            ],
            config_subentry_id=room.id,
        )


class HouseBinarySensor(HouseEntity, BinarySensorEntity):
    """A boolean house state."""

    def __init__(
        self,
        house: House,
        key: str,
        value: Callable[[House], bool],
        device_class: BinarySensorDeviceClass | None = None,
    ) -> None:
        """Initialize."""
        super().__init__(house, key)
        self._value = value
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool:
        """State."""
        return self._value(self.house)


class RoomBinarySensor(RoomEntity, BinarySensorEntity):
    """A boolean room state."""

    def __init__(
        self,
        room: Room,
        key: str,
        value: Callable[[Room], bool],
        device_class: BinarySensorDeviceClass | None = None,
    ) -> None:
        """Initialize."""
        super().__init__(room, key)
        self._value = value
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool:
        """State."""
        return self._value(self.room)


class OverrideBinarySensor(RoomEntity, BinarySensorEntity):
    """On while a manual change is respected."""

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "manual_override")

    @property
    def is_on(self) -> bool:
        """State."""
        return self.room.override_active

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Details of the override."""
        return self.room.override_info()
