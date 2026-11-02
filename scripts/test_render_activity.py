import datetime as dt
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from render_activity import daily_counts, refresh, render

UPDATED_AT = dt.datetime(2026, 11, 2, 10, 30, tzinfo=dt.timezone.utc)


def calendar(count=1, last_days=2):
    start = dt.date(2026, 10, 4)
    weeks = [{"contributionDays": [
        {"date": (start + dt.timedelta(days=w * 7 + d)).isoformat(), "contributionCount": count}
        for d in range(7 if w < 4 else last_days)
    ]} for w in range(5)]
    return {"data": {"user": {"contributionsCollection": {"contributionCalendar": {"weeks": weeks}}}}}


class ActivityTests(unittest.TestCase):
    def test_daily_window_across_week_boundaries(self):
        data = calendar(count=2)
        days = daily_counts(data)
        self.assertEqual(len(days), 30)
        self.assertEqual(days[0], (dt.date(2026, 10, 4), 2))
        self.assertEqual(days[-1], (dt.date(2026, 11, 2), 2))
        svg = ET.fromstring(render(data, UPDATED_AT))
        self.assertIn("60 contributions over 30 days", "".join(svg.itertext()))

    def test_november_first_is_37_not_the_previous_week_total(self):
        data = calendar(count=0)
        weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        for day, count in zip(weeks[-2]["contributionDays"], [6, 26, 6, 15, 17, 3, 22]):
            day["contributionCount"] = count  # Previous week totals 95.
        weeks[-1]["contributionDays"][0]["contributionCount"] = 37
        svg = ET.fromstring(render(data, UPDATED_AT))
        bars = svg.findall(".//{http://www.w3.org/2000/svg}rect[@class='bar']")
        latest = bars[-1]
        self.assertEqual(latest.find("{http://www.w3.org/2000/svg}title").text,
                         "2026-11-01: 37 contributions")
        self.assertEqual(latest.get("height"), "107.3")  # 37/40, not 95/100.
        text = "".join(svg.itertext())
        self.assertIn("01 Nov: 37", text)
        self.assertIn("updated 02 Nov 2026 10:30 UTC", text)

    def test_complete_latest_day_and_trailing_30_day_window(self):
        data = calendar(count=1, last_days=7)
        updated = dt.datetime(2026, 11, 8, tzinfo=dt.timezone.utc)
        days = daily_counts(data)
        self.assertEqual(days[0][0], dt.date(2026, 10, 9))
        svg = ET.fromstring(render(data, updated))
        self.assertIn("07 Nov: 1", "".join(svg.itertext()))

    def test_invalid_counts_dates_and_short_windows_are_rejected(self):
        for bad_count in (-1, True, "37", 1.5):
            data = calendar()
            data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"][-1]["contributionDays"][-1]["contributionCount"] = bad_count
            with self.subTest(count=bad_count), self.assertRaises(ValueError):
                daily_counts(data)
        with self.assertRaises(ValueError):
            daily_counts(calendar(last_days=1))
        with self.assertRaises(ValueError):
            render(calendar(last_days=3), UPDATED_AT)

    def test_zero_activity_is_valid_and_has_no_false_bars(self):
        svg = ET.fromstring(render(calendar(count=0), UPDATED_AT))
        bars = [r for r in svg.findall(".//{http://www.w3.org/2000/svg}rect")
                if r.get("class") == "bar"]
        self.assertEqual(bars, [])
        self.assertIn("0 contributions", "".join(svg.itertext()))

    def test_errors_or_missing_days_cannot_replace_previous_chart(self):
        incomplete = calendar()
        weeks = incomplete["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        weeks[3]["contributionDays"].pop()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "activity.svg"
            self.assertTrue(refresh(output, lambda: calendar()))
            previous = output.read_bytes()
            for bad in ({"errors": [{"message": "unavailable"}]}, incomplete, {}):
                with self.subTest(payload=bad):
                    self.assertFalse(refresh(output, lambda: bad))
                    self.assertEqual(output.read_bytes(), previous)

    def test_first_run_failure_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                refresh(Path(directory) / "activity.svg", lambda: {"errors": ["unavailable"]})


if __name__ == "__main__":
    unittest.main()
