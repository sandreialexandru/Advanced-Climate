"""Heating rate learning for optimal start (pure Python).

The learner observes heating episodes (the room asks for heat and the
temperature rises) and keeps an exponential moving average of the heating
rate in °C per hour, in buckets by outdoor temperature.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

DEFAULT_RATE = 1.0  # °C per hour
MIN_RATE = 0.2
MAX_RATE = 10.0
ALPHA = 0.3
MIN_EPISODE_MINUTES = 10
MIN_RISE = 0.3

BUCKETS = ((-100.0, 0.0, "below_0"), (0.0, 10.0, "0_10"), (10.0, 100.0, "above_10"))


def bucket_for(outdoor: float | None) -> str:
    """Return the outdoor temperature bucket name."""
    if outdoor is None:
        return "unknown"
    for low, high, name in BUCKETS:
        if low <= outdoor < high:
            return name
    return "unknown"


@dataclass(slots=True)
class HeatingRateLearner:
    """Learn how fast a room heats up."""

    rates: dict[str, float] = field(default_factory=dict)
    episode_start: datetime | None = None
    episode_temp: float | None = None
    episode_bucket: str | None = None

    def rate(self, outdoor: float | None) -> float:
        """Return the learned rate for the outdoor temperature."""
        bucket = bucket_for(outdoor)
        if bucket in self.rates:
            return self.rates[bucket]
        if self.rates:
            return sum(self.rates.values()) / len(self.rates)
        return DEFAULT_RATE

    def observe(
        self,
        now: datetime,
        heating: bool,
        current: float | None,
        target: float | None,
        outdoor: float | None,
    ) -> float | None:
        """Feed an observation. Returns a new rate when an episode completes."""
        if current is None:
            return None
        if heating and self.episode_start is None:
            if target is not None and target - current >= 0.5:
                self.episode_start = now
                self.episode_temp = current
                self.episode_bucket = bucket_for(outdoor)
            return None
        if self.episode_start is None:
            return None
        reached = target is not None and current >= target - 0.1
        if heating and not reached:
            return None
        # Episode finished (target reached or heating stopped).
        minutes = (now - self.episode_start).total_seconds() / 60
        rise = current - (self.episode_temp or current)
        bucket = self.episode_bucket or "unknown"
        self.episode_start = None
        self.episode_temp = None
        self.episode_bucket = None
        if minutes < MIN_EPISODE_MINUTES or rise < MIN_RISE:
            return None
        measured = min(max(rise / (minutes / 60), MIN_RATE), MAX_RATE)
        previous = self.rates.get(bucket)
        new = measured if previous is None else previous + ALPHA * (measured - previous)
        self.rates[bucket] = round(new, 3)
        return self.rates[bucket]

    def as_dict(self) -> dict:
        """Serialize."""
        return {"rates": self.rates}

    @classmethod
    def from_dict(cls, data: dict | None) -> HeatingRateLearner:
        """Restore."""
        obj = cls()
        if data and isinstance(data.get("rates"), dict):
            obj.rates = {str(k): float(v) for k, v in data["rates"].items()}
        return obj
