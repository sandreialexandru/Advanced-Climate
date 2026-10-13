"""Config flow and room subentry flow tests."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.advanced_climate.const import DOMAIN, SUBENTRY_ROOM


async def test_user_flow(hass: HomeAssistant) -> None:
    """The house is created with people and nearby zones."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Home", "persons": [], "nearby_zones": [], "home_rule": "any"},
    )
    assert result["step_id"] == "heating"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"source": "switch", "switches": []}
    )
    assert result["errors"] == {"switches": "no_devices"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"source": "switch", "switches": ["input_boolean.heater"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Home"
    assert result["options"]["home_rule"] == "any"
    entry = result["result"]
    zone = next(iter(entry.subentries.values()))
    assert zone.title == "Whole house"
    assert zone.unique_id == "whole_house"
    assert zone.data["switches"] == ["input_boolean.heater"]


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
    """The options add the whole-house zone to an existing house."""
    entry = MockConfigEntry(domain=DOMAIN, title="Home 101", options={})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "heating"}
    )
    assert result["step_id"] == "heating"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"source": "switch", "switches": ["input_boolean.heater"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    zone = next(iter(entry.subentries.values()))
    assert zone.title == "Whole house"
    # Editing again updates the same zone.
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "heating"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"source": "switch", "switches": ["input_boolean.heater", "input_boolean.other"]},
    )
    assert len(entry.subentries) == 1
    assert next(iter(entry.subentries.values())).data["switches"] == [
        "input_boolean.heater",
        "input_boolean.other",
    ]


async def test_options_flow_presence(hass: HomeAssistant) -> None:
    """A menu step is saved into the options."""
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options={"persons": []})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "behavior"}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"override_mode": "until_next_reevaluation"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["override_mode"] == "until_next_reevaluation"
    assert entry.options["override_hours"] == 2.0


async def test_weather_validation(hass: HomeAssistant) -> None:
    """Season dates are validated."""
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options={})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "weather"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"season_start": "13-40"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"season_start": "invalid_month_day"}


async def test_room_subentry_flow(hass: HomeAssistant) -> None:
    """A relay room is added and then reconfigured."""
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options={})
    entry.add_to_hass(hass)

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "basics"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "Bedroom", "source": "switch"}
    )
    assert result["step_id"] == "devices"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"switches": []}
    )
    assert result["errors"] == {"base": "no_devices"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"switches": ["input_boolean.heater"]}
    )
    assert result["step_id"] == "levels"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name_home": "Day", "name_sleep": "Night"}
    )
    assert result["step_id"] == "sensors"
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["step_id"] == "windows"
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["step_id"] == "schedule"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"schedule": "workday: 06:00 Day, 25:00 Night"}
    )
    assert result["errors"] == {"schedule": "invalid_schedule"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"schedule": "workday: 00:00 Night, 06:00 Day, 22:00 Night"}
    )
    assert result["step_id"] == "extras"
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY

    subentry = next(iter(entry.subentries.values()))
    assert subentry.title == "Bedroom"
    assert subentry.data["switches"] == ["input_boolean.heater"]
    assert subentry.data["preset_names"]["home"] == "Day"

    result = await entry.start_subentry_reconfigure_flow(hass, subentry.subentry_id)
    assert result["step_id"] == "basics"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "Master bedroom", "source": "switch"}
    )
    for _ in range(6):
        result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.subentries[subentry.subentry_id].title == "Master bedroom"
    assert SOURCE_RECONFIGURE
