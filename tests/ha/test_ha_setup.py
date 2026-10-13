"""Set up a house with a relay room and check the control loop."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.advanced_climate.const import DOMAIN, SUBENTRY_ROOM


async def _setup(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> MockConfigEntry:
    await hass.config.async_set_time_zone("Europe/Bucharest")
    # Monday 12:00 local time.
    freezer.move_to("2026-10-12 09:00:00+00:00")
    assert await async_setup_component(hass, "input_boolean", {"input_boolean": {"heater": {}}})
    hass.states.async_set("sensor.room_temp", "18.0", {"unit_of_measurement": "°C"})
    hass.states.async_set("person.andrei", "home")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        options={"persons": ["person.andrei"], "nearby_zones": []},
        subentries_data=[
            {
                "data": {
                    "source": "switch",
                    "switches": ["input_boolean.heater"],
                    "temperature_sensors": ["sensor.room_temp"],
                    "min_on_minutes": 0,
                    "min_off_minutes": 0,
                },
                "subentry_type": SUBENTRY_ROOM,
                "title": "Bedroom",
                "unique_id": None,
            }
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _tick(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float) -> None:
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()


async def test_relay_room(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """The relay follows the schedule, presence and mode."""
    entry = await _setup(hass, freezer)
    assert hass.states.get("sensor.bedroom_decision").state == "starting"

    await _tick(hass, freezer, 15)
    decision = hass.states.get("sensor.bedroom_decision")
    assert decision.state == "schedule"
    assert decision.attributes["preset"] == "home"
    assert hass.states.get("sensor.bedroom_target_temperature").state == "21.0"
    assert hass.states.get("input_boolean.heater").state == "on"
    assert hass.states.get("sensor.home_presence").state == "home"

    # Warm room: the relay turns off.
    hass.states.async_set("sensor.room_temp", "21.5", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 5)
    assert hass.states.get("input_boolean.heater").state == "off"

    # Summer mode.
    await hass.services.async_call(
        "select", "select_option",
        {"entity_id": "select.home_mode", "option": "summer"}, blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bedroom_decision").state == "summer"

    # Service: manual temperature for one hour.
    await hass.services.async_call(
        "select", "select_option",
        {"entity_id": "select.home_mode", "option": "auto"}, blocking=True,
    )
    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Bedroom", "temperature": 23, "duration_hours": 1},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bedroom_decision").state == "manual_override"
    assert hass.states.get("binary_sensor.bedroom_manual_change").state == "on"

    await hass.services.async_call(DOMAIN, "clear_override", {"room": "Bedroom"}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bedroom_decision").state == "schedule"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_set_schedule_service(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """The card saves schedules through the service."""
    entry = await _setup(hass, freezer)
    await _tick(hass, freezer, 15)
    await hass.services.async_call(
        DOMAIN,
        "set_schedule",
        {"room": "Bedroom", "profiles": {"workday": [{"time": "00:00", "preset": "eco"}]}},
        blocking=True,
    )
    await hass.async_block_till_done()
    subentry = next(iter(entry.subentries.values()))
    assert subentry.data["schedule"] == "workday: 00:00 eco"
    await _tick(hass, freezer, 15)
    assert hass.states.get("sensor.bedroom_decision").attributes["preset"] == "eco"
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
