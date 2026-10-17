"""Sensors for Advanced Climate."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import AdvancedClimateConfigEntry
from .const import DOMAIN, PRESENCE_STATES, PRESETS, RULES
from .entity import HOUSE_ENTITY_KEYS, ROOM_ENTITY_KEYS, HouseEntity, RoomEntity, entity_map
from .house import House
from .learning import start_gap
from .util import delta_from_celsius, from_celsius
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
                CoolingRateSensor(room),
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
            "vacation_preheating": self.house.vacation_preheating(),
            "pending": self.house.presence.pending,
            "pending_since": iso(self.house.presence.pending_since),
            "advanced_climate_house": True,
            "temperature_unit": self.house.unit,
            "entry_id": self.house.entry.entry_id,
            "house_name": self.house.entry.title,
            "house_entities": entity_map(
                self.hass, self.house.entry.entry_id, HOUSE_ENTITY_KEYS
            ),
        }


def _t(value: float | None, unit: str, digits: int = 2) -> float | None:
    """A temperature kept in °C in the unit of the house."""
    value = from_celsius(value, unit)
    return None if value is None else round(value, digits)


def _d(value: float | None, unit: str, digits: int = 2) -> float | None:
    """A temperature difference kept in °C in the unit of the house."""
    value = delta_from_celsius(value, unit)
    return None if value is None else round(value, digits)


class _HouseUnitTemperature(SensorEntity):
    """Temperature sensor shown in the unit chosen for the house."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    house: House

    @property
    def native_unit_of_measurement(self) -> str:
        """The unit of the house."""
        return self.house.unit

    async def async_added_to_hass(self) -> None:
        """Show the value in the unit of the house, not the one of Home Assistant.

        The unit is set when the sensor is new or the unit of the house changes; a
        display unit chosen later in the entity settings is kept.
        """
        await super().async_added_to_hass()
        registry = er.async_get(self.hass)
        entry = registry.async_get(self.entity_id)
        if entry is None:
            return
        applied = (entry.options.get(DOMAIN) or {}).get("unit")
        if applied == self.house.unit:
            return
        registry.async_update_entity_options(
            self.entity_id,
            "sensor",
            {**(entry.options.get("sensor") or {}), "unit_of_measurement": self.house.unit},
        )
        registry.async_update_entity_options(
            self.entity_id, DOMAIN, {**(entry.options.get(DOMAIN) or {}), "unit": self.house.unit}
        )


class OutdoorAverageSensor(HouseEntity, _HouseUnitTemperature):
    """Average outdoor temperature used by the cutoff."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 1

    def __init__(self, house: House) -> None:
        """Initialize."""
        super().__init__(house, "outdoor_average")

    @property
    def native_value(self) -> float | None:
        """Average outdoor temperature."""
        return _t(self.house.outdoor_average, self.house.unit)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Details."""
        return {
            "latest": _t(self.house.outdoor_now, self.house.unit),
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
            "device_levels",
            "plan",
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
        unit = room.house.unit
        return {
            "room_id": room.id,
            "entry_id": room.house.entry.entry_id,
            "room_name": room.name,
            "reason": decision.description if decision else None,
            "target_kind": decision.target.kind if decision else None,
            "preset": decision.target.preset if decision else None,
            "temperature_unit": unit,
            "target_temperature": _t(room.target_temperature, unit),
            "current_temperature": _t(room.current_temp, unit),
            "offsets": [[label, _d(delta, unit)] for label, delta in decision.offsets]
            if decision
            else [],
            "presence": room.house.presence_state,
            "window_open": room.window_open,
            "override": room.override_info(),
            "profile": state.profile if state else None,
            "profile_select": room.profile_select,
            "next_change": iso(state.next_change) if state else None,
            "next_preset": state.next_preset if state else None,
            "plan": room.plan(dt_util.utcnow()),
            "schedule": profiles_to_dict(room.schedule.profiles),
            "schedule_error": room.schedule_error,
            "schedule_editable": room.config.get("schedule_source", "internal") == "internal",
            "presets": list(PRESETS),
            "preset_names": room.preset_names,
            "levels": {p: _t(room.level_temp(p), unit, 1) for p in PRESETS},
            "min_temperature": _t(room.frost_temp(), unit, 1),
            "max_temperature": _t(room.max_temp(), unit, 1),
            "climate_entities": room.climates,
            "device_preset": room.device_preset(),
            "device_level": room.level_of_device_preset(room.device_preset()),
            "time_to_target": room.time_to_target(room.house.outdoor_now),
            "stop_forecast": _forecast(room, unit),
            "optimal_stop_cancelled": room.stop_cancelled,
            "rate_learned": bool(room.learner.episodes),
            "device_levels": room.device_levels,
            "heat_demand": room.heat_demand,
            "heating": room.heating,
            "day_boundary": room.house.day_boundary_minutes,
            "source": room.source,
            "custom_levels": room.uses_custom_levels,
            "house_name": room.house.entry.title,
            "entities": entity_map(self.hass, room.id, ROOM_ENTITY_KEYS),
            "house_entities": entity_map(
                self.hass, room.house.entry.entry_id, HOUSE_ENTITY_KEYS
            ),
        }


class TargetTemperatureSensor(RoomEntity, _HouseUnitTemperature):
    """The target temperature decided for the room."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "target_temperature")

    @property
    def native_value(self) -> float | None:
        """Target."""
        return _t(self.room.target_temperature, self.house.unit)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Preset."""
        decision = self.room.decision
        return {"preset": decision.target.preset if decision else None}


class CurrentTemperatureSensor(RoomEntity, _HouseUnitTemperature):
    """The room temperature used by the integration."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "room_temperature")

    @property
    def native_value(self) -> float | None:
        """Room temperature."""
        return _t(self.room.current_temp, self.house.unit)


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

    _unrecorded_attributes = frozenset({"rates", "last_episodes"})

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 2

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "heating_rate")

    @property
    def native_unit_of_measurement(self) -> str:
        """Degrees of the house per hour."""
        return f"{self.house.unit}/h"

    @property
    def native_value(self) -> float | None:
        """Rate for the current outdoor temperature."""
        return _d(self.room.learner.rate(self.house.outdoor_now), self.house.unit, 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """All buckets."""
        learner = self.room.learner
        line = learner.fit()
        unit = self.house.unit
        # Estimates at round outdoor temperatures of the unit of the house.
        points = (14, 32, 50, 68) if unit == "°F" else (-10, 0, 10, 20)
        return {
            "rates": (
                {
                    f"{t}{unit}": _d(learner.rate((t - 32) / 1.8 if unit == "°F" else t), unit, 3)
                    for t in points
                }
                if learner.episodes
                else {}
            ),
            "episodes": len(learner.episodes),
            "per_degree_outdoor": round(line[1], 3) if line else None,
            "learning_starts_below_target": _d(start_gap(self.room.learn_tolerance()), unit),
            "last_episodes": [
                {"outdoor": _t(o, unit, 1), "rate": _d(r, unit, 3), "at": at or None}
                for o, r, at in learner.episodes[-5:]
            ],
        }


def _forecast(room: Room, unit: str) -> dict[str, Any] | None:
    """Expected temperature at the scheduled change during an optimal stop."""
    forecast = room.stop_forecast(dt_util.utcnow(), room.house.outdoor_now)
    if forecast is None:
        return None
    return {"at": forecast["at"], "temperature": _t(forecast["temperature"], unit, 1)}


class CoolingRateSensor(RoomEntity, SensorEntity):
    """Learned cooling: how fast the room falls now without heating."""

    _unrecorded_attributes = frozenset({"last_episodes"})

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 2

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "cooling_rate")

    @property
    def native_unit_of_measurement(self) -> str:
        """Degrees of the house per hour."""
        return f"{self.house.unit}/h"

    @property
    def native_value(self) -> float | None:
        """Fall per hour for the current room and outdoor temperatures."""
        rate = self.room.cooling.rate(self.room.current_temp, self.house.outdoor_now)
        return _d(rate, self.house.unit, 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Learned coefficient and the last episodes."""
        cooling = self.room.cooling
        unit = self.house.unit
        return {
            "coefficient_per_hour": cooling.coefficient,
            "episodes": len(cooling.episodes),
            "optimal_stop_tolerance": _d(self.room.stop_tolerance(), unit),
            "last_episodes": [
                {"outdoor": _t(o, unit, 1), "coefficient": k, "at": at or None}
                for o, k, at in cooling.episodes[-5:]
            ],
        }


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
