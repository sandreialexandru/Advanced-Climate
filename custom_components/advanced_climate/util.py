"""Small helpers shared by the house and room controllers."""

from __future__ import annotations

from datetime import datetime, time
import statistics
from typing import Any

from homeassistant.core import HomeAssistant, State
from homeassistant.util import dt as dt_util

from .const import AGG_MEDIAN, AGG_MIN

INVALID = {"unknown", "unavailable", "", None}


def valid(state: State | None) -> bool:
    """Return True if the state is usable."""
    return state is not None and state.state not in INVALID


def float_state(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Return the numeric state of an entity or None."""
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if not valid(state):
        return None
    try:
        return float(state.state)  # type: ignore[union-attr]
    except (TypeError, ValueError):
        return None


def float_attr(state: State | None, attr: str) -> float | None:
    """Return a numeric attribute or None."""
    if state is None:
        return None
    value = state.attributes.get(attr)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Temperature units. Everything is kept in °C inside the integration; values
# are converted where they come from or go to Home Assistant and the user.
# ---------------------------------------------------------------------------
CELSIUS = "°C"
FAHRENHEIT = "°F"


def is_fahrenheit(unit: str | None) -> bool:
    """Return True for a Fahrenheit unit."""
    text = str(unit or "").strip().lower()
    return text.endswith("f") or text.startswith("fahr")


def to_celsius(value: float | None, unit: str | None) -> float | None:
    """Convert an absolute temperature to °C."""
    if value is None:
        return None
    return (value - 32.0) / 1.8 if is_fahrenheit(unit) else value


def from_celsius(value: float | None, unit: str | None) -> float | None:
    """Convert an absolute temperature from °C."""
    if value is None:
        return None
    return value * 1.8 + 32.0 if is_fahrenheit(unit) else value


def delta_to_celsius(value: float | None, unit: str | None) -> float | None:
    """Convert a temperature difference to °C."""
    if value is None:
        return None
    return value / 1.8 if is_fahrenheit(unit) else value


def delta_from_celsius(value: float | None, unit: str | None) -> float | None:
    """Convert a temperature difference from °C."""
    if value is None:
        return None
    return value * 1.8 if is_fahrenheit(unit) else value


def system_unit(hass: HomeAssistant) -> str:
    """Temperature unit of Home Assistant (climate attributes and commands use it)."""
    try:
        return str(hass.config.units.temperature_unit)
    except AttributeError:
        return CELSIUS


def temp_state(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Temperature of a sensor in °C (its own unit, else the system unit)."""
    value = float_state(hass, entity_id)
    if value is None:
        return None
    state = hass.states.get(entity_id)  # type: ignore[arg-type]
    unit = state.attributes.get("unit_of_measurement") if state else None
    return to_celsius(value, unit or system_unit(hass))


def climate_temp(hass: HomeAssistant, state: State | None, attr: str) -> float | None:
    """Temperature attribute of a climate entity in °C (climate uses the system unit)."""
    return to_celsius(float_attr(state, attr), system_unit(hass))


def aggregate(values: list[float], method: str) -> float | None:
    """Aggregate temperatures."""
    if not values:
        return None
    if method == AGG_MIN:
        return min(values)
    if method == AGG_MEDIAN:
        return float(statistics.median(values))
    return round(sum(values) / len(values), 2)


def parse_clock(value: Any, default: time = time(0, 0)) -> time:
    """Parse HH:MM[:SS] into a time."""
    if isinstance(value, time):
        return value
    try:
        parts = [int(p) for p in str(value).split(":")]
        return time(parts[0], parts[1] if len(parts) > 1 else 0)
    except (TypeError, ValueError, IndexError):
        return default


def as_list(value: Any) -> list[str]:
    """Normalize an entity selector value to a list."""
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def iso(value: datetime | None) -> str | None:
    """Datetime to ISO string."""
    return value.isoformat() if value else None


def from_iso(value: Any) -> datetime | None:
    """ISO string to aware datetime."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    parsed = dt_util.parse_datetime(str(value))
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.get_default_time_zone())
    return parsed


def distance_km(state: State | None) -> float | None:
    """Return a distance sensor value in km (handles m / km / mi)."""
    if not valid(state):
        return None
    try:
        value = float(state.state)  # type: ignore[union-attr]
    except (TypeError, ValueError):
        return None
    unit = (state.attributes.get("unit_of_measurement") or "km").lower()  # type: ignore[union-attr]
    if unit == "m":
        return value / 1000
    if unit == "mi":
        return value * 1.609344
    if unit == "ft":
        return value * 0.0003048
    return value


def minutes_value(state: State | None) -> float | None:
    """Return a duration sensor value in minutes (handles s / min / h)."""
    if not valid(state):
        return None
    try:
        value = float(state.state)  # type: ignore[union-attr]
    except (TypeError, ValueError):
        return None
    unit = (state.attributes.get("unit_of_measurement") or "min").lower()  # type: ignore[union-attr]
    if unit in ("s", "sec"):
        return value / 60
    if unit in ("h", "hr"):
        return value * 60
    return value
