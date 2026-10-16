"""Heating rate learning for optimal start (pure Python).

The learner observes heating episodes (the room asks for heat and the
temperature rises from at least 0.5 °C below the target) and keeps the last
episodes. The heating rate in °C per hour is then estimated as a straight
line of the outdoor temperature, so every episode helps at every outdoor
temperature and temperatures not seen yet are estimated from the trend.

Episodes during which a window or door sensor of the room was open are not
used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

DEFAULT_RATE = 1.0  # °C per hour, until the first episode
MIN_RATE = 0.2
MAX_RATE = 10.0
MIN_EPISODE_MINUTES = 10
MIN_RISE = 0.3
MAX_EPISODES = 30
# A line needs a few episodes over a real spread of outdoor temperatures.
MIN_FIT_EPISODES = 3
MIN_FIT_SPREAD = 3.0  # °C
# Rooms heat faster when it is warmer outside, never slower.
MAX_SLOPE = 0.3  # (°C/h) per °C outdoor
# How far beyond the outdoor temperatures seen so far the line is used.
EXTRAPOLATE = 5.0  # °C

# Buckets of the versions before 1.6 (migrated to episodes).
_LEGACY_BUCKETS = {"below_0": -5.0, "0_10": 5.0, "above_10": 15.0}


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
        slope = min(max(cov / var, 0.0), MAX_SLOPE) if var else 0.0
        return mean_y - slope * mean_x, slope

    def rate(self, outdoor: float | None) -> float:
        """Return the learned rate for the outdoor temperature."""
        if not self.episodes:
            return DEFAULT_RATE
        mean = sum(float(r) for _, r, *_ in self.episodes) / len(self.episodes)
        line = self.fit()
        if line is None or outdoor is None:
            return round(min(max(mean, MIN_RATE), MAX_RATE), 3)
        xs = [p[0] for p in self._points()]
        x = min(max(outdoor, min(xs) - EXTRAPOLATE), max(xs) + EXTRAPOLATE)
        intercept, slope = line
        return round(min(max(intercept + slope * x, MIN_RATE), MAX_RATE), 3)

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
    ) -> float | None:
        """Feed an observation. Returns the measured rate when an episode is used.

        ``window_open`` is True while a window or door sensor of the room is open;
        such an episode is not used.
        """
        if current is None:
            return None
        if heating and self.episode_start is None:
            if target is not None and target - current >= 0.5 and not window_open:
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
        if disturbed or minutes < MIN_EPISODE_MINUTES or rise < MIN_RISE:
            return None
        measured = round(min(max(rise / (minutes / 60), MIN_RATE), MAX_RATE), 3)
        mean_outdoor = (
            round(sum(outdoor_values) / len(outdoor_values), 1) if outdoor_values else None
        )
        self.episodes.append([mean_outdoor, measured, now.isoformat()])
        del self.episodes[:-MAX_EPISODES]
        return measured

    # ----------------------------------------------------------- persistence
    def as_dict(self) -> dict:
        """Serialize."""
        return {"episodes": self.episodes}

    @classmethod
    def from_dict(cls, data: dict | None) -> HeatingRateLearner:
        """Restore (rates per bucket of older versions become one episode each)."""
        obj = cls()
        if not data:
            return obj
        episodes = data.get("episodes")
        if isinstance(episodes, list):
            for item in episodes:
                try:
                    outdoor = None if item[0] is None else float(item[0])
                    obj.episodes.append([outdoor, float(item[1]), str(item[2]) if len(item) > 2 else ""])
                except (TypeError, ValueError, IndexError):
                    continue
        elif isinstance(data.get("rates"), dict):
            for bucket, rate in data["rates"].items():
                try:
                    obj.episodes.append([_LEGACY_BUCKETS.get(str(bucket)), float(rate), ""])
                except (TypeError, ValueError):
                    continue
        del obj.episodes[:-MAX_EPISODES]
        return obj
