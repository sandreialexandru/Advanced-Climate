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
from datetime import datetime

# The heat demand must last this long for an episode to be learned.
MIN_DEMAND_MINUTES = 10
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
    episode_outdoor: list[float] = field(default_factory=list)
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
                self.episode_outdoor = [outdoor] if outdoor is not None else []
                self.episode_disturbed = False
            return None
        if self.episode_start is None:
            return None
        if window_open:
            self.episode_disturbed = True
        if outdoor is not None:
            self.episode_outdoor.append(outdoor)
        reached = target is not None and current >= target - 0.1
        if heating and not reached:
            return None
        # Episode finished (target reached or heating stopped).
        minutes = (now - self.episode_start).total_seconds() / 60
        rise = current - (self.episode_temp if self.episode_temp is not None else current)
        outdoor_values = self.episode_outdoor
        disturbed = self.episode_disturbed
        self.episode_start = None
        self.episode_temp = None
        self.episode_outdoor = []
        self.episode_disturbed = False
        # The heat demand lasted at least 10 minutes; any rise counts, a slow one
        # too (it may show a problem, but it is real). Without a rise there is
        # no rate to measure.
        if disturbed or minutes < MIN_DEMAND_MINUTES or rise <= 0:
            return None
        measured = round(rise / (minutes / 60), 3)
        mean_outdoor = (
            round(sum(outdoor_values) / len(outdoor_values), 1) if outdoor_values else None
        )
        self.episodes.append([mean_outdoor, measured, now.isoformat()])
        del self.episodes[:-MAX_EPISODES]
        return measured

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
