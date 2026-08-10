import os
import math
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
         anchor="start", spacing=0, opacity=1, family="JetBrains Mono, DejaVu Sans Mono, monospace"):
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

def defs(seed):
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


def generate_stats_svg(user, repos, daily, total_contributions):
    now = datetime.now(timezone.utc)
    seed = int(now.timestamp()) // 3600

    public_repos = user.get("public_repos", 0)
    private_repos = sum(1 for r in repos if r.get("private"))
    followers = user.get("followers", 0)
    following = user.get("following", 0)
    stars = sum(r.get("stargazers_count", 0) for r in repos)
    forks = sum(r.get("forks_count", 0) for r in repos)

    recent_values = []
    for offset in range(29, -1, -1):
        d = now.date() - timedelta(days=offset)
        recent_values.append(daily.get(str(d), 0))
    recent_total = sum(recent_values)
    active_days = sum(1 for v in recent_values if v > 0)
    best_day = max(recent_values, default=0)
    repo_count = len(repos)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="540" viewBox="0 0 900 540">
  {defs(seed)}
  <g clip-path="url(#clip900)">
    {background(900, 540, seed)}

    <rect x="1" y="1" width="898" height="538" rx="23"
          fill="none" stroke="#24323A" stroke-width="1"/>
    {corner_brackets(900, 540)}

    <rect x="38" y="27" width="824" height="2" fill="url(#edge)" filter="url(#glowC)"/>

    {text(42, 60, "YEABSIRA", 22, WHITE, 800, spacing=2.2)}
    {text(42, 80, "GITHUB // LIVE TELEMETRY", 7, MUTED, 700, spacing=2)}
    {text(858, 56, "SYSTEM", 7, MUTED, 700, "end", spacing=1.5)}
    {circle(838, 52, 3.5, CYAN, 1)}
    {text(858, 72, "ONLINE / {now.strftime('%H:%M UTC')}", 7, CYAN, 700, "end", spacing=1)}

    {stat_tile(38, 104, 190, 100, "Repositories", repo_count, f"{public_repos} public / {private_repos} private", CYAN, 0)}
    {stat_tile(240, 104, 190, 100, "Followers", followers, "network reach", VIOLET, 1)}
    {stat_tile(442, 104, 190, 100, "Stars", stars, "project impact", MAGENTA, 2)}
    {stat_tile(644, 104, 218, 100, "Forks", forks, "collaboration", LIME, 3)}

    {text(42, 231, "CONTRIBUTION MATRIX", 8, MUTED, 700, spacing=1.8)}
    {text(858, 231, f"{total_contributions:,} TOTAL / 365D", 8, DIM, 700, "end", spacing=1)}

    {contribution_matrix(daily)}

    <rect x="42" y="384" width="816" height="1" fill="#182228"/>
    {text(42, 407, "30 DAY ACTIVITY", 7, MUTED, 700, spacing=1.5)}
    {text(858, 407, f"{recent_total:,} EVENTS // {active_days} ACTIVE DAYS", 7, DIM, 700, "end", spacing=.8)}

    <g>
      {sparkline(recent_values, 42, 420, 520, 48, CYAN)}
      {text(42, 487, "0", 6, DIM, 600)}
      {text(562, 487, f"PEAK {best_day}", 6, CYAN, 700, "end")}
    </g>

    <g>
      {rect(590, 416, 268, 62, PANEL_2, 10, "#1C2930", .7)}
      {text(608, 437, "FOLLOWING", 7, MUTED, 700, spacing=1.2)}
      {text(608, 462, following, 20, WHITE, 700)}
      {text(845, 437, "PROFILE", 7, MUTED, 700, "end", spacing=1.2)}
      {text(845, 462, f"@{USERNAME}", 8, CYAN, 700, "end")}
    </g>

    <rect x="42" y="504" width="816" height="1" fill="#182228"/>
    {text(42, 524, "BLACKOUT // DATA IS GENERATED FROM THE GITHUB API", 6.5, DIM, 700, spacing=1)}
    {text(858, 524, "AUTO REFRESH 24H", 6.5, CYAN, 700, "end", spacing=1)}
  </g>
</svg>"""
    return svg


# ============================================================
# LANGUAGE MATRIX
# ============================================================

def language_arc(cx, cy, radius, percent, color):
    # SVG circle dash makes a clean progress ring without JS.
    circumference = 2 * math.pi * radius
    dash = circumference * percent / 100
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" '
        f'stroke="#182329" stroke-width="7"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" '
        f'stroke="{color}" stroke-width="7" stroke-linecap="round" '
        f'stroke-dasharray="{dash:.2f} {circumference:.2f}" '
        f'transform="rotate(-90 {cx} {cy})" filter="url(#glowC)"/>'
    )


def generate_languages_svg(languages):
    total = sum(languages.values())
    ordered = sorted(languages.items(), key=lambda kv: kv[1], reverse=True)[:8]
    data = []
    for lang, amount in ordered:
        pct = (amount / total * 100) if total else 0
        data.append((lang, pct, amount))

    now = datetime.now(timezone.utc)
    seed = int(now.timestamp()) // 3600

    rows = []
    for i, (lang, pct, amount) in enumerate(data):
        y = 112 + i * 42
        color = LANG_COLORS[i % len(LANG_COLORS)]
        width = 420 * pct / 100
        rows.append(f"""
          {text(40, y, lang.upper(), 8, WHITE, 700, spacing=1)}
          {text(610, y, f"{pct:.1f}%", 8, color, 800, "end")}
          <rect x="40" y="{y+10}" width="570" height="5" rx="2.5" fill="#111A1F"/>
          <rect x="40" y="{y+10}" width="{width:.2f}" height="5" rx="2.5"
                fill="{color}" filter="url(#glowC)"/>
          {circle(625, y+12.5, 2.5, color, 1)}
          {text(645, y+15, f"{amount/1024:.0f} KB", 6.5, DIM, 600)}
        """)

    if not rows:
        rows.append(text(40, 120, "NO LANGUAGE DATA RETURNED", 9, RED, 700))

    lead = data[0] if data else ("N/A", 0, 0)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="680" height="500" viewBox="0 0 680 500">
  {defs(seed)}
  <g clip-path="url(#clip720)">
    {background(680, 500, seed + 19)}
    <rect x="1" y="1" width="678" height="498" rx="23" fill="none" stroke="#24323A"/>
    {corner_brackets(680, 500, VIOLET)}

    <rect x="36" y="27" width="608" height="2" fill="url(#edge)" filter="url(#glowC)"/>
    {text(40, 60, "LANGUAGE / MATRIX", 19, WHITE, 800, spacing=1.8)}
    {text(640, 56, "CODEBASE", 7, MUTED, 700, "end", spacing=1.5)}
    {text(640, 72, f"{len(data):02d} LANGUAGES", 7, CYAN, 700, "end", spacing=1)}

    <g>
      {language_arc(565, 78, 27, lead[1], CYAN)}
      {text(565, 83, f"{lead[1]:.0f}%", 8, WHITE, 800, "middle")}
    </g>

    {text(40, 92, "BYTE-WEIGHTED DISTRIBUTION / TOP 8", 6.5, DIM, 700, spacing=1)}

    {"".join(rows)}

    <rect x="40" y="456" width="600" height="1" fill="#182228"/>
    {text(40, 477, "PRIMARY LANGUAGES ACROSS REPOSITORIES", 6.5, DIM, 700, spacing=1)}
    {text(640, 477, f"SYNC // {now.strftime('%Y-%m-%d')}", 6.5, CYAN, 700, "end", spacing=1)}
  </g>
</svg>"""


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
        generate_stats_svg(user, repositories, daily, total_contributions),
        encoding="utf-8",
    )
    LANGUAGES_FILE.write_text(
        generate_languages_svg(languages),
        encoding="utf-8",
    )

    print("=" * 68)
    print("  GENERATION COMPLETE")
    print(f"  -> {STATS_FILE}")
    print(f"  -> {LANGUAGES_FILE}")
    print("  DESIGN: BLACK / CYAN / VIOLET / MAGENTA")
    print("  DATA:   LIVE GITHUB REST + GRAPHQL")
    print("  AUTH:   GH_TOKEN")
    print("=" * 68)


if __name__ == "__main__":
    main()
