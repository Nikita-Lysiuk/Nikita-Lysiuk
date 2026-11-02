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


def daily_counts(payload):
    if payload.get("errors"):
        raise ValueError("GitHub returned GraphQL errors")
    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [day for week in weeks for day in week["contributionDays"]][-30:]
    if len(days) != 30:
        raise ValueError("Expected 30 days of contribution data")
    result, previous = [], None
    for day in days:
        date = dt.date.fromisoformat(day["date"])
        count = day["contributionCount"]
        if type(count) is not int or count < 0:
            raise ValueError("Invalid contribution count")
        if previous and date != previous + dt.timedelta(days=1):
            raise ValueError("Contribution dates must be consecutive")
        result.append((date, count))
        previous = date
    return result


def render(payload, updated_at=None):
    days = daily_counts(payload)
    updated_at = updated_at or dt.datetime.now(dt.timezone.utc)
    updated_at = updated_at.astimezone(dt.timezone.utc)
    first, last = days[0][0], days[-1][0]
    if last > updated_at.date():
        raise ValueError("Contribution calendar contains future dates")
    completed_date, completed_count = days[-2] if last == updated_at.date() else days[-1]
    total = sum(count for _, count in days)
    # Leave room above the tallest bar for its exact count.
    ceiling = max(10, math.ceil((max(count for _, count in days) + 3) / 10) * 10)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="272" '
        'viewBox="0 0 900 272" role="img" aria-labelledby="title desc">',
        f'<title id="title">{total:,} contributions over 30 days</title>',
        f'<desc id="desc">Daily GitHub contributions from {first} to {last}. '
        f'{completed_date}: {completed_count} contributions. '
        'Each bar represents one day. Today may be partial. Contributions include commits, issues, '
        'pull requests, and reviews recorded by GitHub.</desc>',
        '<defs><linearGradient id="sheen" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#7c3aed" stop-opacity="0.09"/>'
        '<stop offset="45%" stop-color="#7c3aed" stop-opacity="0"/>'
        '</linearGradient></defs>',
        '<rect x="0.5" y="0.5" width="899" height="271" rx="12" fill="#0d0d16"/>',
        '<rect x="0.5" y="0.5" width="899" height="271" rx="12" fill="url(#sheen)"/>',
        '<rect x="0.5" y="0.5" width="899" height="271" rx="12" fill="none" '
        'stroke="#23233a" stroke-width="1"/>',
        '<g font-family="\'JetBrains Mono\', monospace">',
        f'<text x="32" y="40" fill="#e6e6ec" font-size="19" font-weight="700">{total:,} contributions</text>',
        '<text x="32" y="62" fill="#8b949e" font-size="12">last 30 days &#183; one bar = one day</text>',
        f'<text x="868" y="40" text-anchor="end" fill="#c4b5fd" font-size="16" font-weight="700">{completed_date:%d %b}: {completed_count}</text>',
        '<text x="868" y="62" text-anchor="end" fill="#8b949e" font-size="11">last completed day</text>',
    ]
    for value in (0, ceiling // 2, ceiling):
        y = 206 - value / ceiling * 116
        parts.extend([
            f'<path d="M64 {y:.1f}H868" stroke="#23233a"/>',
            f'<text x="50" y="{y + 4:.1f}" text-anchor="end" fill="#8b949e" font-size="11">{value}</text>',
        ])
    for index, (date, count) in enumerate(days):
        x = 69 + index * 26.5
        height = count / ceiling * 116
        color = "#c4b5fd" if date == completed_date else "#7c3aed"
        if count:
            parts.append(
                f'<rect class="bar" '
                f'x="{x:.1f}" y="{206 - height:.1f}" width="18" '
                f'height="{height:.1f}" rx="2" fill="{color}">'
                f'<title>{date}: {count} contributions</title></rect>'
            )
        if date == completed_date and count:
            parts.append(
                f'<text x="{x + 9:.1f}" y="{200 - height:.1f}" text-anchor="middle" '
                f'fill="#c4b5fd" font-size="11">{count}</text>'
            )
        if index in (0, 7, 14, 21, 29):
            parts.append(
                f'<text x="{x + 9:.1f}" y="229" text-anchor="middle" '
                f'fill="#8b949e" font-size="11">{date:%d %b}</text>'
            )
    parts.append('<text x="32" y="254" fill="#8b949e" font-size="10">today may be partial</text>')
    parts.append(
        f'<text x="868" y="254" text-anchor="end" fill="#8b949e" font-size="10">'
        f'updated {updated_at:%d %b %Y %H:%M} UTC</text>'
    )
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
