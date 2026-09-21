#!/usr/bin/env python3
"""Render a checked-in contribution chart using GitHub's calendar, not an image host."""
import datetime as dt
import json
import math
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

OUTPUT = Path(__file__).resolve().parent.parent / "profile" / "activity.svg"
QUERY = """
query {
  user(login: "Nikita-Lysiuk") {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_calendar():
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={QUERY}"],
        capture_output=True, text=True, check=True, timeout=60,
    )
    return json.loads(result.stdout)


def weekly_counts(payload):
    if payload.get("errors"):
        raise ValueError("GitHub returned GraphQL errors")
    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"][-26:]
    if len(weeks) != 26:
        raise ValueError("Expected 26 weeks of contribution data")
    result, previous = [], None
    for index, week in enumerate(weeks):
        days = week["contributionDays"]
        if not 1 <= len(days) <= 7 or (index < 25 and len(days) != 7):
            raise ValueError("Incomplete contribution calendar")
        dates, total = [], 0
        for day in days:
            date = dt.date.fromisoformat(day["date"])
            count = day["contributionCount"]
            if type(count) is not int or count < 0:
                raise ValueError("Invalid contribution count")
            if previous and date != previous + dt.timedelta(days=1):
                raise ValueError("Contribution dates must be consecutive")
            dates.append(date)
            total += count
            previous = date
        if dates[0].weekday() != 6:
            raise ValueError("Expected GitHub's Sunday-start weeks")
        result.append((dates[0], dates[-1], total))
    return result


def render(payload):
    weeks = weekly_counts(payload)
    total = sum(week[2] for week in weeks)
    ceiling = max(10, math.ceil(max(week[2] for week in weeks) / 10) * 10)
    first, last = weeks[0][0], weeks[-1][1]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="272" '
        'viewBox="0 0 900 272" role="img" aria-labelledby="title desc">',
        f'<title id="title">{total:,} contributions over 26 weeks</title>',
        f'<desc id="desc">Weekly GitHub contributions from {first} to {last}. '
        'The final week may be partial. Contributions include commits, issues, '
        'pull requests, and reviews recorded by GitHub.</desc>',
        '<rect width="900" height="272" rx="12" fill="#161b22"/>',
        '<g font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif">',
        f'<text x="32" y="37" fill="#eef2f6" font-size="20" font-weight="600">{total:,} contributions</text>',
        '<text x="32" y="61" fill="#a8b3bf" font-size="14">Last 26 weeks · weekly totals</text>',
        f'<text x="868" y="37" text-anchor="end" fill="#a8b3bf" font-size="13">Through {last:%d %b %Y}</text>',
    ]
    for value in (0, ceiling // 2, ceiling):
        y = 206 - value / ceiling * 116
        parts.extend([
            f'<path d="M64 {y:.1f}H868" stroke="#303a46"/>',
            f'<text x="50" y="{y + 4:.1f}" text-anchor="end" fill="#a8b3bf" font-size="12">{value}</text>',
        ])
    for index, (start, end, count) in enumerate(weeks):
        x = 69 + index * 30.5
        height = count / ceiling * 116
        color = "#b3e3e6" if index == 25 else "#78c8ce"
        if count:
            parts.append(
                f'<rect x="{x:.1f}" y="{206 - height:.1f}" width="20" '
                f'height="{height:.1f}" rx="2" fill="{color}">'
                f'<title>{start} to {end}: {count} contributions</title></rect>'
            )
        if index in (0, 5, 10, 15, 20, 25):
            parts.append(
                f'<text x="{x + 10:.1f}" y="229" text-anchor="middle" '
                f'fill="#a8b3bf" font-size="12">{start:%d %b}</text>'
            )
    parts.append('<text x="868" y="254" text-anchor="end" fill="#a8b3bf" font-size="12">Latest week may be partial</text>')
    parts.append('</g></svg>\n')
    return "\n".join(parts)


def refresh(output=OUTPUT, fetch=fetch_calendar):
    try:
        svg = render(fetch())
    except (KeyError, TypeError, ValueError, OSError, subprocess.SubprocessError):
        # Never replace a working chart with an error response or fake zeroes.
        if output.exists() and ET.parse(output).getroot().tag == "{http://www.w3.org/2000/svg}svg":
            print("::warning::Activity refresh failed; keeping the last successful chart.")
            return False
        raise
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent, delete=False) as temp:
        temp.write(svg)
    Path(temp.name).replace(output)
    print(f"Rendered {output.name}")
    return True


if __name__ == "__main__":
    refresh()
