import unittest
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from upload_plugg.core.scheduling import ScheduleError, calculate_schedule, to_youtube_timestamp


class SchedulingTests(unittest.TestCase):
    def test_expected_weekday_sequence(self):
        zone = ZoneInfo("Europe/Berlin")
        result = calculate_schedule(
            5, date(2026, 7, 15), [1, 3, 4, 6], time(18, 0),
            now=datetime(2026, 7, 15, 10, 0, tzinfo=zone),
        )
        self.assertEqual([value.weekday() for value in result], [3, 4, 6, 1, 3])

    def test_daylight_saving_offset_changes(self):
        zone = ZoneInfo("Europe/Berlin")
        result = calculate_schedule(
            2, date(2026, 3, 22), [6], time(18, 0),
            now=datetime(2026, 3, 20, 10, 0, tzinfo=zone),
        )
        self.assertNotEqual(result[0].utcoffset(), result[1].utcoffset())

    def test_invalid_timezone(self):
        with self.assertRaises(ScheduleError):
            calculate_schedule(1, date.today(), [1], time(18), "Moon/Base")

    def test_youtube_timestamp_is_utc(self):
        value = datetime(2026, 7, 20, 18, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        self.assertEqual(to_youtube_timestamp(value), "2026-07-20T16:00:00Z")


if __name__ == "__main__":
    unittest.main()

