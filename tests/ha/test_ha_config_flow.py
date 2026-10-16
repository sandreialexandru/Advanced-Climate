"""Config flow and room subentry flow tests."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.advanced_climate.const import DOMAIN, SUBENTRY_ROOM


def _keys(result) -> set[str]:
    return {str(k) for k in result["data_schema"].schema}


async def _until(hass, result, flow, *, stop: set[str], data=None, limit: int = 15):
    """Submit empty forms until one of ``stop`` (a step id or a result type) is reached."""
    for _ in range(limit):
        if result["type"] is not FlowResultType.FORM or result["step_id"] in stop:
            return result
        result = await flow.async_configure(result["flow_id"], data or {})
    return result


async def test_user_flow(hass: HomeAssistant) -> None:
    """The house is created with people, nearby zones and a relay zone."""
    flow = hass.config_entries.flow
    result = await flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await flow.async_configure(
        result["flow_id"],
        {"name": "Home", "persons": [], "nearby_zones": [], "home_rule": "any"},
    )
    assert result["step_id"] == "heating"
    assert _keys(result) == {"source"}
    result = await flow.async_configure(result["flow_id"], {"source": "switch"})
    assert result["step_id"] == "heating_devices"
    assert _keys(result) == {"switches"}
    result = await flow.async_configure(result["flow_id"], {"switches": []})
    assert result["errors"] == {"switches": "no_devices"}
    result = await flow.async_configure(result["flow_id"], {"switches": ["input_boolean.heater"]})
    assert result["step_id"] == "heating_on_off"
    # A relay needs a temperature sensor.
    result = await flow.async_configure(result["flow_id"], {})
    assert result["errors"] == {"temperature_sensors": "sensor_required"}
    result = await flow.async_configure(
        result["flow_id"], {"temperature_sensors": ["sensor.room"], "hysteresis": 0.5}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Home"
    assert result["options"]["home_rule"] == "any"
    zone = next(iter(result["result"].subentries.values()))
    assert zone.title == "Whole house"
    assert zone.unique_id == "whole_house"
    assert zone.data["switches"] == ["input_boolean.heater"]
    assert zone.data["temperature_sensors"] == ["sensor.room"]
    assert zone.data["hysteresis"] == 0.5


async def test_user_flow_without_devices(hass: HomeAssistant) -> None:
    """A house can be created without heating devices."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Home", "persons": [], "nearby_zones": []}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"source": "none"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert not result["result"].subentries


async def test_options_heating_adds_zone(hass: HomeAssistant) -> None:
    """The options add the whole-house zone to an existing house, then edit it."""
    entry = MockConfigEntry(domain=DOMAIN, title="Home 101", options={})
    entry.add_to_hass(hass)
    flow = hass.config_entries.options
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "heating"})
    assert result["step_id"] == "heating"
    result = await flow.async_configure(result["flow_id"], {"source": "climate"})
    assert _keys(result) == {"climates", "command_mode"}
    result = await flow.async_configure(
        result["flow_id"], {"climates": ["climate.trv"], "command_mode": "temperature"}
    )
    assert result["step_id"] == "heating_thermostat"
    assert _keys(result) == {"learn_tolerance"}
    result = await flow.async_configure(result["flow_id"], {"learn_tolerance": 0.3})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    zone = next(iter(entry.subentries.values()))
    assert zone.title == "Whole house"
    assert zone.data["learn_tolerance"] == 0.3
    # Editing again updates the same zone; the other devices are cleared.
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "heating"})
    result = await flow.async_configure(result["flow_id"], {"source": "switch"})
    result = await flow.async_configure(
        result["flow_id"], {"switches": ["input_boolean.heater", "input_boolean.other"]}
    )
    assert result["step_id"] == "heating_on_off"
    result = await flow.async_configure(result["flow_id"], {"temperature_sensors": ["sensor.room"]})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert len(entry.subentries) == 1
    data = next(iter(entry.subentries.values())).data
    assert data["switches"] == ["input_boolean.heater", "input_boolean.other"]
    assert data["climates"] == []


async def test_options_follow_up_only_when_needed(hass: HomeAssistant) -> None:
    """The second form only appears with the values that apply."""
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options={"persons": []})
    entry.add_to_hass(hass)
    flow = hass.config_entries.options
    result = await flow.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "behavior"})
    assert "override_hours" not in _keys(result)
    result = await flow.async_configure(result["flow_id"], {"override_mode": "until_next_reevaluation"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["override_mode"] == "until_next_reevaluation"
    # Fixed duration asks for the hours.
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "behavior"})
    result = await flow.async_configure(result["flow_id"], {"override_mode": "fixed"})
    assert result["step_id"] == "behavior_details"
    assert _keys(result) == {"override_hours"}
    result = await flow.async_configure(result["flow_id"], {"override_hours": 3})
    assert entry.options["override_hours"] == 3
    # Energy without sensors has no second form.
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "energy"})
    assert _keys(result) == {"price_sensor", "pv_sensor"}
    result = await flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_weather_validation(hass: HomeAssistant) -> None:
    """Season dates are asked only for 'between dates' and are validated."""
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options={})
    entry.add_to_hass(hass)
    flow = hass.config_entries.options
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "weather"})
    assert "season_start" not in _keys(result)
    result = await flow.async_configure(
        result["flow_id"], {
            "season_mode": "dates",
            "cutoff_enabled": False,
            "forecast_enabled": False,
            "compensation_enabled": False,
        }
    )
    assert result["step_id"] == "weather_details"
    assert _keys(result) == {"season_start", "season_end"}
    result = await flow.async_configure(
        result["flow_id"], {"season_start": "13-40", "season_end": "04-15"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"season_start": "invalid_month_day"}
    result = await flow.async_configure(
        result["flow_id"], {"season_start": "10-15", "season_end": "04-15"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["season_start"] == "10-15"


async def test_room_subentry_flow(hass: HomeAssistant) -> None:
    """A relay room is added and then reconfigured."""
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options={})
    entry.add_to_hass(hass)
    flow = hass.config_entries.subentries

    result = await flow.async_init((entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "basics"
    result = await flow.async_configure(result["flow_id"], {"name": "Bedroom", "source": "switch"})
    assert result["step_id"] == "devices"
    result = await flow.async_configure(result["flow_id"], {"switches": []})
    assert result["errors"] == {"switches": "no_devices"}
    result = await flow.async_configure(result["flow_id"], {"switches": ["input_boolean.heater"]})
    # Relays: only the on / off settings.
    assert result["step_id"] == "control_on_off"
    assert _keys(result) == {"hysteresis", "min_on_minutes", "min_off_minutes"}
    result = await flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "levels"
    assert "nearby_temp" not in _keys(result)
    result = await flow.async_configure(
        result["flow_id"], {"name_home": "Day", "name_sleep": "Night", "nearby_mode": "temperature"}
    )
    assert result["step_id"] == "levels_nearby"
    result = await flow.async_configure(result["flow_id"], {"nearby_temp": 18})
    assert result["step_id"] == "sensors"
    assert _keys(result) == {"temperature_sensors", "occupancy_sensors"}
    result = await flow.async_configure(result["flow_id"], {})
    assert result["errors"] == {"temperature_sensors": "sensor_required"}
    result = await flow.async_configure(result["flow_id"], {"temperature_sensors": ["sensor.room"]})
    # One sensor and no occupancy sensors: no details form.
    assert result["step_id"] == "windows"
    result = await flow.async_configure(result["flow_id"], {})
    # No window sensors and no detection: no delays form.
    assert result["step_id"] == "schedule"
    assert _keys(result) == {"schedule_source", "optimal_start", "optimal_stop"}
    result = await flow.async_configure(result["flow_id"], {"optimal_start": True})
    assert result["step_id"] == "schedule_internal"
    result = await flow.async_configure(result["flow_id"], {"schedule": "workday: 06:00 Day, 25:00 Night"})
    assert result["errors"] == {"schedule": "invalid_schedule"}
    result = await flow.async_configure(
        result["flow_id"], {"schedule": "workday: 00:00 Night, 06:00 Day, 22:00 Night"}
    )
    assert result["step_id"] == "schedule_optimal"
    assert _keys(result) == {"optimal_start_max_minutes"}
    result = await flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "extras"
    assert _keys(result) == {"solar_offset"}
    result = await flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY

    subentry = next(iter(entry.subentries.values()))
    assert subentry.title == "Bedroom"
    assert subentry.data["switches"] == ["input_boolean.heater"]
    assert subentry.data["preset_names"]["home"] == "Day"
    assert subentry.data["nearby_temp"] == 18

    result = await entry.start_subentry_reconfigure_flow(hass, subentry.subentry_id)
    assert result["step_id"] == "basics"
    result = await flow.async_configure(result["flow_id"], {"name": "Master bedroom", "source": "switch"})
    result = await _until(hass, result, flow, stop=set())
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.subentries[subentry.subentry_id].title == "Master bedroom"
    assert SOURCE_RECONFIGURE


async def test_room_with_thermostat_presets(hass: HomeAssistant) -> None:
    """With preset control the levels pick thermostat presets and keep temperatures."""
    hass.states.async_set(
        "climate.trv",
        "heat",
        {"preset_modes": ["none", "comfort", "eco", "away", "boost"], "preset_mode": "none"},
    )
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options={})
    entry.add_to_hass(hass)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "Office", "source": "climate"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"climates": ["climate.trv"], "command_mode": "preset"}
    )
    # TRV with presets: only the thermostat tolerance.
    assert result["step_id"] == "control_thermostat"
    assert {str(k) for k in result["data_schema"].schema} == {"learn_tolerance"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"learn_tolerance": 0.3}
    )
    assert result["step_id"] == "levels"
    assert result["description_placeholders"]["presets"] == "comfort, eco, away, boost"
    schema = result["data_schema"].schema
    assert any(str(key) == "device_home" for key in schema)
    assert not any(str(key) == "name_home" for key in schema)

    # Two levels on the same preset are refused.
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"device_home": "comfort", "device_comfort": "comfort"}
    )
    assert result["errors"] == {"base": "duplicate_names"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "device_home": "comfort",
            "device_eco": "eco",
            "device_comfort": "boost",
            "temp_sleep": 18.5,
        },
    )
    assert result["step_id"] == "sensors"
    assert "calibration_mode" in _keys(result)
    flow = hass.config_entries.subentries
    result = await _until(hass, result, flow, stop={"schedule_internal"})
    assert result["step_id"] == "schedule_internal"
    result = await flow.async_configure(
        result["flow_id"], {"schedule": "workday: 00:00 sleep, 07:00 comfort, 22:00 sleep"}
    )
    assert result["step_id"] == "extras"
    assert _keys(result) == {"solar_offset", "valve_exercise"}
    result = await flow.async_configure(result["flow_id"], {"valve_exercise": True})
    assert result["step_id"] == "extras_valves"
    result = await flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY

    subentry = next(iter(entry.subentries.values()))
    assert subentry.data["preset_map"] == {"home": "comfort", "eco": "eco", "comfort": "boost"}
    assert subentry.data["levels"]["sleep"] == 18.5
    assert subentry.data["preset_names"] == {}
    assert subentry.data["learn_tolerance"] == 0.3
