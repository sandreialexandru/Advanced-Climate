"""Outdoor temperature tracking: averages, cutoff and heating season.

Pure Python, no Home Assistant imports, so it can be unit tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .const import SEASON_ALWAYS, SEASON_AUTO, SEASON_DATES

MAX_SAMPLE_AGE = timedelta(hours=48)
MAX_DAILY_MEANS = 30


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
    cutoff_active: bool = False
    season_active: bool = True

    def add(self, now: datetime, value: float) -> None:
        """Add a sample and drop old ones."""
        if self.samples and (now - self.samples[-1][0]) < timedelta(minutes=1):
            self.samples[-1] = (now, value)
        else:
            self.samples.append((now, value))
        limit = now - MAX_SAMPLE_AGE
        while self.samples and self.samples[0][0] < limit:
            self.samples.pop(0)
        self._update_daily(now)

    def _update_daily(self, now: datetime) -> None:
        day = now.date()
        values = [v for t, v in self.samples if t.date() == day]
        if values:
            self.daily_means[day.isoformat()] = round(sum(values) / len(values), 2)
        if len(self.daily_means) > MAX_DAILY_MEANS:
            for key in sorted(self.daily_means)[: len(self.daily_means) - MAX_DAILY_MEANS]:
                del self.daily_means[key]

    def latest(self) -> float | None:
        """Return the latest value."""
        return self.samples[-1][1] if self.samples else None

    def average(self, now: datetime, hours: float) -> float | None:
        """Time-weighted average over the last ``hours`` hours."""
        if not self.samples:
            return None
        start = now - timedelta(hours=hours)
        points = [(t, v) for t, v in self.samples if t >= start]
        # Include the value valid at the start of the window.
        before = [(t, v) for t, v in self.samples if t < start]
        if before:
            points.insert(0, (start, before[-1][1]))
        if not points:
            return None
        if len(points) == 1:
            return points[0][1]
        total = 0.0
        weight = 0.0
        for (t1, v1), (t2, _v2) in zip(points, points[1:], strict=False):
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
            # Only complete days count.
            complete = [
                v
                for k, v in sorted(self.daily_means.items())
                if k < today.isoformat()
            ][-days:]
            if len(complete) >= days:
                if all(v < threshold for v in complete):
                    self.season_active = True
                elif all(v >= threshold for v in complete):
                    self.season_active = False
        return self.season_active

    def as_dict(self) -> dict:
        """Serialize."""
        return {
            "samples": [(t.isoformat(), v) for t, v in self.samples[-600:]],
            "daily_means": self.daily_means,
            "cutoff_active": self.cutoff_active,
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
        obj.cutoff_active = bool(data.get("cutoff_active", False))
        obj.season_active = bool(data.get("season_active", True))
        return obj
