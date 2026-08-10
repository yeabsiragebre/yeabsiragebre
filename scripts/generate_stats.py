import os
from pathlib import Path
from xml.sax.saxutils import escape

import requests


# ============================================================
# CONFIGURATION
# ============================================================

USERNAME = "yeabsiragebre"
TOKEN = os.environ.get("GITHUB_TOKEN")

API = "https://api.github.com"

OUTPUT_DIR = Path("profile")
STATS_FILE = OUTPUT_DIR / "stats.svg"
LANGUAGES_FILE = OUTPUT_DIR / "top-langs.svg"

HEADERS = {
    "Accept": "application/vnd.github+json",
}

if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


# ============================================================
# GITHUB API
# ============================================================

def github_get(url, params=None):
    response = requests.get(
        url,
        headers=HEADERS,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# GET USER DATA
# ============================================================

def get_user():
    return github_get(
        f"{API}/users/{USERNAME}"
    )


# ============================================================
# GET REPOSITORIES
# ============================================================

def get_repositories():
    repositories = []

    page = 1

    while True:

        data = github_get(
            f"{API}/users/{USERNAME}/repos",
            params={
                "per_page": 100,
                "page": page,
                "sort": "updated",
            },
        )

        if not data:
            break

        repositories.extend(data)

        if len(data) < 100:
            break

        page += 1

    return repositories


# ============================================================
# GET LANGUAGE DATA
# ============================================================

def get_languages(repositories):

    languages = {}

    for repository in repositories:

        name = repository.get("name")

        if not name:
            continue

        try:
            data = github_get(
                f"{API}/repos/{USERNAME}/{name}/languages"
            )
        except requests.RequestException:
            continue

        for language, amount in data.items():

            languages[language] = (
                languages.get(language, 0) + amount
            )

    return languages


# ============================================================
# SVG HELPERS
# ============================================================

def text(
    x,
    y,
    value,
    size=14,
    color="#EDE9FE",
    weight="400",
    anchor="start",
):
    return (
        f'<text '
        f'x="{x}" '
        f'y="{y}" '
        f'font-family="JetBrains Mono, '
        f"DejaVu Sans Mono, monospace\" "
        f'font-size="{size}px" '
        f'font-weight="{weight}" '
        f'fill="{color}" '
        f'text-anchor="{anchor}">'
        f'{escape(str(value))}'
        f'</text>'
    )


def rounded_rect(
    x,
    y,
    width,
    height,
    radius=12,
    fill="#0A0D14",
    stroke="#8B5CF6",
    opacity="1",
):
    return (
        f'<rect '
        f'x="{x}" '
        f'y="{y}" '
        f'width="{width}" '
        f'height="{height}" '
        f'rx="{radius}" '
        f'fill="{fill}" '
        f'fill-opacity="{opacity}" '
        f'stroke="{stroke}" '
        f'stroke-opacity="0.32"/>'
    )


# ============================================================
# METRIC CARD
# ============================================================

def metric_card(
    x,
    title,
    value,
    subtitle,
):
    return f"""
    {rounded_rect(
        x,
        115,
        190,
        105,
    )}

    {text(
        x + 17,
        143,
        title,
        9,
        "#A78BFA",
        "700",
    )}

    {text(
        x + 17,
        181,
        value,
        30,
        "#F5F3FF",
        "700",
    )}

    {text(
        x + 17,
        202,
        subtitle,
        8,
        "#6B7280",
        "400",
    )}
    """


# ============================================================
# FUTURISTIC BACKGROUND
# ============================================================

def background_defs():

    return """
    <defs>

        <linearGradient
            id="background"
            x1="0"
            y1="0"
            x2="1"
            y2="1">

            <stop
                offset="0%"
                stop-color="#020204"/>

            <stop
                offset="50%"
                stop-color="#0A0D14"/>

            <stop
                offset="100%"
                stop-color="#1A0830"/>

        </linearGradient>


        <linearGradient
            id="purpleGradient"
            x1="0"
            y1="0"
            x2="1"
            y2="0">

            <stop
                offset="0%"
                stop-color="#6D28D9"/>

            <stop
                offset="50%"
                stop-color="#A855F7"/>

            <stop
                offset="100%"
                stop-color="#D8B4FE"/>

        </linearGradient>


        <filter
            id="purpleGlow"
            x="-50%"
            y="-50%"
            width="200%"
            height="200%">

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


        <pattern
            id="grid"
            width="32"
            height="32"
            patternUnits="userSpaceOnUse">

            <path
                d="M32 0H0V32"
                fill="none"
                stroke="#8B5CF6"
                stroke-opacity="0.055"/>

        </pattern>

    </defs>
    """


# ============================================================
# ACTIVITY VISUAL
# ============================================================

def activity_visual():

    shades = [
        "#241044",
        "#35145F",
        "#4C1D95",
        "#6D28D9",
        "#7C3AED",
        "#8B5CF6",
        "#A855F7",
        "#C084FC",
    ]

    blocks = []

    for index in range(25):

        x = 45 + index * 33

        shade = shades[
            (index * 3) % len(shades)
        ]

        blocks.append(
            f"""
            <rect
                x="{x}"
                y="278"
                width="25"
                height="9"
                rx="3"
                fill="{shade}"
            />
            """
        )

    return "\n".join(blocks)


# ============================================================
# STATS SVG
# ============================================================

def generate_stats_svg(
    user,
    repositories,
):

    public_repositories = user.get(
        "public_repos",
        0,
    )

    followers = user.get(
        "followers",
        0,
    )

    stars = sum(
        repository.get(
            "stargazers_count",
            0,
        )
        for repository in repositories
    )

    forks = sum(
        repository.get(
            "forks_count",
            0,
        )
        for repository in repositories
    )

    svg = f"""<svg
    xmlns="http://www.w3.org/2000/svg"
    width="900"
    height="430"
    viewBox="0 0 900 430">

    {background_defs()}

    <!-- BACKGROUND -->

    <rect
        width="900"
        height="430"
        rx="18"
        fill="url(#background)"
        stroke="#8B5CF6"
        stroke-opacity="0.55"
        stroke-width="1.5"/>

    <rect
        x="1"
        y="1"
        width="898"
        height="428"
        rx="17"
        fill="url(#grid)"/>


    <!-- NEON TOP LINE -->

    <rect
        x="40"
        y="27"
        width="820"
        height="2"
        fill="url(#purpleGradient)"
        filter="url(#purpleGlow)"/>


    <!-- HEADER -->

    {text(
        45,
        65,
        "◈ YEABSIRA // GITHUB CORE",
        18,
        "#F5F3FF",
        "700",
    )}

    {text(
        855,
        65,
        "● ONLINE",
        10,
        "#C084FC",
        "700",
        "end",
    )}

    {text(
        45,
        88,
        "AI ENGINEERING · SOFTWARE DEVELOPMENT · COMPUTER SCIENCE",
        9,
        "#6B7280",
        "400",
    )}


    <!-- METRIC CARDS -->

    {metric_card(
        45,
        "REPOSITORIES",
        public_repositories,
        "PUBLIC PROJECTS",
    )}

    {metric_card(
        255,
        "FOLLOWERS",
        followers,
        "NETWORK",
    )}

    {metric_card(
        465,
        "STARS",
        stars,
        "PROJECT IMPACT",
    )}

    {metric_card(
        675,
        "FORKS",
        forks,
        "COLLABORATION",
    )}


    <!-- ACTIVITY -->

    {text(
        45,
        258,
        "SYSTEM ACTIVITY",
        10,
        "#A78BFA",
        "700",
    )}

    {text(
        855,
        258,
        "LIVE DATA",
        8,
        "#6B7280",
        "700",
        "end",
    )}

    <g filter="url(#purpleGlow)">
        {activity_visual()}
    </g>


    <!-- DIVIDER -->

    <rect
        x="45"
        y="325"
        width="810"
        height="1"
        fill="#8B5CF6"
        fill-opacity="0.25"/>


    <!-- FOOTER -->

    {text(
        45,
        355,
        "FOCUS: LLMs / RAG / AI AGENTS / BACKEND",
        9,
        "#A78BFA",
        "700",
    )}

    {text(
        855,
        355,
        "SYSTEM STATUS: OPERATIONAL",
        9,
        "#A78BFA",
        "700",
        "end",
    )}

    {text(
        45,
        390,
        "BUILDING INTELLIGENT SYSTEMS — ONE COMMIT AT A TIME",
        8,
        "#4B5563",
        "400",
    )}

    {text(
        855,
        390,
        "v2.0",
        8,
        "#4B5563",
        "700",
        "end",
    )}

    </svg>
    """

    return svg


# ============================================================
# LANGUAGE SVG
# ============================================================

def generate_languages_svg(
    languages,
):

    total = sum(
        languages.values()
    )

    language_data = []

    if total > 0:

        sorted_languages = sorted(
            languages.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        for language, amount in sorted_languages[:8]:

            percentage = (
                amount / total
            ) * 100

            language_data.append(
                (
                    language,
                    percentage,
                )
            )

    rows = []

    y = 125

    for language, percentage in language_data:

        bar_width = max(
            5,
            int(
                300
                * percentage
                / 100
            ),
        )

        rows.append(
            f"""
            {text(
                55,
                y,
                language.upper(),
                10,
                "#EDE9FE",
                "700",
            )}

            <rect
                x="200"
                y="{y - 12}"
                width="300"
                height="8"
                rx="4"
                fill="#21152F"/>

            <rect
                x="200"
                y="{y - 12}"
                width="{bar_width}"
                height="8"
                rx="4"
                fill="url(#purpleGradient)"
                filter="url(#purpleGlow)"/>

            {text(
                525,
                y,
                f"{percentage:.1f}%",
                9,
                "#C084FC",
                "700",
            )}
            """
        )

        y += 40

    if not rows:

        rows.append(
            text(
                55,
                125,
                "NO LANGUAGE DATA AVAILABLE",
                10,
                "#6B7280",
                "700",
            )
        )

    svg = f"""<svg
    xmlns="http://www.w3.org/2000/svg"
    width="620"
    height="430"
    viewBox="0 0 620 430">

    {background_defs()}


    <!-- BACKGROUND -->

    <rect
        width="620"
        height="430"
        rx="18"
        fill="url(#background)"
        stroke="#8B5CF6"
        stroke-opacity="0.55"
        stroke-width="1.5"/>

    <rect
        x="1"
        y="1"
        width="618"
        height="428"
        rx="17"
        fill="url(#grid)"/>


    <!-- HEADER -->

    {text(
        35,
        55,
        "◈ LANGUAGE MATRIX",
        18,
        "#F5F3FF",
        "700",
    )}

    {text(
        585,
        55,
        "CODEBASE",
        8,
        "#6B7280",
        "700",
        "end",
    )}


    <!-- NEON LINE -->

    <rect
        x="35"
        y="75"
        width="550"
        height="2"
        fill="url(#purpleGradient)"
        filter="url(#purpleGlow)"/>


    <!-- LANGUAGE ROWS -->

    {"".join(rows)}


    <!-- FOOTER -->

    <rect
        x="35"
        y="375"
        width="550"
        height="1"
        fill="#8B5CF6"
        fill-opacity="0.25"/>

    {text(
        35,
        400,
        "LANGUAGE DISTRIBUTION",
        8,
        "#6B7280",
        "700",
    )}

    {text(
        585,
        400,
        "ANALYSIS COMPLETE",
        8,
        "#C084FC",
        "700",
        "end",
    )}

    </svg>
    """

    return svg


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=========================================="
    )

    print(
        " FUTURISTIC GITHUB STATS GENERATOR"
    )

    print(
        "=========================================="
    )

    print(
        f"User: {USERNAME}"
    )

    print(
        "Fetching GitHub profile..."
    )

    user = get_user()

    print(
        "Fetching repositories..."
    )

    repositories = get_repositories()

    print(
        f"Repositories found: {len(repositories)}"
    )

    print(
        "Analyzing languages..."
    )

    languages = get_languages(
        repositories
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "Generating futuristic stats.svg..."
    )

    stats_svg = generate_stats_svg(
        user,
        repositories,
    )

    STATS_FILE.write_text(
        stats_svg,
        encoding="utf-8",
    )

    print(
        "Generating futuristic top-langs.svg..."
    )

    languages_svg = generate_languages_svg(
        languages,
    )

    LANGUAGES_FILE.write_text(
        languages_svg,
        encoding="utf-8",
    )

    print(
        "=========================================="
    )

    print(
        " FUTURISTIC SVG GENERATION COMPLETE"
    )

    print(
        "=========================================="
    )

    print(
        f"Created: {STATS_FILE}"
    )

    print(
        f"Created: {LANGUAGES_FILE}"
    )


if __name__ == "__main__":
    main()
