"""Tests for outdoor tracking and heating rate learning."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import math
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

    def test_daily_mean_of_the_local_day(self) -> None:
        # 22:30 UTC on 12 October is already 13 October in Bucharest (UTC+3).
        from zoneinfo import ZoneInfo

        tracker = outdoor.OutdoorTracker(tz=ZoneInfo("Europe/Bucharest"))
        tracker.add(datetime(2026, 10, 12, 22, 30, tzinfo=TZ), 4.0)
        self.assertEqual(tracker.daily_means, {"2026-10-13": 4.0})

    def test_unknown_after_the_window(self) -> None:
        # No new value for the averaging window: the outdoor temperature is unknown.
        tracker = outdoor.OutdoorTracker(max_age=timedelta(hours=6))
        t0 = datetime(2026, 10, 12, 0, tzinfo=TZ)
        tracker.add(t0, 10.0)
        self.assertEqual(tracker.latest(t0 + timedelta(hours=6)), 10.0)
        self.assertEqual(tracker.average(t0 + timedelta(hours=6), 6), 10.0)
        self.assertIsNone(tracker.latest(t0 + timedelta(hours=7)))
        self.assertIsNone(tracker.average(t0 + timedelta(hours=7), 6))
        # A short gap is no problem.
        tracker.add(t0 + timedelta(hours=7), 12.0)
        self.assertEqual(tracker.latest(t0 + timedelta(hours=8)), 12.0)

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
        # Just below the target the episode goes on (no margin): it ends at the target.
        self.assertIsNone(self._episode(learner, self.T0, 5.0, rise=2.95))
        rate = learner.observe(self.T0 + timedelta(minutes=90), True, 22.0, 22.0, 5.0)
        self.assertAlmostEqual(rate, 2.0, places=2)
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

    def test_cancel(self) -> None:
        # Outside the cold season the episode in progress is dropped.
        learner = learning.HeatingRateLearner()
        learner.observe(self.T0, True, 19.0, 22.0, 5.0)
        learner.cancel()
        self.assertIsNone(learner.episode_start)
        cooling = learning.CoolingLearner()
        cooling.observe(self.T0, False, 22.0, 5.0)
        cooling.cancel()
        self.assertIsNone(cooling.observe(self.T0 + timedelta(hours=2), True, 21.0, 5.0))

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


class CoolingLearnerTest(unittest.TestCase):
    T0 = datetime(2026, 10, 12, 22, 0, tzinfo=timezone.utc)

    def _cool(self, learner, start, indoor0, indoor1, outdoor, minutes, window=False):
        learner.observe(start, False, indoor0, outdoor, window)
        return learner.observe(start + timedelta(minutes=minutes), True, indoor1, outdoor, False)

    def test_coefficient_from_inside_outside_difference(self) -> None:
        learner = learning.CoolingLearner()
        # 22 -> 21.5 °C in 1 h with 7 °C outside: k = ln(15 / 14.5).
        k = self._cool(learner, self.T0, 22.0, 21.5, 7.0, 60)
        self.assertAlmostEqual(k, math.log(15 / 14.5), places=4)
        # The same house loses heat faster when it is colder outside.
        self.assertGreater(learner.rate(22.0, -5.0), learner.rate(22.0, 7.0))
        # Time to fall from 22 to 21.5 °C at 7 °C outside: 1 h.
        self.assertAlmostEqual(learner.minutes_to_fall(22.0, 21.5, 7.0), 60.0, delta=0.01)
        self.assertAlmostEqual(learner.temperature_after(22.0, 7.0, 60), 21.5, delta=0.001)

    def test_episode_conditions(self) -> None:
        learner = learning.CoolingLearner()
        # Shorter than 10 minutes without heat demand: not used.
        self.assertIsNone(self._cool(learner, self.T0, 22.0, 21.9, 7.0, 9))
        # No fall (sun, cooking): not used.
        self.assertIsNone(self._cool(learner, self.T0, 22.0, 22.0, 7.0, 60))
        # A window open: not used.
        self.assertIsNone(self._cool(learner, self.T0, 22.0, 21.0, 7.0, 60, window=True))
        # Any fall over at least 10 minutes counts.
        self.assertIsNotNone(self._cool(learner, self.T0, 22.0, 21.9, 7.0, 10))
        self.assertEqual(len(learner.episodes), 1)

    def test_restore(self) -> None:
        learner = learning.CoolingLearner()
        self._cool(learner, self.T0, 22.0, 21.5, 7.0, 60)
        again = learning.CoolingLearner.from_dict(learner.as_dict())
        self.assertEqual(again.episodes, learner.episodes)
        self.assertIsNone(learning.CoolingLearner.from_dict(None).coefficient)


if __name__ == "__main__":
    unittest.main()


class ExpectedOutdoorTest(unittest.TestCase):
    """The outdoor temperature expected during an optimal start / stop."""

    NOW = datetime(2026, 1, 10, 4, 20, tzinfo=timezone.utc)

    def hourly(self, *values: float) -> list:
        # Forecast hours from 04:00 on.
        base = datetime(2026, 1, 10, 4, 0, tzinfo=timezone.utc)
        return [(base + timedelta(hours=i), v) for i, v in enumerate(values)]

    def test_time_weighted_mean(self) -> None:
        # 05:30-07:00: half an hour at -2 (05:00), an hour at -6 (06:00).
        value, source = outdoor.expected_outdoor(
            self.NOW,
            datetime(2026, 1, 10, 5, 30, tzinfo=timezone.utc),
            datetime(2026, 1, 10, 7, 0, tzinfo=timezone.utc),
            1.0,
            self.hourly(0.0, -2.0, -6.0, -3.0),
        )
        self.assertEqual(source, "forecast")
        self.assertAlmostEqual(value, (-2 * 30 + -6 * 60) / 90, places=2)

    def test_measured_value_until_the_next_forecast_hour(self) -> None:
        # 04:20-05:20: 40 minutes at the measured 1.0, 20 at -2 (05:00).
        value, _ = outdoor.expected_outdoor(
            self.NOW,
            self.NOW,
            self.NOW + timedelta(hours=1),
            1.0,
            self.hourly(0.0, -2.0, -6.0),
        )
        self.assertAlmostEqual(value, (1.0 * 40 - 2.0 * 20) / 60, places=2)

    def test_start_in_the_past_counts_from_now(self) -> None:
        value, _ = outdoor.expected_outdoor(
            self.NOW,
            self.NOW - timedelta(hours=2),
            self.NOW + timedelta(minutes=50),
            1.0,
            self.hourly(0.0, -2.0),
        )
        self.assertAlmostEqual(value, (1.0 * 40 - 2.0 * 10) / 50, places=2)

    def test_without_a_covering_forecast_the_value_of_now(self) -> None:
        end = datetime(2026, 1, 10, 9, 0, tzinfo=timezone.utc)
        self.assertEqual(
            outdoor.expected_outdoor(self.NOW, self.NOW, end, 1.5, self.hourly(0.0, -2.0)),
            (1.5, "now"),
        )
        self.assertEqual(outdoor.expected_outdoor(self.NOW, self.NOW, end, 1.5, []), (1.5, "now"))
        # An old forecast is not used.
        old = [(self.NOW - timedelta(hours=3), -9.0), (self.NOW - timedelta(hours=2), -9.0)]
        self.assertEqual(
            outdoor.expected_outdoor(self.NOW, self.NOW, self.NOW + timedelta(minutes=10), 1.5, old),
            (1.5, "now"),
        )

    def test_unknown_measured_value_uses_the_forecast(self) -> None:
        value, source = outdoor.expected_outdoor(
            self.NOW, self.NOW, self.NOW + timedelta(minutes=50), None, self.hourly(0.0, -2.0)
        )
        self.assertEqual(source, "forecast")
        self.assertAlmostEqual(value, (0.0 * 40 - 2.0 * 10) / 50, places=2)
