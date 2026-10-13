"""Services for Advanced Climate."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.util import dt as dt_util

from .const import CONF_SCHEDULE, DOMAIN, PRESETS, SCHEDULE_INTERNAL, CONF_SCHEDULE_SOURCE
from .engine import KIND_PRESET, KIND_TEMPERATURE, Target
from .schedule import ScheduleError, format_schedule, parse_schedule, profiles_from_dict

if TYPE_CHECKING:
    from .house import House
    from .room import Room

ATTR_ROOM = "room"
ATTR_ENTITY = "entity_id"
ATTR_PRESET = "preset"
ATTR_TEMPERATURE = "temperature"
ATTR_HOURS = "duration_hours"
ATTR_START = "start"
ATTR_END = "end"
ATTR_SCHEDULE = "schedule"
ATTR_PROFILES = "profiles"
ATTR_ENTRY = "config_entry_id"

SERVICE_SET_OVERRIDE = "set_override"
SERVICE_CLEAR_OVERRIDE = "clear_override"
SERVICE_SET_VACATION = "set_vacation"
SERVICE_REEVALUATE = "reevaluate"
SERVICE_SET_SCHEDULE = "set_schedule"

ROOM_SELECTOR = {
    vol.Optional(ATTR_ROOM): cv.string,
    vol.Optional(ATTR_ENTITY): cv.entity_ids,
}

SET_OVERRIDE_SCHEMA = vol.Schema(
    {
        **ROOM_SELECTOR,
        vol.Optional(ATTR_PRESET): cv.string,
        vol.Optional(ATTR_TEMPERATURE): vol.Coerce(float),
        vol.Optional(ATTR_HOURS): vol.Coerce(float),
    }
)
CLEAR_OVERRIDE_SCHEMA = vol.Schema({**ROOM_SELECTOR})
SET_VACATION_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY): cv.string,
        vol.Optional(ATTR_START): cv.datetime,
        vol.Optional(ATTR_END): cv.datetime,
    }
)
REEVALUATE_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTRY): cv.string})
SET_SCHEDULE_SCHEMA = vol.Schema(
    {
        **ROOM_SELECTOR,
        vol.Optional(ATTR_SCHEDULE): cv.string,
        vol.Optional(ATTR_PROFILES): dict,
    }
)


def _local(value: datetime | None) -> datetime | None:
    """Naive datetimes are local time (the card sends local time)."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=dt_util.get_default_time_zone())
    return dt_util.as_local(value)


def _houses(hass: HomeAssistant) -> list[House]:
    return [
        entry.runtime_data
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]


def _house(hass: HomeAssistant, entry_id: str | None) -> House:
    houses = _houses(hass)
    if entry_id:
        for house in houses:
            if house.entry.entry_id == entry_id:
                return house
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="house_not_found",
            translation_placeholders={"entry": entry_id},
        )
    if len(houses) != 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="house_ambiguous"
        )
    return houses[0]


def _rooms(hass: HomeAssistant, call: ServiceCall, *, required: bool) -> list[Room]:
    """Find rooms by subentry id, name or any of their entities."""
    houses = _houses(hass)
    rooms: list[Room] = []
    wanted = call.data.get(ATTR_ROOM)
    if wanted:
        for house in houses:
            for room in house.rooms.values():
                if wanted in (room.id, room.name) or str(wanted).lower() == room.name.lower():
                    rooms.append(room)
    entity_ids = call.data.get(ATTR_ENTITY) or []
    if entity_ids:
        registry = er.async_get(hass)
        for entity_id in entity_ids:
            entry = registry.async_get(entity_id)
            if entry is None:
                continue
            for house in houses:
                for room in house.rooms.values():
                    if entry.config_subentry_id == room.id or entity_id in room.climates:
                        if room not in rooms:
                            rooms.append(room)
    if required and not rooms:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="room_not_found")
    if not wanted and not entity_ids and not required:
        rooms = [room for house in houses for room in house.rooms.values()]
    return rooms


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the services."""

    async def set_override(call: ServiceCall) -> None:
        preset = call.data.get(ATTR_PRESET)
        temperature = call.data.get(ATTR_TEMPERATURE)
        if (preset is None) == (temperature is None):
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="preset_or_temperature"
            )
        for room in _rooms(hass, call, required=True):
            if preset is not None:
                role = room.aliases.get(str(preset).lower())
                if role is None:
                    raise ServiceValidationError(
                        translation_domain=DOMAIN,
                        translation_key="unknown_preset",
                        translation_placeholders={"preset": str(preset)},
                    )
                target = Target(KIND_PRESET, preset=role)
            else:
                target = Target(KIND_TEMPERATURE, temperature=float(temperature))
            await room.async_apply_manual(target, call.data.get(ATTR_HOURS))
            await room.house.async_evaluate_or_notify()

    async def clear_override(call: ServiceCall) -> None:
        houses: set[House] = set()
        for room in _rooms(hass, call, required=False):
            room.clear_override()
            houses.add(room.house)
        for house in houses:
            await house.async_evaluate_or_notify()

    async def set_vacation(call: ServiceCall) -> None:
        house = _house(hass, call.data.get(ATTR_ENTRY))
        start = call.data.get(ATTR_START)
        end = call.data.get(ATTR_END)
        start = _local(start)
        end = _local(end)
        if start and end and end <= start:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="vacation_order"
            )
        await house.async_set_vacation(start, end)

    async def reevaluate(call: ServiceCall) -> None:
        entry_id = call.data.get(ATTR_ENTRY)
        houses = [_house(hass, entry_id)] if entry_id else _houses(hass)
        for house in houses:
            await house.async_evaluate_or_notify()

    async def set_schedule(call: ServiceCall) -> None:
        text = call.data.get(ATTR_SCHEDULE)
        profiles: Any = call.data.get(ATTR_PROFILES)
        if (text is None) == (profiles is None):
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="schedule_or_profiles"
            )
        for room in _rooms(hass, call, required=True):
            if room.config.get(CONF_SCHEDULE_SOURCE, SCHEDULE_INTERNAL) != SCHEDULE_INTERNAL:
                raise ServiceValidationError(
                    translation_domain=DOMAIN, translation_key="schedule_external"
                )
            valid_names = list(PRESETS) + list(room.preset_names.values())
            try:
                if profiles is not None:
                    parsed = profiles_from_dict(profiles, valid_names)
                else:
                    parsed = parse_schedule(str(text), valid_names)
            except (ScheduleError, KeyError, TypeError) as err:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="invalid_schedule",
                    translation_placeholders={"error": str(err)},
                ) from err
            entry = room.house.entry
            subentry = entry.subentries[room.id]
            hass.config_entries.async_update_subentry(
                entry,
                subentry,
                data={**subentry.data, CONF_SCHEDULE: format_schedule(parsed)},
            )
            # The update listener reloads the entry.

    hass.services.async_register(DOMAIN, SERVICE_SET_OVERRIDE, set_override, SET_OVERRIDE_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_OVERRIDE, clear_override, CLEAR_OVERRIDE_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_SET_VACATION, set_vacation, SET_VACATION_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_REEVALUATE, reevaluate, REEVALUATE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_SCHEDULE, set_schedule, SET_SCHEDULE_SCHEMA)
