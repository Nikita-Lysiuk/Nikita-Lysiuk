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
        '<defs><linearGradient id="sheen" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#7c3aed" stop-opacity="0.09"/>'
        '<stop offset="45%" stop-color="#7c3aed" stop-opacity="0"/>'
        '</linearGradient></defs>',
        '<style>'
        '.bar { animation: grow 0.6s cubic-bezier(0.2, 0.7, 0.3, 1) backwards; '
        'transform-origin: center bottom; }'
        '@keyframes grow { from { transform: scaleY(0); opacity: 0.4; } '
        'to { transform: scaleY(1); opacity: 1; } }'
        '.cursor { animation: blink 1.1s steps(1) infinite; }'
        '@keyframes blink { 0%, 55% { opacity: 1; } 56%, 100% { opacity: 0; } }'
        '</style>',
        '<rect x="0.5" y="0.5" width="899" height="271" rx="12" fill="#0d0d16"/>',
        '<rect x="0.5" y="0.5" width="899" height="271" rx="12" fill="url(#sheen)"/>',
        '<rect x="0.5" y="0.5" width="899" height="271" rx="12" fill="none" '
        'stroke="#23233a" stroke-width="1"/>',
        '<g font-family="\'JetBrains Mono\', monospace">',
        f'<text x="32" y="40" fill="#e6e6ec" font-size="19" font-weight="700">{total:,} contributions</text>',
        '<text x="32" y="62" fill="#8b949e" font-size="12" letter-spacing="1">last 26 weeks &#183; weekly totals</text>',
        f'<text x="868" y="40" text-anchor="end" fill="#a78bfa" font-size="12" opacity="0.8">through {last:%d %b %Y}</text>',
    ]
    for value in (0, ceiling // 2, ceiling):
        y = 206 - value / ceiling * 116
        parts.extend([
            f'<path d="M64 {y:.1f}H868" stroke="#23233a"/>',
            f'<text x="50" y="{y + 4:.1f}" text-anchor="end" fill="#8b949e" font-size="11">{value}</text>',
        ])
    for index, (start, end, count) in enumerate(weeks):
        x = 69 + index * 30.5
        height = count / ceiling * 116
        color = "#c4b5fd" if index == 25 else "#7c3aed"
        if count:
            parts.append(
                f'<rect class="bar" style="animation-delay: {index * 0.045:.2f}s" '
                f'x="{x:.1f}" y="{206 - height:.1f}" width="20" '
                f'height="{height:.1f}" rx="2" fill="{color}">'
                f'<title>{start} to {end}: {count} contributions</title></rect>'
            )
        if index in (0, 5, 10, 15, 20, 25):
            parts.append(
                f'<text x="{x + 10:.1f}" y="229" text-anchor="middle" '
                f'fill="#8b949e" font-size="11">{start:%d %b}</text>'
            )
    parts.append('<text x="32" y="254" fill="#7c3aed" font-size="12" font-weight="700">$</text>')
    parts.append('<text x="50" y="254" fill="#8b949e" font-size="11">latest week may be partial</text>')
    parts.append('<rect class="cursor" x="222" y="243" width="7" height="14" fill="#c4b5fd" opacity="0.9"/>')
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
