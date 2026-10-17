"""Decision engine (pure Python, no Home Assistant imports).

For every room the rules are evaluated from the top down; the first rule that
applies sets the target. Final adjustments (weather, tariff, solar gain) can
move a heating target by a few tenths of a degree and the result always goes
through the safety limits.

Rule order:
 1. safety (frost protection / maximum temperature) - always applied last
 2. global mode Off / Pause / Summer / out of season
 3. valve exercise
 4. window open
 5. manual override
 6. vacation
 7. presence (far -> away, nearby -> eco or a fixed temperature)
 8. schedule (with optimal start / stop and room occupancy)
 Adjustments: outdoor cutoff, compensation, tariff, PV, solar gain.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .const import (
    MODE_OFF,
    MODE_SUMMER,
    MODE_VACATION,
    NEARBY_TEMPERATURE,
    PRESENCE_FAR,
    PRESENCE_NEARBY,
    PRESET_AWAY,
    PRESET_ECO,
    RULE_CUTOFF,
    RULE_FAR,
    RULE_MODE_OFF,
    RULE_NEARBY,
    RULE_OPTIMAL_START,
    RULE_OPTIMAL_STOP,
    RULE_OUT_OF_SEASON,
    RULE_OVERRIDE,
    RULE_PAUSE,
    RULE_SAFETY,
    RULE_SCHEDULE,
    RULE_SENSOR_FALLBACK,
    RULE_SUMMER,
    RULE_UNOCCUPIED,
    RULE_VACATION,
    RULE_VALVE_EXERCISE,
    RULE_WINDOW,
    WINDOW_ACTION_OFF,
)

KIND_PRESET = "preset"
KIND_TEMPERATURE = "temperature"
KIND_OFF = "off"
KIND_NONE = "none"  # do not send any command

MAX_TOTAL_OFFSET = 3.0


def fmt_temp(value: float, unit: str = "°C") -> str:
    """A temperature (kept in °C) as text in the unit of the house."""
    if str(unit).strip().lower().endswith("f"):
        return f"{value * 1.8 + 32:.1f} °F"
    return f"{value:.1f} °C"


def fmt_delta(value: float, unit: str = "°C") -> str:
    """A temperature difference (kept in °C) as text in the unit of the house."""
    if str(unit).strip().lower().endswith("f"):
        value *= 1.8
    return f"{value:+.1f}"


@dataclass(slots=True)
class Target:
    """What the room should be set to."""

    kind: str
    preset: str | None = None
    temperature: float | None = None

    def as_dict(self) -> dict:
        """Serialize."""
        return {"kind": self.kind, "preset": self.preset, "temperature": self.temperature}

    def describe(self, unit: str = "°C") -> str:
        """Short text form."""
        if self.kind == KIND_PRESET:
            return f"preset {self.preset}"
        if self.kind == KIND_TEMPERATURE:
            label = f" ({self.preset})" if self.preset else ""
            return f"{fmt_temp(self.temperature or 0.0, unit)}{label}"
        if self.kind == KIND_OFF:
            return "off"
        return "no command"


@dataclass(slots=True)
class RoomInputs:
    """Everything the engine needs to decide for one room."""

    now: datetime
    mode: str
    paused: bool
    season_active: bool
    cutoff_active: bool
    valve_exercise: bool
    window_open: bool
    window_action: str
    override_active: bool
    vacation_active: bool
    presence: str
    arriving: bool
    room_unoccupied: bool
    sensor_failed: bool
    schedule_preset: str | None
    schedule_rule: str
    current_temp: float | None
    frost_temp: float
    max_temp: float
    nearby_mode: str
    nearby_temp: float | None
    level_temp: Callable[[str], float | None]
    offsets: list[tuple[str, float]] = field(default_factory=list)
    supports_off: bool = True
    exercise_temp: float | None = None
    unit: str = "°C"  # only for the texts; every value is in °C
    # The last hours of a vacation: the schedule applies, so the house is warm on return.
    vacation_preheat: bool = False
    # Frost protection is heating: it continues until the device stops asking for heat.
    frost_holding: bool = False


@dataclass(slots=True)
class Decision:
    """The result of the engine."""

    rule: str
    target: Target
    description: str
    offsets: list[tuple[str, float]] = field(default_factory=list)

    def as_dict(self) -> dict:
        """Serialize."""
        return {
            "rule": self.rule,
            "target": self.target.as_dict(),
            "description": self.description,
            "offsets": [list(o) for o in self.offsets],
        }


def _heating(target: Target) -> bool:
    return target.kind in (KIND_PRESET, KIND_TEMPERATURE)


def _off(inputs: RoomInputs) -> Target:
    """Heating off, or frost temperature when the device cannot be turned off."""
    if inputs.supports_off:
        return Target(KIND_OFF)
    return Target(KIND_TEMPERATURE, temperature=inputs.frost_temp)


def base_decision(inputs: RoomInputs) -> Decision:
    """Evaluate rules 2-8 (without adjustments and safety)."""
    if inputs.paused:
        return Decision(RULE_PAUSE, Target(KIND_NONE), "Paused: no commands are sent")
    if inputs.mode == MODE_OFF:
        return Decision(
            RULE_MODE_OFF,
            Target(KIND_TEMPERATURE, temperature=inputs.frost_temp),
            "Mode off: frost protection only",
        )
    if inputs.mode == MODE_SUMMER:
        return Decision(RULE_SUMMER, _off(inputs), "Summer mode: heating off")
    if not inputs.season_active:
        return Decision(
            RULE_OUT_OF_SEASON, _off(inputs), "Outside the heating season: heating off"
        )
    if inputs.valve_exercise:
        return Decision(
            RULE_VALVE_EXERCISE,
            Target(
                KIND_TEMPERATURE,
                temperature=inputs.exercise_temp
                if inputs.exercise_temp is not None
                else inputs.max_temp,
            ),
            "Valve exercise: valves fully open for a few minutes",
        )
    if inputs.window_open:
        if inputs.window_action == WINDOW_ACTION_OFF:
            return Decision(RULE_WINDOW, _off(inputs), "Window open: heating off")
        return Decision(
            RULE_WINDOW,
            Target(KIND_TEMPERATURE, temperature=inputs.frost_temp),
            "Window open: frost protection",
        )
    if inputs.override_active:
        return Decision(RULE_OVERRIDE, Target(KIND_NONE), "Manual change is respected")
    if inputs.mode == MODE_VACATION or inputs.vacation_active:
        return Decision(
            RULE_VACATION, Target(KIND_PRESET, preset=PRESET_AWAY), "Vacation"
        )
    if not inputs.arriving and not inputs.vacation_preheat:
        if inputs.presence == PRESENCE_FAR:
            return Decision(
                RULE_FAR,
                Target(KIND_PRESET, preset=PRESET_AWAY),
                "Everyone is far away (outside the nearby zones)",
            )
        if inputs.presence == PRESENCE_NEARBY:
            if inputs.nearby_mode == NEARBY_TEMPERATURE and inputs.nearby_temp is not None:
                return Decision(
                    RULE_NEARBY,
                    Target(KIND_TEMPERATURE, temperature=inputs.nearby_temp),
                    "Nobody home, someone nearby: fixed temperature",
                )
            return Decision(
                RULE_NEARBY,
                Target(KIND_PRESET, preset=PRESET_ECO),
                "Nobody home, someone nearby",
            )
    arriving = (
        " (vacation ends soon: preheating)"
        if inputs.vacation_preheat
        else " (someone is on the way home)"
        if inputs.arriving
        else ""
    )
    if inputs.schedule_preset is None:
        return Decision(RULE_SCHEDULE, Target(KIND_NONE), "No schedule available")
    preset = inputs.schedule_preset
    if inputs.sensor_failed:
        return Decision(
            RULE_SENSOR_FALLBACK,
            Target(KIND_PRESET, preset=PRESET_ECO),
            "Temperature sensors unavailable: eco until they recover",
        )
    if inputs.room_unoccupied and _warmer(inputs, preset, PRESET_ECO):
        return Decision(
            RULE_UNOCCUPIED,
            Target(KIND_PRESET, preset=PRESET_ECO),
            f"Room unoccupied (schedule: {preset})",
        )
    descriptions = {
        RULE_SCHEDULE: f"Schedule: {preset}",
        RULE_OPTIMAL_START: f"Optimal start: heating early for {preset}",
        RULE_OPTIMAL_STOP: f"Optimal stop: lowering early to {preset}",
    }
    return Decision(
        inputs.schedule_rule,
        Target(KIND_PRESET, preset=preset),
        descriptions.get(inputs.schedule_rule, f"Schedule: {preset}") + arriving,
    )


def _warmer(inputs: RoomInputs, preset: str, than: str) -> bool:
    a = inputs.level_temp(preset)
    b = inputs.level_temp(than)
    if a is None or b is None:
        return preset not in (than, PRESET_AWAY)
    return a > b


def decide(inputs: RoomInputs) -> Decision:
    """Run the full decision: rules, adjustments, safety."""
    decision = base_decision(inputs)
    target = decision.target

    adjustable = decision.rule not in (
        RULE_PAUSE,
        RULE_MODE_OFF,
        RULE_VALVE_EXERCISE,
        RULE_WINDOW,
        RULE_OVERRIDE,
    )
    # Outdoor cutoff: heating is not needed when it is warm outside.
    if adjustable and inputs.cutoff_active and _heating(target):
        decision = Decision(
            RULE_CUTOFF,
            _off(inputs),
            f"Warm outside: heating off (would be {target.describe(inputs.unit)})",
        )
        target = decision.target
    elif adjustable and _heating(target) and inputs.offsets:
        total = sum(delta for _label, delta in inputs.offsets)
        total = max(-MAX_TOTAL_OFFSET, min(MAX_TOTAL_OFFSET, total))
        if abs(total) >= 0.05:
            base = (
                target.temperature
                if target.kind == KIND_TEMPERATURE
                else inputs.level_temp(target.preset or "")
            )
            if base is not None:
                target = Target(
                    KIND_TEMPERATURE,
                    preset=target.preset,
                    temperature=round(base + total, 1),
                )
                labels = ", ".join(
                    f"{label} {fmt_delta(delta, inputs.unit)}" for label, delta in inputs.offsets
                )
                decision = Decision(
                    decision.rule,
                    target,
                    f"{decision.description} ({labels})",
                    list(inputs.offsets),
                )

    return apply_safety(decision, inputs)


def apply_safety(decision: Decision, inputs: RoomInputs) -> Decision:
    """Clamp to the safety limits and enforce frost protection."""
    target = decision.target
    frost, maximum = inputs.frost_temp, inputs.max_temp
    if target.kind == KIND_TEMPERATURE and target.temperature is not None:
        clamped = min(max(target.temperature, frost), maximum)
        if decision.rule == RULE_VALVE_EXERCISE:
            clamped = target.temperature
        if clamped != target.temperature:
            target = Target(KIND_TEMPERATURE, preset=target.preset, temperature=clamped)
            decision = Decision(
                decision.rule,
                target,
                f"{decision.description} (limited to {fmt_temp(clamped, inputs.unit)})",
                decision.offsets,
            )
        return decision
    if target.kind == KIND_PRESET:
        level = inputs.level_temp(target.preset or "")
        if level is not None and level < frost:
            return Decision(
                RULE_SAFETY,
                Target(KIND_TEMPERATURE, preset=target.preset, temperature=frost),
                f"Frost protection ({target.preset} is below {fmt_temp(frost, inputs.unit)})",
            )
        return decision
    # Off or no command: protect against frost. Once started it continues while the
    # device still heats, so it does not switch on and off around the limit.
    if inputs.current_temp is not None and (inputs.current_temp < frost or inputs.frost_holding):
        text = (
            f"Frost protection: {fmt_temp(inputs.current_temp, inputs.unit)} is below "
            f"{fmt_temp(frost, inputs.unit)}"
            if inputs.current_temp < frost
            else f"Frost protection: heating up to {fmt_temp(frost, inputs.unit)}"
        )
        return Decision(RULE_SAFETY, Target(KIND_TEMPERATURE, temperature=frost), text)
    return decision


def optimal_schedule(
    now: datetime,
    current_preset: str,
    next_change: datetime | None,
    next_preset: str | None,
    current_temp: float | None,
    level_temp: Callable[[str], float | None],
    rate: float,
    start_enabled: bool,
    start_max_minutes: float,
    stop_enabled: bool,
    stop_minutes: float,
    started: bool = False,
) -> tuple[str, str]:
    """Return (preset, rule) applying optimal start / stop.

    ``started`` is True when the optimal start for this change already began: it
    then continues until the change, even if the room is warm early (no switching
    back and forth). The other rules can still override it.
    """
    if next_change is None or next_preset is None or next_change <= now:
        return current_preset, RULE_SCHEDULE
    now_temp = level_temp(current_preset)
    next_temp = level_temp(next_preset)
    if now_temp is None or next_temp is None:
        return current_preset, RULE_SCHEDULE
    remaining = next_change - now
    if start_enabled and next_temp > now_temp and started:
        return next_preset, RULE_OPTIMAL_START
    if start_enabled and next_temp > now_temp and current_temp is not None:
        if current_temp < next_temp and rate > 0:
            hours = (next_temp - current_temp) / rate
            needed = min(timedelta(hours=hours), timedelta(minutes=start_max_minutes))
            if remaining <= needed:
                return next_preset, RULE_OPTIMAL_START
    if stop_enabled and next_temp < now_temp:
        if remaining <= timedelta(minutes=stop_minutes):
            return next_preset, RULE_OPTIMAL_STOP
    return current_preset, RULE_SCHEDULE
