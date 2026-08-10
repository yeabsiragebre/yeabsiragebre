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
#
# Auth:
#   GitHub Actions -> GH_TOKEN -> GitHub REST/GraphQL API
#   GITHUB_TOKEN remains a local/testing fallback.
# ============================================================

USERNAME = "yeabsiragebre"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

REST_API = "https://api.github.com"
GRAPHQL_API = "https://api.github.com/graphql"

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
# DESIGN TOKENS
# ============================================================

BG = "#030507"
PANEL = "#080B0F"
PANEL_2 = "#0B1015"
WHITE = "#F4F7F8"
MUTED = "#69757E"
DIM = "#364149"
GRID = "#8EA3AE"
CYAN = "#00F5D4"
CYAN_2 = "#00C2FF"
LIME = "#B7FF4A"
VIOLET = "#9B7BFF"
MAGENTA = "#FF4FD8"
ORANGE = "#FF9D3D"
RED = "#FF476F"

LANG_COLORS = [
    CYAN, VIOLET, MAGENTA, LIME, CYAN_2, ORANGE, "#6EE7FF", "#C084FC"
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


def github_graphql(query, variables=None):
    if not TOKEN:
        return None
    try:
        response = session.post(
            GRAPHQL_API,
            json={"query": query, "variables": variables or {}},
            timeout=30,
        )
        if not response.ok:
            print(f"[WARN] GraphQL {response.status_code}")
            print(response.text[:500])
            return None
        payload = response.json()
        if payload.get("errors"):
            print(f"[WARN] GraphQL errors: {payload['errors']}")
            return None
        return payload.get("data")
    except requests.RequestException as exc:
        print(f"[WARN] GraphQL request failed: {exc}")
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
        r for r in repos
        if r.get("owner", {}).get("login", "").lower() == USERNAME.lower()
    ]

    # If an authenticated call unexpectedly returned nothing, fall back to
    # public repositories so the card never renders as a dead panel.
    if not owned:
        public = github_get(
            f"{REST_API}/users/{USERNAME}/repos",
            params={"per_page": 100, "sort": "updated"},
        ) or []
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


def get_contribution_calendar():
    """Return real contribution-day counts from GitHub's contribution calendar."""
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=364)

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                contributionLevel
              }
            }
          }
        }
      }
    }
    """

    data = github_graphql(
        query,
        {
            "login": USERNAME,
            "from": f"{start.isoformat()}T00:00:00Z",
            "to": f"{end.isoformat()}T23:59:59Z",
        },
    )

    daily = {}
    total = 0

    try:
        calendar = data["user"]["contributionsCollection"]["contributionCalendar"]
        total = calendar.get("totalContributions", 0)
        for week in calendar.get("weeks", []):
            for day in week.get("contributionDays", []):
                daily[day["date"]] = day.get("contributionCount", 0)
    except (TypeError, KeyError):
        print("[WARN] Contribution calendar unavailable.")
        return {}, 0

    return daily, total


# ============================================================
# SVG PRIMITIVES
# ============================================================

def esc(value):
    return escape(str(value))


def text(x, y, value, size=14, fill=WHITE, weight=400,
         anchor="start", spacing=0, opacity=1,
         family="JetBrains Mono, DejaVu Sans Mono, monospace",
         letter_spacing=None):
    if letter_spacing is not None:
        spacing = letter_spacing
    return (
        f'<text x="{x}" y="{y}" font-family="{family}" '
        f'font-size="{size}px" font-weight="{weight}" '
        f'letter-spacing="{spacing}px" fill="{fill}" '
        f'fill-opacity="{opacity}" text-anchor="{anchor}">{esc(value)}</text>'
    )


def rect(x, y, w, h, fill, radius=8, stroke="none", stroke_opacity=0,
         opacity=1):
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

def defs(seed=0):
    # Seed changes the ambient animation phase from one generation to another.
    return f"""
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#020304"/>
    <stop offset="48%" stop-color="#070B0E"/>
    <stop offset="100%" stop-color="#020405"/>
  </linearGradient>

  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="{CYAN}" stop-opacity="0"/>
    <stop offset="20%" stop-color="{CYAN}" stop-opacity=".95"/>
    <stop offset="55%" stop-color="{VIOLET}" stop-opacity=".9"/>
    <stop offset="82%" stop-color="{MAGENTA}" stop-opacity=".75"/>
    <stop offset="100%" stop-color="{MAGENTA}" stop-opacity="0"/>
  </linearGradient>

  <linearGradient id="cyanSweep" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="{CYAN}" stop-opacity=".05"/>
    <stop offset="48%" stop-color="{CYAN}" stop-opacity=".9"/>
    <stop offset="100%" stop-color="{CYAN_2}" stop-opacity=".05"/>
  </linearGradient>

  <linearGradient id="violetSweep" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="{VIOLET}" stop-opacity=".04"/>
    <stop offset="50%" stop-color="{MAGENTA}" stop-opacity=".8"/>
    <stop offset="100%" stop-color="{VIOLET}" stop-opacity=".04"/>
  </linearGradient>

  <pattern id="microgrid" width="24" height="24" patternUnits="userSpaceOnUse">
    <path d="M24 0H0V24" fill="none" stroke="{GRID}" stroke-opacity=".055"/>
  </pattern>

  <pattern id="scan" width="6" height="6" patternUnits="userSpaceOnUse">
    <path d="M0 0H6" stroke="#FFFFFF" stroke-opacity=".018"/>
  </pattern>

  <filter id="glowC" x="-100%" y="-100%" width="300%" height="300%">
    <feGaussianBlur stdDeviation="3" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>

  <filter id="glowS" x="-100%" y="-100%" width="300%" height="300%">
    <feGaussianBlur stdDeviation="13"/>
  </filter>

  <filter id="glowXL" x="-100%" y="-100%" width="300%" height="300%">
    <feGaussianBlur stdDeviation="28"/>
  </filter>

  <clipPath id="clip900"><rect x="0" y="0" width="900" height="540" rx="24"/></clipPath>
  <clipPath id="clip720"><rect x="0" y="0" width="720" height="500" rx="24"/></clipPath>

  <style>
    .blink {{ animation: blink 2.2s ease-in-out infinite; }}
    .pulse {{ animation: pulse 3.4s ease-in-out infinite; transform-origin:center; }}
    .drift {{ animation: drift 9s ease-in-out infinite alternate; }}
    .scanmove {{ animation: scanmove 5s linear infinite; }}
    @keyframes blink {{ 0%,100% {{ opacity:.25; }} 50% {{ opacity:1; }} }}
    @keyframes pulse {{ 0%,100% {{ opacity:.35; transform:scale(.96); }} 50% {{ opacity:.95; transform:scale(1.04); }} }}
    @keyframes drift {{ from {{ transform:translateX(-18px); }} to {{ transform:translateX(18px); }} }}
    @keyframes scanmove {{ from {{ transform:translateY(-80px); }} to {{ transform:translateY(600px); }} }}
  </style>
</defs>
"""


def corner_brackets(w, h, color=CYAN):
    s = 18
    return "".join([
        line(16, 16, 16+s, 16, color, 2, .9),
        line(16, 16, 16, 16+s, color, 2, .9),
        line(w-16-s, 16, w-16, 16, color, 2, .9),
        line(w-16, 16, w-16, 16+s, color, 2, .9),
        line(16, h-16, 16+s, h-16, color, 2, .9),
        line(16, h-16-s, 16, h-16, color, 2, .9),
        line(w-16-s, h-16, w-16, h-16, color, 2, .9),
        line(w-16, h-16-s, w-16, h-16, color, 2, .9),
    ])


def background(w, h, seed):
    phase = seed % 360
    return f"""
      <rect width="{w}" height="{h}" fill="url(#bg)"/>
      <rect width="{w}" height="{h}" fill="url(#microgrid)"/>
      <rect width="{w}" height="{h}" fill="url(#scan)"/>

      <circle class="drift" cx="120" cy="75" r="95" fill="{CYAN}"
              opacity=".045" filter="url(#glowXL)"/>
      <circle class="pulse" cx="790" cy="430" r="105" fill="{MAGENTA}"
              opacity=".035" filter="url(#glowXL)"/>

      <g opacity=".22">
        <path d="M0 86H{w}" stroke="{CYAN}" stroke-opacity=".08"/>
        <path d="M0 430H{w}" stroke="{VIOLET}" stroke-opacity=".07"/>
      </g>

      <rect class="scanmove" x="0" y="-100" width="{w}" height="70"
            fill="url(#cyanSweep)" opacity=".14"/>
      <g transform="rotate({phase} 450 270)" opacity=".025">
        <circle cx="450" cy="270" r="240" fill="none" stroke="{CYAN}" stroke-width="1"/>
        <circle cx="450" cy="270" r="330" fill="none" stroke="{MAGENTA}" stroke-width="1"/>
      </g>
"""


# ============================================================
# STATS CARD
# ============================================================

def stat_tile(x, y, w, h, label, value, sub, accent, index):
    return f"""
      <g>
        {rect(x, y, w, h, PANEL, 12, "#1C2930", .8)}
        <rect x="{x}" y="{y}" width="3" height="{h}" rx="1.5" fill="{accent}"/>
        <circle class="pulse" cx="{x+w-18}" cy="{y+18}" r="3"
                fill="{accent}" filter="url(#glowC)" style="animation-delay:{index*.3}s"/>
        {text(x+17, y+27, label.upper(), 7, MUTED, 700, spacing=1.6)}
        {text(x+17, y+62, value, 27, WHITE, 700)}
        {text(x+17, y+83, sub.upper(), 7, DIM, 700, spacing=.8)}
      </g>
    """


def sparkline(values, x, y, w, h, color=CYAN):
    if not values:
        return ""
    vmax = max(values) or 1
    vmin = min(values)
    span = max(vmax - vmin, 1)
    pts = []
    for i, value in enumerate(values):
        px = x + (i / max(len(values)-1, 1)) * w
        py = y + h - ((value-vmin)/span) * h
        pts.append(f"{px:.1f},{py:.1f}")
    points = " ".join(pts)
    return f"""
      <polyline points="{points}" fill="none" stroke="{color}"
        stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
        filter="url(#glowC)"/>
      <polyline points="{points}" fill="none" stroke="{color}"
        stroke-opacity=".18" stroke-width="8" stroke-linecap="round"/>
    """


def contribution_matrix(daily, x=42, y=305, cols=53, rows=7, cell=9, gap=3):
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=363)
    max_count = max(daily.values(), default=1)

    palette = ["#0A0F12", "#12352F", "#11604F", "#00A887", CYAN, LIME]
    out = []

    for day_index in range(364):
        date = start + timedelta(days=day_index)
        count = daily.get(str(date), 0)
        if count <= 0:
            level = 0
        else:
            ratio = count / max_count
            level = min(5, max(1, int(math.ceil(ratio * 5))))

        col = day_index // 7
        row = day_index % 7
        px = x + col * (cell + gap)
        py = y + row * (cell + gap)

        out.append(
            f'<rect x="{px}" y="{py}" width="{cell}" height="{cell}" rx="2" '
            f'fill="{palette[level]}" opacity=".94">'
            f'<title>{date.isoformat()} · {count} contributions</title></rect>'
        )

    return "".join(out)


def generate_stats_svg(user, repositories, daily, total_contributions):
    """
    Generate a larger, readable dashboard card.

    Layout:
      - 2x2 stat cards so the four headline metrics remain readable.
      - Large contribution matrix with room to breathe.
      - Compact 30-day activity telemetry.
      - Prominent ONLINE status that never overlaps the header.
      - Same canvas size as the language card for README side-by-side use.
    """
    WIDTH = 900
    HEIGHT = 620

    public_repositories = user.get("public_repos", 0)
    followers = user.get("followers", 0)
    following = user.get("following", 0)

    stars = sum(repo.get("stargazers_count", 0) for repo in repositories)
    forks = sum(repo.get("forks_count", 0) for repo in repositories)

    private_repositories = sum(
        1 for repo in repositories if repo.get("private")
    )

    total_activity = total_contributions

    # Recent 30-day telemetry.
    today = datetime.now(timezone.utc).date()
    recent_days = [today - timedelta(days=i) for i in range(29, -1, -1)]
    recent_values = [
        daily.get(str(day), 0)
        for day in recent_days
    ]
    recent_total = sum(recent_values)
    recent_peak = max(recent_values, default=1)

    # Keep the matrix visually dense but readable.
    matrix = activity_grid_large(daily, WIDTH=900)

    # Build the 30-day mini graph.
    graph_x = 48
    graph_y = 524
    graph_w = 804
    graph_h = 44

    graph_points = []
    for i, value in enumerate(recent_values):
        x = graph_x + (i / max(1, len(recent_values) - 1)) * graph_w
        y = graph_y + graph_h - (
            (value / max(1, recent_peak)) * graph_h
        )
        graph_points.append(f"{x:.1f},{y:.1f}")

    graph_polyline = " ".join(graph_points)

    # Dynamic status text.
    if recent_total >= 50:
        activity_state = "HIGH ACTIVITY"
    elif recent_total >= 15:
        activity_state = "ACTIVE"
    elif recent_total > 0:
        activity_state = "LOW ACTIVITY"
    else:
        activity_state = "STANDBY"

    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg"
     width="{WIDTH}" height="{HEIGHT}"
     viewBox="0 0 {WIDTH} {HEIGHT}">

    {defs()}

    <defs>
        <linearGradient id="blackPanel" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#05070A"/>
            <stop offset="55%" stop-color="#080B10"/>
            <stop offset="100%" stop-color="#030406"/>
        </linearGradient>

        <linearGradient id="statGlow" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#22D3EE"/>
            <stop offset="50%" stop-color="#818CF8"/>
            <stop offset="100%" stop-color="#D946EF"/>
        </linearGradient>

        <linearGradient id="graphGlow" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#22D3EE"/>
            <stop offset="100%" stop-color="#A78BFA"/>
        </linearGradient>

        <filter id="strongGlow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="4" result="blur"/>
            <feMerge>
                <feMergeNode in="blur"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>

        <filter id="softBlackGlow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="24"/>
        </filter>

        <clipPath id="statsClip">
            <rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" rx="22"/>
        </clipPath>
    </defs>

    <g clip-path="url(#statsClip)">

        <!-- BLACK FOUNDATION -->
        <rect width="{WIDTH}" height="{HEIGHT}" fill="#020304"/>
        <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#blackPanel)"/>
        <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#microgrid)"/>
        <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#scan)"/>

        <!-- AMBIENT LIGHT -->
        <circle cx="70" cy="70" r="150"
                fill="#22D3EE" opacity="0.045"
                filter="url(#softBlackGlow)"/>
        <circle cx="820" cy="570" r="170"
                fill="#A855F7" opacity="0.035"
                filter="url(#softBlackGlow)"/>

        <!-- OUTER FRAME -->
        <rect x="1" y="1" width="898" height="618" rx="21"
              fill="none" stroke="#334155" stroke-opacity="0.65"/>

        <!-- TOP SIGNAL LINE -->
        <rect x="38" y="25" width="824" height="2"
              fill="url(#statGlow)" filter="url(#strongGlow)"/>

        <!-- HEADER -->
        {text(42, 64, "◈ YEABSIRA", 21, "#F8FAFC", "700", letter_spacing="1")}
        {text(42, 87, "GITHUB // LIVE TELEMETRY", 9, "#64748B", "700", letter_spacing="1")}

        <!-- ONLINE STATUS — deliberately isolated from all other content -->
        <circle cx="780" cy="56" r="5"
                fill="#22D3EE" filter="url(#strongGlow)">
            <animate attributeName="opacity"
                     values="1;0.35;1" dur="2s"
                     repeatCount="indefinite"/>
        </circle>

        {text(852, 59, "SYSTEM ONLINE", 9, "#67E8F9", "700",
               "end", letter_spacing="1")}
        {text(852, 79, activity_state, 7, "#475569", "700",
               "end", letter_spacing="1")}

        <!-- 2x2 STAT GRID -->
        {stat_card_large(42, 108, 392, 84, "REPOSITORIES",
                         public_repositories, "PUBLIC PROJECTS", "#22D3EE")}

        {stat_card_large(466, 108, 392, 84, "FOLLOWERS",
                         followers, "NETWORK", "#818CF8")}

        {stat_card_large(42, 204, 392, 84, "STARS",
                         stars, "PROJECT IMPACT", "#D946EF")}

        {stat_card_large(466, 204, 392, 84, "FORKS",
                         forks, "COLLABORATION", "#38BDF8")}

        <!-- SECONDARY METADATA -->
        {text(42, 310, "REPOSITORY TELEMETRY", 8, "#64748B", "700",
               letter_spacing="1")}

        {text(42, 334, f"{private_repositories} PRIVATE", 9,
               "#CBD5E1", "700")}
        {text(170, 334, f"{following} FOLLOWING", 9,
               "#CBD5E1", "700")}
        {text(340, 334, f"{total_activity} RECENT EVENTS", 9,
               "#CBD5E1", "700")}

        <!-- CONTRIBUTION MATRIX -->
        {text(42, 367, "CONTRIBUTION MATRIX", 9, "#67E8F9", "700",
               letter_spacing="1")}
        {text(858, 367, "LAST 365 DAYS", 8, "#475569", "700",
               "end", letter_spacing="1")}

        {matrix}

        <!-- 30-DAY ACTIVITY -->
        {text(42, 480, "30-DAY ACTIVITY", 8, "#64748B", "700",
               letter_spacing="1")}
        {text(858, 480, f"{recent_total} EVENTS", 8, "#7DD3FC",
               "700", "end", letter_spacing="1")}

        <polyline points="{graph_polyline}"
                  fill="none"
                  stroke="url(#graphGlow)"
                  stroke-width="2.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  filter="url(#strongGlow)"/>

        <polyline points="{graph_polyline}"
                  fill="none"
                  stroke="#67E8F9"
                  stroke-width="1"
                  stroke-opacity="0.35"/>

        <!-- FOOTER -->
        <rect x="42" y="587" width="816" height="1"
              fill="#1E293B"/>

        {text(42, 608, "BUILDING INTELLIGENT SYSTEMS", 7,
               "#475569", "700", letter_spacing="1")}
        {text(858, 608, "LIVE GITHUB DATA", 7,
               "#475569", "700", "end", letter_spacing="1")}

    </g>
</svg>
"""

    return svg


def stat_card_large(x, y, width, height, title, value,
                    subtitle, accent):
    return f"""
    <g>
        <rect x="{x}" y="{y}" width="{width}" height="{height}"
              rx="12" fill="#070A0E"
              stroke="#1E293B" stroke-width="1"/>

        <rect x="{x}" y="{y}" width="3" height="{height}"
              rx="2" fill="{accent}"/>

        <rect x="{x + 18}" y="{y + 18}"
              width="55" height="2"
              fill="{accent}" opacity="0.65"/>

        {text(x + 18, y + 40, title, 8, "#64748B",
               "700", letter_spacing="1")}

        {text(x + 18, y + 70, value, 24, "#F8FAFC", "700")}

        {text(x + width - 18, y + 70, subtitle, 8, "#475569",
               "700", "end")}
    </g>
"""


def activity_grid_large(daily, WIDTH=900):
    """
    Larger, clean 52-column x 7-row contribution matrix.
    Fits beneath the 2x2 stats without colliding with the activity graph.
    """
    today = datetime.now(timezone.utc).date()

    # Start on a Sunday so the seven rows remain aligned.
    start = today - timedelta(days=364)
    start -= timedelta(days=(start.weekday() + 1) % 7)

    total_days = 371
    columns = 53

    max_activity = max(daily.values(), default=1)

    colors = [
        "#0B1117",
        "#12303A",
        "#155E63",
        "#0E7490",
        "#0891B2",
        "#22D3EE",
        "#A78BFA",
    ]

    blocks = []

    cell = 12
    gap = 3
    x0 = 44
    y0 = 378

    for day_index in range(total_days):
        date = start + timedelta(days=day_index)
        count = daily.get(str(date), 0)

        if count <= 0:
            level = 0
        else:
            ratio = count / max_activity
            if ratio < 0.15:
                level = 1
            elif ratio < 0.30:
                level = 2
            elif ratio < 0.50:
                level = 3
            elif ratio < 0.70:
                level = 4
            elif ratio < 0.90:
                level = 5
            else:
                level = 6

        column = day_index // 7
        row = day_index % 7

        x = x0 + column * (cell + gap)
        y = y0 + row * (cell - 1)

        # Keep the last column inside the frame.
        if x + cell > 858:
            continue

        blocks.append(
            f"""
            <rect x="{x}" y="{y}" width="{cell}" height="{cell - 1}"
                  rx="3" fill="{colors[level]}" opacity="0.96">
                <title>{escape(str(date))}: {count} contribution events</title>
            </rect>
            """
        )

    return "\n".join(blocks)


def generate_languages_svg(languages):
    """
    Generate the same-size companion card as the stats dashboard.

    The language panel is intentionally simplified:
      - no redundant CODEBASE labels
      - larger language names
      - percentage and bar on the same visual row
      - enough vertical spacing to prevent overlap
      - top 8 languages remain fully readable
    """
    WIDTH = 900
    HEIGHT = 620

    total_bytes = sum(languages.values())
    language_data = []

    if total_bytes:
        for language, amount in sorted(
            languages.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:8]:
            percentage = amount / total_bytes * 100
            language_data.append((language, percentage, amount))

    language_colors = [
        "#22D3EE",
        "#818CF8",
        "#D946EF",
        "#38BDF8",
        "#A78BFA",
        "#67E8F9",
        "#60A5FA",
        "#C084FC",
    ]

    rows = []

    # Large, readable rows.
    y = 126
    row_height = 53

    for index, (language, percentage, amount) in enumerate(language_data):
        color = language_colors[index % len(language_colors)]

        bar_x = 250
        bar_y = y + 8
        bar_width = 570
        fill_width = max(10, int(bar_width * percentage / 100))

        rows.append(
            f"""
            <g>
                {text(48, y + 15, language.upper(), 12,
                       "#F1F5F9", "700", letter_spacing="0.5")}

                {text(850, y + 15, f"{percentage:.1f}%", 11,
                       color, "700", "end")}

                <rect x="{bar_x}" y="{bar_y}"
                      width="{bar_width}" height="10"
                      rx="5" fill="#111827"/>

                <rect x="{bar_x}" y="{bar_y}"
                      width="{fill_width}" height="10"
                      rx="5" fill="{color}"
                      filter="url(#languageGlow)"/>

                {text(48, y + 38,
                       f"{format_bytes(amount)}",
                       8, "#475569", "700")}

                <rect x="48" y="{y + 47}"
                      width="802" height="1"
                      fill="#111827"/>
            </g>
            """
        )

        y += row_height

    if not language_data:
        rows.append(
            text(48, 150, "NO LANGUAGE DATA RETURNED", 12,
                 "#F87171", "700")
        )
        rows.append(
            text(48, 178, "CHECK GH_TOKEN REPOSITORY ACCESS", 9,
                 "#64748B", "700")
        )

    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg"
     width="{WIDTH}" height="{HEIGHT}"
     viewBox="0 0 {WIDTH} {HEIGHT}">

    {defs()}

    <defs>
        <linearGradient id="languageAccent"
                        x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#22D3EE"/>
            <stop offset="50%" stop-color="#818CF8"/>
            <stop offset="100%" stop-color="#D946EF"/>
        </linearGradient>

        <filter id="languageGlow"
                x="-50%" y="-100%" width="200%" height="300%">
            <feGaussianBlur stdDeviation="2.5" result="blur"/>
            <feMerge>
                <feMergeNode in="blur"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>

        <filter id="languageAmbient"
                x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="25"/>
        </filter>

        <clipPath id="languageClip">
            <rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" rx="22"/>
        </clipPath>
    </defs>

    <g clip-path="url(#languageClip)">

        <!-- BLACK FOUNDATION -->
        <rect width="{WIDTH}" height="{HEIGHT}" fill="#020304"/>
        <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#blackPanel)"/>
        <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#microgrid)"/>
        <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#scan)"/>

        <!-- AMBIENT LIGHT -->
        <circle cx="820" cy="100" r="150"
                fill="#A855F7" opacity="0.035"
                filter="url(#languageAmbient)"/>
        <circle cx="80" cy="560" r="150"
                fill="#22D3EE" opacity="0.035"
                filter="url(#languageAmbient)"/>

        <!-- FRAME -->
        <rect x="1" y="1" width="898" height="618" rx="21"
              fill="none" stroke="#334155" stroke-opacity="0.65"/>

        <rect x="38" y="25" width="824" height="2"
              fill="url(#languageAccent)"
              filter="url(#languageGlow)"/>

        <!-- HEADER -->
        {text(42, 65, "◈ LANGUAGE MATRIX", 21,
               "#F8FAFC", "700", letter_spacing="1")}

        {text(42, 88, "CODEBASE // BYTE DISTRIBUTION", 9,
               "#64748B", "700", letter_spacing="1")}

        <!-- ONLINE STATUS -->
        <circle cx="780" cy="56" r="5"
                fill="#22D3EE" filter="url(#languageGlow)">
            <animate attributeName="opacity"
                     values="1;0.35;1" dur="2s"
                     repeatCount="indefinite"/>
        </circle>

        {text(852, 59, "SYSTEM ONLINE", 9,
               "#67E8F9", "700", "end", letter_spacing="1")}

        {text(852, 79, "LANGUAGE ANALYSIS", 7,
               "#475569", "700", "end", letter_spacing="1")}

        <!-- SECTION LABEL -->
        {text(48, 111, f"{len(language_data)} PRIMARY LANGUAGES",
               8, "#64748B", "700", letter_spacing="1")}

        <!-- LANGUAGE ROWS -->
        {"".join(rows)}

        <!-- FOOTER -->
        <rect x="42" y="570" width="816" height="1"
              fill="#1E293B"/>

        {text(42, 594,
               "LANGUAGE SHARE IS BASED ON GITHUB BYTE DISTRIBUTION",
               7, "#475569", "700", letter_spacing="0.5")}

        {text(858, 594,
               f"{len(languages)} TOTAL DETECTED",
               7, "#475569", "700", "end", letter_spacing="1")}

    </g>
</svg>
"""

    return svg


def format_bytes(value):
    """Compact byte display for the language card."""
    value = float(value)

    if value >= 1024 ** 3:
        return f"{value / (1024 ** 3):.1f} GB"
    if value >= 1024 ** 2:
        return f"{value / (1024 ** 2):.1f} MB"
    if value >= 1024:
        return f"{value / 1024:.1f} KB"
    return f"{int(value)} B"



def generate_combined_svg(user, repositories, daily, total_contributions, languages):
    """
    Generate one tall SVG containing the stats dashboard followed immediately
    by the language matrix. Both sections keep the same 900px width so the
    result can be embedded as one long GitHub profile image.
    """
    stats_svg = generate_stats_svg(
        user, repositories, daily, total_contributions
    )
    language_svg = generate_languages_svg(languages)

    # Extract the reusable SVG contents from each existing renderer.
    stats_match = re.search(
        r"<svg[^>]*>(.*)</svg>\s*$", stats_svg, flags=re.DOTALL
    )
    language_match = re.search(
        r"<svg[^>]*>(.*)</svg>\s*$", language_svg, flags=re.DOTALL
    )

    if not stats_match or not language_match:
        raise RuntimeError("Could not compose the generated SVG cards.")

    stats_content = stats_match.group(1)
    language_content = language_match.group(1)

    WIDTH = 900
    CARD_HEIGHT = 620
    GAP = 24
    HEIGHT = CARD_HEIGHT * 2 + GAP

    return f"""<svg xmlns="http://www.w3.org/2000/svg"
    width="{WIDTH}" height="{HEIGHT}"
    viewBox="0 0 {WIDTH} {HEIGHT}">
    <rect width="{WIDTH}" height="{HEIGHT}" fill="#020304"/>

    <svg x="0" y="0" width="{WIDTH}" height="{CARD_HEIGHT}"
         viewBox="0 0 {WIDTH} {CARD_HEIGHT}">
        {stats_content}
    </svg>

    <rect x="0" y="{CARD_HEIGHT}" width="{WIDTH}" height="{GAP}"
          fill="#020304"/>

    <svg x="0" y="{CARD_HEIGHT + GAP}" width="{WIDTH}"
         height="{CARD_HEIGHT}" viewBox="0 0 {WIDTH} {CARD_HEIGHT}">
        {language_content}
    </svg>
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

    print("[1/5] Authenticating...")
    user = get_user()
    if not user:
        raise RuntimeError("Could not retrieve GitHub user.")
    print(f"[OK] Authenticated API identity: {user.get('login', 'unknown')}")

    print("[2/5] Loading repositories...")
    repositories = get_repositories()

    print("[3/5] Calculating language distribution...")
    languages = get_languages(repositories)
    print(f"[OK] Languages discovered: {len(languages)}")

    print("[4/5] Loading contribution calendar...")
    daily, total_contributions = get_contribution_calendar()
    print(f"[OK] Contribution total: {total_contributions:,}")

    print("[5/5] Rendering Blackout HUD...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    STATS_FILE.write_text(
        generate_combined_svg(
            user,
            repositories,
            daily,
            total_contributions,
            languages,
        ),
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
    print("  DESIGN: BLACK / CYAN / VIOLET / MAGENTA")
    print("  DATA:   LIVE GITHUB REST + GRAPHQL")
    print("  AUTH:   GH_TOKEN")
    print("=" * 68)


if __name__ == "__main__":
    main()
