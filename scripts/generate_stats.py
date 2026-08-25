import os
import math
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from xml.sax.saxutils import escape

import requests

# ============================================================
# YEABSIRA // BLACKOUT HUD
# A high-end, data-driven GitHub profile renderer.
# Theme: gold accents on a black/graphite background.
#
# Auth:
#   GitHub Actions -> GH_TOKEN -> GitHub REST API
#   GITHUB_TOKEN remains a local/testing fallback.
# ============================================================

USERNAME = "yeabsiragebre"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

REST_API = "https://api.github.com"

OUTPUT_DIR = Path("profile")
STATS_FILE = OUTPUT_DIR / "stats.svg"
LANGUAGES_FILE = OUTPUT_DIR / "top-langs.svg"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

session = requests.Session()
session.headers.update(HEADERS)

# ============================================================
# DESIGN TOKENS — gold on black
# ============================================================

BG = "#050505"
PANEL = "#0A0A0A"
PANEL_2 = "#0E0E0E"
WHITE = "#F5F1E6"
MUTED = "#8A8172"
DIM = "#4A453B"
GRID = "#6E6555"

GOLD = "#D4AF37"
GOLD_2 = "#F1C453"
GOLD_DIM = "#8C6D1F"
RED = "#E06C75"

# Language bar palette: gold family only, light to dark, so the
# whole card reads as a single coherent gold/black composition.
LANG_COLORS = [
    GOLD,
    GOLD_2,
    "#C9A227",
    "#B8860B",
    GOLD_DIM,
    "#E6C767",
    "#A67C00",
    "#7A5C00",
]

# ============================================================
# API
# ============================================================


def github_get(url, params=None):
    try:
        response = session.get(url, params=params, timeout=30)
        if not response.ok:
            print(f"[WARN] GET {response.status_code}: {url}")
            print(response.text[:300])
            return None
        return response.json()
    except requests.RequestException as exc:
        print(f"[WARN] Request failed: {exc}")
        return None


def get_user():
    data = github_get(f"{REST_API}/user") if TOKEN else None
    if data and data.get("login", "").lower() == USERNAME.lower():
        return data
    return github_get(f"{REST_API}/users/{USERNAME}")


def get_repositories():
    repos = []
    page = 1
    while True:
        data = github_get(
            f"{REST_API}/user/repos",
            params={
                "visibility": "all",
                "affiliation": "owner,collaborator,organization_member",
                "per_page": 100,
                "page": page,
                "sort": "updated",
            },
        )
        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1

    owned = [
        r
        for r in repos
        if r.get("owner", {}).get("login", "").lower() == USERNAME.lower()
    ]

    # If an authenticated call unexpectedly returned nothing, fall back to
    # public repositories so the card never renders as a dead panel.
    if not owned:
        public = (
            github_get(
                f"{REST_API}/users/{USERNAME}/repos",
                params={"per_page": 100, "sort": "updated"},
            )
            or []
        )
        owned = public

    print(f"[INFO] Repositories: {len(owned)}")
    return owned


def get_languages(repositories):
    totals = defaultdict(int)
    for i, repo in enumerate(repositories, 1):
        name = repo.get("name")
        if not name:
            continue
        data = github_get(f"{REST_API}/repos/{USERNAME}/{name}/languages")
        if isinstance(data, dict):
            for language, amount in data.items():
                totals[language] += amount
        print(f"[LANG {i}/{len(repositories)}] {name}")

    return dict(totals)


# ============================================================
# SVG PRIMITIVES
# ============================================================


def esc(value):
    return escape(str(value))


def text(
    x,
    y,
    value,
    size=14,
    fill=WHITE,
    weight=400,
    anchor="start",
    spacing=0,
    opacity=1,
    family="JetBrains Mono, DejaVu Sans Mono, monospace",
    letter_spacing=None,
):
    if letter_spacing is not None:
        spacing = letter_spacing
    return (
        f'<text x="{x}" y="{y}" font-family="{family}" '
        f'font-size="{size}px" font-weight="{weight}" '
        f'letter-spacing="{spacing}px" fill="{fill}" '
        f'fill-opacity="{opacity}" text-anchor="{anchor}">{esc(value)}</text>'
    )


def rect(x, y, w, h, fill, radius=8, stroke="none", stroke_opacity=0, opacity=1):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
        f'fill="{fill}" fill-opacity="{opacity}" stroke="{stroke}" '
        f'stroke-opacity="{stroke_opacity}"/>'
    )


def line(x1, y1, x2, y2, stroke=DIM, width=1, opacity=1):
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{stroke}" stroke-width="{width}" stroke-opacity="{opacity}"/>'
    )


def circle(cx, cy, r, fill, opacity=1, stroke="none", stroke_width=0):
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" '
        f'fill-opacity="{opacity}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
    )


# ============================================================
# SVG DESIGN SYSTEM
# ============================================================


def defs():
    return f"""
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#030303"/>
    <stop offset="55%" stop-color="#0A0A0A"/>
    <stop offset="100%" stop-color="#020202"/>
  </linearGradient>

  <linearGradient id="accentLine" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="{GOLD}" stop-opacity="0"/>
    <stop offset="18%" stop-color="{GOLD}" stop-opacity=".85"/>
    <stop offset="52%" stop-color="{GOLD_2}" stop-opacity=".9"/>
    <stop offset="82%" stop-color="{GOLD_DIM}" stop-opacity=".65"/>
    <stop offset="100%" stop-color="{GOLD_DIM}" stop-opacity="0"/>
  </linearGradient>

  <linearGradient id="bar" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="{GOLD}"/>
    <stop offset="100%" stop-color="{GOLD_2}"/>
  </linearGradient>

  <pattern id="microgrid" width="28" height="28" patternUnits="userSpaceOnUse">
    <path d="M28 0H0V28" fill="none" stroke="{GRID}" stroke-opacity=".035"/>
  </pattern>

  <pattern id="scan" width="4" height="8" patternUnits="userSpaceOnUse">
    <path d="M0 0H4" stroke="#FFFFFF" stroke-opacity=".012"/>
  </pattern>

  <filter id="glow" x="-100%" y="-100%" width="300%" height="300%">
    <feGaussianBlur stdDeviation="3" result="blur"/>
    <feMerge>
      <feMergeNode in="blur"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>

  <filter id="softGlow" x="-100%" y="-100%" width="300%" height="300%">
    <feGaussianBlur stdDeviation="18"/>
  </filter>

  <filter id="tinyGlow" x="-100%" y="-100%" width="300%" height="300%">
    <feGaussianBlur stdDeviation="1.8" result="blur"/>
    <feMerge>
      <feMergeNode in="blur"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>

  <style>
    .pulse {{ animation:pulse 2.8s ease-in-out infinite; }}
    .scanmove {{ animation:scanmove 7s linear infinite; }}
    .float {{ animation:float 8s ease-in-out infinite alternate; }}
    @keyframes pulse {{
      0%,100% {{ opacity:.35; }}
      50% {{ opacity:1; }}
    }}
    @keyframes scanmove {{
      from {{ transform:translateY(-100px); }}
      to {{ transform:translateY(720px); }}
    }}
    @keyframes float {{
      from {{ transform:translateX(-14px); }}
      to {{ transform:translateX(14px); }}
    }}
    .hudPulse {{ animation:hudPulse 3.2s ease-in-out infinite; }}
    .hudSweep {{ animation:hudSweep 6s linear infinite; }}
    .hudRotate {{ transform-origin:450px 310px; animation:hudRotate 24s linear infinite; }}
    .hudFlicker {{ animation:hudFlicker 4.5s ease-in-out infinite; }}
    @keyframes hudPulse {{
      0%,100% {{ opacity:.25; }}
      50% {{ opacity:.85; }}
    }}
    @keyframes hudSweep {{
      from {{ transform:translateX(-180px); opacity:0; }}
      12% {{ opacity:.7; }}
      50% {{ opacity:.35; }}
      88% {{ opacity:.7; }}
      to {{ transform:translateX(1180px); opacity:0; }}
    }}
    @keyframes hudRotate {{
      from {{ transform:rotate(0deg); }}
      to {{ transform:rotate(360deg); }}
    }}
    @keyframes hudFlicker {{
      0%,96%,100% {{ opacity:1; }}
      97% {{ opacity:.55; }}
      98% {{ opacity:.9; }}
    }}
  </style>
</defs>
"""


def corner_brackets(w, h, color=GOLD):
    # Wrapped in a group with the existing hudPulse keyframe so the frame
    # breathes gently — reuses the animation already defined in defs(),
    # nothing new added, nothing removed.
    s = 14
    segments = "".join(
        [
            line(18, 18, 18 + s, 18, color, 1, 0.8),
            line(18, 18, 18, 18 + s, color, 1, 0.8),
            line(w - 18 - s, 18, w - 18, 18, color, 1, 0.8),
            line(w - 18, 18, w - 18, 18 + s, color, 1, 0.8),
            line(18, h - 18, 18 + s, h - 18, color, 1, 0.8),
            line(18, h - 18 - s, 18, h - 18, color, 1, 0.8),
            line(w - 18 - s, h - 18, w - 18, h - 18, color, 1, 0.8),
            line(w - 18, h - 18 - s, w - 18, h - 18, color, 1, 0.8),
        ]
    )
    return f'<g class="hudPulse">{segments}</g>'


# ============================================================
# STATS CARD
# ============================================================


def _truncate(value, max_len=10):
    value = str(value)
    if len(value) <= max_len:
        return value
    return value[: max_len - 1] + "\u2026"


def generate_stats_svg(user, repositories, languages=None):
    WIDTH = 900
    HEIGHT = 620
    languages = languages or {}

    public_repositories = user.get("public_repos", 0)
    followers = user.get("followers", 0)
    following = user.get("following", 0)
    stars = sum(repo.get("stargazers_count", 0) for repo in repositories)
    forks = sum(repo.get("forks_count", 0) for repo in repositories)
    private_repositories = sum(1 for repo in repositories if repo.get("private"))
    open_issues = sum(repo.get("open_issues_count", 0) for repo in repositories)
    watched = sum(repo.get("watchers_count", 0) for repo in repositories)
    total_repos = public_repositories + private_repositories

    top_language = max(languages, key=languages.get) if languages else "N/A"
    avg_stars_per_repo = (stars / total_repos) if total_repos else 0.0

    cards = [
        (
            42,
            118,
            396,
            112,
            "REPOSITORIES",
            public_repositories,
            f"{private_repositories} PRIVATE",
            GOLD,
            0,
        ),
        (
            462,
            118,
            396,
            112,
            "FOLLOWERS",
            followers,
            f"{following} FOLLOWING",
            GOLD_2,
            1,
        ),
        (42, 246, 396, 112, "STARS", stars, "STARS ACROSS REPOS", GOLD, 2),
        (462, 246, 396, 112, "FORKS", forks, f"{open_issues} OPEN ISSUES", GOLD_2, 3),
    ]

    def advanced_tile(x, y, w, h, label, value, sub, accent, index):
        return f"""
        <g>
          <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14"
                fill="{PANEL}" stroke="#1F1B0F" stroke-width="1"/>
          <rect x="{x}" y="{y}" width="3" height="{h}" rx="2" fill="{accent}"/>
          <circle class="pulse" cx="{x + w - 25}" cy="{y + 25}" r="4"
                  fill="{accent}" filter="url(#glow)"
                  style="animation-delay:{index * 0.25}s"/>
          {text(x + 22, y + 31, label, 14, MUTED, 700, spacing=1.6)}
          {text(x + 22, y + 73, f"{value:,}", 42, WHITE, 800)}
          {text(x + 22, y + 98, sub, 13, DIM, 700, spacing=0.8)}
          <rect x="{x + w - 132}" y="{y + h - 15}" width="106" height="3" rx="1.5"
                fill="{accent}" opacity=".10"/>
          <rect class="hudSweep" x="{x + w - 132}" y="{y + h - 15}" width="106" height="3"
                rx="1.5" fill="{accent}" opacity=".80"
                style="animation-delay:{index * 0.45}s"/>
          <circle class="hudPulse" cx="{x + w - 20}" cy="{y + h - 15}" r="3"
                  fill="{accent}" style="animation-delay:{index * 0.35}s"/>
        </g>
        """

    # Six evenly spaced mini-columns in the telemetry strip.
    mini_x = [62, 191, 320, 449, 578, 707]

    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg"
     width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
  {defs()}

  <defs>
    <clipPath id="statsClip">
      <rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" rx="20"/>
    </clipPath>
  </defs>

  <g clip-path="url(#statsClip)">
    <rect width="{WIDTH}" height="{HEIGHT}" fill="#020202"/>
    <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#bg)"/>
    <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#microgrid)"/>
    <rect class="scanmove" x="0" y="-100" width="{WIDTH}" height="{HEIGHT}" fill="url(#scan)" opacity=".45"/>

    <circle class="float" cx="70" cy="80" r="130" fill="{GOLD}"
            opacity=".03" filter="url(#softGlow)"/>
    <circle class="float" cx="840" cy="520" r="150" fill="{GOLD_2}"
            opacity=".02" filter="url(#softGlow)"/>

    <rect x="1" y="1" width="898" height="618" rx="20"
          fill="none" stroke="#332B14" stroke-opacity=".9"/>
    {corner_brackets(WIDTH, HEIGHT)}

    <rect x="42" y="27" width="816" height="2"
          fill="url(#accentLine)" filter="url(#glow)"/>

    <circle class="pulse" cx="52" cy="60" r="6" fill="{GOLD}" filter="url(#glow)"/>{text(68, 66, "SYSTEM ONLINE", 25, WHITE, 700, spacing=1.3)}
    {text(42, 96, "LIVE GITHUB DATA // PROFILE TELEMETRY", 12, MUTED, 700, spacing=1.6)}

    <!-- 2 x 2 primary statistics -->
    {"".join(advanced_tile(*card) for card in cards)}

    <!-- Secondary telemetry -->
    <rect x="42" y="382" width="816" height="168" rx="14"
          fill="#070605" stroke="#1B1710"/>

    {text(62, 414, "LIVE REPOSITORY TELEMETRY", 14, WHITE, 800, spacing=1.5)}
    {text(838, 414, "SYNCED", 12, GOLD, 700, "end", spacing=1.2)}

    {text(mini_x[0], 450, "PUBLIC", 11, DIM, 700, spacing=1.1)}
    {text(mini_x[0], 481, public_repositories, 25, WHITE, 800)}

    {text(mini_x[1], 450, "PRIVATE", 11, DIM, 700, spacing=1.1)}
    {text(mini_x[1], 481, private_repositories, 25, WHITE, 800)}

    {text(mini_x[2], 450, "WATCHERS", 11, DIM, 700, spacing=1.1)}
    {text(mini_x[2], 481, watched, 25, WHITE, 800)}

    {text(mini_x[3], 450, "OPEN ISSUES", 11, DIM, 700, spacing=1.1)}
    {text(mini_x[3], 481, open_issues, 25, WHITE, 800)}

    {text(mini_x[4], 450, "TOTAL REPOS", 11, DIM, 700, spacing=1.1)}
    {text(mini_x[4], 481, total_repos, 25, GOLD, 800)}

    {text(mini_x[5], 450, "TOP LANG", 11, DIM, 700, spacing=1.1)}
    {text(mini_x[5], 481, _truncate(top_language).upper(), 18, GOLD, 800)}

    <line x1="62" y1="507" x2="838" y2="507"
          stroke="#201B10" stroke-width="1"/>

    {text(62, 532, "AVG STARS/REPO", 10, DIM, 700, spacing=1.0)}
    {text(200, 532, f"{avg_stars_per_repo:.1f}", 11, WHITE, 700)}
    {text(310, 532, "AUTHENTICATED", 10, DIM, 700, spacing=1.0)}
    {text(425, 532, "GH_TOKEN", 11, WHITE, 700)}
    {text(575, 532, "STATUS", 10, DIM, 700, spacing=1.0)}
    {text(630, 532, "LIVE", 11, GOLD, 800)}

    {text(42, 586, "GITHUB PROFILE INTELLIGENCE // LIVE DATA LAYER", 13, WHITE, 800, spacing=1.1)}
    {text(858, 586, "ONLINE", 13, GOLD, 800, "end", spacing=1.2)}
  </g>
</svg>
"""
    return svg


# ============================================================
# LANGUAGE CARD
# ============================================================


def generate_languages_svg(languages):
    WIDTH = 900
    HEIGHT = 620

    total_bytes = sum(languages.values())
    language_data = []

    if total_bytes:
        for language, amount in sorted(
            languages.items(), key=lambda item: item[1], reverse=True
        )[:8]:
            percentage = amount / total_bytes * 100
            language_data.append((language, percentage, amount))

    rows = []
    y = 140
    row_height = 50
    bar_x = 245
    bar_width = 575

    for index, (language, percentage, amount) in enumerate(language_data):
        color = LANG_COLORS[index % len(LANG_COLORS)]
        fill_width = max(4, int(bar_width * percentage / 100))
        rank = index + 1
        marker_x = bar_x + fill_width

        rows.append(f"""
        <g>
          <circle cx="54" cy="{y + 13}" r="12" fill="#0B0A08"
                  stroke="{color}" stroke-opacity=".35"/>
          {text(54, y + 17, f"{rank:02d}", 8, color, 800, "middle", spacing=0.5)}
          {text(78, y + 15, language.upper(), 15, WHITE, 700, spacing=0.8)}
          {text(78, y + 36, format_bytes(amount), 11, DIM, 700)}

          <rect x="{bar_x}" y="{y + 1}" width="{bar_width}" height="12"
                rx="6" fill="#0B0A08" stroke="#1B1710" stroke-width="1"/>
          <rect x="{bar_x}" y="{y + 1}" width="{fill_width}" height="12"
                rx="6" fill="{color}" filter="url(#glow)"/>
          <rect x="{bar_x}" y="{y + 1}" width="{fill_width}" height="3"
                rx="1.5" fill="#FFFFFF" opacity=".10"/>

          <circle cx="{marker_x}" cy="{y + 7}" r="3.2" fill="{color}"
                  filter="url(#tinyGlow)" class="pulse"
                  style="animation-delay:{index * 0.22}s"/>
          <line x1="{bar_x + bar_width * 0.25}" y1="{y + 16}"
                x2="{bar_x + bar_width * 0.25}" y2="{y + 20}"
                stroke="#2B2415" stroke-width="1"/>
          <line x1="{bar_x + bar_width * 0.50}" y1="{y + 16}"
                x2="{bar_x + bar_width * 0.50}" y2="{y + 20}"
                stroke="#2B2415" stroke-width="1"/>
          <line x1="{bar_x + bar_width * 0.75}" y1="{y + 16}"
                x2="{bar_x + bar_width * 0.75}" y2="{y + 20}"
                stroke="#2B2415" stroke-width="1"/>

          {text(850, y + 12, f"{percentage:.1f}%", 13, color, 700, "end")}

          <line x1="48" y1="{y + 41}" x2="850" y2="{y + 41}"
                stroke="#161208" stroke-width="1"/>
        </g>
        """)
        y += row_height

    if not language_data:
        rows.append(text(48, 145, "NO LANGUAGE DATA RETURNED", 14, RED, 700))
        rows.append(text(48, 168, "CHECK GH_TOKEN REPOSITORY ACCESS", 11, MUTED, 700))

    return f"""
<svg xmlns="http://www.w3.org/2000/svg"
     width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">

  {defs()}

  <defs>
    <clipPath id="languageClip">
      <rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" rx="20"/>
    </clipPath>
  </defs>

  <g clip-path="url(#languageClip)">
    <rect width="{WIDTH}" height="{HEIGHT}" fill="#020202"/>
    <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#bg)"/>
    <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#microgrid)"/>
    <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#scan)"/>

    <g class="hudRotate" opacity=".11">
      <circle cx="450" cy="620" r="340" fill="none"
              stroke="{GOLD}" stroke-width="1"/>
      <circle cx="450" cy="620" r="300" fill="none"
              stroke="{GOLD_DIM}" stroke-width="1"/>
      <circle cx="450" cy="620" r="260" fill="none"
              stroke="{GOLD_2}" stroke-width="1" stroke-dasharray="2 10"/>
    </g>

    <circle cx="820" cy="80" r="130" fill="{GOLD_DIM}"
            opacity=".025" filter="url(#softGlow)"/>
    <circle cx="70" cy="550" r="120" fill="{GOLD}"
            opacity=".025" filter="url(#softGlow)"/>

    <line x1="42" y1="126" x2="858" y2="126"
          stroke="#241F10" stroke-width="1"/>
    <line x1="42" y1="129" x2="310" y2="129"
          stroke="{GOLD}" stroke-width="1" stroke-opacity=".45"/>

    <rect x="1" y="1" width="898" height="618" rx="20"
          fill="none" stroke="#332B14" stroke-opacity=".9"/>

    {corner_brackets(WIDTH, HEIGHT)}

    <rect x="42" y="27" width="816" height="2"
          fill="url(#accentLine)" filter="url(#glow)"/>

    {text(42, 67, "LANGUAGE MATRIX", 28, WHITE, 800, spacing=1.4)}
    {text(42, 96, "CODEBASE // BYTE DISTRIBUTION // LIVE REPOSITORY ANALYSIS", 12, MUTED, 700, spacing=1.6)}

    <circle class="pulse" cx="782" cy="53" r="4"
            fill="{GOLD}" filter="url(#glow)"/>
    {text(852, 56, "SYSTEM ONLINE", 8, GOLD, 700, "end", spacing=1.1)}
    {text(852, 75, "LANGUAGE ANALYSIS", 7, DIM, 700, "end", spacing=1)}

    {text(48, 116, f"{len(language_data)} PRIMARY LANGUAGES", 12, MUTED, 700, spacing=1.2)}
    {text(850, 116, f"{len(languages)} TOTAL DETECTED", 12, DIM, 700, "end", spacing=1)}
    {text(245, 133, "DISTRIBUTION", 7, DIM, 700, spacing=1.1)}
    {text(820, 133, "RELATIVE SHARE", 7, DIM, 700, "end", spacing=1.1)}

    {"".join(rows)}

    <rect x="42" y="570" width="816" height="1" fill="#241F10"/>
    <rect x="42" y="578" width="816" height="28" rx="8"
          fill="#070605" stroke="#191509"/>

    {text(58, 596, "LANGUAGE DISTRIBUTION", 10, WHITE, 700, spacing=0.9)}
    {text(250, 596, "BYTE WEIGHTED", 9, DIM, 700, spacing=1.0)}
    {text(430, 596, f"{format_bytes(total_bytes)} TOTAL", 9, DIM, 700, spacing=0.8)}
    {text(858, 596, "ONLINE", 10, GOLD, 700, "end", spacing=1.1)}

  </g>
</svg>
"""


def format_bytes(value):
    value = float(value)
    if value >= 1024**3:
        return f"{value / (1024**3):.1f} GB"
    if value >= 1024**2:
        return f"{value / (1024**2):.1f} MB"
    if value >= 1024:
        return f"{value / 1024:.1f} KB"
    return f"{int(value)} B"


def generate_combined_svg(user, repositories, languages):
    stats_svg = generate_stats_svg(user, repositories, languages)
    language_svg = generate_languages_svg(languages)

    stats_match = re.search(r"<svg[^>]*>(.*)</svg>\s*$", stats_svg, flags=re.DOTALL)
    language_match = re.search(
        r"<svg[^>]*>(.*)</svg>\s*$", language_svg, flags=re.DOTALL
    )

    if not stats_match or not language_match:
        raise RuntimeError("Could not compose the generated SVG cards.")

    stats_content = stats_match.group(1)
    language_content = language_match.group(1)

    WIDTH = 900
    CARD_HEIGHT = 620
    GAP = 4
    HEIGHT = CARD_HEIGHT * 2 + GAP

    return f"""<svg xmlns="http://www.w3.org/2000/svg"
    width="{WIDTH}" height="{HEIGHT}"
    viewBox="0 0 {WIDTH} {HEIGHT}">
    <defs>
      <linearGradient id="unifiedFlow" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="{GOLD}" stop-opacity="0"/>
        <stop offset="20%" stop-color="{GOLD}" stop-opacity=".45"/>
        <stop offset="50%" stop-color="{GOLD_2}" stop-opacity=".7"/>
        <stop offset="80%" stop-color="{GOLD_DIM}" stop-opacity=".45"/>
        <stop offset="100%" stop-color="{GOLD_DIM}" stop-opacity="0"/>
      </linearGradient>
      <style>
        .flow {{ animation: flow 5s linear infinite; }}
        .blink {{ animation: blink 1.8s ease-in-out infinite; }}
        @keyframes flow {{
          from {{ transform: translateX(-220px); opacity:.15; }}
          50% {{ opacity:1; }}
          to {{ transform: translateX(1120px); opacity:.15; }}
        }}
        @keyframes blink {{
          0%,100% {{ opacity:.35; }}
          50% {{ opacity:1; }}
        }}
      </style>
    </defs>

    <rect width="{WIDTH}" height="{HEIGHT}" fill="#020202"/>
    <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#bg)"/>
    <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#microgrid)"/>
    <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#scan)"/>

    <g class="hudRotate" opacity=".11">
      <circle cx="450" cy="620" r="340" fill="none"
              stroke="{GOLD}" stroke-width="1"/>
      <circle cx="450" cy="620" r="300" fill="none"
              stroke="{GOLD_DIM}" stroke-width="1"/>
    </g>

    <rect class="hudSweep" x="-180" y="0" width="180" height="{HEIGHT}"
          fill="url(#accentLine)" opacity=".035"/>

    <g transform="translate(0,0)">
      {stats_content}
    </g>

    <line x1="42" y1="{CARD_HEIGHT + GAP // 2}" x2="858" y2="{CARD_HEIGHT + GAP // 2}"
          stroke="#1B1710" stroke-width="1"/>
    <g class="flow">
      <rect x="-220" y="{CARD_HEIGHT + GAP // 2 - 1}" width="220" height="2"
            rx="1" fill="url(#unifiedFlow)" filter="url(#glow)"/>
    </g>
    <circle class="blink" cx="450" cy="{CARD_HEIGHT + GAP // 2}" r="2.5"
            fill="{GOLD}" filter="url(#tinyGlow)"/>

    <g transform="translate(0,{CARD_HEIGHT + GAP})">
      {language_content}
    </g>
</svg>
"""


# ============================================================
# MAIN
# ============================================================


def main():
    print("=" * 68)
    print("  YEABSIRA // BLACKOUT HUD // GITHUB DATA ENGINE")
    print("=" * 68)

    if not TOKEN:
        raise RuntimeError(
            "No GitHub token found. Set GH_TOKEN in GitHub Actions "
            "or GITHUB_TOKEN for local testing."
        )

    print("[1/4] Authenticating...")
    user = get_user()
    if not user:
        raise RuntimeError("Could not retrieve GitHub user.")
    print(f"[OK] Authenticated API identity: {user.get('login', 'unknown')}")

    print("[2/4] Loading repositories...")
    repositories = get_repositories()

    print("[3/4] Calculating language distribution...")
    languages = get_languages(repositories)
    print(f"[OK] Languages discovered: {len(languages)}")

    print("[4/4] Rendering Blackout HUD...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    STATS_FILE.write_text(
        generate_combined_svg(user, repositories, languages),
        encoding="utf-8",
    )
    LANGUAGES_FILE.write_text(
        generate_languages_svg(languages),
        encoding="utf-8",
    )

    print("=" * 68)
    print("  GENERATION COMPLETE")
    print(f"  -> {STATS_FILE}")
    print(f"  -> {LANGUAGES_FILE} (standalone compatibility copy)")
    print("  DESIGN: BLACK / GRAPHITE / GOLD")
    print("  DATA:   LIVE GITHUB REST API")
    print("  AUTH:   GH_TOKEN")
    print("=" * 68)


if __name__ == "__main__":
    main()
