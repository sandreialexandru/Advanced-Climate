"""Room controller: decides and commands one heating zone."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from datetime import date, datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import Event, EventStateChangedData, State, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    CALIBRATION_EXTERNAL,
    CALIBRATION_OFFSET,
    CONF_AREA,
    CONF_BATTERY_THRESHOLD,
    CONF_CALIBRATION_ENTITIES,
    CONF_CALIBRATION_MODE,
    CONF_CLIMATES,
    CONF_COMMAND_MODE,
    CONF_FROST_TEMP,
    CONF_HELPER_OFF_PRESET,
    CONF_HELPER_ON_PRESET,
    CONF_HYSTERESIS,
    CONF_LEARN_TOLERANCE,
    CONF_LINKED_WINDOW_SENSORS,
    CONF_MAX_TEMP,
    CONF_MIN_OFF,
    CONF_MIN_ON,
    CONF_NEARBY_MODE,
    CONF_NEARBY_TEMP,
    CONF_OCCUPANCY_MINUTES,
    CONF_OCCUPANCY_SENSORS,
    CONF_OPTIMAL_START,
    CONF_OPTIMAL_START_MAX,
    CONF_OPTIMAL_STOP,
    CONF_OPTIMAL_STOP_MINUTES,
    CONF_OVERRIDE_HOURS,
    CONF_OVERRIDE_MODE,
    CONF_LEVELS,
    CONF_PRESET_MAP,
    CONF_PRESET_NAMES,
    CONF_SCHEDULE,
    CONF_SCHEDULE_HELPER,
    CONF_SCHEDULE_SOURCE,
    CONF_SOLAR_OFFSET,
    CONF_SOURCE,
    CONF_SWITCHES,
    CONF_TEMP_AGGREGATION,
    CONF_TEMP_SENSORS,
    CONF_VALVE_DAY,
    CONF_VALVE_EXERCISE,
    CONF_VALVE_TIME,
    CONF_VERIFY_COMMANDS,
    CONF_WINDOW_ACTION,
    CONF_WINDOW_CLOSE_DELAY,
    CONF_WINDOW_DROP_DEGREES,
    CONF_WINDOW_DROP_DETECT,
    CONF_WINDOW_DROP_MINUTES,
    CONF_WINDOW_OPEN_DELAY,
    CONF_WINDOW_SENSORS,
    CONF_ALERT_WINDOW_MINUTES,
    COMMAND_HVAC,
    COMMAND_PRESET,
    DEFAULT_LEVEL_TEMPS,
    DEFAULT_SCHEDULE,
    DOMAIN,
    EVENT_DECISION_CHANGED,
    GT_DOMAIN,
    GT_PRESET_KEYS,
    MAX_DECISION_LOG,
    MODE_OFF,
    MODE_SUMMER,
    OVERRIDE_FIXED,
    OVERRIDE_NEXT,
    PRESETS,
    PRESET_NONE,
    ROOM_DEFAULTS,
    RULE_STARTING,
    SCHEDULE_HELPER,
    SOURCE_CLIMATE,
    SOURCE_GT,
    SOURCE_SWITCH,
    TEMP_DROP_HOLD_MINUTES,
    VALVE_EXERCISE_SECONDS,
    VERIFY_DELAY,
    WEEKDAYS,
)
from .engine import (
    KIND_NONE,
    KIND_OFF,
    KIND_PRESET,
    KIND_TEMPERATURE,
    Decision,
    RoomInputs,
    Target,
    decide,
    optimal_schedule,
)
from .learning import HeatingRateLearner
from .schedule import Schedule, ScheduleError, ScheduleState, Slot, parse_schedule
from .util import (
    aggregate,
    as_list,
    climate_temp,
    delta_from_celsius,
    delta_to_celsius,
    float_attr,
    from_celsius,
    from_iso,
    iso,
    parse_clock,
    system_unit,
    temp_state,
    to_celsius,
    valid,
)

if TYPE_CHECKING:
    from .house import House

_LOGGER = logging.getLogger(__name__)

AUTO_PROFILE = "auto"


class Room:
    """Controller for one room (config subentry)."""

    def __init__(self, house: House, subentry: ConfigSubentry, stored: dict[str, Any]) -> None:
        """Initialize."""
        self.house = house
        self.hass = house.hass
        self.id = subentry.subentry_id
        self.name = subentry.title
        self.unique_id = subentry.unique_id
        self.config: dict[str, Any] = {**ROOM_DEFAULTS, **subentry.data}
        self.source: str = self.config[CONF_SOURCE]
        self.climates = as_list(self.config.get(CONF_CLIMATES))
        self.switches = as_list(self.config.get(CONF_SWITCHES))
        self.command_mode: str = (
            COMMAND_PRESET if self.source == SOURCE_GT else self.config[CONF_COMMAND_MODE]
        )

        # Custom level names (when not using Generic Thermostat).
        names = dict(self.config.get(CONF_PRESET_NAMES) or {})
        self.preset_names: dict[str, str] = {
            p: (str(names.get(p)).strip() or p) if names.get(p) else p for p in PRESETS
        }
        # Climate devices commanded with presets: which device preset each level uses.
        # Levels without a device preset are reached with a temperature.
        self.preset_map: dict[str, str] | None = None
        self._legacy_map = False
        if self.source == SOURCE_CLIMATE and self.command_mode == COMMAND_PRESET:
            raw = self.config.get(CONF_PRESET_MAP)
            if raw is None:
                # Rooms made before 1.4: the level name (or the role) is the device preset.
                self._legacy_map = True
                raw = dict(self.preset_names)
            self.preset_map = {
                p: str(v).strip() for p, v in dict(raw).items() if p in PRESETS and v and str(v).strip()
            }
            if not self._legacy_map:
                self.preset_names = {p: self.preset_map.get(p, p) for p in PRESETS}
        self.aliases: dict[str, str] = {p: p for p in PRESETS}
        for role, name in self.preset_names.items():
            self.aliases[name.lower()] = role

        # Schedule
        self.schedule_error: str | None = None
        self.schedule = self._build_schedule(self.config.get(CONF_SCHEDULE) or DEFAULT_SCHEDULE)
        self.schedule_state: ScheduleState | None = None

        # Persisted state
        self.levels: dict[str, float] = {
            p: float(stored.get("levels", {}).get(p, DEFAULT_LEVEL_TEMPS[p])) for p in PRESETS
        }
        configured = self.config.get(CONF_LEVELS) or None
        if configured and configured != stored.get("levels_config"):
            # New temperatures chosen in the room settings win over older edits.
            for preset, value in configured.items():
                if preset in PRESETS and value is not None:
                    self.levels[preset] = float(value)
        self.levels_config: dict[str, float] | None = configured
        self.nearby_temp: float = float(
            stored.get("nearby_temp", self.config.get(CONF_NEARBY_TEMP) or 17.0)
        )
        self.override: dict[str, Any] | None = stored.get("override")
        if self.override is not None:
            self.override["until"] = from_iso(self.override.get("until"))
            self.override["since"] = from_iso(self.override.get("since"))
        self.child_lock = bool(stored.get("child_lock", False))
        self.profile_select: str = stored.get("profile_select", AUTO_PROFILE)
        if self.profile_select != AUTO_PROFILE and self.profile_select not in self.schedule.profiles:
            self.profile_select = AUTO_PROFILE
        self.learner = HeatingRateLearner.from_dict(stored.get("learner"))
        self.runtime_s = float(stored.get("runtime_s", 0.0))
        self.observed_temps: dict[str, float] = {
            str(k): float(v) for k, v in (stored.get("observed_temps") or {}).items()
        }
        self.decisions: deque[dict[str, Any]] = deque(
            stored.get("decisions", []), maxlen=MAX_DECISION_LOG
        )
        self.last_exercise: str | None = stored.get("last_exercise")

        # Runtime state
        self.decision: Decision | None = None
        self.current_temp: float | None = None
        self.target_temperature: float | None = None
        self.heat_demand = False
        self.next_wakeup: datetime | None = None
        self.window_open = False
        self._window_raw_since: datetime | None = None
        self._window_closed_since: datetime | None = None
        self._window_opened_at: datetime | None = None
        self._window_timer: Callable[[], None] | None = None
        self._temp_samples: deque[tuple[datetime, float]] = deque(maxlen=120)
        self._drop_until: datetime | None = None
        self._last_occupied: datetime | None = None
        self._started_at = dt_util.now()
        self._exercise_until: datetime | None = None
        self._relay_on: bool | None = None
        self._relay_changed: datetime | None = None
        self._demand_since: datetime | None = None
        self._unsubs: list[Callable[[], None]] = []
        self._verify_unsub: Callable[[], None] | None = None
        self._verify_attempts = 0
        self._unavailable_since: dict[str, datetime] = {}
        self._calibration_written: dict[str, datetime] = {}
        self.sensor_failed = False
        self.external_failed = False
        self.signature: tuple | None = None

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def apply_schedule(self, text: str) -> None:
        """Use a new schedule without reloading the integration."""
        self.config[CONF_SCHEDULE] = text
        self.schedule_error = None
        self.schedule = self._build_schedule(text)
        if self.profile_select != AUTO_PROFILE and self.profile_select not in self.schedule.profiles:
            self.profile_select = AUTO_PROFILE

    def _build_schedule(self, text: str) -> Schedule:
        valid_names = list(PRESETS) + [n for n in self.preset_names.values() if n not in PRESETS]
        try:
            profiles = parse_schedule(text, valid_names)
        except ScheduleError as err:
            self.schedule_error = str(err)
            _LOGGER.error("Room %s: invalid schedule (%s); using the default", self.name, err)
            profiles = parse_schedule(DEFAULT_SCHEDULE, PRESETS)
        normalized = {
            name: [Slot(s.minute, self.aliases.get(s.preset.lower(), s.preset)) for s in slots]
            for name, slots in profiles.items()
        }
        return Schedule(normalized, self.house.day_boundary_minutes)

    @callback
    def async_start(self) -> None:
        """Start tracking the room entities."""
        cfg = self.config
        tracked = set(self.climates) | set(self.switches)
        tracked |= set(as_list(cfg.get(CONF_TEMP_SENSORS)))
        tracked |= set(as_list(cfg.get(CONF_WINDOW_SENSORS)))
        tracked |= set(as_list(cfg.get(CONF_LINKED_WINDOW_SENSORS)))
        tracked |= set(as_list(cfg.get(CONF_OCCUPANCY_SENSORS)))
        if cfg.get(CONF_SCHEDULE_SOURCE) == SCHEDULE_HELPER and cfg.get(CONF_SCHEDULE_HELPER):
            tracked.add(cfg[CONF_SCHEDULE_HELPER])
        if tracked:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, sorted(tracked), self._async_entity_changed
                )
            )
        self._update_temperature(dt_util.now())
        self._update_window(dt_util.now())

    @callback
    def async_stop(self) -> None:
        """Stop all listeners and timers."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        for attr in ("_window_timer", "_verify_unsub"):
            unsub = getattr(self, attr)
            if unsub:
                unsub()
                setattr(self, attr, None)

    def as_dict(self) -> dict[str, Any]:
        """Data persisted between restarts."""
        override = None
        if self.override:
            override = {
                **self.override,
                "until": iso(self.override.get("until")),
                "since": iso(self.override.get("since")),
            }
        return {
            "levels": self.levels,
            "levels_config": self.levels_config,
            "nearby_temp": self.nearby_temp,
            "override": override,
            "child_lock": self.child_lock,
            "profile_select": self.profile_select,
            "learner": self.learner.as_dict(),
            "runtime_s": round(self.runtime_s, 1),
            "observed_temps": self.observed_temps,
            "decisions": list(self.decisions),
            "last_exercise": self.last_exercise,
        }

    # ------------------------------------------------------------------
    # Properties used by entities
    # ------------------------------------------------------------------
    @property
    def is_whole_house(self) -> bool:
        """True for the zone created with the house."""
        return self.unique_id == "whole_house"

    @property
    def area_name(self) -> str | None:
        """Name of the configured area."""
        area_id = self.config.get(CONF_AREA)
        if not area_id:
            return None
        area = ar.async_get(self.hass).async_get_area(area_id)
        return area.name if area else None

    @property
    def uses_custom_levels(self) -> bool:
        """True when the temperatures of the levels are set by this integration."""
        return self.source != SOURCE_GT

    @property
    def device_levels(self) -> list[str]:
        """Levels whose temperature is kept by the thermostat itself."""
        if self.source == SOURCE_GT:
            return list(PRESETS)
        if self.preset_map is None:
            return []
        if self._legacy_map:
            available = self.device_presets()
            return [p for p in PRESETS if self._device_preset(p, available) is not None]
        return [p for p in PRESETS if p in self.preset_map]

    @property
    def editable_levels(self) -> list[str]:
        """Levels whose temperature is set in this integration."""
        if self.source == SOURCE_GT:
            return []
        if self._legacy_map:
            # Rooms made before 1.4 keep every level editable until reconfigured.
            return list(PRESETS)
        return [p for p in PRESETS if p not in self.device_levels]

    def level_of_device_preset(self, name: str | None) -> str | None:
        """Level that uses the given device preset."""
        if not name:
            return None
        if self.source == SOURCE_GT:
            return name if name in PRESETS else None
        if self.preset_map is not None:
            for preset, device in self.preset_map.items():
                if device == name:
                    return preset
            if self._legacy_map and name in PRESETS:
                return name
        return None

    @property
    def supports_valve_exercise(self) -> bool:
        """Valve exercise only makes sense for climate devices (TRVs)."""
        return self.source == SOURCE_CLIMATE and self.command_mode != COMMAND_HVAC

    @property
    def rule(self) -> str:
        """The current decision rule."""
        return self.decision.rule if self.decision else RULE_STARTING

    @property
    def override_active(self) -> bool:
        """Return True if a manual override is active."""
        return self.override is not None

    @property
    def profile_options(self) -> list[str]:
        """Options of the profile select."""
        return [AUTO_PROFILE, *self.schedule.profile_names]

    def display_name(self, preset: str | None) -> str | None:
        """Return the user facing name of a level."""
        if preset is None:
            return None
        return self.preset_names.get(preset, preset)

    # ------------------------------------------------------------------
    # Temperatures of the levels
    # ------------------------------------------------------------------
    def _gt_options(self) -> dict[str, Any]:
        """Options of the Generic Thermostat config entry, if any."""
        if self.source != SOURCE_GT or not self.climates:
            return {}
        registry = er.async_get(self.hass)
        entry = registry.async_get(self.climates[0])
        if entry is None or entry.config_entry_id is None:
            return {}
        config_entry = self.hass.config_entries.async_get_entry(entry.config_entry_id)
        if config_entry is None or config_entry.domain != GT_DOMAIN:
            return {}
        return dict(config_entry.options)

    def level_temp(self, preset: str) -> float | None:
        """Return the temperature of a level, if known."""
        if preset not in PRESETS:
            return None
        if self.source != SOURCE_GT:
            if preset in self.device_levels and preset in self.observed_temps:
                # The thermostat keeps this preset; show what it really uses.
                return self.observed_temps[preset]
            return self.levels.get(preset)
        value = self._gt_options().get(GT_PRESET_KEYS[preset])
        if value is not None:
            try:
                return float(to_celsius(float(value), system_unit(self.hass)))
            except (TypeError, ValueError):
                pass
        return self.observed_temps.get(preset)

    def device_presets(self) -> list[str]:
        """Presets supported by the first available climate entity."""
        for entity_id in self.climates:
            state = self.hass.states.get(entity_id)
            if valid(state):
                return list(state.attributes.get("preset_modes") or [])  # type: ignore[union-attr]
        return []

    def device_preset(self) -> str | None:
        """Preset currently active on the first available thermostat."""
        for entity_id in self.climates:
            state = self.hass.states.get(entity_id)
            if valid(state):
                return state.attributes.get("preset_mode")  # type: ignore[union-attr]
        return None

    def frost_temp(self) -> float:
        """Frost protection temperature."""
        if self.source == SOURCE_GT:
            for entity_id in self.climates:
                value = climate_temp(self.hass, self.hass.states.get(entity_id), "min_temp")
                if value is not None:
                    return value
            gt_min = self._gt_options().get("min_temp")
            if gt_min is not None:
                return float(to_celsius(float(gt_min), system_unit(self.hass)))
        return float(self.house.options[CONF_FROST_TEMP])

    def max_temp(self) -> float:
        """Maximum allowed temperature."""
        maximum = float(self.house.options[CONF_MAX_TEMP])
        for entity_id in self.climates:
            value = climate_temp(self.hass, self.hass.states.get(entity_id), "max_temp")
            if value is not None:
                maximum = min(maximum, value) if self.source != SOURCE_GT else maximum
        return maximum

    def device_max_temp(self) -> float | None:
        """Highest temperature the thermostats accept (valve exercise)."""
        values = [
            v
            for entity_id in self.climates
            if (v := climate_temp(self.hass, self.hass.states.get(entity_id), "max_temp")) is not None
        ]
        return min(values) if values else None

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    @callback
    def _async_entity_changed(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        old: State | None = event.data["old_state"]
        new: State | None = event.data["new_state"]
        now = dt_util.now()
        if entity_id in self.climates:
            self._remember_preset_temp(new)
            if self._is_manual_change(event, old, new):
                self._handle_manual_change(entity_id, new)
        elif entity_id in self.switches:
            if (
                old is not None
                and new is not None
                and valid(old)
                and valid(new)
                and old.state != new.state
                and not self.house.is_own_context(event.context)
            ):
                self._handle_manual_change(entity_id, new)
        if entity_id in as_list(self.config.get(CONF_TEMP_SENSORS)) or entity_id in self.climates:
            self._update_temperature(now)
        self._update_window(now)
        self.house.async_request_evaluate()

    def _remember_preset_temp(self, state: State | None) -> None:
        """Learn the temperatures of the thermostat presets from the climate state."""
        if not valid(state):
            return
        preset = self.level_of_device_preset(state.attributes.get("preset_mode"))  # type: ignore[union-attr]
        temperature = climate_temp(self.hass, state, ATTR_TEMPERATURE)
        if preset is not None and temperature is not None:
            self.observed_temps[preset] = temperature

    def _is_manual_change(self, event: Event, old: State | None, new: State | None) -> bool:
        if old is None or new is None or not valid(old) or not valid(new):
            return False
        if self.house.is_own_context(event.context):
            return False
        if not self.house.started:
            return False
        if old.state != new.state:
            return True
        for attr in ("preset_mode", ATTR_TEMPERATURE):
            if old.attributes.get(attr) != new.attributes.get(attr):
                return True
        return False

    def _handle_manual_change(self, entity_id: str, new: State | None) -> None:
        if self.house.paused:
            return
        if self.child_lock and self.decision is not None:
            _LOGGER.debug("Room %s: child lock reverts a manual change", self.name)
            self.hass.async_create_task(self._async_apply(self.decision.target, force=True))
            return
        description = "manual change"
        if new is not None:
            if new.state == STATE_OFF:
                description = "turned off"
            elif new.attributes.get("preset_mode") not in (None, PRESET_NONE):
                description = f"preset {new.attributes.get('preset_mode')}"
            elif (value := climate_temp(self.hass, new, ATTR_TEMPERATURE)) is not None:
                unit = self.house.unit
                description = f"{from_celsius(value, unit):.1f} {unit}"
            elif entity_id in self.switches:
                description = f"switch {new.state}"
        if self.house.override_scope_house:
            for room in self.house.rooms.values():
                room.set_override(description, source=self.name)
        else:
            self.set_override(description)

    def set_override(
        self,
        description: str,
        *,
        source: str | None = None,
        hours: float | None = None,
        target: Target | None = None,
    ) -> None:
        """Start a manual override."""
        now = dt_util.now()
        mode = self.house.options[CONF_OVERRIDE_MODE]
        if hours is None and mode == OVERRIDE_FIXED:
            hours = float(self.house.options[CONF_OVERRIDE_HOURS])
        until = now + timedelta(hours=hours) if hours else None
        self.override = {
            "description": description if source is None else f"{description} ({source})",
            "since": now,
            "until": until,
            "mode": OVERRIDE_FIXED if until else OVERRIDE_NEXT,
            "signature": list(self.signature) if self.signature else None,
            "target": target.as_dict() if target else None,
        }
        self.house.async_save()

    def clear_override(self) -> None:
        """Clear the manual override."""
        self.override = None
        self.house.async_save()

    def _check_override(self, now: datetime, signature: tuple) -> None:
        if self.override is None:
            return
        until = self.override.get("until")
        if until is not None:
            if now >= until:
                self.override = None
            return
        stored = self.override.get("signature")
        if stored is None:
            self.override["signature"] = list(signature)
        elif tuple(stored) != tuple(signature):
            # Something relevant changed: the override ends.
            self.override = None

    # ------------------------------------------------------------------
    # Inputs
    # ------------------------------------------------------------------
    def _update_temperature(self, now: datetime) -> None:
        sensors = as_list(self.config.get(CONF_TEMP_SENSORS))
        values = []
        for entity_id in sensors:
            value = temp_state(self.hass, entity_id)
            if value is not None:
                values.append(value)
        external = aggregate(values, self.config[CONF_TEMP_AGGREGATION])
        self.external_failed = bool(sensors) and external is None
        device = None
        device_values = [
            v
            for eid in self.climates
            if (v := climate_temp(self.hass, self.hass.states.get(eid), "current_temperature"))
            is not None
        ]
        if device_values:
            device = round(sum(device_values) / len(device_values), 2)
        self.current_temp = external if external is not None else device
        # Without any temperature a relay cannot be regulated.
        needs_temp = self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC
        self.sensor_failed = self.current_temp is None and (bool(sensors) or needs_temp)
        if self.current_temp is not None:
            self._temp_samples.append((now, self.current_temp))
            self._check_temp_drop(now)

    def external_temperature(self) -> float | None:
        """Aggregated external sensors only."""
        values = []
        for entity_id in as_list(self.config.get(CONF_TEMP_SENSORS)):
            state = self.hass.states.get(entity_id)
            if valid(state):
                try:
                    values.append(float(state.state))  # type: ignore[union-attr]
                except (TypeError, ValueError):
                    continue
        return aggregate(values, self.config[CONF_TEMP_AGGREGATION])

    def _check_temp_drop(self, now: datetime) -> None:
        if not self.config[CONF_WINDOW_DROP_DETECT] or self.current_temp is None:
            return
        if self._drop_until is not None and now < self._drop_until:
            return  # already holding
        window = timedelta(minutes=float(self.config[CONF_WINDOW_DROP_MINUTES]))
        recent = [v for t, v in self._temp_samples if now - t <= window]
        # The value valid at the start of the window (sensors report on change).
        before = [(t, v) for t, v in self._temp_samples if now - t > window]
        if before and now - before[-1][0] <= window + timedelta(minutes=15):
            recent.append(before[-1][1])
        if recent and max(recent) - self.current_temp >= float(
            self.config[CONF_WINDOW_DROP_DEGREES]
        ):
            self._drop_until = now + timedelta(minutes=TEMP_DROP_HOLD_MINUTES)

    def learn_tolerance(self) -> float:
        """How far below the target the thermostat lets the room fall before heating."""
        if self.source == SOURCE_GT:
            value = self._gt_options().get("cold_tolerance")
            try:
                return (
                    float(delta_to_celsius(float(value), system_unit(self.hass)))
                    if value is not None
                    else 0.0
                )
            except (TypeError, ValueError):
                return 0.0
        if self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC:
            return float(self.config[CONF_HYSTERESIS])
        return float(self.config.get(CONF_LEARN_TOLERANCE, 0.0))

    def time_to_target(self, outdoor: float | None) -> int | None:
        """Minutes until the target is reached at the learned rate (None when not heating up)."""
        if self.current_temp is None or self.target_temperature is None:
            return None
        if self.decision is None or self.decision.target.kind == KIND_OFF or self.window_open:
            return None
        gap = self.target_temperature - self.current_temp
        if gap <= 0.1:
            return None
        return max(1, round(gap / self.learner.rate(outdoor) * 60))

    def _window_sensor_open(self) -> bool:
        """A window or door sensor of the room (or a linked one) is open right now."""
        sensors = as_list(self.config.get(CONF_WINDOW_SENSORS)) + as_list(
            self.config.get(CONF_LINKED_WINDOW_SENSORS)
        )
        return any(
            (st := self.hass.states.get(eid)) is not None and st.state == STATE_ON
            for eid in sensors
        )

    def _window_raw(self, now: datetime) -> bool:
        if self.house.windows_ignored:
            return False
        sensors = as_list(self.config.get(CONF_WINDOW_SENSORS)) + as_list(
            self.config.get(CONF_LINKED_WINDOW_SENSORS)
        )
        if any(
            (st := self.hass.states.get(eid)) is not None and st.state == STATE_ON
            for eid in sensors
        ):
            return True
        return self._drop_until is not None and now < self._drop_until

    def _update_window(self, now: datetime) -> None:
        """Debounce the window state with the open / close delays."""
        raw = self._window_raw(now)
        open_delay = timedelta(seconds=float(self.config[CONF_WINDOW_OPEN_DELAY]))
        close_delay = timedelta(seconds=float(self.config[CONF_WINDOW_CLOSE_DELAY]))
        due: datetime | None = None
        if raw:
            self._window_closed_since = None
            if not self.window_open:
                if self._window_raw_since is None:
                    self._window_raw_since = now
                if now - self._window_raw_since >= open_delay:
                    self.window_open = True
                    self._window_opened_at = now
                else:
                    due = self._window_raw_since + open_delay
        else:
            self._window_raw_since = None
            if self.window_open:
                if self._window_closed_since is None:
                    self._window_closed_since = now
                if now - self._window_closed_since >= close_delay:
                    self.window_open = False
                    self._window_opened_at = None
                    self._window_closed_since = None
                    self.house.clear_alert(f"window_{self.id}")
                else:
                    due = self._window_closed_since + close_delay
        if self._drop_until is not None and now < self._drop_until:
            due = min(due, self._drop_until) if due else self._drop_until
        if self._window_timer:
            self._window_timer()
            self._window_timer = None
        if due is not None:
            delay = max((due - now).total_seconds(), 0) + 0.5

            @callback
            def _recheck(_now: datetime) -> None:
                self._window_timer = None
                self._update_window(dt_util.now())
                self.house.async_request_evaluate(0)

            self._window_timer = async_call_later(self.hass, delay, _recheck)

    def _room_unoccupied(self, now: datetime) -> bool:
        sensors = as_list(self.config.get(CONF_OCCUPANCY_SENSORS))
        if not sensors:
            return False
        if any(
            (st := self.hass.states.get(eid)) is not None and st.state == STATE_ON
            for eid in sensors
        ):
            self._last_occupied = now
            return False
        since = self._last_occupied or self._started_at
        return now - since >= timedelta(minutes=float(self.config[CONF_OCCUPANCY_MINUTES]))

    def _day_info(self, day: date) -> tuple[bool, str | None]:
        forced = None
        today = self.schedule.schedule_day(dt_util.now())
        if day == today:
            if self.profile_select != AUTO_PROFILE:
                forced = self.profile_select
            elif self.house.calendar_message:
                message = self.house.calendar_message.lower()
                if message in self.schedule.profiles:
                    forced = message
        return self.house.is_workday(day), forced

    def _schedule_lookup(self, now: datetime) -> ScheduleState | None:
        cfg = self.config
        if cfg.get(CONF_SCHEDULE_SOURCE) == SCHEDULE_HELPER and cfg.get(CONF_SCHEDULE_HELPER):
            state = self.hass.states.get(cfg[CONF_SCHEDULE_HELPER])
            if not valid(state):
                return None
            on = state.state == STATE_ON  # type: ignore[union-attr]
            preset = cfg[CONF_HELPER_ON_PRESET] if on else cfg[CONF_HELPER_OFF_PRESET]
            data_preset = state.attributes.get("preset")  # type: ignore[union-attr]
            if on and data_preset:
                preset = self.aliases.get(str(data_preset).lower(), preset)
            next_event = from_iso(state.attributes.get("next_event"))  # type: ignore[union-attr]
            next_preset = cfg[CONF_HELPER_OFF_PRESET] if on else cfg[CONF_HELPER_ON_PRESET]
            return ScheduleState(
                preset=preset,
                profile="helper",
                slot_start=state.last_changed,  # type: ignore[union-attr]
                next_change=next_event,
                next_preset=next_preset if next_event else None,
            )
        return self.schedule.lookup(now, self._day_info)

    def plan(self, now: datetime, hours: float = 12) -> list[dict[str, Any]]:
        """Schedule levels for the next hours (shown by the card)."""
        state = self.schedule_state
        if state is None:
            return []
        result = [{"at": now.isoformat(), "preset": state.preset}]
        cfg = self.config
        if cfg.get(CONF_SCHEDULE_SOURCE) == SCHEDULE_HELPER and cfg.get(CONF_SCHEDULE_HELPER):
            if state.next_change and state.next_preset:
                result.append({"at": state.next_change.isoformat(), "preset": state.next_preset})
            return result
        try:
            changes = self.schedule.upcoming(now, self._day_info, timedelta(hours=hours))
        except Exception:  # noqa: BLE001 - the plan is only informative
            return result
        result += [{"at": moment.isoformat(), "preset": preset} for moment, preset in changes]
        return result

    def _calendar_preset(self) -> str | None:
        message = self.house.calendar_message
        if not message:
            return None
        return self.aliases.get(message.lower())

    def _offsets(self) -> list[tuple[str, float]]:
        offsets = self.house.house_offsets()
        solar = float(self.config.get(CONF_SOLAR_OFFSET) or 0)
        if solar and self.house.sunny():
            offsets.append(("solar_gain", solar))
        return offsets

    def _valve_exercise_due(self, now: datetime) -> bool:
        if not self.config[CONF_VALVE_EXERCISE] or not self.supports_valve_exercise:
            return False
        if self._exercise_until is not None:
            if now < self._exercise_until:
                return True
            self._exercise_until = None
            return False
        if WEEKDAYS[now.weekday()] != self.config[CONF_VALVE_DAY]:
            return False
        start = parse_clock(self.config[CONF_VALVE_TIME])
        start_dt = now.replace(hour=start.hour, minute=start.minute, second=0, microsecond=0)
        today = now.date().isoformat()
        if start_dt <= now < start_dt + timedelta(minutes=30) and self.last_exercise != today:
            self.last_exercise = today
            self._exercise_until = now + timedelta(seconds=VALVE_EXERCISE_SECONDS)
            return True
        return False

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    async def async_evaluate(self, now: datetime) -> None:
        """Decide and apply."""
        house = self.house
        self._update_temperature(now)
        self._update_window(now)
        self._account_runtime(now)

        state = self._schedule_lookup(now)
        self.schedule_state = state
        preset = state.preset if state else None
        schedule_rule = "schedule"
        calendar_preset = self._calendar_preset()
        if calendar_preset is not None:
            preset = calendar_preset
        elif state is not None:
            preset, schedule_rule = optimal_schedule(
                now,
                state.preset,
                state.next_change,
                state.next_preset,
                self.current_temp,
                self.level_temp,
                self.learner.rate(house.outdoor.latest()),
                bool(self.config[CONF_OPTIMAL_START]),
                float(self.config[CONF_OPTIMAL_START_MAX]),
                bool(self.config[CONF_OPTIMAL_STOP]),
                float(self.config[CONF_OPTIMAL_STOP_MINUTES]),
            )

        vacation = house.vacation_active(now)
        signature = (
            house.mode,
            house.presence_state,
            house.arriving,
            vacation,
            preset,
            state.profile if state else None,
            self.window_open,
            house.cutoff_active,
            house.season_active,
        )
        self.signature = signature
        self._check_override(now, signature)
        valve = self._valve_exercise_due(now)

        inputs = RoomInputs(
            now=now,
            mode=house.mode,
            paused=house.paused,
            season_active=house.season_active,
            cutoff_active=house.cutoff_active,
            valve_exercise=valve,
            window_open=self.window_open,
            window_action=self.config[CONF_WINDOW_ACTION],
            override_active=self.override_active,
            vacation_active=vacation,
            presence=house.presence_state or "home",
            arriving=house.arriving,
            room_unoccupied=self._room_unoccupied(now),
            sensor_failed=self.sensor_failed,
            schedule_preset=preset,
            schedule_rule=schedule_rule,
            current_temp=self.current_temp,
            frost_temp=self.frost_temp(),
            max_temp=self.max_temp(),
            exercise_temp=self.device_max_temp(),
            nearby_mode=self.config[CONF_NEARBY_MODE],
            nearby_temp=self.nearby_temp,
            level_temp=self.level_temp,
            offsets=self._offsets(),
            supports_off=self._supports_off(),
            unit=self.house.unit,
        )
        decision = decide(inputs)
        self._record(decision, now)
        self.decision = decision
        self.target_temperature = self._resolve_temperature(decision.target)

        await self._async_apply(decision.target)
        await self._async_calibrate(now)
        self._update_demand()
        self.learner.observe(
            now, self.heat_demand, self.current_temp, self.target_temperature,
            house.outdoor.latest(), self._window_sensor_open(), self.learn_tolerance(),
        )
        self._check_alerts(now)

        # When should we look again?
        wakeups = []
        if state and state.next_change:
            wakeups.append(state.next_change)
        if self.override and self.override.get("until"):
            wakeups.append(self.override["until"])
        if self._exercise_until:
            wakeups.append(self._exercise_until)
        self.next_wakeup = min(wakeups) if wakeups else None

    def _supports_off(self) -> bool:
        if self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC:
            return True
        for entity_id in self.climates:
            state = self.hass.states.get(entity_id)
            if valid(state):
                return STATE_OFF in (state.attributes.get("hvac_modes") or [])  # type: ignore[union-attr]
        return True

    def _override_target(self) -> Target | None:
        """Level or temperature of a manual change set by the card or a service."""
        stored = (self.override or {}).get("target")
        if not isinstance(stored, dict) or stored.get("kind") not in (KIND_TEMPERATURE, KIND_PRESET):
            return None
        return Target(stored["kind"], preset=stored.get("preset"), temperature=stored.get("temperature"))

    def _resolve_temperature(self, target: Target) -> float | None:
        if target.kind == KIND_TEMPERATURE:
            return target.temperature
        if target.kind == KIND_PRESET and target.preset:
            return self.level_temp(target.preset)
        if target.kind == KIND_NONE and (stored := self._override_target()) is not None:
            return self._resolve_temperature(stored)
        if target.kind == KIND_NONE:
            for entity_id in self.climates:
                value = climate_temp(self.hass, self.hass.states.get(entity_id), ATTR_TEMPERATURE)
                if value is not None:
                    return value
        return None

    def _record(self, decision: Decision, now: datetime) -> None:
        previous = self.decision
        if (
            previous is not None
            and previous.rule == decision.rule
            and previous.target == decision.target
        ):
            return
        entry = {
            "time": now.isoformat(),
            "rule": decision.rule,
            "target": decision.target.as_dict(),
            "description": decision.description,
        }
        self.decisions.append(entry)
        self.hass.bus.async_fire(
            EVENT_DECISION_CHANGED,
            {
                "room": self.name,
                "room_id": self.id,
                "old_rule": previous.rule if previous else None,
                "old_target": previous.target.as_dict() if previous else None,
                "rule": decision.rule,
                "target": decision.target.as_dict(),
                "reason": decision.description,
            },
        )

    def _account_runtime(self, now: datetime) -> None:
        if self._demand_since is not None:
            self.runtime_s += (now - self._demand_since).total_seconds()
            self._demand_since = now if self.heat_demand else None

    def _update_demand(self) -> None:
        demand = False
        if self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC:
            demand = bool(self._relay_on)
        else:
            for entity_id in self.climates:
                state = self.hass.states.get(entity_id)
                if not valid(state):
                    continue
                action = state.attributes.get("hvac_action")  # type: ignore[union-attr]
                if action is not None:
                    demand = demand or action == "heating"
                    continue
                current = climate_temp(self.hass, state, "current_temperature")
                target = climate_temp(self.hass, state, ATTR_TEMPERATURE)
                if (
                    state.state != STATE_OFF  # type: ignore[union-attr]
                    and current is not None
                    and target is not None
                    and current < target - 0.2
                ):
                    demand = True
        if demand and self._demand_since is None:
            self._demand_since = dt_util.now()
        if not demand and self._demand_since is not None:
            self._account_runtime(dt_util.now())
            self._demand_since = None
        self.heat_demand = demand

    def temperature_gap(self) -> float | None:
        """Degrees below the target (negative when above)."""
        if self.current_temp is None or self.target_temperature is None:
            return None
        if self.decision is None or self.decision.target.kind == KIND_OFF:
            return None
        return round(self.target_temperature - self.current_temp, 2)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    async def _call(self, domain: str, service: str, data: dict[str, Any]) -> bool:
        try:
            await self.hass.services.async_call(
                domain, service, data, blocking=True, context=self.house.new_context()
            )
        except (HomeAssistantError, ValueError) as err:
            _LOGGER.warning("Room %s: %s.%s failed: %s", self.name, domain, service, err)
            return False
        return True

    async def _async_apply(self, target: Target, *, force: bool = False) -> None:
        """Send the commands needed to reach ``target``."""
        on_off = self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC
        if target.kind == KIND_NONE:
            # Relays keep regulating around a manual temperature set by the card or a service.
            stored = self._override_target() if on_off else None
            if stored is None:
                return
            target = stored
        sent = False
        if on_off:
            sent = await self._async_apply_relay(target)
        else:
            for entity_id in self.climates:
                sent |= await self._async_apply_climate(entity_id, target, force)
        if sent and self.house.options[CONF_VERIFY_COMMANDS]:
            self._schedule_verify(target)

    def _device_preset(self, preset: str, available: list[str]) -> str | None:
        """Map a level to the device preset name."""
        if self.source == SOURCE_GT:
            return preset if preset in available else None
        if self.preset_map is None:
            return None
        candidates = [self.preset_map.get(preset)]
        if self._legacy_map:
            candidates.append(preset)
        for candidate in candidates:
            if candidate and candidate in available:
                return candidate
        return None

    def _matches(self, state: State, target: Target) -> bool:
        """Return True if the climate state already matches the target."""
        if target.kind == KIND_OFF:
            if STATE_OFF in (state.attributes.get("hvac_modes") or []):
                return state.state == STATE_OFF
            return float_attr(state, ATTR_TEMPERATURE) == float_attr(state, "min_temp")
        if state.state == STATE_OFF:
            return False
        if target.kind == KIND_PRESET and self.command_mode == COMMAND_PRESET:
            name = self._device_preset(
                target.preset or "", list(state.attributes.get("preset_modes") or [])
            )
            if name is not None:
                return state.attributes.get("preset_mode") == name
        temperature = (
            target.temperature
            if target.kind == KIND_TEMPERATURE
            else self.level_temp(target.preset or "")
        )
        if temperature is None:
            return True
        # Compared in the unit of the thermostat, as sent.
        current = float_attr(state, ATTR_TEMPERATURE)
        wanted = round(float(from_celsius(temperature, system_unit(self.hass))), 1)
        return current is not None and abs(current - wanted) < 0.05

    async def _async_apply_climate(self, entity_id: str, target: Target, force: bool) -> bool:
        state = self.hass.states.get(entity_id)
        if not valid(state):
            return False
        assert state is not None
        if not force and self._matches(state, target):
            return False
        modes = list(state.attributes.get("hvac_modes") or [])
        heat_mode = "heat" if "heat" in modes else ("auto" if "auto" in modes else None)

        if target.kind == KIND_OFF:
            if STATE_OFF in modes:
                return await self._call(
                    "climate", "set_hvac_mode", {ATTR_ENTITY_ID: entity_id, "hvac_mode": STATE_OFF}
                )
            minimum = float_attr(state, "min_temp")
            if minimum is None:
                return False
            return await self._call(
                "climate", "set_temperature", {ATTR_ENTITY_ID: entity_id, ATTR_TEMPERATURE: minimum}
            )

        if state.state == STATE_OFF and heat_mode:
            await self._call(
                "climate", "set_hvac_mode", {ATTR_ENTITY_ID: entity_id, "hvac_mode": heat_mode}
            )

        if target.kind == KIND_PRESET and self.command_mode == COMMAND_PRESET:
            available = list(state.attributes.get("preset_modes") or [])
            name = self._device_preset(target.preset or "", available)
            if name is not None:
                self.house.clear_alert(f"preset_{self.id}_{target.preset}")
                return await self._call(
                    "climate", "set_preset_mode", {ATTR_ENTITY_ID: entity_id, "preset_mode": name}
                )
        temperature = (
            target.temperature
            if target.kind == KIND_TEMPERATURE
            else self.level_temp(target.preset or "")
        )
        if temperature is None:
            self.house.notify(
                f"preset_{self.id}_{target.preset}",
                f"{self.name}: the level '{self.display_name(target.preset)}' is not "
                f"available on {entity_id} and its temperature is unknown. "
                "Configure this preset in the thermostat.",
            )
            return False
        return await self._call(
            "climate",
            "set_temperature",
            {
                ATTR_ENTITY_ID: entity_id,
                ATTR_TEMPERATURE: round(float(from_celsius(temperature, system_unit(self.hass))), 1),
            },
        )

    async def _async_apply_relay(self, target: Target) -> bool:
        """On/off control for switches or climates in hvac_mode command mode."""
        now = dt_util.now()
        if target.kind == KIND_OFF:
            want = False
        else:
            temperature = self._resolve_temperature(target)
            if temperature is None or self.current_temp is None:
                want = False
            else:
                hysteresis = float(self.config[CONF_HYSTERESIS])
                if self.current_temp <= temperature - hysteresis:
                    want = True
                elif self.current_temp >= temperature + hysteresis:
                    want = False
                else:
                    want = bool(self._relay_on)
        actual = self._relay_actual()
        if actual is None:
            return False
        self._relay_on = actual
        if want == actual:
            return False
        if self._relay_changed is not None:
            minimum = timedelta(
                minutes=float(self.config[CONF_MIN_ON] if actual else self.config[CONF_MIN_OFF])
            )
            if now - self._relay_changed < minimum:
                return False
        ok = True
        if self.source == SOURCE_SWITCH:
            for entity_id in self.switches:
                ok &= await self._call(
                    entity_id.split(".", 1)[0],
                    SERVICE_TURN_ON if want else SERVICE_TURN_OFF,
                    {ATTR_ENTITY_ID: entity_id},
                )
        else:
            for entity_id in self.climates:
                state = self.hass.states.get(entity_id)
                modes = list(state.attributes.get("hvac_modes") or []) if valid(state) else []  # type: ignore[union-attr]
                on_mode = "heat" if "heat" in modes else ("auto" if "auto" in modes else "heat")
                ok &= await self._call(
                    "climate",
                    "set_hvac_mode",
                    {ATTR_ENTITY_ID: entity_id, "hvac_mode": on_mode if want else STATE_OFF},
                )
        if ok:
            self._relay_on = want
            self._relay_changed = now
        return ok

    def _relay_actual(self) -> bool | None:
        entities = self.switches if self.source == SOURCE_SWITCH else self.climates
        states = [self.hass.states.get(eid) for eid in entities]
        usable = [s for s in states if valid(s)]
        if not usable:
            return None
        return any(s.state not in (STATE_OFF,) for s in usable)  # type: ignore[union-attr]

    def _schedule_verify(self, target: Target) -> None:
        if self._verify_unsub:
            self._verify_unsub()
        expected = target

        async def _verify(_now: datetime) -> None:
            self._verify_unsub = None
            if self.decision is None or self.decision.target != expected:
                self._verify_attempts = 0
                return
            if self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC:
                self._verify_attempts = 0
                return
            mismatched = [
                eid
                for eid in self.climates
                if valid(state := self.hass.states.get(eid))
                and not self._matches(state, expected)  # type: ignore[arg-type]
            ]
            if not mismatched:
                self._verify_attempts = 0
                self.house.clear_alert(f"verify_{self.id}")
                return
            self._verify_attempts += 1
            if self._verify_attempts == 1:
                await self._async_apply(expected, force=True)
            else:
                self._verify_attempts = 0
                self.house.notify(
                    f"verify_{self.id}",
                    f"{self.name}: {', '.join(mismatched)} did not accept "
                    f"{expected.describe(self.house.unit)}.",
                    repeat=timedelta(hours=6),
                )

        self._verify_unsub = async_call_later(self.hass, VERIFY_DELAY, _verify)

    async def async_apply_manual(self, target: Target, hours: float | None) -> None:
        """Service: set a manual target and keep it as an override."""
        await self._async_apply(target, force=True)
        self.set_override(
            f"set by service: {target.describe(self.house.unit)}", hours=hours, target=target
        )

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------
    async def _async_calibrate(self, now: datetime) -> None:
        mode = self.config[CONF_CALIBRATION_MODE]
        if mode not in (CALIBRATION_OFFSET, CALIBRATION_EXTERNAL):
            return
        external = self.external_temperature()
        if external is None:
            return
        entity_reg = er.async_get(self.hass)
        for number_id in as_list(self.config.get(CONF_CALIBRATION_ENTITIES)):
            number = self.hass.states.get(number_id)
            if not valid(number):
                continue
            assert number is not None
            last = self._calibration_written.get(number_id)
            interval = timedelta(minutes=10 if mode == CALIBRATION_OFFSET else 5)
            if last is not None and now - last < interval:
                continue
            step = float_attr(number, "step") or 0.1
            minimum = float_attr(number, "min")
            maximum = float_attr(number, "max")
            current = float(number.state)
            # The TRV number has its own unit (usually °C).
            number_unit = number.attributes.get("unit_of_measurement") or system_unit(self.hass)
            if mode == CALIBRATION_EXTERNAL:
                value = float(from_celsius(external, number_unit))
            else:
                climate_id = self._climate_on_same_device(entity_reg, number_id)
                device_temp = (
                    climate_temp(self.hass, self.hass.states.get(climate_id), "current_temperature")
                    if climate_id
                    else None
                )
                if device_temp is None:
                    continue
                value = current + float(delta_from_celsius(external - device_temp, number_unit))
            value = round(round(value / step) * step, 2)
            if minimum is not None:
                value = max(minimum, value)
            if maximum is not None:
                value = min(maximum, value)
            if abs(value - current) < max(step, 0.1):
                continue
            if await self._call("number", "set_value", {ATTR_ENTITY_ID: number_id, "value": value}):
                self._calibration_written[number_id] = now

    def _climate_on_same_device(self, registry: er.EntityRegistry, entity_id: str) -> str | None:
        entry = registry.async_get(entity_id)
        if entry is None or entry.device_id is None:
            return self.climates[0] if len(self.climates) == 1 else None
        for climate_id in self.climates:
            climate_entry = registry.async_get(climate_id)
            if climate_entry is not None and climate_entry.device_id == entry.device_id:
                return climate_id
        return None

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------
    def _check_alerts(self, now: datetime) -> None:
        house = self.house
        # Window open for too long while heating matters.
        if self.window_open and self._window_opened_at is not None:
            minutes = float(house.options[CONF_ALERT_WINDOW_MINUTES])
            heating_relevant = house.mode not in (MODE_OFF, MODE_SUMMER) and house.season_active
            if heating_relevant and now - self._window_opened_at >= timedelta(minutes=minutes):
                house.notify(
                    f"window_{self.id}",
                    f"{self.name}: a window has been open for more than {minutes:.0f} minutes.",
                )
        # Unavailable devices.
        limit = timedelta(minutes=house.alert_unavailable_minutes)
        for entity_id in self.climates + self.switches:
            state = self.hass.states.get(entity_id)
            if valid(state):
                if self._unavailable_since.pop(entity_id, None) is not None:
                    house.clear_alert(f"unavailable_{entity_id}")
                continue
            since = self._unavailable_since.setdefault(entity_id, now)
            if now - since >= limit:
                house.notify(
                    f"unavailable_{entity_id}",
                    f"{self.name}: {entity_id} has been unavailable for more than "
                    f"{limit.total_seconds() / 60:.0f} minutes.",
                )
        # External sensors.
        if self.external_failed:
            fallback = "the device sensor" if not self.sensor_failed else "eco"
            house.notify(
                f"sensor_{self.id}",
                f"{self.name}: the temperature sensors are unavailable; using {fallback}.",
            )
        else:
            house.clear_alert(f"sensor_{self.id}")
        # Schedule errors.
        if self.schedule_error:
            house.notify(
                f"schedule_{self.id}",
                f"{self.name}: the schedule is invalid ({self.schedule_error}); "
                "the default schedule is used.",
            )

    @callback
    def check_batteries(self) -> None:
        """Alert about low batteries of the room devices."""
        threshold = float(self.house.options[CONF_BATTERY_THRESHOLD])
        entity_reg = er.async_get(self.hass)
        device_reg = dr.async_get(self.hass)
        devices: set[str] = set()
        related = (
            self.climates
            + self.switches
            + as_list(self.config.get(CONF_TEMP_SENSORS))
            + as_list(self.config.get(CONF_WINDOW_SENSORS))
            + as_list(self.config.get(CONF_OCCUPANCY_SENSORS))
        )
        for entity_id in related:
            entry = entity_reg.async_get(entity_id)
            if entry is not None and entry.device_id:
                devices.add(entry.device_id)
        for device_id in devices:
            device = device_reg.async_get(device_id)
            for entry in er.async_entries_for_device(entity_reg, device_id):
                if entry.domain != "sensor":
                    continue
                if (entry.device_class or entry.original_device_class) != "battery":
                    continue
                state = self.hass.states.get(entry.entity_id)
                if not valid(state):
                    continue
                try:
                    level = float(state.state)  # type: ignore[union-attr]
                except (TypeError, ValueError):
                    continue
                key = f"battery_{entry.entity_id}"
                if level < threshold:
                    name = (device.name_by_user or device.name) if device else entry.entity_id
                    self.house.notify(
                        key,
                        f"{self.name}: low battery on {name} ({level:.0f}%).",
                        repeat=timedelta(days=1),
                    )
                else:
                    self.house.clear_alert(key)

    # ------------------------------------------------------------------
    # Setters used by entities and services
    # ------------------------------------------------------------------
    async def async_set_level(self, preset: str, value: float) -> None:
        """Set the temperature of a custom level."""
        if preset == "nearby":
            self.nearby_temp = value
        else:
            self.levels[preset] = value
        await self.house.async_evaluate_or_notify()

    async def async_set_profile(self, profile: str) -> None:
        """Select a profile manually (or auto)."""
        if profile != AUTO_PROFILE and profile not in self.schedule.profiles:
            raise HomeAssistantError(f"Unknown profile {profile}")
        self.profile_select = profile
        await self.house.async_evaluate_or_notify()

    async def async_set_child_lock(self, on: bool) -> None:
        """Enable or disable the child lock."""
        self.child_lock = on
        await self.house.async_evaluate_or_notify()

    # ------------------------------------------------------------------
    # Diagnostics / attributes
    # ------------------------------------------------------------------
    def override_info(self) -> dict[str, Any] | None:
        """Override details for attributes."""
        if not self.override:
            return None
        return {
            "description": self.override.get("description"),
            "since": iso(self.override.get("since")),
            "until": iso(self.override.get("until")),
            "mode": self.override.get("mode"),
        }

    def diagnostics(self) -> dict[str, Any]:
        """Diagnostics for this room."""
        return {
            "id": self.id,
            "config": self.config,
            "rule": self.rule,
            "decision": self.decision.as_dict() if self.decision else None,
            "current_temperature": self.current_temp,
            "target_temperature": self.target_temperature,
            "heat_demand": self.heat_demand,
            "window_open": self.window_open,
            "override": self.override_info(),
            "profile_select": self.profile_select,
            "schedule_error": self.schedule_error,
            "schedule_state": (
                {
                    "preset": self.schedule_state.preset,
                    "profile": self.schedule_state.profile,
                    "next_change": iso(self.schedule_state.next_change),
                    "next_preset": self.schedule_state.next_preset,
                }
                if self.schedule_state
                else None
            ),
            "levels": {p: self.level_temp(p) for p in PRESETS},
            "learned_rates": self.learner.rates,
            "runtime_hours": round(self.runtime_s / 3600, 2),
            "decisions": list(self.decisions),
        }

    @property
    def domain(self) -> str:
        """Integration domain."""
        return DOMAIN
