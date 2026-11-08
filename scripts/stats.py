import collections
import json
import os
import random
import sys
import urllib.error
import urllib.request
from common import (
    BG1,
    BG2,
    PURPLE,
    LIGHT,
    PALE,
    DIM,
    DEEP,
    cube,
    svg,
    text_width,
    xml_escape,
)

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

# Palette ramp for city blocks (lit from top-left)
RAMP = {
    1: {"top": "#7842c8", "left": "#562a94", "right": "#3c1a6b"},
    2: {"top": "#9f67ee", "left": "#7843c6", "right": "#552899"},
    3: {"top": "#c598fb", "left": "#9c60e5", "right": "#7139b4"},
    4: {"top": "#f4ecff", "left": "#cba5ff", "right": "#9763e4"},
}

LANG_PALETTE = [
    "#9955e7",  # Brand PURPLE
    "#c9a8ff",  # LIGHT
    "#7c3aed",  # Indigo violet
    "#e879f9",  # Magenta pink-purple
    "#8b5cf6",  # Bright violet
    "#d946ef",  # Fuchsia purple
    "#581c87",  # Deep purple for Other
]


def ensure_assets_dir():
    os.makedirs(ASSETS_DIR, exist_ok=True)


def calculate_streaks(counts: list[int]) -> tuple[int, int]:
    """Calculate current and longest streaks.
    Streak is alive if count > 0 today, or count == 0 today but count > 0 yesterday."""
    if not counts:
        return 0, 0
    longest = 0
    cur = 0
    for c in counts:
        if c > 0:
            cur += 1
            if cur > longest:
                longest = cur
        else:
            cur = 0

    cur_streak = 0
    idx = len(counts) - 1
    if counts[idx] == 0:
        if idx > 0 and counts[idx - 1] > 0:
            idx -= 1
        else:
            return 0, longest

    while idx >= 0 and counts[idx] > 0:
        cur_streak += 1
        idx -= 1

    return cur_streak, longest


def build_city_svg(grid: list[list[int]], all_counts: list[int], total: int) -> str:
    """assets/city.svg, 850x330. 3D isometric city representing 53 weeks x 7 days."""
    w, h = 850, 330
    tw = 13.0
    th = 6.5
    hw = tw / 2.0
    hh = th / 2.0

    # Center horizontally: (ox - 45.5 + ox + 344.5) / 2 = 425 => ox = 275.5
    ox = 275.5
    # oy = 118 leaves ~70px above for tallest block (h=47)
    oy = 118.0

    nz = sorted([c for c in all_counts if c > 0])
    if nz:
        q1 = nz[len(nz) // 4]
        q2 = nz[len(nz) // 2]
        q3 = nz[(len(nz) * 3) // 4]
    else:
        q1 = q2 = q3 = 1

    def get_level(c):
        if c <= 0:
            return 0
        if c <= q1:
            return 1
        if c <= q2:
            return 2
        if c <= q3:
            return 3
        return 4

    blocks = []
    for col in range(53):
        for row in range(7):
            cnt = grid[col][row]
            bx = ox + (col - row) * hw
            by = oy + (col + row) * hh
            blocks.append({"col": col, "row": row, "count": cnt, "bx": bx, "by": by})

    # Sort back-to-front (painter's order: increasing col+row)
    blocks.sort(key=lambda b: (b["col"] + b["row"], b["col"]))

    blocks_svg = []
    for b in blocks:
        col = b["col"]
        bx = b["bx"]
        by = b["by"]
        cnt = b["count"]
        lvl = get_level(cnt)

        delay_ms = col * 25

        if lvl == 0:
            # Flat dark tile
            pts = f"{bx:.1f},{by - hh:.1f} {bx + hw:.1f},{by:.1f} {bx:.1f},{by + hh:.1f} {bx - hw:.1f},{by:.1f}"
            tile = f'<polygon points="{pts}" fill="{DEEP}" fill-opacity="0.35"/>'
        else:
            bh = round(3.0 + min(cnt, 20) * 2.2, 1)
            colors = RAMP[lvl]

            top_pts = f"{bx:.1f},{by - hh - bh:.1f} {bx + hw:.1f},{by - bh:.1f} {bx:.1f},{by + hh - bh:.1f} {bx - hw:.1f},{by - bh:.1f}"
            left_pts = f"{bx - hw:.1f},{by - bh:.1f} {bx:.1f},{by + hh - bh:.1f} {bx:.1f},{by + hh:.1f} {bx - hw:.1f},{by:.1f}"
            right_pts = f"{bx:.1f},{by + hh - bh:.1f} {bx + hw:.1f},{by - bh:.1f} {bx + hw:.1f},{by:.1f} {bx:.1f},{by + hh:.1f}"

            tile = (
                f'<polygon points="{left_pts}" fill="{colors["left"]}"/>\n'
                f'<polygon points="{right_pts}" fill="{colors["right"]}"/>\n'
                f'<polygon points="{top_pts}" fill="{colors["top"]}"/>'
            )

        blocks_svg.append(f'<g class="b" style="animation-delay: {delay_ms}ms;">\n{tile}\n</g>')

    glow_ellipse = f'<ellipse cx="425" cy="212" rx="210" ry="85" fill="{PURPLE}" opacity="0.12" filter="url(#glow)"/>'

    title_left = f'<text x="28" y="44" font-size="22" fill="{LIGHT}">Last 12 months</text>'
    total_str = f"{total:,}"
    title_right = (
        f'<text x="822" y="44" font-size="22" text-anchor="end">'
        f'<tspan fill="{PALE}">{total_str}</tspan> <tspan fill="{DIM}">contributions</tspan>'
        f"</text>"
    )

    body = f"{glow_ellipse}\n{title_left}\n{title_right}\n" + "\n".join(blocks_svg)
    extra_css = ".b{animation:rise .6s ease-out both;}@keyframes rise{from{transform:translateY(14px);opacity:0;}to{transform:none;opacity:1;}}"
    font_text = f"Last 12 months {total_str} contributions"

    return svg(w, h, body, text_for_font=font_text, extra_css=extra_css)


def build_cards_svg(total: int, cur_streak: int, longest_streak: int) -> str:
    """assets/cards.svg, 850x150. Three cards: Total, Current streak, Longest streak."""
    w, h = 850, 150
    sections = [
        ("Total", total, LIGHT, PURPLE, DEEP),
        ("Current streak", cur_streak, "#e082db", "#b742b0", "#791f74"),
        ("Longest streak", longest_streak, "#9d92fc", "#6d5dfc", "#4332c8"),
    ]

    col_centers = [141.6, 425.0, 708.3]
    dividers = [
        f'<line x1="283.3" y1="24" x2="283.3" y2="126" stroke="{PURPLE}" stroke-opacity="0.25" stroke-width="1"/>',
        f'<line x1="566.6" y1="24" x2="566.6" y2="126" stroke="{PURPLE}" stroke-opacity="0.25" stroke-width="1"/>',
    ]

    body_parts = list(dividers)
    all_text_parts = []

    for i, (label, val, top_c, left_c, right_c) in enumerate(sections):
        cx = col_centers[i]
        val_str = f"{val:,}"
        all_text_parts.extend([label, val_str])

        val_w = text_width(val_str, 56)
        s = 14
        dx = s * 0.8660254037844386
        cube_w = dx * 2.0
        gap = 10.0
        total_w = cube_w + gap + val_w

        start_x = cx - total_w / 2.0
        cube_cx = start_x + dx
        num_x = start_x + cube_w + gap

        cube_markup = cube(cube_cx, 60, s, top_c, left_c, right_c)
        num_text = f'<text x="{num_x:.1f}" y="78" font-size="56" fill="{PALE}" filter="url(#glow)">{val_str}</text>'
        lbl_text = f'<text x="{cx:.1f}" y="112" font-size="18" fill="{DIM}" text-anchor="middle">{label}</text>'

        card_group = f"<g>\n{cube_markup}\n{num_text}\n{lbl_text}\n</g>"
        body_parts.append(card_group)

    font_text = " ".join(all_text_parts)
    return svg(w, h, "\n".join(body_parts), text_for_font=font_text)


def build_langs_svg(langs: list[tuple[str, int]]) -> str:
    """assets/langs.svg, 850x150. Horizontal stacked bar + 2-row legend."""
    w, h = 850, 150
    bar_w = 770.0
    bar_h = 22.0
    bar_x = 40.0
    bar_y = 52.0

    total_bytes = sum(sz for _, sz in langs) if langs else 1

    # Segments and legend
    segments_svg = []
    legend_svg = []
    cur_x = bar_x
    all_text_parts = ["Languages"]

    # Calculate segment widths
    seg_widths = []
    for name, sz in langs:
        fraction = sz / total_bytes
        seg_widths.append(round(bar_w * fraction, 1))

    # Adjust last segment to match bar_w exactly
    if seg_widths:
        seg_widths[-1] = round(bar_w - sum(seg_widths[:-1]), 1)

    for i, ((name, sz), seg_w) in enumerate(zip(langs, seg_widths)):
        color = LANG_PALETTE[i % len(LANG_PALETTE)]
        pct = (sz / total_bytes) * 100.0
        pct_str = f"{pct:.1f}%"
        all_text_parts.extend([name, pct_str])

        # Segment with width animation from 0
        seg_rect = (
            f'<rect x="{cur_x:.1f}" y="{bar_y}" width="{seg_w:.1f}" height="{bar_h}" fill="{color}">\n'
            f'  <animate attributeName="width" from="0" to="{seg_w:.1f}" dur="0.8s" fill="freeze"/>\n'
            f"</rect>"
        )
        segments_svg.append(seg_rect)
        cur_x += seg_w

        # Legend position: 2 rows of up to 4 items
        row = i // 4
        col = i % 4
        item_x = 40.0 + col * 192.5
        item_y = 104.0 if row == 0 else 128.0

        dot = f'<circle cx="{item_x + 6:.1f}" cy="{item_y - 5:.1f}" r="5" fill="{color}"/>'
        leg_text = (
            f'<text x="{item_x + 18:.1f}" y="{item_y:.1f}" font-size="14">'
            f'<tspan fill="{PALE}">{xml_escape(name)}</tspan> <tspan fill="{DIM}">{pct_str}</tspan>'
            f"</text>"
        )
        legend_svg.append(f"<g>\n{dot}\n{leg_text}\n</g>")

    clip_id = "langs-bar-clip"
    defs = f'<clipPath id="{clip_id}"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="6" ry="6"/></clipPath>'

    title_svg = f'<text x="40" y="38" font-size="22" fill="{LIGHT}">Languages</text>'
    bar_group = f'<g clip-path="url(#{clip_id})">\n' + "\n".join(segments_svg) + "\n</g>"
    legend_group = f"<g>\n" + "\n".join(legend_svg) + "\n</g>"

    body = f"{title_svg}\n{bar_group}\n{legend_group}"
    font_text = " ".join(all_text_parts)
    return svg(w, h, body, text_for_font=font_text, extra_defs=defs)


def generate_demo_data():
    """Generates deterministic fake data using random.Random(7)."""
    rng = random.Random(7)
    grid = [[0 for _ in range(7)] for _ in range(53)]
    all_counts = []

    for col in range(53):
        r = rng.random()
        if r < 0.25:  # quiet week
            p_active, max_c = 0.25, 4
        elif r < 0.80:  # normal week
            p_active, max_c = 0.65, 10
        else:  # burst week
            p_active, max_c = 0.90, 20

        for row in range(7):
            if rng.random() < p_active:
                cnt = rng.randint(1, max_c)
            else:
                cnt = 0
            grid[col][row] = cnt
            all_counts.append(cnt)

    total_contributions = sum(all_counts)
    cur_streak, longest_streak = calculate_streaks(all_counts)

    demo_langs = [
        ("TypeScript", 450000),
        ("Java", 320000),
        ("Python", 195000),
        ("Rust", 110000),
        ("C#", 75000),
        ("Swift", 40000),
        ("Other", 30000),
    ]
    return grid, all_counts, total_contributions, cur_streak, longest_streak, demo_langs


def fetch_real_data(username: str, token: str):
    """Fetches contribution calendar and language stats from GitHub GraphQL API."""
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                weekday
              }
            }
          }
        }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          nodes {
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                }
              }
            }
          }
        }
      }
    }
    """
    req_data = json.dumps({"query": query, "variables": {"login": username}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=req_data,
        headers={
            "Authorization": f"bearer {token}",
            "User-Agent": "spananide-profile-stats",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error fetching GitHub data: {e}", file=sys.stderr)
        sys.exit(1)

    if "errors" in body:
        print(f"GitHub GraphQL errors: {body['errors']}", file=sys.stderr)
        sys.exit(1)

    user_data = body.get("data", {}).get("user")
    if not user_data:
        print(f"User {username} not found or no data returned.", file=sys.stderr)
        sys.exit(1)

    calendar = user_data.get("contributionsCollection", {}).get("contributionCalendar", {})
    total_contributions = calendar.get("totalContributions", 0)
    weeks_data = calendar.get("weeks", [])

    if len(weeks_data) > 53:
        weeks_data = weeks_data[-53:]
    while len(weeks_data) < 53:
        weeks_data.insert(0, {"contributionDays": []})

    grid = [[0 for _ in range(7)] for _ in range(53)]
    all_counts = []
    for col, w in enumerate(weeks_data):
        for d in w.get("contributionDays", []):
            weekday = d.get("weekday", 0)
            count = d.get("contributionCount", 0)
            if 0 <= weekday < 7:
                grid[col][weekday] = count
            all_counts.append(count)

    cur_streak, longest_streak = calculate_streaks(all_counts)

    lang_sizes = collections.defaultdict(int)
    repos = user_data.get("repositories", {}).get("nodes", [])
    for repo in repos:
        edges = repo.get("languages", {}).get("edges", [])
        for edge in edges:
            name = edge.get("node", {}).get("name", "")
            size = edge.get("size", 0)
            if name and size > 0:
                lang_sizes[name] += size

    sorted_langs = sorted(lang_sizes.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_langs) > 6:
        top6 = sorted_langs[:6]
        other_size = sum(sz for _, sz in sorted_langs[6:])
        langs_list = top6 + [("Other", other_size)]
    else:
        langs_list = sorted_langs

    return grid, all_counts, total_contributions, cur_streak, longest_streak, langs_list


def main():
    demo_mode = "--demo" in sys.argv

    if demo_mode:
        print("Running in DEMO mode...")
        grid, all_counts, total, cur_streak, longest_streak, langs = generate_demo_data()
    else:
        token = os.environ.get("GH_TOKEN")
        username = os.environ.get("USERNAME")
        if not token or not username:
            print("Error: Both GH_TOKEN and USERNAME environment variables must be set.", file=sys.stderr)
            sys.exit(1)
        grid, all_counts, total, cur_streak, longest_streak, langs = fetch_real_data(username, token)

    city_svg = build_city_svg(grid, all_counts, total)
    cards_svg = build_cards_svg(total, cur_streak, longest_streak)
    langs_svg = build_langs_svg(langs)

    # Only write files after all three are successfully generated
    ensure_assets_dir()
    for name, content in [("city.svg", city_svg), ("cards.svg", cards_svg), ("langs.svg", langs_svg)]:
        out_path = os.path.join(ASSETS_DIR, name)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Wrote", out_path)


if __name__ == "__main__":
    main()
