"""Numbers for Advanced Climate: level temperatures (rooms without GT)."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AdvancedClimateConfigEntry
from .const import CONF_NEARBY_MODE, NEARBY_TEMPERATURE, PRESETS
from .entity import RoomEntity
from .room import Room


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdvancedClimateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up numbers."""
    house = entry.runtime_data
    for room in house.rooms.values():
        entities: list[NumberEntity] = []
        if room.uses_custom_levels:
            entities += [LevelNumber(room, preset) for preset in PRESETS]
        if room.config.get(CONF_NEARBY_MODE) == NEARBY_TEMPERATURE:
            entities.append(LevelNumber(room, "nearby"))
        if entities:
            async_add_entities(entities, config_subentry_id=room.id)


class LevelNumber(RoomEntity, NumberEntity):
    """Temperature of one level."""

    _attr_device_class = None
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = 5.0
    _attr_native_max_value = 30.0
    _attr_native_step = 0.5
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, room: Room, preset: str) -> None:
        """Initialize."""
        super().__init__(room, f"level_{preset}")
        self.preset = preset
        if preset != "nearby" and room.preset_names.get(preset, preset) != preset:
            # Custom level name chosen by the user.
            self._attr_translation_key = "level_custom"
            self._attr_translation_placeholders = {"name": room.preset_names[preset]}

    @property
    def native_value(self) -> float:
        """Current value."""
        if self.preset == "nearby":
            return self.room.nearby_temp
        return self.room.levels[self.preset]

    async def async_set_native_value(self, value: float) -> None:
        """Set the level temperature."""
        await self.room.async_set_level(self.preset, value)
