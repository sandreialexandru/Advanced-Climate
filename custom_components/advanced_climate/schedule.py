"""Schedule parsing and evaluation (pure Python, no Home Assistant imports).

A schedule is a set of named profiles. Each profile is a list of time slots;
a slot starts at a clock time and lasts until the next slot. The text format
used in the configuration is one profile per line::

    workday: 00:00 sleep, 06:00 home, 22:00 sleep
    weekend: 00:00 sleep, 08:00 home, 23:00 sleep
    fri: 00:00 sleep, 06:00 home, 23:30 sleep
    home_office: 00:00 sleep, 07:00 home, 23:00 sleep

Profile selection for a day, highest priority first:
1. a profile forced for that day (manual selection or a calendar event),
2. a weekday profile (``mon`` ... ``sun``),
3. ``workday`` or ``weekend`` depending on whether the day is a workday,
4. any other profile (the first one defined).

The day boundary (default 00:00) moves the start of the schedule day, so a
night shift can keep one profile from e.g. 04:00 to 04:00 the next day.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import re

from .const import WEEKDAYS

PROFILE_WORKDAY = "workday"
PROFILE_WEEKEND = "weekend"

_PROFILE_RE = re.compile(r"^[a-z0-9_][a-z0-9_ -]*$")
_SLOT_RE = re.compile(r"^(\d{1,2}):(\d{2})\s+([A-Za-z0-9_ -]+)$")

MINUTES_PER_DAY = 24 * 60


class ScheduleError(ValueError):
    """Raised when a schedule text cannot be parsed."""


@dataclass(frozen=True, slots=True)
class Slot:
    """A schedule slot: from ``minute`` (since midnight) the ``preset`` applies."""

    minute: int
    preset: str

    @property
    def time_str(self) -> str:
        """Return the slot start as HH:MM."""
        return f"{self.minute // 60:02d}:{self.minute % 60:02d}"


@dataclass(frozen=True, slots=True)
class ScheduleState:
    """Result of a schedule lookup."""

    preset: str
    profile: str
    slot_start: datetime
    next_change: datetime | None
    next_preset: str | None


def parse_time(value: str) -> int:
    """Parse ``HH:MM`` or ``HH:MM:SS`` into minutes since midnight."""
    parts = str(value).strip().split(":")
    if len(parts) < 2:
        raise ScheduleError(f"Invalid time '{value}'")
    try:
        hours, minutes = int(parts[0]), int(parts[1])
    except ValueError as err:
        raise ScheduleError(f"Invalid time '{value}'") from err
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        raise ScheduleError(f"Invalid time '{value}'")
    return hours * 60 + minutes


def parse_schedule(text: str, valid_presets: Iterable[str]) -> dict[str, list[Slot]]:
    """Parse the schedule text into profiles.

    Preset names are matched case-insensitively against ``valid_presets`` and
    stored with the spelling used in ``valid_presets``.
    """
    lookup = {p.lower(): p for p in valid_presets}
    profiles: dict[str, list[Slot]] = {}
    for line_no, raw_line in enumerate((text or "").splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            raise ScheduleError(f"Line {line_no}: expected 'profile: HH:MM preset, ...'")
        name, _, body = line.partition(":")
        name = name.strip().lower()
        if not _PROFILE_RE.match(name):
            raise ScheduleError(f"Line {line_no}: invalid profile name '{name}'")
        if name in profiles:
            raise ScheduleError(f"Line {line_no}: profile '{name}' is defined twice")
        slots: dict[int, Slot] = {}
        for chunk in body.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            match = _SLOT_RE.match(chunk)
            if not match:
                raise ScheduleError(
                    f"Line {line_no}: invalid slot '{chunk}' (expected 'HH:MM preset')"
                )
            minute = parse_time(f"{match.group(1)}:{match.group(2)}")
            preset_raw = match.group(3).strip().lower()
            if preset_raw not in lookup:
                raise ScheduleError(
                    f"Line {line_no}: unknown preset '{match.group(3).strip()}'"
                    f" (valid: {', '.join(lookup.values())})"
                )
            if minute in slots:
                raise ScheduleError(
                    f"Line {line_no}: two slots start at {chunk.split()[0]}"
                )
            slots[minute] = Slot(minute, lookup[preset_raw])
        if not slots:
            raise ScheduleError(f"Line {line_no}: profile '{name}' has no slots")
        profiles[name] = sorted(slots.values(), key=lambda s: s.minute)
    if not profiles:
        raise ScheduleError("The schedule has no profiles")
    return profiles


def format_schedule(profiles: dict[str, list[Slot]]) -> str:
    """Format profiles back into the text representation."""
    return "\n".join(
        f"{name}: " + ", ".join(f"{s.time_str} {s.preset}" for s in slots)
        for name, slots in profiles.items()
    )


def profiles_to_dict(profiles: dict[str, list[Slot]]) -> dict[str, list[dict[str, str]]]:
    """Return a JSON friendly representation (used by the card)."""
    return {
        name: [{"time": s.time_str, "preset": s.preset} for s in slots]
        for name, slots in profiles.items()
    }


def profiles_from_dict(
    data: dict[str, list[dict[str, str]]], valid_presets: Iterable[str]
) -> dict[str, list[Slot]]:
    """Build profiles from the JSON representation and validate them."""
    text = "\n".join(
        f"{name}: " + ", ".join(f"{slot['time']} {slot['preset']}" for slot in slots)
        for name, slots in data.items()
    )
    return parse_schedule(text, valid_presets)


DayInfo = Callable[[date], tuple[bool, str | None]]
"""Return (is_workday, forced_profile) for a date."""


class Schedule:
    """Evaluate a parsed schedule."""

    def __init__(self, profiles: dict[str, list[Slot]], day_boundary: int = 0) -> None:
        """Initialize the schedule. ``day_boundary`` is in minutes after midnight."""
        if not profiles:
            raise ScheduleError("The schedule has no profiles")
        self.profiles = profiles
        self.boundary = day_boundary % MINUTES_PER_DAY

    @property
    def profile_names(self) -> list[str]:
        """Return the profile names in definition order."""
        return list(self.profiles)

    def profile_for(self, day: date, is_workday: bool, forced: str | None) -> str:
        """Return the profile used for the given schedule day."""
        if forced and forced.lower() in self.profiles:
            return forced.lower()
        weekday = WEEKDAYS[day.weekday()]
        if weekday in self.profiles:
            return weekday
        preferred = PROFILE_WORKDAY if is_workday else PROFILE_WEEKEND
        if preferred in self.profiles:
            return preferred
        other = PROFILE_WEEKEND if is_workday else PROFILE_WORKDAY
        if other in self.profiles:
            return other
        return next(iter(self.profiles))

    def _key(self, minute: int) -> int:
        """Position of a clock minute inside the schedule day."""
        return (minute - self.boundary) % MINUTES_PER_DAY

    def _ordered(self, profile: str) -> list[Slot]:
        """Slots of a profile in the order of the schedule day."""
        return sorted(self.profiles[profile], key=lambda s: self._key(s.minute))

    def schedule_day(self, moment: datetime) -> date:
        """Return the schedule day a moment belongs to."""
        return (moment - timedelta(minutes=self.boundary)).date()

    def day_start(self, day: date, tzinfo) -> datetime:
        """Return the moment a schedule day starts."""
        start = datetime.combine(day, time(0, 0), tzinfo)
        return start + timedelta(minutes=self.boundary)

    def _slot_moment(self, day: date, slot: Slot, tzinfo) -> datetime:
        """Moment a slot starts on a schedule day."""
        return self.day_start(day, tzinfo) + timedelta(minutes=self._key(slot.minute))

    def lookup(self, moment: datetime, day_info: DayInfo) -> ScheduleState:
        """Return the active preset and the next change for ``moment``."""
        tz = moment.tzinfo
        day = self.schedule_day(moment)
        is_workday, forced = day_info(day)
        profile = self.profile_for(day, is_workday, forced)
        slots = self._ordered(profile)
        position = self._key(moment.hour * 60 + moment.minute)

        current: Slot | None = None
        current_day = day
        for slot in slots:
            if self._key(slot.minute) <= position:
                current = slot
        if current is None:
            # Before the first slot: the last slot of the previous day continues.
            prev_day = day - timedelta(days=1)
            prev_workday, prev_forced = day_info(prev_day)
            prev_profile = self.profile_for(prev_day, prev_workday, prev_forced)
            current = self._ordered(prev_profile)[-1]
            current_day = prev_day
        slot_start = self._slot_moment(current_day, current, tz)

        next_change, next_preset = self._next_change(
            moment, day, slots, position, current.preset, day_info
        )
        return ScheduleState(
            preset=current.preset,
            profile=profile,
            slot_start=slot_start,
            next_change=next_change,
            next_preset=next_preset,
        )

    def _next_change(
        self,
        moment: datetime,
        day: date,
        slots: list[Slot],
        position: int,
        preset: str,
        day_info: DayInfo,
    ) -> tuple[datetime | None, str | None]:
        """Find the next moment the preset actually changes (up to 8 days)."""
        tz = moment.tzinfo
        candidates: list[tuple[date, Slot]] = [
            (day, s) for s in slots if self._key(s.minute) > position
        ]
        for offset in range(1, 9):
            next_day = day + timedelta(days=offset)
            workday, forced = day_info(next_day)
            profile = self.profile_for(next_day, workday, forced)
            candidates.extend((next_day, s) for s in self._ordered(profile))
            for cand_day, slot in candidates:
                if slot.preset != preset:
                    return self._slot_moment(cand_day, slot, tz), slot.preset
            candidates = []
        return None, None

    def upcoming(
        self, moment: datetime, day_info: DayInfo, horizon: timedelta
    ) -> list[tuple[datetime, str]]:
        """Return preset changes between ``moment`` and ``moment + horizon``."""
        result: list[tuple[datetime, str]] = []
        cursor = moment
        end = moment + horizon
        state = self.lookup(cursor, day_info)
        while state.next_change is not None and state.next_change <= end:
            result.append((state.next_change, state.next_preset or state.preset))
            cursor = state.next_change
            state = self.lookup(cursor, day_info)
        return result
