import datetime as dt
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from render_activity import refresh, render, weekly_counts


def calendar(count=1, last_days=3):
    start = dt.date(2026, 3, 29)
    weeks = [{"contributionDays": [
        {"date": (start + dt.timedelta(days=w * 7 + d)).isoformat(), "contributionCount": count}
        for d in range(7 if w < 25 else last_days)
    ]} for w in range(26)]
    return {"data": {"user": {"contributionsCollection": {"contributionCalendar": {"weeks": weeks}}}}}


class ActivityTests(unittest.TestCase):
    def test_weekly_totals_and_partial_week(self):
        data = calendar(count=2)
        weeks = weekly_counts(data)
        self.assertEqual([w[2] for w in weeks], [14] * 25 + [6])
        svg = ET.fromstring(render(data))
        self.assertIn("356 contributions", "".join(svg.itertext()))

    def test_zero_activity_is_valid_and_has_no_false_bars(self):
        svg = ET.fromstring(render(calendar(count=0)))
        bars = [r for r in svg.findall(".//{http://www.w3.org/2000/svg}rect")
                if r.get("class") == "bar"]
        self.assertEqual(bars, [])  # Background and cursor only, no bars.
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
