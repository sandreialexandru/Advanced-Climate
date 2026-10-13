"""Config flow for Advanced Climate: the house entry and room subentries."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentry,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    AGG_MEAN,
    AGG_MEDIAN,
    AGG_MIN,
    CALIBRATION_EXTERNAL,
    CALIBRATION_OFF,
    CALIBRATION_OFFSET,
    COMMAND_HVAC,
    COMMAND_PRESET,
    COMMAND_TEMPERATURE,
    CONF_ALERT_UNAVAILABLE_MINUTES,
    CONF_ALERT_WINDOW_MINUTES,
    CONF_AREA,
    CONF_ARRIVAL_DELAY,
    CONF_ARRIVAL_DISTANCE,
    CONF_ARRIVAL_MINUTES,
    CONF_AUTO_VACATION_HOURS,
    CONF_BATTERY_THRESHOLD,
    CONF_BOILER_ENTITY,
    CONF_BOILER_MIN_OFF,
    CONF_BOILER_MIN_ON,
    CONF_BOILER_MIN_ROOMS,
    CONF_CALENDAR,
    CONF_CALIBRATION_ENTITIES,
    CONF_CALIBRATION_MODE,
    CONF_CLIMATES,
    CONF_COMMAND_MODE,
    CONF_COMP_BELOW,
    CONF_COMP_ENABLED,
    CONF_COMP_OFFSET,
    CONF_CUTOFF_AVG_HOURS,
    CONF_CUTOFF_ENABLED,
    CONF_CUTOFF_HYSTERESIS,
    CONF_CUTOFF_TEMP,
    CONF_DAY_BOUNDARY,
    CONF_DEPARTURE_DELAY,
    CONF_FORECAST_ENABLED,
    CONF_FORECAST_HOURS,
    CONF_FROST_TEMP,
    CONF_GUEST_EXPIRE_HOURS,
    CONF_HELPER_OFF_PRESET,
    CONF_HELPER_ON_PRESET,
    CONF_HOME_RULE,
    CONF_HYSTERESIS,
    CONF_LINKED_WINDOW_SENSORS,
    CONF_MAX_TEMP,
    CONF_MIN_OFF,
    CONF_MIN_ON,
    CONF_NEARBY_GEOMETRIC,
    CONF_NEARBY_MODE,
    CONF_NEARBY_TEMP,
    CONF_NEARBY_ZONES,
    CONF_NOTIFY_SERVICE,
    CONF_OCCUPANCY_MINUTES,
    CONF_OCCUPANCY_SENSORS,
    CONF_OPTIMAL_START,
    CONF_OPTIMAL_START_MAX,
    CONF_OPTIMAL_STOP,
    CONF_OPTIMAL_STOP_MINUTES,
    CONF_OUTDOOR_SENSOR,
    CONF_OVERRIDE_HOURS,
    CONF_OVERRIDE_MODE,
    CONF_OVERRIDE_SCOPE,
    CONF_PERSONS,
    CONF_PRESENCE_SENSORS,
    CONF_PRESET_NAMES,
    CONF_PRICE_HIGH,
    CONF_PRICE_HIGH_OFFSET,
    CONF_PRICE_LOW,
    CONF_PRICE_LOW_OFFSET,
    CONF_PRICE_SENSOR,
    CONF_PROXIMITY_DIRECTION,
    CONF_PROXIMITY_DISTANCE,
    CONF_PV_OFFSET,
    CONF_PV_SENSOR,
    CONF_PV_THRESHOLD,
    CONF_REEVAL_MINUTES,
    CONF_REFERENCE_ROOM,
    CONF_ROOM_DIFF_ALERT,
    CONF_SCHEDULE,
    CONF_SCHEDULE_HELPER,
    CONF_SCHEDULE_SOURCE,
    CONF_SEASON_DAYS,
    CONF_SEASON_END,
    CONF_SEASON_MODE,
    CONF_SEASON_START,
    CONF_SEASON_TEMP,
    CONF_SOLAR_OFFSET,
    CONF_SOURCE,
    CONF_SWITCHES,
    CONF_TEMP_AGGREGATION,
    CONF_TEMP_SENSORS,
    CONF_TRAVEL_TIME,
    CONF_VACATION_PREHEAT,
    CONF_VALVE_DAY,
    CONF_VALVE_EXERCISE,
    CONF_VALVE_TIME,
    CONF_VERIFY_COMMANDS,
    CONF_WEATHER,
    CONF_WINDOW_ACTION,
    CONF_WINDOW_CLOSE_DELAY,
    CONF_WINDOW_DROP_DEGREES,
    CONF_WINDOW_DROP_DETECT,
    CONF_WINDOW_DROP_MINUTES,
    CONF_WINDOW_IGNORE_ABOVE,
    CONF_WINDOW_OPEN_DELAY,
    CONF_WINDOW_SENSORS,
    CONF_WORKDAY_SENSOR,
    DOMAIN,
    GT_DOMAIN,
    HOME_RULE_ALL,
    HOME_RULE_ANY,
    HOUSE_DEFAULTS,
    NEARBY_PRESET,
    NEARBY_TEMPERATURE,
    OVERRIDE_FIXED,
    OVERRIDE_NEXT,
    OVERRIDE_SCOPE_HOUSE,
    OVERRIDE_SCOPE_ROOM,
    PRESETS,
    ROOM_DEFAULTS,
    SCHEDULE_HELPER,
    SCHEDULE_INTERNAL,
    SEASON_ALWAYS,
    SEASON_AUTO,
    SEASON_DATES,
    SOURCE_CLIMATE,
    SOURCE_GT,
    SOURCE_SWITCH,
    SUBENTRY_ROOM,
    WEEKDAYS,
    WINDOW_ACTION_FROST,
    WINDOW_ACTION_OFF,
)
from .outdoor import parse_month_day
from .schedule import ScheduleError, parse_schedule

CONF_NAME = "name"

# ---------------------------------------------------------------------------
# Selector helpers
# ---------------------------------------------------------------------------


def _entity(domain: str | list[str], *, multiple: bool = False, **kwargs: Any) -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain=domain, multiple=multiple, **kwargs)
    )


def _number(
    minimum: float, maximum: float, step: float = 1, unit: str | None = None
) -> selector.NumberSelector:
    config = selector.NumberSelectorConfig(
        min=minimum, max=maximum, step=step, mode=selector.NumberSelectorMode.BOX
    )
    if unit:
        config["unit_of_measurement"] = unit
    return selector.NumberSelector(config)


def _select(options: list[str], key: str) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options, translation_key=key, mode=selector.SelectSelectorMode.DROPDOWN
        )
    )


def _bool() -> selector.BooleanSelector:
    return selector.BooleanSelector()


def _text(multiline: bool = False) -> selector.TextSelector:
    return selector.TextSelector(selector.TextSelectorConfig(multiline=multiline))


def _opt(key: str, values: dict[str, Any]) -> vol.Optional:
    """Optional field pre-filled with the current value (can be cleared)."""
    return vol.Optional(key, description={"suggested_value": values.get(key)})


def _req(key: str, values: dict[str, Any], defaults: dict[str, Any]) -> vol.Required:
    return vol.Required(key, default=values.get(key, defaults.get(key)))


def _merge(current: dict[str, Any], schema: vol.Schema, user_input: dict[str, Any]) -> dict[str, Any]:
    """Merge a step into the stored values; cleared optional fields are removed."""
    result = dict(current)
    for marker in schema.schema:
        key = str(getattr(marker, "schema", marker))
        if key in user_input:
            result[key] = user_input[key]
        else:
            result.pop(key, None)
    return result


# ---------------------------------------------------------------------------
# House schemas (used by the options flow)
# ---------------------------------------------------------------------------


def _presence_schema(v: dict[str, Any]) -> vol.Schema:
    d = HOUSE_DEFAULTS
    return vol.Schema(
        {
            _req(CONF_PERSONS, v, d): _entity("person", multiple=True),
            _req(CONF_HOME_RULE, v, d): _select([HOME_RULE_ANY, HOME_RULE_ALL], "home_rule"),
            _req(CONF_NEARBY_ZONES, v, d): _entity("zone", multiple=True),
            _req(CONF_NEARBY_GEOMETRIC, v, d): _bool(),
            _req(CONF_DEPARTURE_DELAY, v, d): _number(0, 240, 1, "min"),
            _req(CONF_ARRIVAL_DELAY, v, d): _number(0, 240, 1, "min"),
            _req(CONF_PRESENCE_SENSORS, v, d): _entity(
                ["binary_sensor", "input_boolean", "switch"], multiple=True
            ),
            _req(CONF_GUEST_EXPIRE_HOURS, v, d): _number(0, 720, 1, "h"),
            _opt(CONF_PROXIMITY_DISTANCE, v): _entity("sensor"),
            _opt(CONF_PROXIMITY_DIRECTION, v): _entity("sensor"),
            _opt(CONF_TRAVEL_TIME, v): _entity("sensor"),
            _req(CONF_ARRIVAL_DISTANCE, v, d): _number(0, 500, 0.5, "km"),
            _req(CONF_ARRIVAL_MINUTES, v, d): _number(0, 240, 1, "min"),
        }
    )


def _calendar_schema(v: dict[str, Any]) -> vol.Schema:
    d = HOUSE_DEFAULTS
    return vol.Schema(
        {
            _opt(CONF_WORKDAY_SENSOR, v): _entity("binary_sensor"),
            _opt(CONF_CALENDAR, v): _entity("calendar"),
            _req(CONF_DAY_BOUNDARY, v, d): selector.TimeSelector(),
        }
    )


def _weather_schema(v: dict[str, Any]) -> vol.Schema:
    d = HOUSE_DEFAULTS
    return vol.Schema(
        {
            _opt(CONF_OUTDOOR_SENSOR, v): _entity("sensor", device_class="temperature"),
            _opt(CONF_WEATHER, v): _entity("weather"),
            _req(CONF_CUTOFF_ENABLED, v, d): _bool(),
            _req(CONF_CUTOFF_TEMP, v, d): _number(5, 30, 0.5, "°C"),
            _req(CONF_CUTOFF_HYSTERESIS, v, d): _number(0, 5, 0.1, "°C"),
            _req(CONF_CUTOFF_AVG_HOURS, v, d): _number(0, 48, 1, "h"),
            _req(CONF_FORECAST_ENABLED, v, d): _bool(),
            _req(CONF_FORECAST_HOURS, v, d): _number(1, 24, 1, "h"),
            _req(CONF_SEASON_MODE, v, d): _select(
                [SEASON_ALWAYS, SEASON_DATES, SEASON_AUTO], "season_mode"
            ),
            _req(CONF_SEASON_START, v, d): _text(),
            _req(CONF_SEASON_END, v, d): _text(),
            _req(CONF_SEASON_DAYS, v, d): _number(1, 14, 1, "d"),
            _req(CONF_SEASON_TEMP, v, d): _number(0, 25, 0.5, "°C"),
            _req(CONF_COMP_ENABLED, v, d): _bool(),
            _req(CONF_COMP_BELOW, v, d): _number(-30, 15, 0.5, "°C"),
            _req(CONF_COMP_OFFSET, v, d): _number(-3, 3, 0.1, "°C"),
            _opt(CONF_WINDOW_IGNORE_ABOVE, v): _number(0, 40, 0.5, "°C"),
        }
    )


def _energy_schema(v: dict[str, Any]) -> vol.Schema:
    d = HOUSE_DEFAULTS
    return vol.Schema(
        {
            _opt(CONF_PRICE_SENSOR, v): _entity("sensor"),
            _opt(CONF_PRICE_HIGH, v): _number(-1000, 1000, 0.001),
            _req(CONF_PRICE_HIGH_OFFSET, v, d): _number(-3, 3, 0.1, "°C"),
            _opt(CONF_PRICE_LOW, v): _number(-1000, 1000, 0.001),
            _req(CONF_PRICE_LOW_OFFSET, v, d): _number(-3, 3, 0.1, "°C"),
            _opt(CONF_PV_SENSOR, v): _entity("sensor"),
            _req(CONF_PV_THRESHOLD, v, d): _number(0, 100000, 10, "W"),
            _req(CONF_PV_OFFSET, v, d): _number(-3, 3, 0.1, "°C"),
        }
    )


def _boiler_schema(v: dict[str, Any], rooms: list[selector.SelectOptionDict]) -> vol.Schema:
    d = HOUSE_DEFAULTS
    schema: dict[Any, Any] = {
        _opt(CONF_BOILER_ENTITY, v): _entity(["switch", "climate", "input_boolean"]),
        _req(CONF_BOILER_MIN_ROOMS, v, d): _number(1, 20, 1),
        _req(CONF_BOILER_MIN_ON, v, d): _number(0, 60, 1, "min"),
        _req(CONF_BOILER_MIN_OFF, v, d): _number(0, 60, 1, "min"),
        _req(CONF_ROOM_DIFF_ALERT, v, d): _number(0, 10, 0.5, "°C"),
    }
    if rooms:
        schema[_opt(CONF_REFERENCE_ROOM, v)] = selector.SelectSelector(
            selector.SelectSelectorConfig(options=rooms, mode=selector.SelectSelectorMode.DROPDOWN)
        )
    return vol.Schema(schema)


def _behavior_schema(v: dict[str, Any]) -> vol.Schema:
    d = HOUSE_DEFAULTS
    return vol.Schema(
        {
            _req(CONF_OVERRIDE_MODE, v, d): _select([OVERRIDE_FIXED, OVERRIDE_NEXT], "override_mode"),
            _req(CONF_OVERRIDE_HOURS, v, d): _number(0.25, 72, 0.25, "h"),
            _req(CONF_OVERRIDE_SCOPE, v, d): _select(
                [OVERRIDE_SCOPE_ROOM, OVERRIDE_SCOPE_HOUSE], "override_scope"
            ),
            _req(CONF_VACATION_PREHEAT, v, d): _number(0, 48, 0.5, "h"),
            _req(CONF_AUTO_VACATION_HOURS, v, d): _number(0, 720, 1, "h"),
            _req(CONF_FROST_TEMP, v, d): _number(3, 15, 0.5, "°C"),
            _req(CONF_MAX_TEMP, v, d): _number(15, 35, 0.5, "°C"),
            _req(CONF_REEVAL_MINUTES, v, d): _number(1, 60, 1, "min"),
        }
    )


def _alerts_schema(v: dict[str, Any]) -> vol.Schema:
    d = HOUSE_DEFAULTS
    return vol.Schema(
        {
            _opt(CONF_NOTIFY_SERVICE, v): _text(),
            _req(CONF_ALERT_WINDOW_MINUTES, v, d): _number(1, 720, 1, "min"),
            _req(CONF_ALERT_UNAVAILABLE_MINUTES, v, d): _number(1, 720, 1, "min"),
            _req(CONF_BATTERY_THRESHOLD, v, d): _number(1, 100, 1, "%"),
            _req(CONF_VERIFY_COMMANDS, v, d): _bool(),
        }
    )


# ---------------------------------------------------------------------------
# Whole-house heating (a zone created together with the house)
# ---------------------------------------------------------------------------
HOUSE_ZONE_ID = "whole_house"
HOUSE_ZONE_TITLE = "Whole house"
SOURCE_NONE = "none"


def _heating_schema(v: dict[str, Any], allow_none: bool) -> vol.Schema:
    sources = [SOURCE_GT, SOURCE_CLIMATE, SOURCE_SWITCH]
    if allow_none:
        sources = [*sources, SOURCE_NONE]
    return vol.Schema(
        {
            vol.Required(CONF_SOURCE, default=v.get(CONF_SOURCE, SOURCE_GT)): _select(
                sources, "house_source"
            ),
            _opt(CONF_CLIMATES, v): _entity("climate", multiple=True),
            _opt(CONF_SWITCHES, v): _entity(["switch", "input_boolean"], multiple=True),
            vol.Required(
                CONF_COMMAND_MODE, default=v.get(CONF_COMMAND_MODE, COMMAND_TEMPERATURE)
            ): _select([COMMAND_TEMPERATURE, COMMAND_PRESET, COMMAND_HVAC], "command_mode"),
        }
    )


def _heating_errors(user_input: dict[str, Any]) -> dict[str, str]:
    source = user_input[CONF_SOURCE]
    if source == SOURCE_NONE:
        return {}
    key = CONF_SWITCHES if source == SOURCE_SWITCH else CONF_CLIMATES
    if not user_input.get(key):
        return {key: "no_devices"}
    return {}


def _zone_data(user_input: dict[str, Any], base: dict[str, Any] | None = None) -> dict[str, Any]:
    data = {**ROOM_DEFAULTS, **(base or {})}
    data[CONF_SOURCE] = user_input[CONF_SOURCE]
    data[CONF_CLIMATES] = list(user_input.get(CONF_CLIMATES) or [])
    data[CONF_SWITCHES] = list(user_input.get(CONF_SWITCHES) or [])
    data[CONF_COMMAND_MODE] = user_input[CONF_COMMAND_MODE]
    return data


# ---------------------------------------------------------------------------
# Main config flow
# ---------------------------------------------------------------------------


class AdvancedClimateConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create the house."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._house: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """First step: name, people and nearby zones."""
        if user_input is not None:
            self._house = dict(user_input)
            return await self.async_step_heating()
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Home"): _text(),
                vol.Required(CONF_PERSONS, default=[]): _entity("person", multiple=True),
                vol.Required(CONF_NEARBY_ZONES, default=[]): _entity("zone", multiple=True),
                vol.Required(CONF_HOME_RULE, default=HOME_RULE_ANY): _select(
                    [HOME_RULE_ANY, HOME_RULE_ALL], "home_rule"
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_heating(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """How the whole house is heated (rooms can be added later)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _heating_errors(user_input)
            if not errors:
                options = dict(self._house)
                name = options.pop(CONF_NAME)
                subentries = []
                if user_input[CONF_SOURCE] != SOURCE_NONE:
                    subentries.append(
                        {
                            "data": _zone_data(user_input),
                            "subentry_type": SUBENTRY_ROOM,
                            "title": HOUSE_ZONE_TITLE,
                            "unique_id": HOUSE_ZONE_ID,
                        }
                    )
                return self.async_create_entry(
                    title=name, data={}, options=options, subentries=subentries
                )
        values = {**(user_input or {})}
        return self.async_show_form(
            step_id="heating",
            data_schema=_heating_schema(values, True),
            errors=errors,
            description_placeholders={"zone": HOUSE_ZONE_TITLE},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Options flow."""
        return AdvancedClimateOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Rooms are subentries."""
        return {SUBENTRY_ROOM: RoomSubentryFlow}


class AdvancedClimateOptionsFlow(OptionsFlow):
    """House options, grouped in a menu."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "heating",
                "presence",
                "calendar",
                "weather",
                "energy",
                "boiler",
                "behavior",
                "alerts",
            ],
        )

    def _house_zone(self) -> ConfigSubentry | None:
        """The whole-house zone, or the only room if there is just one."""
        rooms = [
            sub
            for sub in self.config_entry.subentries.values()
            if sub.subentry_type == SUBENTRY_ROOM
        ]
        for sub in rooms:
            if sub.unique_id == HOUSE_ZONE_ID:
                return sub
        return rooms[0] if len(rooms) == 1 else None

    async def async_step_heating(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Heating devices of the whole house (creates or edits the house zone)."""
        zone = self._house_zone()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _heating_errors(user_input)
            if not errors:
                entries = self.hass.config_entries
                if user_input[CONF_SOURCE] == SOURCE_NONE:
                    if zone is not None and zone.unique_id == HOUSE_ZONE_ID:
                        entries.async_remove_subentry(self.config_entry, zone.subentry_id)
                elif zone is None:
                    entries.async_add_subentry(
                        self.config_entry,
                        ConfigSubentry(
                            data=MappingProxyType(_zone_data(user_input)),
                            subentry_type=SUBENTRY_ROOM,
                            title=HOUSE_ZONE_TITLE,
                            unique_id=HOUSE_ZONE_ID,
                        ),
                    )
                else:
                    entries.async_update_subentry(
                        self.config_entry, zone, data=_zone_data(user_input, dict(zone.data))
                    )
                return self.async_create_entry(data=dict(self.config_entry.options))
        values = dict(zone.data) if zone else {}
        if user_input:
            values.update(user_input)
        return self.async_show_form(
            step_id="heating",
            data_schema=_heating_schema(values, True),
            errors=errors,
            description_placeholders={"zone": zone.title if zone else HOUSE_ZONE_TITLE},
        )

    @property
    def _values(self) -> dict[str, Any]:
        return {**HOUSE_DEFAULTS, **self.config_entry.options}

    def _save(self, schema: vol.Schema, user_input: dict[str, Any]) -> ConfigFlowResult:
        return self.async_create_entry(
            data=_merge(dict(self.config_entry.options), schema, user_input)
        )

    async def async_step_presence(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Presence options."""
        schema = _presence_schema(self._values)
        if user_input is not None:
            return self._save(schema, user_input)
        return self.async_show_form(step_id="presence", data_schema=schema)

    async def async_step_calendar(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Workday and calendar options."""
        schema = _calendar_schema(self._values)
        if user_input is not None:
            return self._save(schema, user_input)
        return self.async_show_form(step_id="calendar", data_schema=schema)

    async def async_step_weather(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Weather and season options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            for key in (CONF_SEASON_START, CONF_SEASON_END):
                try:
                    parse_month_day(str(user_input.get(key, "")))
                except ValueError:
                    errors[key] = "invalid_month_day"
            if not errors:
                return self._save(_weather_schema(self._values), user_input)
        values = {**self._values, **(user_input or {})}
        return self.async_show_form(
            step_id="weather", data_schema=_weather_schema(values), errors=errors
        )

    async def async_step_energy(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Tariff and PV options."""
        schema = _energy_schema(self._values)
        if user_input is not None:
            return self._save(schema, user_input)
        return self.async_show_form(step_id="energy", data_schema=schema)

    async def async_step_boiler(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Boiler and heat demand options."""
        rooms = [
            selector.SelectOptionDict(value=sub.subentry_id, label=sub.title)
            for sub in self.config_entry.subentries.values()
            if sub.subentry_type == SUBENTRY_ROOM
        ]
        schema = _boiler_schema(self._values, rooms)
        if user_input is not None:
            return self._save(schema, user_input)
        return self.async_show_form(step_id="boiler", data_schema=schema)

    async def async_step_behavior(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Overrides, vacation and limits."""
        schema = _behavior_schema(self._values)
        if user_input is not None:
            return self._save(schema, user_input)
        return self.async_show_form(step_id="behavior", data_schema=schema)

    async def async_step_alerts(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Notifications."""
        schema = _alerts_schema(self._values)
        if user_input is not None:
            return self._save(schema, user_input)
        return self.async_show_form(step_id="alerts", data_schema=schema)


# ---------------------------------------------------------------------------
# Room subentry flow
# ---------------------------------------------------------------------------


class RoomSubentryFlow(ConfigSubentryFlow):
    """Add or reconfigure a room."""

    def __init__(self) -> None:
        """Initialize."""
        self._data: dict[str, Any] = {}
        self._reconfigure = False

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Start a new room."""
        self._data = dict(ROOM_DEFAULTS)
        return await self.async_step_basics(user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit an existing room."""
        subentry = self._get_reconfigure_subentry()
        self._data = {**ROOM_DEFAULTS, **subentry.data, CONF_NAME: subentry.title}
        self._reconfigure = True
        return await self.async_step_basics()

    async def async_step_basics(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Name, area and how the room is heated."""
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=self._data.get(CONF_NAME, "")): _text(),
                _opt(CONF_AREA, self._data): selector.AreaSelector(),
                vol.Required(CONF_SOURCE, default=self._data[CONF_SOURCE]): _select(
                    [SOURCE_GT, SOURCE_CLIMATE, SOURCE_SWITCH], "source"
                ),
            }
        )
        if user_input is not None:
            self._data = _merge(self._data, schema, user_input)
            return await self.async_step_devices()
        return self.async_show_form(step_id="basics", data_schema=schema)

    async def async_step_devices(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """The devices that heat the room."""
        source = self._data[CONF_SOURCE]
        d = self._data
        fields: dict[Any, Any] = {}
        if source == SOURCE_GT:
            fields[vol.Required(CONF_CLIMATES, default=d.get(CONF_CLIMATES, []))] = _entity(
                "climate", multiple=True, integration=GT_DOMAIN
            )
        elif source == SOURCE_CLIMATE:
            fields[vol.Required(CONF_CLIMATES, default=d.get(CONF_CLIMATES, []))] = _entity(
                "climate", multiple=True
            )
            fields[vol.Required(CONF_COMMAND_MODE, default=d[CONF_COMMAND_MODE])] = _select(
                [COMMAND_TEMPERATURE, COMMAND_PRESET, COMMAND_HVAC], "command_mode"
            )
        else:
            fields[vol.Required(CONF_SWITCHES, default=d.get(CONF_SWITCHES, []))] = _entity(
                ["switch", "input_boolean"], multiple=True
            )
        if source in (SOURCE_SWITCH, SOURCE_CLIMATE):
            fields[_req(CONF_HYSTERESIS, d, ROOM_DEFAULTS)] = _number(0.1, 3, 0.1, "°C")
            fields[_req(CONF_MIN_ON, d, ROOM_DEFAULTS)] = _number(0, 60, 1, "min")
            fields[_req(CONF_MIN_OFF, d, ROOM_DEFAULTS)] = _number(0, 60, 1, "min")
        schema = vol.Schema(fields)
        errors: dict[str, str] = {}
        if user_input is not None:
            entities = user_input.get(CONF_SWITCHES if source == SOURCE_SWITCH else CONF_CLIMATES)
            if not entities:
                errors["base"] = "no_devices"
            else:
                self._data = _merge(self._data, schema, user_input)
                return await self.async_step_levels()
        return self.async_show_form(step_id="devices", data_schema=schema, errors=errors)

    async def async_step_levels(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Level names (without GT) and what 'nearby' means."""
        d = self._data
        names = dict(d.get(CONF_PRESET_NAMES) or {})
        fields: dict[Any, Any] = {
            vol.Required(CONF_NEARBY_MODE, default=d[CONF_NEARBY_MODE]): _select(
                [NEARBY_PRESET, NEARBY_TEMPERATURE], "nearby_mode"
            ),
            _req(CONF_NEARBY_TEMP, d, ROOM_DEFAULTS): _number(5, 30, 0.5, "°C"),
        }
        if d[CONF_SOURCE] != SOURCE_GT:
            for preset in PRESETS:
                fields[vol.Optional(f"name_{preset}", default=names.get(preset, preset))] = _text()
        schema = vol.Schema(fields)
        if user_input is not None:
            new_names = {
                p: str(user_input.pop(f"name_{p}", "")).strip() or p
                for p in PRESETS
                if d[CONF_SOURCE] != SOURCE_GT
            }
            lowered = [n.lower() for n in new_names.values()]
            if len(set(lowered)) != len(lowered):
                return self.async_show_form(
                    step_id="levels", data_schema=schema, errors={"base": "duplicate_names"}
                )
            self._data[CONF_PRESET_NAMES] = new_names
            self._data[CONF_NEARBY_MODE] = user_input[CONF_NEARBY_MODE]
            self._data[CONF_NEARBY_TEMP] = user_input[CONF_NEARBY_TEMP]
            return await self.async_step_sensors()
        return self.async_show_form(step_id="levels", data_schema=schema)

    async def async_step_sensors(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Temperature, calibration and occupancy sensors."""
        d = self._data
        schema = vol.Schema(
            {
                _req(CONF_TEMP_SENSORS, d, ROOM_DEFAULTS): _entity(
                    "sensor", multiple=True, device_class="temperature"
                ),
                _req(CONF_TEMP_AGGREGATION, d, ROOM_DEFAULTS): _select(
                    [AGG_MEAN, AGG_MIN, AGG_MEDIAN], "aggregation"
                ),
                _req(CONF_CALIBRATION_MODE, d, ROOM_DEFAULTS): _select(
                    [CALIBRATION_OFF, CALIBRATION_OFFSET, CALIBRATION_EXTERNAL], "calibration"
                ),
                _req(CONF_CALIBRATION_ENTITIES, d, ROOM_DEFAULTS): _entity("number", multiple=True),
                _req(CONF_OCCUPANCY_SENSORS, d, ROOM_DEFAULTS): _entity(
                    ["binary_sensor", "input_boolean"], multiple=True
                ),
                _req(CONF_OCCUPANCY_MINUTES, d, ROOM_DEFAULTS): _number(1, 720, 1, "min"),
            }
        )
        if user_input is not None:
            self._data = _merge(self._data, schema, user_input)
            return await self.async_step_windows()
        return self.async_show_form(step_id="sensors", data_schema=schema)

    async def async_step_windows(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Window and door sensors."""
        d = self._data
        schema = vol.Schema(
            {
                _req(CONF_WINDOW_SENSORS, d, ROOM_DEFAULTS): _entity(
                    ["binary_sensor", "input_boolean"], multiple=True
                ),
                _req(CONF_LINKED_WINDOW_SENSORS, d, ROOM_DEFAULTS): _entity(
                    ["binary_sensor", "input_boolean"], multiple=True
                ),
                _req(CONF_WINDOW_OPEN_DELAY, d, ROOM_DEFAULTS): _number(0, 3600, 5, "s"),
                _req(CONF_WINDOW_CLOSE_DELAY, d, ROOM_DEFAULTS): _number(0, 3600, 5, "s"),
                _req(CONF_WINDOW_ACTION, d, ROOM_DEFAULTS): _select(
                    [WINDOW_ACTION_FROST, WINDOW_ACTION_OFF], "window_action"
                ),
                _req(CONF_WINDOW_DROP_DETECT, d, ROOM_DEFAULTS): _bool(),
                _req(CONF_WINDOW_DROP_DEGREES, d, ROOM_DEFAULTS): _number(0.2, 5, 0.1, "°C"),
                _req(CONF_WINDOW_DROP_MINUTES, d, ROOM_DEFAULTS): _number(1, 30, 1, "min"),
            }
        )
        if user_input is not None:
            self._data = _merge(self._data, schema, user_input)
            return await self.async_step_schedule()
        return self.async_show_form(step_id="windows", data_schema=schema)

    async def async_step_schedule(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """The schedule."""
        d = {**self._data, **(user_input or {})}
        names = list(PRESETS) + list((self._data.get(CONF_PRESET_NAMES) or {}).values())
        schema = vol.Schema(
            {
                _req(CONF_SCHEDULE_SOURCE, d, ROOM_DEFAULTS): _select(
                    [SCHEDULE_INTERNAL, SCHEDULE_HELPER], "schedule_source"
                ),
                _req(CONF_SCHEDULE, d, ROOM_DEFAULTS): _text(multiline=True),
                _opt(CONF_SCHEDULE_HELPER, d): _entity("schedule"),
                _req(CONF_HELPER_ON_PRESET, d, ROOM_DEFAULTS): _select(list(PRESETS), "preset"),
                _req(CONF_HELPER_OFF_PRESET, d, ROOM_DEFAULTS): _select(list(PRESETS), "preset"),
                _req(CONF_OPTIMAL_START, d, ROOM_DEFAULTS): _bool(),
                _req(CONF_OPTIMAL_START_MAX, d, ROOM_DEFAULTS): _number(10, 360, 5, "min"),
                _req(CONF_OPTIMAL_STOP, d, ROOM_DEFAULTS): _bool(),
                _req(CONF_OPTIMAL_STOP_MINUTES, d, ROOM_DEFAULTS): _number(5, 180, 5, "min"),
            }
        )
        errors: dict[str, str] = {}
        placeholders = {"error": ""}
        if user_input is not None:
            try:
                parse_schedule(user_input[CONF_SCHEDULE], names)
            except ScheduleError as err:
                errors[CONF_SCHEDULE] = "invalid_schedule"
                placeholders["error"] = str(err)
            if (
                user_input[CONF_SCHEDULE_SOURCE] == SCHEDULE_HELPER
                and not user_input.get(CONF_SCHEDULE_HELPER)
            ):
                errors[CONF_SCHEDULE_HELPER] = "helper_required"
            if not errors:
                self._data = _merge(self._data, schema, user_input)
                return await self.async_step_extras()
        return self.async_show_form(
            step_id="schedule",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_extras(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Solar gain and valve exercise."""
        d = self._data
        schema = vol.Schema(
            {
                _req(CONF_SOLAR_OFFSET, d, ROOM_DEFAULTS): _number(-3, 0, 0.1, "°C"),
                _req(CONF_VALVE_EXERCISE, d, ROOM_DEFAULTS): _bool(),
                _req(CONF_VALVE_DAY, d, ROOM_DEFAULTS): _select(list(WEEKDAYS), "weekday"),
                _req(CONF_VALVE_TIME, d, ROOM_DEFAULTS): selector.TimeSelector(),
            }
        )
        if user_input is not None:
            self._data = _merge(self._data, schema, user_input)
            return self._finish()
        return self.async_show_form(step_id="extras", data_schema=schema)

    def _finish(self) -> SubentryFlowResult:
        data = dict(self._data)
        title = str(data.pop(CONF_NAME, "Room")).strip() or "Room"
        if self._reconfigure:
            return self.async_update_and_abort(
                self._get_entry(), self._get_reconfigure_subentry(), title=title, data=data
            )
        return self.async_create_entry(title=title, data=data)
