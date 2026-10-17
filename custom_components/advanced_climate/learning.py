"""Heating rate learning for optimal start (pure Python).

The learner observes heating episodes (the room asks for heat and the
temperature rises from clearly below the target) and keeps the last episodes.
An episode starts when the room is at least the thermostat tolerance below
the target, so the cycles of a thermostat that keeps the temperature are
learned too. The heating rate in °C per hour is then estimated as a straight
line of the outdoor temperature, so every episode helps at every outdoor
temperature and temperatures not seen yet are estimated from the trend. The
learning is free: the measured rates and the line are used as they are.

Episodes during which a window or door sensor of the room was open are not
used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from datetime import datetime

# The heat demand must last this long for an episode to be learned.
MIN_DEMAND_MINUTES = 10  # also for cooling: without heat demand
DEFAULT_RATE = 1.0  # °C per hour, until the first episode
DATA_VERSION = 3  # learning data of older versions is discarded
# Version 2 cut the rates to 0.2 … 10 °C/h; episodes at those values are dropped.
_V2_CLAMPED = (0.2, 10.0)
MAX_EPISODES = 30
# A line needs a few episodes over a real spread of outdoor temperatures.
MIN_FIT_EPISODES = 3
MIN_FIT_SPREAD = 3.0  # °C


def start_gap(tolerance: float) -> float:
    """Degrees below the target (at least) needed to start an episode."""
    return round(max(0.0, tolerance), 2)


@dataclass(slots=True)
class HeatingRateLearner:
    """Learn how fast a room heats up, as a function of the outdoor temperature."""

    # [outdoor °C or None, rate °C/h, end time ISO]
    episodes: list[list] = field(default_factory=list)
    episode_start: datetime | None = None
    episode_temp: float | None = None
    # Sum and count of the outdoor temperatures seen during the episode.
    episode_outdoor_sum: float = 0.0
    episode_outdoor_count: int = 0
    episode_disturbed: bool = False

    # ------------------------------------------------------------------ model
    def _points(self) -> list[tuple[float, float]]:
        return [(float(o), float(r)) for o, r, *_ in self.episodes if o is not None]

    def fit(self) -> tuple[float, float] | None:
        """Return (intercept, slope) of rate = intercept + slope * outdoor, if possible."""
        points = self._points()
        if len(points) < MIN_FIT_EPISODES:
            return None
        xs = [p[0] for p in points]
        if max(xs) - min(xs) < MIN_FIT_SPREAD:
            return None
        mean_x = sum(xs) / len(xs)
        mean_y = sum(p[1] for p in points) / len(points)
        var = sum((x - mean_x) ** 2 for x in xs)
        cov = sum((x - mean_x) * (y - mean_y) for x, y in points)
        slope = cov / var if var else 0.0
        return mean_y - slope * mean_x, slope

    def rate(self, outdoor: float | None) -> float:
        """Return the learned rate for the outdoor temperature."""
        if not self.episodes:
            return DEFAULT_RATE
        mean = sum(float(r) for _, r, *_ in self.episodes) / len(self.episodes)
        line = self.fit()
        if line is None or outdoor is None:
            return round(mean, 3)
        intercept, slope = line
        estimate = intercept + slope * outdoor
        # A line can reach zero far from what was seen; a room that heats has a
        # positive rate, so the average of the episodes is used there.
        return round(estimate if estimate > 0 else mean, 3)

    @property
    def rates(self) -> dict[str, float]:
        """Estimated rates at a few outdoor temperatures (attributes, diagnostics)."""
        if not self.episodes:
            return {}
        return {f"{t}°C": self.rate(float(t)) for t in (-10, 0, 10, 20)}

    # -------------------------------------------------------------- learning
    def observe(
        self,
        now: datetime,
        heating: bool,
        current: float | None,
        target: float | None,
        outdoor: float | None,
        window_open: bool = False,
        tolerance: float = 0.0,
    ) -> float | None:
        """Feed an observation. Returns the measured rate when an episode is used.

        ``window_open`` is True while a window or door sensor of the room is open;
        such an episode is not used. ``tolerance`` is how far below the target the
        thermostat lets the room fall before heating (its normal cycle).
        """
        if current is None:
            return None
        if heating and self.episode_start is None:
            if (
                target is not None
                and target - current >= start_gap(tolerance) - 1e-9
                and not window_open
            ):
                self.episode_start = now
                self.episode_temp = current
                self.episode_outdoor_sum = outdoor if outdoor is not None else 0.0
                self.episode_outdoor_count = 1 if outdoor is not None else 0
                self.episode_disturbed = False
            return None
        if self.episode_start is None:
            return None
        if window_open:
            self.episode_disturbed = True
        if outdoor is not None:
            self.episode_outdoor_sum += outdoor
            self.episode_outdoor_count += 1
        reached = target is not None and current >= target
        if heating and not reached:
            return None
        # Episode finished (target reached or heating stopped).
        minutes = (now - self.episode_start).total_seconds() / 60
        rise = current - (self.episode_temp if self.episode_temp is not None else current)
        outdoor_mean = self._outdoor_mean()
        disturbed = self.episode_disturbed
        self.cancel()
        # The heat demand lasted at least 10 minutes; any rise counts, a slow one
        # too (it may show a problem, but it is real). Without a rise there is
        # no rate to measure.
        if disturbed or minutes < MIN_DEMAND_MINUTES or rise <= 0:
            return None
        measured = round(rise / (minutes / 60), 3)
        mean_outdoor = round(outdoor_mean, 1) if outdoor_mean is not None else None
        self.episodes.append([mean_outdoor, measured, now.isoformat()])
        del self.episodes[:-MAX_EPISODES]
        return measured

    def _outdoor_mean(self) -> float | None:
        if not self.episode_outdoor_count:
            return None
        return self.episode_outdoor_sum / self.episode_outdoor_count

    def cancel(self) -> None:
        """Drop the episode in progress (e.g. outside the heating season)."""
        self.episode_start = None
        self.episode_temp = None
        self.episode_outdoor_sum = 0.0
        self.episode_outdoor_count = 0
        self.episode_disturbed = False

    # ----------------------------------------------------------- persistence
    def as_dict(self) -> dict:
        """Serialize."""
        return {"version": DATA_VERSION, "episodes": self.episodes}

    @classmethod
    def from_dict(cls, data: dict | None) -> HeatingRateLearner:
        """Restore. Data of older versions is discarded: it also learned the small
        maintenance cycles of the thermostats."""
        obj = cls()
        version = (data or {}).get("version")
        if version not in (2, DATA_VERSION):
            return obj
        episodes = data.get("episodes")
        if isinstance(episodes, list):
            for item in episodes:
                try:
                    outdoor = None if item[0] is None else float(item[0])
                    if version == 2 and float(item[1]) in _V2_CLAMPED:
                        continue
                    obj.episodes.append([outdoor, float(item[1]), str(item[2]) if len(item) > 2 else ""])
                except (TypeError, ValueError, IndexError):
                    continue
        del obj.episodes[:-MAX_EPISODES]
        return obj


# ---------------------------------------------------------------------------
# Cooling
# ---------------------------------------------------------------------------
def cooling_coefficient(
    start: float, end: float, outdoor: float, hours: float
) -> float | None:
    """How fast a room cools per degree warmer than outdoors (per hour).

    A room loses heat in proportion to the difference between inside and
    outside: T(t) = outdoor + (start - outdoor) * exp(-k * t). Returns k, or
    None when it cannot be measured (no drop, or not warmer than outdoors).
    """
    if hours <= 0 or end >= start or end <= outdoor:
        return None
    return math.log((start - outdoor) / (end - outdoor)) / hours


@dataclass(slots=True)
class CoolingLearner:
    """Learn how fast a room cools without heating.

    It is the opposite of the heating learning: an episode starts when the heat
    demand stops (no window or door sensor open) and ends when the heat demand
    starts again. It is used when it lasted at least 10 minutes and the
    temperature fell, however little. The cooling depends on the difference
    between inside and outside, so one coefficient per room is learned (the
    walls, radiators and insulation of each house are in it, not modelled).
    """

    # [outdoor °C, coefficient 1/h, end time ISO]
    episodes: list[list] = field(default_factory=list)
    episode_start: datetime | None = None
    episode_temp: float | None = None
    # Sum and count of the outdoor temperatures seen during the episode.
    episode_outdoor_sum: float = 0.0
    episode_outdoor_count: int = 0
    episode_disturbed: bool = False

    @property
    def coefficient(self) -> float | None:
        """Mean learned coefficient (1/h), None before the first episode."""
        if not self.episodes:
            return None
        return round(sum(float(k) for _, k, *_ in self.episodes) / len(self.episodes), 5)

    def rate(self, indoor: float | None, outdoor: float | None) -> float | None:
        """Degrees per hour the room falls now (positive), if known."""
        k = self.coefficient
        if k is None or indoor is None or outdoor is None:
            return None
        return round(k * (indoor - outdoor), 3)

    def minutes_to_fall(self, indoor: float, floor: float, outdoor: float | None) -> float | None:
        """Minutes until the room falls from ``indoor`` to ``floor`` without heating."""
        k = self.coefficient
        if k is None or outdoor is None or k <= 0:
            return None
        if indoor <= floor:
            return 0.0
        if floor <= outdoor:
            return None  # it never gets that cold
        return math.log((indoor - outdoor) / (floor - outdoor)) / k * 60

    def temperature_after(self, indoor: float, outdoor: float | None, minutes: float) -> float | None:
        """Room temperature after ``minutes`` without heating."""
        k = self.coefficient
        if k is None or outdoor is None:
            return None
        return outdoor + (indoor - outdoor) * math.exp(-k * minutes / 60)

    def observe(
        self,
        now: datetime,
        heating: bool,
        current: float | None,
        outdoor: float | None,
        window_open: bool = False,
    ) -> float | None:
        """Feed an observation. Returns the coefficient when an episode is used."""
        if current is None:
            return None
        if not heating and self.episode_start is None:
            if not window_open:
                self.episode_start = now
                self.episode_temp = current
                self.episode_outdoor_sum = outdoor if outdoor is not None else 0.0
                self.episode_outdoor_count = 1 if outdoor is not None else 0
                self.episode_disturbed = False
            return None
        if self.episode_start is None:
            return None
        if window_open:
            self.episode_disturbed = True
        if outdoor is not None:
            self.episode_outdoor_sum += outdoor
            self.episode_outdoor_count += 1
        if not heating:
            return None
        # The heat demand started again: the episode is finished.
        minutes = (now - self.episode_start).total_seconds() / 60
        start = self.episode_temp
        mean_outdoor = self._outdoor_mean()
        disturbed = self.episode_disturbed
        self.cancel()
        if disturbed or minutes < MIN_DEMAND_MINUTES or start is None or mean_outdoor is None:
            return None
        k = cooling_coefficient(start, current, mean_outdoor, minutes / 60)
        if k is None:
            return None
        k = round(k, 5)
        self.episodes.append([round(mean_outdoor, 1), k, now.isoformat()])
        del self.episodes[:-MAX_EPISODES]
        return k

    def _outdoor_mean(self) -> float | None:
        if not self.episode_outdoor_count:
            return None
        return self.episode_outdoor_sum / self.episode_outdoor_count

    def cancel(self) -> None:
        """Drop the episode in progress (e.g. outside the heating season)."""
        self.episode_start = None
        self.episode_temp = None
        self.episode_outdoor_sum = 0.0
        self.episode_outdoor_count = 0
        self.episode_disturbed = False

    def as_dict(self) -> dict:
        """Serialize."""
        return {"version": 1, "episodes": self.episodes}

    @classmethod
    def from_dict(cls, data: dict | None) -> CoolingLearner:
        """Restore."""
        obj = cls()
        if not data or data.get("version") != 1:
            return obj
        for item in data.get("episodes") or []:
            try:
                obj.episodes.append([float(item[0]), float(item[1]), str(item[2])])
            except (TypeError, ValueError, IndexError):
                continue
        del obj.episodes[:-MAX_EPISODES]
        return obj
