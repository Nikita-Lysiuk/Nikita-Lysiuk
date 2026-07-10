#!/usr/bin/env python3
"""Render custom project cards (profile/card-*.svg) for the README.

Star counts and primary language come from the GitHub API; taglines are
curated here so cards never show "No description provided".
Run: GITHUB_TOKEN=<token> python3 scripts/render_cards.py
"""
import html
import json
import os
import urllib.request

USER = "Nikita-Lysiuk"
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "profile")

BG = "#0d0d16"
BORDER = "#23233a"
VIOLET = "#7c3aed"
VIOLET_LT = "#a78bfa"
VIOLET_XLT = "#c4b5fd"
TEXT = "#e6e6ec"
GREY = "#8b949e"

LANG_COLORS = {
    "Rust": "#dea584",
    "C++": "#f34b7d",
    "C": "#555555",
    "Java": "#b07219",
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Python": "#3572A5",
    "Kotlin": "#A97BFF",
}

REPOS = [
    {
        "name": "Fluid-Engine",
        "featured": True,
        "tag": "diploma project",
        "tagline": "Real-time fluid simulation in Rust with Vulkan rendering — "
                   "compute pipelines, CPU/GPU parallelism, performance first.",
    },
    {
        "name": "Vinyl-Store",
        "tagline": "REST API for a vinyl record store — auth, orders, reviews, "
                   "Stripe payments, AWS S3.",
    },
    {
        "name": "egypt_adventure",
        "tagline": "Roguelike survival horror in C++ — procedural catacombs "
                   "where light itself is a resource.",
    },
    {
        "name": "PixelPatternsAI",
        "tagline": "A neural network built from scratch in pure NumPy — "
                   "no frameworks, just the math.",
    },
    {
        "name": "spring-library",
        "tagline": "Library platform backend in TypeScript — clean "
                   "architecture, books that find their readers.",
    },
]


def fetch(repo):
    req = urllib.request.Request(f"https://api.github.com/repos/{USER}/{repo}")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        return data.get("stargazers_count", 0), data.get("language") or ""
    except Exception as e:  # keep rendering with placeholders on API failure
        print(f"  warn: could not fetch {repo}: {e}")
        return 0, ""


def wrap(text, max_chars):
    words, lines, cur = text.split(), [], ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if len(cand) <= max_chars:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:2]


def head(w, h):
    return f'''<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="sheen" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{VIOLET}" stop-opacity="0.09"/>
      <stop offset="45%" stop-color="{VIOLET}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" fill="{BG}"/>
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" fill="url(#sheen)"/>
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" fill="none" stroke="{BORDER}" stroke-width="1"/>
'''


def lang_stars(x, y, lang, stars, anchor_end_x=None):
    parts = []
    if lang:
        color = LANG_COLORS.get(lang, GREY)
        parts.append(f'<circle cx="{x + 5}" cy="{y - 4}" r="5" fill="{color}"/>')
        parts.append(f'<text x="{x + 18}" y="{y}" font-family="\'JetBrains Mono\', monospace" font-size="11.5" fill="{GREY}">{html.escape(lang)}</text>')
    if stars > 0 and anchor_end_x:
        parts.append(f'<text x="{anchor_end_x}" y="{y}" text-anchor="end" font-family="\'JetBrains Mono\', monospace" font-size="11.5" fill="{VIOLET_LT}">&#9733; {stars}</text>')
    return "".join(parts)


def card(repo, stars, lang):
    W, H = 440, 150
    name = html.escape(repo["name"])
    lines = wrap(repo["tagline"], 54)
    svg = head(W, H)
    svg += f'  <text x="24" y="40" font-family="\'JetBrains Mono\', monospace" font-size="14" fill="{VIOLET}" font-weight="700">&#10095;</text>\n'
    svg += f'  <text x="42" y="40" font-family="\'JetBrains Mono\', monospace" font-size="15" font-weight="700" fill="{TEXT}">{name}</text>\n'
    for i, ln in enumerate(lines):
        svg += f'  <text x="24" y="{72 + i * 19}" font-family="\'JetBrains Mono\', monospace" font-size="11.5" fill="{GREY}">{html.escape(ln)}</text>\n'
    svg += "  " + lang_stars(24, 126, lang, stars, anchor_end_x=352) + "\n"
    svg += f'  <text x="416" y="126" text-anchor="end" font-family="\'JetBrains Mono\', monospace" font-size="11" fill="{VIOLET_LT}" opacity="0.8">view &#8594;</text>\n'
    svg += "</svg>\n"
    return svg


def featured_card(repo, stars, lang):
    W, H = 900, 176
    name = html.escape(repo["name"])
    tag = html.escape(repo.get("tag", "featured"))
    lines = wrap(repo["tagline"], 92)
    tag_w = round(44 + 7.8 * (len(tag) + 10))
    svg = head(W, H)
    svg += f'''  <text x="32" y="52" font-family="'JetBrains Mono', monospace" font-size="18" fill="{VIOLET}" font-weight="700">&#10095;</text>
  <text x="54" y="52" font-family="'JetBrains Mono', monospace" font-size="20" font-weight="700" fill="{TEXT}">{name}</text>
  <rect x="{W - 32 - tag_w}" y="30" width="{tag_w}" height="28" rx="14" fill="{VIOLET}" opacity="0.16"/>
  <rect x="{W - 32 - tag_w}" y="30" width="{tag_w}" height="28" rx="14" fill="none" stroke="{VIOLET_LT}" stroke-width="1" opacity="0.6"/>
  <circle cx="{W - 32 - tag_w + 16}" cy="44" r="4" fill="{VIOLET_XLT}">
    <animate attributeName="opacity" values="0.3;1;0.3" dur="2s" repeatCount="indefinite"/>
  </circle>
  <text x="{W - 32 - tag_w + 28}" y="48" font-family="'JetBrains Mono', monospace" font-size="11" fill="{VIOLET_XLT}" letter-spacing="1">active // {tag}</text>
'''
    for i, ln in enumerate(lines):
        svg += f'  <text x="32" y="{92 + i * 21}" font-family="\'JetBrains Mono\', monospace" font-size="12.5" fill="{GREY}">{html.escape(ln)}</text>\n'
    svg += "  " + lang_stars(32, 148, lang, stars, anchor_end_x=760) + "\n"
    svg += f'  <text x="868" y="148" text-anchor="end" font-family="\'JetBrains Mono\', monospace" font-size="11.5" fill="{VIOLET_LT}" opacity="0.8">view repo &#8594;</text>\n'
    svg += "</svg>\n"
    return svg


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for repo in REPOS:
        stars, lang = fetch(repo["name"])
        svg = featured_card(repo, stars, lang) if repo.get("featured") else card(repo, stars, lang)
        path = os.path.join(OUT_DIR, f"card-{repo['name']}.svg")
        with open(path, "w") as f:
            f.write(svg)
        print(f"wrote {path} (lang={lang or '?'}, stars={stars})")


if __name__ == "__main__":
    main()
