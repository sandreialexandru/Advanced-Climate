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
    T0 = datetime(2026, 10, 12, 6, tzinfo=TZ)

    def _episode(self, learner, start, outdoor, rise=3.0, minutes=90, window=False):
        learner.observe(start, True, 19.0, 22.0, outdoor)
        learner.observe(start + timedelta(minutes=30), True, 20.0, 22.0, outdoor, window)
        return learner.observe(
            start + timedelta(minutes=minutes), True, 19.0 + rise, 22.0, outdoor
        )

    def test_episode(self) -> None:
        learner = learning.HeatingRateLearner()
        self.assertEqual(learner.rate(5.0), learning.DEFAULT_RATE)
        rate = self._episode(learner, self.T0, 5.0, rise=2.95)
        self.assertAlmostEqual(rate, 1.967, places=2)
        # One episode: the same rate at every outdoor temperature.
        self.assertAlmostEqual(learner.rate(5.0), rate, places=2)
        self.assertAlmostEqual(learner.rate(-5.0), rate, places=2)

    def test_short_demand_ignored(self) -> None:
        # The heat demand must last at least 10 minutes.
        learner = learning.HeatingRateLearner()
        learner.observe(self.T0, True, 19.0, 22.0, 5.0)
        self.assertIsNone(learner.observe(self.T0 + timedelta(minutes=9), False, 19.5, 22.0, 5.0))
        self.assertEqual(learner.episodes, [])
        learner.observe(self.T0, True, 19.0, 22.0, 5.0)
        rate = learner.observe(self.T0 + timedelta(minutes=10), False, 19.1, 22.0, 5.0)
        self.assertAlmostEqual(rate, 0.6, places=3)

    def test_window_episode_ignored(self) -> None:
        learner = learning.HeatingRateLearner()
        self.assertIsNone(self._episode(learner, self.T0, 5.0, window=True))
        self.assertEqual(learner.episodes, [])
        # No episode starts while a window is open.
        learner.observe(self.T0, True, 19.0, 22.0, 5.0, True)
        self.assertIsNone(learner.episode_start)

    def test_line_of_outdoor_temperature(self) -> None:
        learner = learning.HeatingRateLearner()
        # Faster when it is warmer outside: 1 °C/h at 0 °C, 2 °C/h at 10 °C.
        for i, (outdoor, minutes) in enumerate([(0.0, 180), (5.0, 120), (10.0, 90)]):
            self._episode(learner, self.T0 + timedelta(days=i), outdoor, minutes=minutes)
        intercept, slope = learner.fit()
        self.assertAlmostEqual(slope, 0.1, places=2)
        self.assertAlmostEqual(learner.rate(0.0), 1.0, delta=0.1)
        self.assertAlmostEqual(learner.rate(10.0), 2.0, delta=0.1)
        # Never seen -3 °C: estimated from the trend.
        self.assertAlmostEqual(learner.rate(-3.0), 0.7, delta=0.1)
        # No limits: the line is followed further out too (0.4 °C/h at -6 °C).
        self.assertAlmostEqual(learner.rate(-6.0), 0.4, delta=0.1)
        # Where the line reaches zero the average of the episodes is used.
        mean = sum(r for _, r, *_ in learner.episodes) / len(learner.episodes)
        self.assertAlmostEqual(learner.rate(-30.0), round(mean, 3))

    def test_learning_is_free(self) -> None:
        learner = learning.HeatingRateLearner()
        # Slower when warmer outside is learned as measured.
        for i, (outdoor, minutes) in enumerate([(0.0, 90), (5.0, 120), (10.0, 180)]):
            self._episode(learner, self.T0 + timedelta(days=i), outdoor, minutes=minutes)
        self.assertLess(learner.fit()[1], 0.0)
        # A very slow room is not raised to a minimum: 0.4 °C in 3 h.
        slow = learning.HeatingRateLearner()
        slow.observe(self.T0, True, 21.3, 22.0, 7.0, tolerance=0.5)
        rate = slow.observe(self.T0 + timedelta(hours=3), False, 21.7, 22.0, 7.0, tolerance=0.5)
        self.assertAlmostEqual(rate, 0.133, places=3)
        # A rise of only 0.1 °C is learned too; no rise is no rate.
        tiny = learning.HeatingRateLearner()
        tiny.observe(self.T0, True, 21.4, 22.0, 7.0, tolerance=0.5)
        rate = tiny.observe(self.T0 + timedelta(hours=1), False, 21.5, 22.0, 7.0, tolerance=0.5)
        self.assertAlmostEqual(rate, 0.1, places=3)
        flat = learning.HeatingRateLearner()
        flat.observe(self.T0, True, 21.4, 22.0, 7.0, tolerance=0.5)
        self.assertIsNone(
            flat.observe(self.T0 + timedelta(hours=1), False, 21.4, 22.0, 7.0, tolerance=0.5)
        )

    def test_restore_and_migrate(self) -> None:
        learner = learning.HeatingRateLearner()
        self._episode(learner, self.T0, 5.0)
        again = learning.HeatingRateLearner.from_dict(learner.as_dict())
        self.assertEqual(again.episodes, learner.episodes)
        # Data of older versions is discarded.
        # Version 2 cut the rates to 0.2 … 10 °C/h: those episodes are dropped.
        v2 = learning.HeatingRateLearner.from_dict(
            {"version": 2, "episodes": [[7.0, 0.2, "a"], [5.0, 0.8, "b"], [1.0, 10.0, "c"]]}
        )
        self.assertEqual(v2.episodes, [[5.0, 0.8, "b"]])
        old = learning.HeatingRateLearner.from_dict({"rates": {"above_10": 0.284}})
        self.assertEqual(old.episodes, [])
        self.assertEqual(old.rate(2.0), learning.DEFAULT_RATE)

    def test_episode_starts_at_tolerance(self) -> None:
        # Generic Thermostat with cold_tolerance 0.5: it heats from 0.5 below the target.
        learner = learning.HeatingRateLearner()
        learner.observe(self.T0, True, 21.6, 22.0, 5.0, tolerance=0.5)
        self.assertIsNone(learner.episode_start)
        # At least the tolerance below the target starts an episode (maintenance too).
        learner.observe(self.T0, True, 21.5, 22.0, 5.0, tolerance=0.5)
        self.assertIsNotNone(learner.episode_start)
        self.assertEqual(learning.start_gap(0.5), 0.5)


if __name__ == "__main__":
    unittest.main()
