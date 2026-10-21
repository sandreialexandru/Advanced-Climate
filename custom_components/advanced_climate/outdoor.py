"""Outdoor temperature tracking: averages, cutoff and heating season.

Pure Python, no Home Assistant imports, so it can be unit tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, tzinfo
from itertools import pairwise

from .const import SEASON_ALWAYS, SEASON_AUTO, SEASON_DATES

MAX_SAMPLE_AGE = timedelta(hours=48)
MAX_DAILY_MEANS = 30


def expected_outdoor(
    now: datetime,
    start: datetime,
    end: datetime,
    current: float | None,
    hourly: list[tuple[datetime, float]],
) -> tuple[float | None, str]:
    """Mean outdoor temperature expected between ``start`` and ``end``, and its source.

    Each hourly forecast value holds for its hour; the measured temperature
    (``current``) stands for the time until the next forecast hour. Without a
    forecast covering the period, ``current`` is returned with the source "now".
    """
    start = max(start, now)
    if end <= start:
        return current, "now"
    # The forecast hour that holds at ``now`` and the ones ahead.
    points = sorted((t, v) for t, v in hourly if t + timedelta(hours=1) > now)
    if not points or end > points[-1][0] + timedelta(hours=1):
        return current, "now"
    first = current if current is not None else points[0][1]
    series = [(now, first), *[(t, v) for t, v in points if t > now]]
    total = 0.0
    forecast_used = False
    for index, (moment, value) in enumerate(series):
        until = series[index + 1][0] if index + 1 < len(series) else end
        begin, finish = max(moment, start), min(until, end)
        if finish > begin:
            total += value * (finish - begin).total_seconds()
            forecast_used = forecast_used or index > 0 or current is None
    mean = round(total / (end - start).total_seconds(), 2)
    # The whole period before the next forecast hour: the measured value.
    return mean, "forecast" if forecast_used else "now"


def parse_month_day(value: str) -> tuple[int, int]:
    """Parse ``MM-DD``."""
    month, day = str(value).strip().split("-")
    month_i, day_i = int(month), int(day)
    if not (1 <= month_i <= 12 and 1 <= day_i <= 31):
        raise ValueError(f"Invalid date '{value}'")
    return month_i, day_i


def in_date_season(today: date, start: str, end: str) -> bool:
    """Return True if ``today`` is inside the [start, end] month-day range.

    The range may wrap the new year (e.g. 10-15 to 04-15).
    """
    s = parse_month_day(start)
    e = parse_month_day(end)
    t = (today.month, today.day)
    if s <= e:
        return s <= t <= e
    return t >= s or t <= e


@dataclass(slots=True)
class OutdoorTracker:
    """Keep outdoor temperature samples and derived state."""

    samples: list[tuple[datetime, float]] = field(default_factory=list)
    daily_means: dict[str, float] = field(default_factory=dict)
    # Per calendar day: [sum of value × seconds, seconds covered]. Built as the
    # values come and saved, so a restart does not change the mean of a day.
    daily_sums: dict[str, list[float]] = field(default_factory=dict)
    # Days with a mean saved before daily_sums existed: kept as they are.
    legacy_days: set[str] = field(default_factory=set)
    cutoff_active: bool = False
    # Heating off earlier by the forecast mean (with the same hysteresis).
    forecast_cutoff_active: bool = False
    season_active: bool = True
    # How long a value stays valid without a new one (the averaging window of
    # the cutoff); None = always.
    max_age: timedelta | None = None
    # Time zone of the calendar days of the daily means (None = as given).
    tz: tzinfo | None = None

    def add(self, now: datetime, value: float) -> None:
        """Add a sample and drop old ones."""
        if self.samples:
            # The previous value held until now (at most max_age).
            self._accumulate(*self.samples[-1], now)
        if self.samples and (now - self.samples[-1][0]) < timedelta(minutes=1):
            self.samples[-1] = (now, value)
        else:
            self.samples.append((now, value))
        limit = now - MAX_SAMPLE_AGE
        while self.samples and self.samples[0][0] < limit:
            self.samples.pop(0)
        self._update_daily(now)

    def _day(self, moment: datetime) -> date:
        """Calendar day of a moment in the time zone of the house."""
        return (moment.astimezone(self.tz) if self.tz else moment).date()

    def _accumulate(self, start: datetime, value: float, end: datetime) -> None:
        """Add ``value`` held from ``start`` to ``end`` to the days it covers."""
        if self.max_age is not None:
            end = min(end, start + self.max_age)
        zone = self.tz or start.tzinfo
        moment = start
        while moment < end:
            day = self._day(moment)
            midnight = datetime.combine(day + timedelta(days=1), time(0), tzinfo=zone)
            until = min(end, midnight)
            seconds = (until - moment).total_seconds()
            key = day.isoformat()
            if seconds > 0 and key not in self.legacy_days:
                acc = self.daily_sums.setdefault(key, [0.0, 0.0])
                acc[0] += value * seconds
                acc[1] += seconds
            if until <= moment:
                break
            moment = until

    def _update_daily(self, now: datetime) -> None:
        """Update the daily means (used by the automatic season).

        Each value counts for the time it held (at most ``max_age``; after that
        the outdoor temperature is unknown and the time does not count), so a
        day with Home Assistant stopped part of the time uses only the covered
        time. The first value of a day is its mean until time has passed.
        """
        today = self._day(now).isoformat()
        for key, (total, seconds) in self.daily_sums.items():
            if seconds > 0:
                self.daily_means[key] = round(total / seconds, 2)
        if today not in self.daily_sums and today not in self.legacy_days and self.samples:
            self.daily_means[today] = self.samples[-1][1]
        for store in (self.daily_means, self.daily_sums):
            for key in sorted(store)[: max(len(store) - MAX_DAILY_MEANS, 0)]:
                del store[key]
        self.legacy_days &= set(self.daily_means)

    def latest(self, now: datetime | None = None) -> float | None:
        """Return the latest value, None when it is older than ``max_age``."""
        if not self.samples:
            return None
        moment, value = self.samples[-1]
        if now is not None and self.max_age is not None and now - moment > self.max_age:
            return None
        return value

    def average(self, now: datetime, hours: float) -> float | None:
        """Time-weighted average over the last ``hours`` hours."""
        if not self.samples:
            return None
        start = now - timedelta(hours=hours)
        points = [(t, v) for t, v in self.samples if t >= start]
        if not points:
            return None  # no value in the window: the outdoor temperature is unknown
        # Include the value valid at the start of the window.
        before = [(t, v) for t, v in self.samples if t < start]
        if before:
            points.insert(0, (start, before[-1][1]))
        if len(points) == 1:
            return points[0][1]
        total = 0.0
        weight = 0.0
        for (t1, v1), (t2, _v2) in pairwise(points):
            seconds = (t2 - t1).total_seconds()
            total += v1 * seconds
            weight += seconds
        last_t, last_v = points[-1]
        seconds = max((now - last_t).total_seconds(), 0.0)
        total += last_v * seconds
        weight += seconds
        if weight <= 0:
            return points[-1][1]
        return round(total / weight, 2)

    def update_cutoff(
        self, average: float | None, threshold: float, hysteresis: float
    ) -> bool:
        """Update the cutoff state with hysteresis and return it."""
        if average is None:
            return self.cutoff_active
        if self.cutoff_active:
            if average <= threshold - hysteresis:
                self.cutoff_active = False
        elif average >= threshold:
            self.cutoff_active = True
        return self.cutoff_active

    def update_forecast_cutoff(
        self, mean: float | None, threshold: float, hysteresis: float
    ) -> bool:
        """Update the forecast cutoff: on at the threshold, off at threshold − hysteresis.

        Without a forecast mean it is off.
        """
        if mean is None:
            self.forecast_cutoff_active = False
        elif self.forecast_cutoff_active:
            if mean <= threshold - hysteresis:
                self.forecast_cutoff_active = False
        elif mean >= threshold:
            self.forecast_cutoff_active = True
        return self.forecast_cutoff_active

    def update_season(
        self,
        today: date,
        mode: str,
        start: str,
        end: str,
        days: int,
        threshold: float,
    ) -> bool:
        """Update and return whether the heating season is active."""
        if mode == SEASON_ALWAYS:
            self.season_active = True
        elif mode == SEASON_DATES:
            try:
                self.season_active = in_date_season(today, start, end)
            except ValueError:
                self.season_active = True
        elif mode == SEASON_AUTO:
            # Only complete days count, the ``days`` days before today in a row:
            # a missing day (no value all day) breaks the run.
            wanted = [(today - timedelta(days=n)).isoformat() for n in range(days, 0, -1)]
            complete = [self.daily_means[k] for k in wanted if k in self.daily_means]
            if days > 0 and len(complete) == days:
                if all(v < threshold for v in complete):
                    self.season_active = True
                elif all(v >= threshold for v in complete):
                    self.season_active = False
        return self.season_active

    def _samples_to_save(self) -> list[tuple[datetime, float]]:
        """The samples of the averaging window (all of them without one)."""
        if self.max_age is None or not self.samples:
            return list(self.samples)
        limit = self.samples[-1][0] - self.max_age
        keep = [i for i, (t, _v) in enumerate(self.samples) if t >= limit]
        first = max((keep[0] if keep else len(self.samples)) - 1, 0)
        return self.samples[first:]

    def as_dict(self) -> dict:
        """Serialize."""
        return {
            # Every value the averaging window may still use (and the one valid
            # at its start), so a long average survives a restart.
            "samples": [(t.isoformat(), v) for t, v in self._samples_to_save()],
            "daily_means": self.daily_means,
            "daily_sums": self.daily_sums,
            "cutoff_active": self.cutoff_active,
            "forecast_cutoff_active": self.forecast_cutoff_active,
            "season_active": self.season_active,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> OutdoorTracker:
        """Restore."""
        obj = cls()
        if not data:
            return obj
        for item in data.get("samples", []):
            try:
                obj.samples.append((datetime.fromisoformat(item[0]), float(item[1])))
            except (ValueError, TypeError, IndexError):
                continue
        obj.daily_means = {
            str(k): float(v) for k, v in (data.get("daily_means") or {}).items()
        }
        sums = data.get("daily_sums")
        if isinstance(sums, dict):
            for key, pair in sums.items():
                try:
                    obj.daily_sums[str(key)] = [float(pair[0]), float(pair[1])]
                except (TypeError, ValueError, IndexError):
                    continue
        else:
            # Saved before 2.3.9: the means stay, new time is not added to them.
            obj.legacy_days = set(obj.daily_means)
        obj.cutoff_active = bool(data.get("cutoff_active", False))
        obj.forecast_cutoff_active = bool(data.get("forecast_cutoff_active", False))
        obj.season_active = bool(data.get("season_active", True))
        return obj
