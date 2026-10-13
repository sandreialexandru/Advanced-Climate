"""Base entities for Advanced Climate."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, SIGNAL_UPDATE
from .house import House
from .room import Room


class HouseEntity(Entity):
    """Entity attached to the house device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, house: House, key: str) -> None:
        """Initialize."""
        self.house = house
        self._attr_translation_key = key
        self._attr_unique_id = f"{house.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, house.entry.entry_id)},
            name=house.entry.title,
            manufacturer="Advanced Climate",
            model="House",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE.format(self.house.entry.entry_id),
                self.async_write_ha_state,
            )
        )


class RoomEntity(Entity):
    """Entity attached to a room device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, room: Room, key: str) -> None:
        """Initialize."""
        self.room = room
        self.house = room.house
        self._attr_translation_key = key
        self._attr_unique_id = f"{room.id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, room.id)},
            name=room.name,
            manufacturer="Advanced Climate",
            model="Room",
            entry_type=DeviceEntryType.SERVICE,
            via_device=(DOMAIN, room.house.entry.entry_id),
            suggested_area=room.area_name,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE.format(self.house.entry.entry_id),
                self.async_write_ha_state,
            )
        )
