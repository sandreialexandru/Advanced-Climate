"""Set up a house with a relay room and check the control loop."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from homeassistant.core import Context
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.advanced_climate.const import DOMAIN, SUBENTRY_ROOM


async def _setup(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, **extra: object
) -> MockConfigEntry:
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
                    **extra,
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


async def test_levels_from_room_settings(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Temperatures chosen in the room settings are used and shown as numbers."""
    entry = await _setup(hass, freezer, levels={"home": 22.5, "sleep": 18.5})
    await _tick(hass, freezer, 15)
    assert hass.states.get("sensor.bedroom_target_temperature").state == "22.5"
    assert hass.states.get("number.bedroom_level_home").state == "22.5"
    decision = hass.states.get("sensor.bedroom_decision")
    assert decision.attributes["device_levels"] == []
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_set_schedule_service(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """The card saves schedules through the service."""
    entry = await _setup(hass, freezer)
    await _tick(hass, freezer, 15)
    seen: list[str] = []
    hass.bus.async_listen(
        "state_changed",
        lambda event: seen.append(event.data["new_state"].state)
        if event.data["entity_id"] == "sensor.bedroom_decision" and event.data["new_state"]
        else None,
    )
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
    # Saving a schedule does not reload the integration.
    assert "unavailable" not in seen
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_card_resource(hass: HomeAssistant) -> None:
    """The card is added to (and kept up to date in) the dashboard resources."""
    from custom_components.advanced_climate.const import CARD_URL
    from custom_components.advanced_climate.frontend import (
        async_ensure_lovelace_resource,
        async_remove_lovelace_resource,
        lovelace_resources,
    )

    assert await async_setup_component(hass, "lovelace", {})
    resources = lovelace_resources(hass)
    assert resources is not None
    assert await async_ensure_lovelace_resource(hass, f"{CARD_URL}?v=1.0.0")
    assert await async_ensure_lovelace_resource(hass, f"{CARD_URL}?v=1.1.1")
    mine = [i for i in resources.async_items() if i["url"].startswith(CARD_URL)]
    assert len(mine) == 1
    assert mine[0]["url"] == f"{CARD_URL}?v=1.1.1"
    assert mine[0]["type"] == "module"
    await async_remove_lovelace_resource(hass)
    assert not [i for i in resources.async_items() if i["url"].startswith(CARD_URL)]


async def test_fahrenheit_house(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """A house in °F: sensors, levels, card attributes and services use °F; values kept in °C."""
    await hass.config.async_set_time_zone("Europe/Bucharest")
    freezer.move_to("2026-10-12 09:00:00+00:00")
    assert await async_setup_component(hass, "input_boolean", {"input_boolean": {"heater": {}}})
    # 64.4 °F = 18 °C
    hass.states.async_set("sensor.room_temp", "64.4", {"unit_of_measurement": "°F"})
    hass.states.async_set("person.andrei", "home")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        options={"persons": ["person.andrei"], "nearby_zones": [], "temperature_unit": "fahrenheit"},
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
    await _tick(hass, freezer, 15)

    decision = hass.states.get("sensor.bedroom_decision")
    assert decision.attributes["temperature_unit"] == "°F"
    assert decision.attributes["current_temperature"] == 64.4
    # Level home = 21 °C = 69.8 °F
    assert decision.attributes["target_temperature"] == 69.8
    assert decision.attributes["levels"]["home"] == 69.8
    target = hass.states.get("sensor.bedroom_target_temperature")
    assert target.attributes["unit_of_measurement"] == "°F"
    assert float(target.state) == 69.8
    assert hass.states.get("input_boolean.heater").state == "on"
    level = hass.states.get("number.bedroom_level_home")
    assert level.attributes["unit_of_measurement"] == "°F"
    assert float(level.state) == 69.8

    # A manual temperature is given in °F.
    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Bedroom", "temperature": 72, "duration_hours": 1},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bedroom_decision").attributes["target_temperature"] == 72.0

    # Setting a level in °F stores it in °C.
    await hass.services.async_call(
        "number", "set_value", {"entity_id": "number.bedroom_level_home", "value": 71.6},
        blocking=True,
    )
    await hass.async_block_till_done()
    room = entry.runtime_data.rooms[next(iter(entry.subentries))]
    assert round(room.levels["home"], 2) == 22.0
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_late_device_report_is_not_manual(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A TRV that confirms a command later (new context) is not a manual change."""
    await hass.config.async_set_time_zone("Europe/Bucharest")
    freezer.move_to("2026-10-12 09:00:00+00:00")
    calls = async_mock_service(hass, "climate", "set_temperature")
    trv = {
        "hvac_modes": ["heat", "off"],
        "current_temperature": 18.0,
        "temperature": 17.0,
        "target_temp_step": 0.5,
    }
    hass.states.async_set("climate.trv", "heat", trv)
    hass.states.async_set("person.andrei", "home")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        options={"persons": ["person.andrei"], "nearby_zones": []},
        subentries_data=[
            {
                "data": {"source": "climate", "climates": ["climate.trv"], "command_mode": "temperature"},
                "subentry_type": SUBENTRY_ROOM,
                "title": "Office",
                "unique_id": None,
            }
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await _tick(hass, freezer, 15)
    assert calls and calls[-1].data["temperature"] == 21.0

    # The device reports the new set point a minute later, with its own context.
    await _tick(hass, freezer, 60)
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 21.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert hass.states.get("binary_sensor.office_manual_change").state == "off"
    assert hass.states.get("sensor.office_decision").state == "schedule"

    # A person changes it: respected.
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 23.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert hass.states.get("binary_sensor.office_manual_change").state == "on"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_vacation_end_only_and_preheat(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Only an end date starts the vacation now; before the end the schedule applies."""
    entry = await _setup(hass, freezer)
    await _tick(hass, freezer, 15)
    hass.states.async_set("person.andrei", "not_home")
    await _tick(hass, freezer, 11 * 60)
    assert hass.states.get("sensor.home_presence").state == "far"

    end = dt_util.now() + timedelta(hours=10)
    await hass.services.async_call(DOMAIN, "set_vacation", {"end": end}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bedroom_decision").state == "vacation"

    # 4 h before the end (default): the schedule, although nobody is near.
    await _tick(hass, freezer, 6 * 3600 + 60)
    decision = hass.states.get("sensor.bedroom_decision")
    assert decision.state == "schedule", decision.attributes["reason"]
    assert "preheating" in decision.attributes["reason"]
    assert hass.states.get("sensor.home_presence").attributes["vacation_preheating"] is True

    # After the end: presence again (far = away).
    await _tick(hass, freezer, 4 * 3600)
    assert hass.states.get("sensor.bedroom_decision").state == "presence_far"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
