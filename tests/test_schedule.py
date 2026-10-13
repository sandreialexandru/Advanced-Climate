"""Tests for schedule parsing and lookup."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import unittest

from tests.pure import const, schedule

TZ = timezone(timedelta(hours=3))
PRESETS = const.PRESETS


def weekday_info(day: date) -> tuple[bool, str | None]:
    return day.weekday() < 5, None


class ParseTest(unittest.TestCase):
    def test_parse_default(self) -> None:
        profiles = schedule.parse_schedule(const.DEFAULT_SCHEDULE, PRESETS)
        self.assertEqual(list(profiles), ["workday", "weekend"])
        self.assertEqual(profiles["workday"][1].minute, 6 * 60)
        self.assertEqual(profiles["workday"][1].preset, "home")

    def test_roundtrip(self) -> None:
        profiles = schedule.parse_schedule(const.DEFAULT_SCHEDULE, PRESETS)
        text = schedule.format_schedule(profiles)
        self.assertEqual(schedule.parse_schedule(text, PRESETS), profiles)

    def test_case_and_comments(self) -> None:
        profiles = schedule.parse_schedule(
            "# comment\nWorkday: 06:00 HOME, 00:00 Sleep  # trailing\n", PRESETS
        )
        self.assertEqual([s.preset for s in profiles["workday"]], ["sleep", "home"])

    def test_errors(self) -> None:
        for text in (
            "",
            "workday 06:00 home",
            "workday: 25:00 home",
            "workday: 06:00 boost",
            "workday: 06:00 home, 06:00 sleep",
            "workday: 06:00 home\nworkday: 07:00 home",
            "workday: ",
        ):
            with self.subTest(text=text), self.assertRaises(schedule.ScheduleError):
                schedule.parse_schedule(text, PRESETS)

    def test_custom_names(self) -> None:
        profiles = schedule.parse_schedule("workday: 06:00 Day, 22:00 Night", ["Day", "Night"])
        self.assertEqual(profiles["workday"][0].preset, "Day")


class LookupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sched = schedule.Schedule(
            schedule.parse_schedule(const.DEFAULT_SCHEDULE, PRESETS)
        )

    def test_workday_morning(self) -> None:
        # 2026-10-12 is a Monday.
        state = self.sched.lookup(datetime(2026, 10, 12, 7, 0, tzinfo=TZ), weekday_info)
        self.assertEqual(state.preset, "home")
        self.assertEqual(state.profile, "workday")
        self.assertEqual(state.next_change, datetime(2026, 10, 12, 22, 0, tzinfo=TZ))
        self.assertEqual(state.next_preset, "sleep")

    def test_friday_night_to_saturday(self) -> None:
        state = self.sched.lookup(datetime(2026, 10, 16, 23, 0, tzinfo=TZ), weekday_info)
        self.assertEqual(state.preset, "sleep")
        # Saturday 00:00 is still sleep, so the next change is Saturday 08:00.
        self.assertEqual(state.next_change, datetime(2026, 10, 17, 8, 0, tzinfo=TZ))
        self.assertEqual(state.next_preset, "home")

    def test_weekend(self) -> None:
        state = self.sched.lookup(datetime(2026, 10, 17, 7, 59, tzinfo=TZ), weekday_info)
        self.assertEqual((state.profile, state.preset), ("weekend", "sleep"))
        state = self.sched.lookup(datetime(2026, 10, 17, 8, 0, tzinfo=TZ), weekday_info)
        self.assertEqual(state.preset, "home")

    def test_forced_and_weekday_profiles(self) -> None:
        sched = schedule.Schedule(
            schedule.parse_schedule(
                const.DEFAULT_SCHEDULE + "\nfri: 00:00 sleep, 07:00 comfort\nparty: 00:00 activity",
                PRESETS,
            )
        )
        friday = datetime(2026, 10, 16, 9, 0, tzinfo=TZ)
        self.assertEqual(sched.lookup(friday, weekday_info).preset, "comfort")
        forced = sched.lookup(friday, lambda d: (True, "party"))
        self.assertEqual((forced.profile, forced.preset), ("party", "activity"))

    def test_holiday_uses_weekend(self) -> None:
        state = self.sched.lookup(
            datetime(2026, 12, 1, 7, 0, tzinfo=TZ), lambda d: (False, None)
        )
        self.assertEqual((state.profile, state.preset), ("weekend", "sleep"))

    def test_missing_first_slot_wraps(self) -> None:
        sched = schedule.Schedule(
            schedule.parse_schedule("workday: 06:00 home, 22:00 sleep", PRESETS)
        )
        state = sched.lookup(datetime(2026, 10, 12, 3, 0, tzinfo=TZ), weekday_info)
        self.assertEqual(state.preset, "sleep")
        self.assertEqual(state.slot_start, datetime(2026, 10, 11, 22, 0, tzinfo=TZ))

    def test_day_boundary(self) -> None:
        sched = schedule.Schedule(
            schedule.parse_schedule(
                "workday: 04:00 home, 23:00 sleep\nweekend: 04:00 sleep, 10:00 home",
                PRESETS,
            ),
            day_boundary=4 * 60,
        )
        # Saturday 02:00 still belongs to Friday (workday) -> sleep from 23:00.
        state = sched.lookup(datetime(2026, 10, 17, 2, 0, tzinfo=TZ), weekday_info)
        self.assertEqual((state.profile, state.preset), ("workday", "sleep"))
        self.assertEqual(state.next_change, datetime(2026, 10, 17, 10, 0, tzinfo=TZ))

    def test_upcoming(self) -> None:
        start = datetime(2026, 10, 12, 5, 0, tzinfo=TZ)
        changes = self.sched.upcoming(start, weekday_info, timedelta(hours=24))
        self.assertEqual(
            changes,
            [
                (datetime(2026, 10, 12, 6, 0, tzinfo=TZ), "home"),
                (datetime(2026, 10, 12, 22, 0, tzinfo=TZ), "sleep"),
            ],
        )

    def test_dict_roundtrip(self) -> None:
        data = schedule.profiles_to_dict(self.sched.profiles)
        self.assertEqual(schedule.profiles_from_dict(data, PRESETS), self.sched.profiles)


if __name__ == "__main__":
    unittest.main()
