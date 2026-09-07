#!/usr/bin/env python3
"""Generate a static language-stats SVG from the user's public repos.

Replaces the github-readme-stats.vercel.app widget, which goes down whenever
the maintainer's shared Vercel deployment hits its usage limits. Run on a
schedule by .github/workflows/update-languages.yml so the card stays fresh
without depending on any third-party service at render time.
"""

import json
import os
import sys
import urllib.request

USERNAME = os.environ.get("GITHUB_USERNAME", "Gor-2001")
TOKEN = os.environ.get("GITHUB_TOKEN")
LANGS_COUNT = 6
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "languages.svg")

# Nord "frost" palette (nordtheme.com), cycled by rank so the card reads as a
# cohesive blue-toned set rather than each language's real linguist color.
NORD_PALETTE = [
    "#88C0D0",  # nord8 - frost cyan
    "#81A1C1",  # nord9 - frost blue
    "#5E81AC",  # nord10 - frost deep blue
    "#8FBCBB",  # nord7 - frost teal
    "#B48EAD",  # nord15 - purple accent
    "#4C566A",  # nord3 - muted slate
]
NORD_BG = "#2E3440"        # nord0
NORD_BORDER = "#5E81AC"    # nord10
NORD_TITLE = "#88C0D0"     # nord8
NORD_TEXT = "#D8DEE9"      # nord4


def color_for_rank(index):
    return NORD_PALETTE[index % len(NORD_PALETTE)]


def api_get(url):
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        request.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


def fetch_repos(username):
    repos = []
    page = 1
    while True:
        batch = api_get(f"https://api.github.com/users/{username}/repos?per_page=100&page={page}")
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return [r for r in repos if not r.get("fork") and not r.get("archived")]


def fetch_language_totals(username, repos):
    totals = {}
    for repo in repos:
        langs = api_get(f"https://api.github.com/repos/{username}/{repo['name']}/languages")
        for lang, byte_count in langs.items():
            totals[lang] = totals.get(lang, 0) + byte_count
    return totals


def estimate_text_width(text, font_size):
    return len(text) * font_size * 0.58


def build_svg(top_langs, total_bytes):
    padding = 18
    title = "My Programming Languages"
    title_font_size = 14
    legend_font_size = 12
    dot_radius = 4
    dot_text_gap = 6
    item_gap = 20
    bar_height = 8

    labels = [f"{name} ({byte_count / total_bytes * 100:.2f}%)" for name, byte_count in top_langs]
    label_widths = [estimate_text_width(label, legend_font_size) for label in labels]
    legend_row_width = (
        sum(label_widths)
        + len(labels) * (dot_radius * 2 + dot_text_gap)
        + item_gap * (len(labels) - 1)
    )
    title_row_width = estimate_text_width(title, title_font_size)

    width = int(max(title_row_width, legend_row_width) + padding * 2)
    bar_width = width - padding * 2
    bar_y = 34
    legend_y = bar_y + bar_height + 24
    height = legend_y + 12

    bar_segments = []
    x = padding
    for i, (name, byte_count) in enumerate(top_langs):
        seg_width = byte_count / total_bytes * bar_width
        bar_segments.append(
            f'<rect x="{x:.2f}" y="{bar_y}" width="{seg_width:.2f}" '
            f'height="{bar_height}" fill="{color_for_rank(i)}" />'
        )
        x += seg_width

    legend_items = []
    x = padding
    for i, label in enumerate(labels):
        color = color_for_rank(i)
        legend_items.append(
            f'<circle cx="{x + dot_radius:.2f}" cy="{legend_y - 4}" r="{dot_radius}" fill="{color}" />'
            f'<text x="{x + dot_radius * 2 + dot_text_gap:.2f}" y="{legend_y}" class="legend">{label}</text>'
        )
        x += dot_radius * 2 + dot_text_gap + label_widths[i] + item_gap

    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" \
xmlns="http://www.w3.org/2000/svg" font-family="'Segoe UI', Ubuntu, Sans-Serif">
  <defs>
    <clipPath id="bar-clip">
      <rect x="{padding}" y="{bar_y}" width="{bar_width}" height="{bar_height}" rx="{bar_height / 2}" />
    </clipPath>
  </defs>
  <style>
    .bg {{ fill: {NORD_BG}; stroke: {NORD_BORDER}; stroke-width: 1; rx: 8; }}
    .title {{ fill: {NORD_TITLE}; font-size: {title_font_size}px; font-weight: 600; }}
    .legend {{ fill: {NORD_TEXT}; font-size: {legend_font_size}px; }}
  </style>
  <rect class="bg" x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" />
  <text x="{padding}" y="20" class="title">{title}</text>
  <g clip-path="url(#bar-clip)">
    {"".join(bar_segments)}
  </g>
  {"".join(legend_items)}
</svg>
'''


def main():
    repos = fetch_repos(USERNAME)
    totals = fetch_language_totals(USERNAME, repos)
    if not totals:
        print("No language data found; leaving existing SVG untouched.", file=sys.stderr)
        return

    total_bytes = sum(totals.values())
    top_langs = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:LANGS_COUNT]

    svg = build_svg(top_langs, total_bytes)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(svg)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
