"""Sensors for Advanced Climate."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AdvancedClimateConfigEntry
from .const import PRESENCE_STATES, PRESETS, RULES
from .entity import HOUSE_ENTITY_KEYS, ROOM_ENTITY_KEYS, HouseEntity, RoomEntity, entity_map
from .house import House
from .room import Room
from .schedule import profiles_to_dict
from .util import iso


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdvancedClimateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    house = entry.runtime_data
    async_add_entities(
        [
            PresenceSensor(house),
            OutdoorAverageSensor(house),
            HouseRuntimeSensor(house),
        ]
    )
    for room in house.rooms.values():
        async_add_entities(
            [
                DecisionSensor(room),
                TargetTemperatureSensor(room),
                CurrentTemperatureSensor(room),
                NextChangeSensor(room),
                HeatingRateSensor(room),
                RoomRuntimeSensor(room),
            ],
            config_subentry_id=room.id,
        )


class PresenceSensor(HouseEntity, SensorEntity):
    """House presence: home / nearby / far."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(PRESENCE_STATES)
    _unrecorded_attributes = frozenset(
        {"advanced_climate_house", "entry_id", "house_name", "house_entities"}
    )

    def __init__(self, house: House) -> None:
        """Initialize."""
        super().__init__(house, "presence")

    @property
    def native_value(self) -> str | None:
        """Return the presence."""
        return self.house.presence_state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Details."""
        return {
            "persons": self.house.person_classes,
            "arriving": self.house.arriving,
            "guest_mode": self.house.guest,
            "vacation_active": self.house.vacation_active(),
            "pending": self.house.presence.pending,
            "pending_since": iso(self.house.presence.pending_since),
            "advanced_climate_house": True,
            "entry_id": self.house.entry.entry_id,
            "house_name": self.house.entry.title,
            "house_entities": entity_map(
                self.hass, self.house.entry.entry_id, HOUSE_ENTITY_KEYS
            ),
        }


class OutdoorAverageSensor(HouseEntity, SensorEntity):
    """Average outdoor temperature used by the cutoff."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 1

    def __init__(self, house: House) -> None:
        """Initialize."""
        super().__init__(house, "outdoor_average")

    @property
    def native_value(self) -> float | None:
        """Average outdoor temperature."""
        return self.house.outdoor_average

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Details."""
        return {
            "latest": self.house.outdoor.latest(),
            "cutoff_active": self.house.cutoff_active,
            "forecast_cutoff": self.house.forecast_cutoff,
            "heating_season": self.house.season_active,
        }


class HouseRuntimeSensor(HouseEntity, SensorEntity):
    """Total time the house asked for heat."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 2

    def __init__(self, house: House) -> None:
        """Initialize."""
        super().__init__(house, "heating_runtime")

    @property
    def native_value(self) -> float:
        """Hours."""
        return round(self.house.boiler_runtime_s / 3600, 3)


class DecisionSensor(RoomEntity, SensorEntity):
    """The rule that decides the room right now, with the reason."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(RULES)
    _unrecorded_attributes = frozenset(
        {
            "schedule",
            "presets",
            "preset_names",
            "levels",
            "climate_entities",
            "current_temperature",
            "day_boundary",
            "schedule_editable",
            "entry_id",
            "room_id",
            "entities",
            "house_entities",
            "house_name",
            "source",
            "custom_levels",
        }
    )

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "decision")

    @property
    def native_value(self) -> str:
        """Winning rule."""
        return self.room.rule

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Everything the card and automations need."""
        room = self.room
        decision = room.decision
        state = room.schedule_state
        return {
            "room_id": room.id,
            "entry_id": room.house.entry.entry_id,
            "room_name": room.name,
            "reason": decision.description if decision else None,
            "target_kind": decision.target.kind if decision else None,
            "preset": decision.target.preset if decision else None,
            "target_temperature": room.target_temperature,
            "current_temperature": room.current_temp,
            "offsets": [list(o) for o in decision.offsets] if decision else [],
            "presence": room.house.presence_state,
            "window_open": room.window_open,
            "override": room.override_info(),
            "profile": state.profile if state else None,
            "profile_select": room.profile_select,
            "next_change": iso(state.next_change) if state else None,
            "next_preset": state.next_preset if state else None,
            "schedule": profiles_to_dict(room.schedule.profiles),
            "schedule_error": room.schedule_error,
            "schedule_editable": room.config.get("schedule_source", "internal") == "internal",
            "presets": list(PRESETS),
            "preset_names": room.preset_names,
            "levels": {p: room.level_temp(p) for p in PRESETS},
            "climate_entities": room.climates,
            "device_preset": room.device_preset(),
            "heat_demand": room.heat_demand,
            "day_boundary": room.house.day_boundary_minutes,
            "source": room.source,
            "custom_levels": room.uses_custom_levels,
            "house_name": room.house.entry.title,
            "entities": entity_map(self.hass, room.id, ROOM_ENTITY_KEYS),
            "house_entities": entity_map(
                self.hass, room.house.entry.entry_id, HOUSE_ENTITY_KEYS
            ),
        }


class TargetTemperatureSensor(RoomEntity, SensorEntity):
    """The target temperature decided for the room."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "target_temperature")

    @property
    def native_value(self) -> float | None:
        """Target."""
        return self.room.target_temperature

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Preset."""
        decision = self.room.decision
        return {"preset": decision.target.preset if decision else None}


class CurrentTemperatureSensor(RoomEntity, SensorEntity):
    """The room temperature used by the integration."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "room_temperature")

    @property
    def native_value(self) -> float | None:
        """Room temperature."""
        return self.room.current_temp


class NextChangeSensor(RoomEntity, SensorEntity):
    """Next scheduled change."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "next_change")

    @property
    def native_value(self) -> datetime | None:
        """Moment of the next change."""
        state = self.room.schedule_state
        return state.next_change if state else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Next preset."""
        state = self.room.schedule_state
        return {
            "next_preset": state.next_preset if state else None,
            "profile": state.profile if state else None,
        }


class HeatingRateSensor(RoomEntity, SensorEntity):
    """Learned heating rate."""

    _attr_native_unit_of_measurement = "°C/h"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 2

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "heating_rate")

    @property
    def native_value(self) -> float:
        """Rate for the current outdoor temperature."""
        return round(self.room.learner.rate(self.house.outdoor.latest()), 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """All buckets."""
        return {"rates": self.room.learner.rates}


class RoomRuntimeSensor(RoomEntity, SensorEntity):
    """Total time the room asked for heat."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 2

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "heating_runtime")

    @property
    def native_value(self) -> float:
        """Hours."""
        return round(self.room.runtime_s / 3600, 3)
