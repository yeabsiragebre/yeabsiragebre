import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from xml.sax.saxutils import escape

import requests

# ============================================================

# CONFIG

# ============================================================

USERNAME = "yeabsiragebre"

# GH_TOKEN is preferred because this is the secret used

# by the GitHub Actions workflow.

TOKEN = (
os.environ.get("GH_TOKEN")
or os.environ.get("GITHUB_TOKEN")
)

API = "https://api.github.com"

OUTPUT_DIR = Path("profile")
STATS_FILE = OUTPUT_DIR / "stats.svg"
LANGUAGES_FILE = OUTPUT_DIR / "top-langs.svg"

HEADERS = {
"Accept": "application/vnd.github+json",
"X-GitHub-Api-Version": "2022-11-28",
}

if TOKEN:
HEADERS["Authorization"] = f"Bearer {TOKEN}"

# ============================================================

# API

# ============================================================

session = requests.Session()
session.headers.update(HEADERS)

def github_get(url, params=None):
response = session.get(
url,
params=params,
timeout=30,
)

```
if not response.ok:
    print(
        f"[WARNING] GitHub API {response.status_code}: "
        f"{url}"
    )

    print(response.text[:500])

    return None

return response.json()
```

# ============================================================

# USER

# ============================================================

def get_user():
data = github_get(
f"{API}/user"
)

```
if data:
    return data

return github_get(
    f"{API}/users/{USERNAME}"
)
```

# ============================================================

# REPOSITORIES

# ============================================================

def get_repositories():
"""
Get repositories visible to the authenticated token.

```
This includes private repositories when GH_TOKEN has
permission to access them.
"""

repositories = []

page = 1

while True:

    data = github_get(
        f"{API}/user/repos",
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

    repositories.extend(data)

    print(
        f"[INFO] Repository page {page}: "
        f"{len(data)} repositories"
    )

    if len(data) < 100:
        break

    page += 1

# Keep repositories relevant to the profile.
repositories = [
    repo
    for repo in repositories
    if repo.get("owner", {}).get("login", "").lower()
    == USERNAME.lower()
]

print(
    f"[INFO] Repositories belonging to "
    f"{USERNAME}: {len(repositories)}"
)

return repositories
```

# ============================================================

# LANGUAGES

# ============================================================

def get_languages(repositories):
"""
Collect language byte counts from every repository.

```
Unlike the previous version, failed requests are NOT
silently ignored.
"""

language_bytes = defaultdict(int)

successful = 0
failed = 0

for index, repository in enumerate(
    repositories,
    start=1,
):

    name = repository.get("name")

    if not name:
        continue

    url = (
        f"{API}/repos/"
        f"{USERNAME}/"
        f"{name}/languages"
    )

    response = session.get(
        url,
        timeout=30,
    )

    if response.ok:

        data = response.json()

        for language, amount in data.items():
            language_bytes[language] += amount

        successful += 1

        print(
            f"[LANGUAGE {index}/{len(repositories)}] "
            f"{name}: OK"
        )

    else:

        failed += 1

        print(
            f"[LANGUAGE {index}/{len(repositories)}] "
            f"{name}: FAILED "
            f"{response.status_code}"
        )

print(
    f"[INFO] Language requests successful: "
    f"{successful}"
)

print(
    f"[INFO] Language requests failed: "
    f"{failed}"
)

print(
    f"[INFO] Languages discovered: "
    f"{len(language_bytes)}"
)

return dict(language_bytes)
```

# ============================================================

# CONTRIBUTION DATA

# ============================================================

def get_contributions():
"""
Retrieve contribution activity using GitHub's events API.

```
This gives the visual generator real activity data
without requiring GraphQL.
"""

events = []

page = 1

while page <= 3:

    data = github_get(
        f"{API}/users/{USERNAME}/events",
        params={
            "per_page": 100,
            "page": page,
        },
    )

    if not data:
        break

    events.extend(data)

    if len(data) < 100:
        break

    page += 1

daily = defaultdict(int)

for event in events:

    created = event.get(
        "created_at"
    )

    if not created:
        continue

    try:
        date = datetime.fromisoformat(
            created.replace(
                "Z",
                "+00:00",
            )
        ).date()

        daily[str(date)] += 1

    except ValueError:
        continue

return daily
```

# ============================================================

# SVG HELPERS

# ============================================================

def text(
x,
y,
value,
size=14,
color="#E8F1FF",
weight="400",
anchor="start",
letter_spacing="0",
):
return (
f'<text '
f'x="{x}" '
f'y="{y}" '
f'font-family="JetBrains Mono, '
f"DejaVu Sans Mono, monospace" "
f'font-size="{size}px" '
f'font-weight="{weight}" '
f'letter-spacing="{letter_spacing}px" '
f'fill="{color}" '
f'text-anchor="{anchor}">'
f'{escape(str(value))}'
f'</text>'
)

def rect(
x,
y,
width,
height,
fill,
radius=10,
stroke="none",
stroke_opacity="0",
):
return (
f'<rect '
f'x="{x}" '
f'y="{y}" '
f'width="{width}" '
f'height="{height}" '
f'rx="{radius}" '
f'fill="{fill}" '
f'stroke="{stroke}" '
f'stroke-opacity="{stroke_opacity}"/>'
)

# ============================================================

# DESIGN SYSTEM

# ============================================================

def definitions():

```
return """
<defs>

    <!-- Main background -->

    <linearGradient
        id="bg"
        x1="0"
        y1="0"
        x2="1"
        y2="1">

        <stop
            offset="0%"
            stop-color="#07111F"/>

        <stop
            offset="48%"
            stop-color="#0B1830"/>

        <stop
            offset="100%"
            stop-color="#10152B"/>

    </linearGradient>


    <!-- Accent -->

    <linearGradient
        id="accent"
        x1="0"
        y1="0"
        x2="1"
        y2="0">

        <stop
            offset="0%"
            stop-color="#38BDF8"/>

        <stop
            offset="45%"
            stop-color="#818CF8"/>

        <stop
            offset="100%"
            stop-color="#C084FC"/>

    </linearGradient>


    <!-- Cyan -->

    <linearGradient
        id="cyan"
        x1="0"
        y1="0"
        x2="1"
        y2="0">

        <stop
            offset="0%"
            stop-color="#22D3EE"/>

        <stop
            offset="100%"
            stop-color="#38BDF8"/>

    </linearGradient>


    <!-- Purple -->

    <linearGradient
        id="purple"
        x1="0"
        y1="0"
        x2="1"
        y2="0">

        <stop
            offset="0%"
            stop-color="#818CF8"/>

        <stop
            offset="100%"
            stop-color="#C084FC"/>

    </linearGradient>


    <!-- Glow -->

    <filter
        id="glow"
        x="-100%"
        y="-100%"
        width="300%"
        height="300%">

        <feGaussianBlur
            stdDeviation="3"
            result="blur"/>

        <feMerge>

            <feMergeNode
                in="blur"/>

            <feMergeNode
                in="SourceGraphic"/>

        </feMerge>

    </filter>


    <!-- Large glow -->

    <filter
        id="softGlow"
        x="-100%"
        y="-100%"
        width="300%"
        height="300%">

        <feGaussianBlur
            stdDeviation="18"/>

    </filter>


    <!-- Grid -->

    <pattern
        id="grid"
        width="36"
        height="36"
        patternUnits="userSpaceOnUse">

        <path
            d="M36 0H0V36"
            fill="none"
            stroke="#60A5FA"
            stroke-opacity="0.045"/>

    </pattern>


    <!-- Scanline -->

    <pattern
        id="scanlines"
        width="4"
        height="4"
        patternUnits="userSpaceOnUse">

        <path
            d="M0 0H4"
            stroke="#FFFFFF"
            stroke-opacity="0.018"/>

    </pattern>


    <!-- Clip -->

    <clipPath id="panelClip">

        <rect
            x="0"
            y="0"
            width="900"
            height="500"
            rx="22"/>

    </clipPath>

</defs>
"""
```

# ============================================================

# STAT CARD

# ============================================================

def stat_card(
x,
title,
value,
subtitle,
accent,
):

```
return f"""
{rect(
    x,
    122,
    190,
    108,
    "#0A1628",
    14,
    "#5EE7FF",
    "0.12",
)}

<rect
    x="{x}"
    y="122"
    width="3"
    height="108"
    rx="2"
    fill="{accent}"/>

{text(
    x + 18,
    147,
    title,
    8,
    "#7DD3FC",
    "700",
    letter_spacing="1",
)}

{text(
    x + 18,
    187,
    value,
    30,
    "#F1F5FF",
    "700",
)}

{text(
    x + 18,
    210,
    subtitle,
    8,
    "#64748B",
    "400",
)}
"""
```

# ============================================================

# ACTIVITY GRID

# ============================================================

def activity_grid(contributions):

```
today = datetime.now(
    timezone.utc
).date()

start = today - timedelta(
    days=364
)

blocks = []

max_activity = max(
    contributions.values(),
    default=1,
)

colors = [
    "#10233A",
    "#164E63",
    "#155E75",
    "#0369A1",
    "#0284C7",
    "#38BDF8",
    "#818CF8",
]

for day_index in range(365):

    date = (
        start
        + timedelta(days=day_index)
    )

    count = contributions.get(
        str(date),
        0,
    )

    if count == 0:

        level = 0

    else:

        ratio = (
            count / max_activity
        )

        if ratio < 0.2:
            level = 1
        elif ratio < 0.4:
            level = 2
        elif ratio < 0.6:
            level = 3
        elif ratio < 0.8:
            level = 4
        else:
            level = 6

    column = day_index // 7
    row = day_index % 7

    x = 45 + column * 11
    y = 288 + row * 9

    color = colors[level]

    blocks.append(
        f"""
        <rect
            x="{x}"
            y="{y}"
            width="7"
            height="7"
            rx="2"
            fill="{color}"
            opacity="0.95"/>
        """
    )

return "\n".join(blocks)
```

# ============================================================

# STATS SVG

# ============================================================

def generate_stats_svg(
user,
repositories,
contributions,
):

```
public_repositories = user.get(
    "public_repos",
    0,
)

followers = user.get(
    "followers",
    0,
)

following = user.get(
    "following",
    0,
)

stars = sum(
    repo.get(
        "stargazers_count",
        0,
    )
    for repo in repositories
)

forks = sum(
    repo.get(
        "forks_count",
        0,
    )
    for repo in repositories
)

total_activity = sum(
    contributions.values()
)

svg = f"""
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="900"
    height="500"
    viewBox="0 0 900 500">

    {definitions()}

    <g clip-path="url(#panelClip)">

        <!-- BACKGROUND -->

        <rect
            width="900"
            height="500"
            fill="url(#bg)"/>

        <rect
            width="900"
            height="500"
            fill="url(#grid)"/>

        <rect
            width="900"
            height="500"
            fill="url(#scanlines)"/>


        <!-- AMBIENT LIGHT -->

        <circle
            cx="100"
            cy="70"
            r="100"
            fill="#38BDF8"
            opacity="0.055"
            filter="url(#softGlow)"/>

        <circle
            cx="800"
            cy="420"
            r="120"
            fill="#A78BFA"
            opacity="0.06"
            filter="url(#softGlow)"/>


        <!-- OUTER BORDER -->

        <rect
            x="1"
            y="1"
            width="898"
            height="498"
            rx="21"
            fill="none"
            stroke="#64748B"
            stroke-opacity="0.32"/>


        <!-- TOP ACCENT -->

        <rect
            x="35"
            y="27"
            width="830"
            height="2"
            fill="url(#accent)"
            filter="url(#glow)"/>


        <!-- HEADER -->

        {text(
            42,
            65,
            "◈ YEABSIRA",
            20,
            "#F8FAFC",
            "700",
            letter_spacing="1",
        )}

        {text(
            42,
            88,
            "AI ENGINEERING  /  SOFTWARE  /  COMPUTER SCIENCE",
            8,
            "#64748B",
            "700",
            letter_spacing="1",
        )}

        {text(
            858,
            61,
            "SYSTEM // ONLINE",
            8,
            "#67E8F9",
            "700",
            "end",
            letter_spacing="1",
        )}

        <circle
            cx="846"
            cy="57"
            r="4"
            fill="#22D3EE"
            filter="url(#glow)"/>


        <!-- STAT CARDS -->

        {stat_card(
            35,
            "REPOSITORIES",
            public_repositories,
            "PUBLIC PROJECTS",
            "#38BDF8",
        )}

        {stat_card(
            240,
            "FOLLOWERS",
            followers,
            "NETWORK",
            "#818CF8",
        )}

        {stat_card(
            445,
            "STARS",
            stars,
            "PROJECT IMPACT",
            "#C084FC",
        )}

        {stat_card(
            650,
            "FORKS",
            forks,
            "COLLABORATION",
            "#22D3EE",
        )}


        <!-- ACTIVITY HEADER -->

        {text(
            42,
            272,
            "CONTRIBUTION MATRIX",
            8,
            "#7DD3FC",
            "700",
            letter_spacing="1",
        )}

        {text(
            858,
            272,
            f"{total_activity} RECENT EVENTS",
            8,
            "#475569",
            "700",
            "end",
            letter_spacing="1",
        )}


        <!-- CONTRIBUTION GRID -->

        {activity_grid(
            contributions
        )}


        <!-- FOOTER DIVIDER -->

        <rect
            x="42"
            y="362"
            width="816"
            height="1"
            fill="url(#accent)"
            opacity="0.22"/>


        <!-- FOOTER DATA -->

        {text(
            42,
            390,
            "CURRENT STACK",
            8,
            "#64748B",
            "700",
            letter_spacing="1",
        )}

        {text(
            42,
            414,
            "LLMs  ·  RAG  ·  AI AGENTS  ·  BACKEND  ·  SYSTEM DESIGN",
            9,
            "#CBD5E1",
            "700",
        )}

        {text(
            858,
            390,
            "FOLLOWING",
            8,
            "#64748B",
            "700",
            "end",
            letter_spacing="1",
        )}

        {text(
            858,
            414,
            following,
            18,
            "#A5B4FC",
            "700",
            "end",
        )}


        <!-- BOTTOM STATUS -->

        <rect
            x="42"
            y="445"
            width="816"
            height="1"
            fill="#334155"/>

        {text(
            42,
            468,
            "BUILDING INTELLIGENT SYSTEMS",
            8,
            "#475569",
            "700",
            letter_spacing="1",
        )}

        {text(
            858,
            468,
            "LIVE PROFILE DATA",
            8,
            "#475569",
            "700",
            "end",
            letter_spacing="1",
        )}

    </g>

</svg>
"""

return svg
```

# ============================================================

# LANGUAGE SVG

# ============================================================

def generate_languages_svg(
languages,
):

```
total_bytes = sum(
    languages.values()
)

language_data = []

if total_bytes:

    for language, amount in sorted(
        languages.items(),
        key=lambda item: item[1],
        reverse=True,
    ):

        percentage = (
            amount
            / total_bytes
            * 100
        )

        language_data.append(
            (
                language,
                percentage,
                amount,
            )
        )

# Keep the most important 8 languages.
language_data = language_data[:8]

rows = []

y = 128

language_colors = [
    "#38BDF8",
    "#818CF8",
    "#C084FC",
    "#22D3EE",
    "#60A5FA",
    "#A78BFA",
    "#67E8F9",
    "#93C5FD",
]

for index, (
    language,
    percentage,
    amount,
) in enumerate(language_data):

    bar_width = max(
        8,
        int(
            310
            * percentage
            / 100
        ),
    )

    color = language_colors[
        index
        % len(language_colors)
    ]

    rows.append(
        f"""
        <!-- {escape(language)} -->

        {text(
            48,
            y,
            language.upper(),
            9,
            "#E2E8F0",
            "700",
            letter_spacing="1",
        )}

        {text(
            570,
            y,
            f"{percentage:.1f}%",
            9,
            color,
            "700",
            "end",
        )}

        <rect
            x="48"
            y="{y + 10}"
            width="522"
            height="7"
            rx="4"
            fill="#172338"/>

        <rect
            x="48"
            y="{y + 10}"
            width="{bar_width}"
            height="7"
            rx="4"
            fill="{color}"
            filter="url(#glow)"/>

        """
    )

    y += 40

if not language_data:

    rows.append(
        text(
            48,
            135,
            "NO LANGUAGE DATA RETURNED",
            10,
            "#F87171",
            "700",
        )
    )

    rows.append(
        text(
            48,
            160,
            "CHECK GH_TOKEN REPOSITORY ACCESS",
            8,
            "#64748B",
            "700",
        )
    )

svg = f"""
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="620"
    height="430"
    viewBox="0 0 620 430">

    {definitions()}


    <!-- BACKGROUND -->

    <rect
        width="620"
        height="430"
        rx="20"
        fill="url(#bg)"/>

    <rect
        width="620"
        height="430"
        rx="20"
        fill="url(#grid)"/>


    <!-- BORDER -->

    <rect
        x="1"
        y="1"
        width="618"
        height="428"
        rx="19"
        fill="none"
        stroke="#64748B"
        stroke-opacity="0.32"/>


    <!-- HEADER -->

    {text(
        35,
        50,
        "◈ LANGUAGE MATRIX",
        18,
        "#F8FAFC",
        "700",
        letter_spacing="1",
    )}

    {text(
        585,
        48,
        "CODEBASE",
        8,
        "#64748B",
        "700",
        "end",
        letter_spacing="1",
    )}


    <!-- ACCENT -->

    <rect
        x="35"
        y="70"
        width="550"
        height="2"
        fill="url(#accent)"
        filter="url(#glow)"/>


    <!-- LANGUAGE DATA -->

    {"".join(rows)}


    <!-- FOOTER -->

    <rect
        x="35"
        y="365"
        width="550"
        height="1"
        fill="#334155"/>

    {text(
        35,
        390,
        f"{len(language_data)} LANGUAGES DETECTED",
        8,
        "#64748B",
        "700",
        letter_spacing="1",
    )}

    {text(
        585,
        390,
        "BYTE DISTRIBUTION",
        8,
        "#7DD3FC",
        "700",
        "end",
        letter_spacing="1",
    )}

    {text(
        35,
        410,
        "PRIMARY LANGUAGES ACROSS REPOSITORIES",
        7,
        "#475569",
        "400",
        letter_spacing="1",
    )}

    {text(
        585,
        410,
        "ANALYSIS // COMPLETE",
        7,
        "#475569",
        "700",
        "end",
        letter_spacing="1",
    )}

</svg>
"""

return svg
```

# ============================================================

# MAIN

# ============================================================

def main():

```
print()
print("=" * 60)
print("  YEABSIRA // FUTURISTIC GITHUB ENGINE")
print("=" * 60)
print()

if not TOKEN:

    raise RuntimeError(
        "No GitHub token found. "
        "Set GH_TOKEN in GitHub Actions."
    )

print(
    "[1/5] Authenticating with GitHub..."
)

user = get_user()

if not user:

    raise RuntimeError(
        "Could not retrieve GitHub user."
    )

authenticated_name = user.get(
    "login",
    "unknown",
)

print(
    f"[OK] Authenticated as: "
    f"{authenticated_name}"
)

print()

print(
    "[2/5] Loading repositories..."
)

repositories = get_repositories()

if not repositories:

    print(
        "[WARNING] No repositories were found."
    )

print()

print(
    "[3/5] Calculating language distribution..."
)

languages = get_languages(
    repositories
)

if languages:

    print()

    print(
        "[LANGUAGES]"
    )

    total = sum(
        languages.values()
    )

    for language, amount in sorted(
        languages.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:10]:

        percentage = (
            amount
            / total
            * 100
        )

        print(
            f"  {language:<18}"
            f"{percentage:>6.2f}%"
        )

else:

    print(
        "[WARNING] No language data was collected."
    )

print()

print(
    "[4/5] Loading contribution activity..."
)

contributions = get_contributions()

print(
    f"[OK] Activity points: "
    f"{sum(contributions.values())}"
)

print()

print(
    "[5/5] Rendering futuristic SVGs..."
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

stats_svg = generate_stats_svg(
    user,
    repositories,
    contributions,
)

languages_svg = generate_languages_svg(
    languages,
)

STATS_FILE.write_text(
    stats_svg,
    encoding="utf-8",
)

LANGUAGES_FILE.write_text(
    languages_svg,
    encoding="utf-8",
)

print()
print("=" * 60)
print("  GENERATION COMPLETE")
print("=" * 60)
print()
print(
    f"  ✓ {STATS_FILE}"
)
print(
    f"  ✓ {LANGUAGES_FILE}"
)
print()
print(
    "  Design: NAVY / CYAN / INDIGO / VIOLET"
)
print(
    "  Data:   LIVE GITHUB API"
)
print(
    "  Engine: PYTHON + SVG"
)
print()
```

if **name** == "**main**":
main()
