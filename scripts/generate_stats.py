import json
import os
import urllib.request
from collections import Counter
from pathlib import Path


USERNAME = "yeabsiragebre"
OUTPUT_DIR = Path("profile")

GITHUB_API = "https://api.github.com"


def github_request(endpoint):
    token = os.environ.get("GH_TOKEN")

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "yeabsiragebre-profile-stats",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        f"{GITHUB_API}{endpoint}",
        headers=headers,
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode())


def get_user():
    return github_request(f"/users/{USERNAME}")


def get_repositories():
    repositories = []
    page = 1

    while True:
        data = github_request(
            f"/users/{USERNAME}/repos"
            f"?per_page=100&page={page}&type=owner"
        )

        if not data:
            break

        repositories.extend(data)

        if len(data) < 100:
            break

        page += 1

    return repositories


def get_languages(repo):
    return github_request(f"/repos/{USERNAME}/{repo}/languages")


def calculate_languages(repositories):
    language_counts = Counter()

    for repo in repositories:
        if repo.get("fork"):
            continue

        try:
            languages = get_languages(repo["name"])

            for language, amount in languages.items():
                language_counts[language] += amount

        except Exception as error:
            print(f"Could not read {repo['name']}: {error}")

    return language_counts


def percentage_values(counter):
    total = sum(counter.values())

    if total == 0:
        return []

    return [
        (language, amount / total * 100)
        for language, amount in counter.most_common(8)
    ]


def escape(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def stat_card(user):
    followers = user.get("followers", 0)
    following = user.get("following", 0)
    public_repos = user.get("public_repos", 0)

    return f"""
<svg xmlns="http://www.w3.org/2000/svg"
     width="650"
     height="430"
     viewBox="0 0 650 430">

<style>
    .title {{
        font-family: monospace;
        font-size: 25px;
        font-weight: bold;
        fill: #ffffff;
    }}

    .label {{
        font-family: monospace;
        font-size: 14px;
        fill: #8b9bb4;
        letter-spacing: 2px;
    }}

    .value {{
        font-family: monospace;
        font-size: 29px;
        font-weight: bold;
        fill: #ffffff;
    }}

    .small {{
        font-family: monospace;
        font-size: 12px;
        fill: #718096;
    }}

    .accent {{
        fill: #ff2bd6;
    }}

    .cyan {{
        fill: #00e5ff;
    }}

    .green {{
        fill: #39ff88;
    }}

    .glow {{
        filter: url(#glow);
    }}

    .pulse {{
        animation: pulse 2s infinite;
    }}

    .scan {{
        animation: scan 4s linear infinite;
    }}

    @keyframes pulse {{
        0%, 100% {{ opacity: .45; }}
        50% {{ opacity: 1; }}
    }}

    @keyframes scan {{
        from {{ transform: translateY(-20px); }}
        to {{ transform: translateY(450px); }}
    }}
</style>

<defs>

    <linearGradient id="background" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#090914"/>
        <stop offset="55%" stop-color="#111124"/>
        <stop offset="100%" stop-color="#07070d"/>
    </linearGradient>

    <linearGradient id="line" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#ff2bd6"/>
        <stop offset="50%" stop-color="#00e5ff"/>
        <stop offset="100%" stop-color="#39ff88"/>
    </linearGradient>

    <filter id="glow">
        <feGaussianBlur stdDeviation="4" result="blur"/>
        <feMerge>
            <feMergeNode in="blur"/>
            <feMergeNode in="SourceGraphic"/>
        </feMerge>
    </filter>

    <pattern id="grid"
             width="30"
             height="30"
             patternUnits="userSpaceOnUse">
        <path d="M 30 0 L 0 0 0 30"
              fill="none"
              stroke="#ffffff"
              stroke-opacity=".035"/>
    </pattern>

</defs>

<rect width="650" height="430" rx="22"
      fill="url(#background)"
      stroke="#24243d"
      stroke-width="2"/>

<rect width="650" height="430" rx="22"
      fill="url(#grid)"/>

<rect x="0" y="0"
      width="650"
      height="3"
      fill="url(#line)"
      class="glow"/>

<rect x="0" y="-30"
      width="650"
      height="20"
      fill="#00e5ff"
      opacity=".08"
      class="scan"/>

<text x="35" y="55" class="label">
    GITHUB // CORE
</text>

<text x="35" y="92" class="title">
    YEABSIRA
</text>

<circle cx="590" cy="48"
        r="7"
        class="green pulse glow"/>

<text x="535" y="78" class="small">
    ONLINE
</text>

<line x1="35" y1="112"
      x2="615" y2="112"
      stroke="url(#line)"
      stroke-opacity=".5"/>

<!-- PUBLIC REPOSITORIES -->

<text x="55" y="155" class="label">
    REPOSITORIES
</text>

<text x="55" y="195" class="value">
    {public_repos}
</text>

<text x="55" y="220" class="small">
    PUBLIC
</text>

<!-- FOLLOWERS -->

<text x="245" y="155" class="label">
    FOLLOWERS
</text>

<text x="245" y="195" class="value">
    {followers}
</text>

<text x="245" y="220" class="small">
    NETWORK
</text>

<!-- FOLLOWING -->

<text x="435" y="155" class="label">
    FOLLOWING
</text>

<text x="435" y="195" class="value">
    {following}
</text>

<text x="435" y="220" class="small">
    CONNECTIONS
</text>

<line x1="55" y1="250"
      x2="595" y2="250"
      stroke="#272741"/>

<text x="55" y="290" class="label">
    SYSTEM STATUS
</text>

<text x="55" y="325" class="cyan value">
    ACTIVE
</text>

<text x="55" y="350" class="small">
    AI ENGINEERING / SOFTWARE DEVELOPMENT
</text>

<text x="55" y="385" class="small">
    DATA STREAM // LIVE
</text>

<circle cx="565" cy="382"
        r="5"
        class="cyan pulse glow"/>

</svg>
"""


def language_card(languages):
    width = 650
    height = 430

    colors = [
        "#00e5ff",
        "#ff2bd6",
        "#39ff88",
        "#a855f7",
        "#ffb020",
        "#ff4d6d",
        "#38bdf8",
        "#f8fafc",
    ]

    language_values = percentage_values(languages)

    rows = []

    for index, (language, percentage) in enumerate(language_values):
        y = 130 + index * 34

        color = colors[index % len(colors)]

        rows.append(
            f"""
            <text x="55" y="{y}" class="language">
                {escape(language)}
            </text>

            <rect x="190"
                  y="{y - 14}"
                  width="320"
                  height="8"
                  rx="4"
                  fill="#202033"/>

            <rect x="190"
                  y="{y - 14}"
                  width="{320 * percentage / 100:.2f}"
                  height="8"
                  rx="4"
                  fill="{color}"
                  class="glow"/>

            <text x="535"
                  y="{y}"
                  class="percentage">
                {percentage:.1f}%
            </text>
            """
        )

    if not language_values:
        rows.append(
            """
            <text x="55" y="180" class="language">
                NO LANGUAGE DATA
            </text>
            """
        )

    return f"""
<svg xmlns="http://www.w3.org/2000/svg"
     width="{width}"
     height="{height}"
     viewBox="0 0 {width} {height}">

<style>
    .title {{
        font-family: monospace;
        font-size: 25px;
        font-weight: bold;
        fill: #ffffff;
    }}

    .label {{
        font-family: monospace;
        font-size: 14px;
        fill: #8b9bb4;
        letter-spacing: 2px;
    }}

    .language {{
        font-family: monospace;
        font-size: 14px;
        font-weight: bold;
        fill: #ffffff;
    }}

    .percentage {{
        font-family: monospace;
        font-size: 13px;
        fill: #8b9bb4;
    }}

    .glow {{
        filter: url(#glow);
    }}

    .pulse {{
        animation: pulse 2s infinite;
    }}

    .scan {{
        animation: scan 4s linear infinite;
    }}

    @keyframes pulse {{
        0%, 100% {{ opacity: .45; }}
        50% {{ opacity: 1; }}
    }}

    @keyframes scan {{
        from {{ transform: translateY(-20px); }}
        to {{ transform: translateY(450px); }}
    }}
</style>

<defs>

    <linearGradient id="background" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#090914"/>
        <stop offset="55%" stop-color="#111124"/>
        <stop offset="100%" stop-color="#07070d"/>
    </linearGradient>

    <linearGradient id="line" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#ff2bd6"/>
        <stop offset="50%" stop-color="#00e5ff"/>
        <stop offset="100%" stop-color="#39ff88"/>
    </linearGradient>

    <filter id="glow">
        <feGaussianBlur stdDeviation="4" result="blur"/>
        <feMerge>
            <feMergeNode in="blur"/>
            <feMergeNode in="SourceGraphic"/>
        </feMerge>
    </filter>

    <pattern id="grid"
             width="30"
             height="30"
             patternUnits="userSpaceOnUse">
        <path d="M 30 0 L 0 0 0 30"
              fill="none"
              stroke="#ffffff"
              stroke-opacity=".035"/>
    </pattern>

</defs>

<rect width="{width}"
      height="{height}"
      rx="22"
      fill="url(#background)"
      stroke="#24243d"
      stroke-width="2"/>

<rect width="{width}"
      height="{height}"
      rx="22"
      fill="url(#grid)"/>

<rect x="0"
      y="0"
      width="{width}"
      height="3"
      fill="url(#line)"
      class="glow"/>

<rect x="0"
      y="-30"
      width="{width}"
      height="20"
      fill="#00e5ff"
      opacity=".08"
      class="scan"/>

<text x="35" y="55" class="label">
    LANGUAGE // MATRIX
</text>

<text x="35" y="92" class="title">
    MOST USED LANGUAGES
</text>

<circle cx="590"
        cy="48"
        r="7"
        fill="#39ff88"
        class="pulse glow"/>

<line x1="35"
      y1="112"
      x2="615"
      y2="112"
      stroke="url(#line)"
      stroke-opacity=".5"/>

{''.join(rows)}

</svg>
"""


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching GitHub profile...")

    user = get_user()

    print("Fetching repositories...")

    repositories = get_repositories()

    print(f"Found {len(repositories)} repositories.")

    print("Calculating language distribution...")

    languages = calculate_languages(repositories)

    print("Languages:")

    for language, amount in languages.most_common():
        print(f"  {language}: {amount}")

    stats_svg = stat_card(user)
    languages_svg = language_card(languages)

    (OUTPUT_DIR / "stats.svg").write_text(
        stats_svg,
        encoding="utf-8",
    )

    (OUTPUT_DIR / "top-langs.svg").write_text(
        languages_svg,
        encoding="utf-8",
    )

    print("Generated:")
    print("  profile/stats.svg")
    print("  profile/top-langs.svg")


if __name__ == "__main__":
    main()
