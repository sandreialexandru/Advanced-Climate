"""Tests for outdoor tracking and heating rate learning."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import unittest

from tests.pure import const, learning, outdoor

TZ = timezone.utc


class OutdoorTest(unittest.TestCase):
    def test_average(self) -> None:
        tracker = outdoor.OutdoorTracker()
        t0 = datetime(2026, 10, 12, 0, tzinfo=TZ)
        tracker.add(t0, 10.0)
        tracker.add(t0 + timedelta(hours=3), 20.0)
        self.assertAlmostEqual(tracker.average(t0 + timedelta(hours=6), 6), 15.0)
        self.assertAlmostEqual(tracker.average(t0 + timedelta(hours=6), 3), 20.0)

    def test_cutoff_hysteresis(self) -> None:
        tracker = outdoor.OutdoorTracker()
        self.assertFalse(tracker.update_cutoff(17.5, 18, 1))
        self.assertTrue(tracker.update_cutoff(18.0, 18, 1))
        self.assertTrue(tracker.update_cutoff(17.5, 18, 1))
        self.assertFalse(tracker.update_cutoff(17.0, 18, 1))

    def test_date_season(self) -> None:
        self.assertTrue(outdoor.in_date_season(date(2026, 12, 1), "10-15", "04-15"))
        self.assertTrue(outdoor.in_date_season(date(2026, 4, 15), "10-15", "04-15"))
        self.assertFalse(outdoor.in_date_season(date(2026, 7, 1), "10-15", "04-15"))
        self.assertTrue(outdoor.in_date_season(date(2026, 7, 1), "06-01", "08-01"))

    def test_auto_season(self) -> None:
        tracker = outdoor.OutdoorTracker()
        tracker.daily_means = {"2026-10-09": 12.0, "2026-10-10": 13.0, "2026-10-11": 14.0}
        today = date(2026, 10, 12)
        self.assertTrue(tracker.update_season(today, const.SEASON_AUTO, "", "", 3, 15.0))
        tracker.daily_means = {"2026-05-09": 16.0, "2026-05-10": 18.0, "2026-05-11": 17.0}
        self.assertFalse(
            tracker.update_season(date(2026, 5, 12), const.SEASON_AUTO, "", "", 3, 15.0)
        )
        # Mixed days keep the previous state.
        tracker.daily_means = {"2026-05-12": 14.0, "2026-05-13": 18.0, "2026-05-14": 17.0}
        self.assertFalse(
            tracker.update_season(date(2026, 5, 15), const.SEASON_AUTO, "", "", 3, 15.0)
        )

    def test_serialize(self) -> None:
        tracker = outdoor.OutdoorTracker()
        tracker.add(datetime(2026, 10, 12, tzinfo=TZ), 5.0)
        tracker.cutoff_active = True
        again = outdoor.OutdoorTracker.from_dict(tracker.as_dict())
        self.assertEqual(again.latest(), 5.0)
        self.assertTrue(again.cutoff_active)


class LearningTest(unittest.TestCase):
    def test_episode(self) -> None:
        learner = learning.HeatingRateLearner()
        t0 = datetime(2026, 10, 12, 6, tzinfo=TZ)
        self.assertEqual(learner.rate(5.0), learning.DEFAULT_RATE)
        learner.observe(t0, True, 19.0, 22.0, 5.0)
        learner.observe(t0 + timedelta(minutes=30), True, 20.0, 22.0, 5.0)
        rate = learner.observe(t0 + timedelta(minutes=90), True, 21.95, 22.0, 5.0)
        self.assertAlmostEqual(rate, 1.967, places=2)
        self.assertAlmostEqual(learner.rate(5.0), rate)
        # Unknown bucket falls back to the average of known buckets.
        self.assertAlmostEqual(learner.rate(-5.0), rate)

    def test_short_episode_ignored(self) -> None:
        learner = learning.HeatingRateLearner()
        t0 = datetime(2026, 10, 12, 6, tzinfo=TZ)
        learner.observe(t0, True, 19.0, 22.0, 5.0)
        self.assertIsNone(learner.observe(t0 + timedelta(minutes=5), False, 19.5, 22.0, 5.0))
        self.assertEqual(learner.rates, {})


if __name__ == "__main__":
    unittest.main()
