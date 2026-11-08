import os
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


def ensure_assets_dir():
    os.makedirs(ASSETS_DIR, exist_ok=True)


def build_hero():
    """assets/hero.svg, 850x150. Typing animation with 3 lines, cursor, and floating cubes."""
    w, h = 850, 150
    lines = [
        ("building things on a Raspberry Pi at 3 am", 52, 0.0, 2.4, PALE, False),
        ("Minecraft mods · bots · web", 90, 2.6, 4.4, PALE, False),
        ("spanani.de", 128, 4.6, 5.6, LIGHT, True),
    ]

    prompt = "> "
    prompt_w = text_width(prompt, 30)
    left_pad = 40.0
    text_start_x = left_pad + prompt_w

    total_t = 14.0

    # Keyframes helper for clip rect width
    def make_clip_keyframes(text, st, en):
        n = len(text)
        kt = []
        vals = []
        if st > 0:
            kt.append(0.0)
            vals.append(0.0)
            kt.append(round(st / total_t, 4))
            vals.append(0.0)
        for i in range(n + 1):
            t = st + (en - st) * (i / n)
            kt.append(round(t / total_t, 4))
            vals.append(text_width(text[:i], 30))
        # hold until 11.5s
        kt.append(round(11.5 / total_t, 4))
        vals.append(vals[-1])
        # reset at 12.5s
        kt.append(round(12.5 / total_t, 4))
        vals.append(0.0)
        kt.append(1.0)
        vals.append(0.0)

        # Ensure strict monotonicity for keyTimes
        clean_kt = [kt[0]]
        clean_v = [vals[0]]
        for k, v in zip(kt[1:], vals[1:]):
            if k > clean_kt[-1]:
                clean_kt.append(k)
                clean_v.append(v)
            else:
                # nudge slightly if equal
                k_nudged = round(clean_kt[-1] + 0.0001, 4)
                if k_nudged < 1.0:
                    clean_kt.append(k_nudged)
                    clean_v.append(v)
        if clean_kt[-1] < 1.0:
            clean_kt.append(1.0)
            clean_v.append(clean_v[-1])
        return ";".join(str(k) for k in clean_kt), ";".join(str(v) for v in clean_v)

    # Keyframes for cursor x and opacity
    def make_cursor_keyframes(idx, text, st, en):
        n = len(text)
        # x keyframes
        kt_x = []
        v_x = []
        if st > 0:
            kt_x.append(0.0)
            v_x.append(text_start_x)
            kt_x.append(round(st / total_t, 4))
            v_x.append(text_start_x)
        for i in range(n + 1):
            t = st + (en - st) * (i / n)
            kt_x.append(round(t / total_t, 4))
            v_x.append(round(text_start_x + text_width(text[:i], 30) + 1.0, 2))
        kt_x.append(round(11.5 / total_t, 4))
        v_x.append(v_x[-1])
        kt_x.append(1.0)
        v_x.append(v_x[-1])

        # Clean monotonicity for x
        clean_kx = [kt_x[0]]
        clean_vx = [v_x[0]]
        for k, v in zip(kt_x[1:], v_x[1:]):
            if k > clean_kx[-1]:
                clean_kx.append(k)
                clean_vx.append(v)

        # Opacity keyframes
        kt_op = []
        v_op = []
        if idx == 0:
            # Line 1: visible 0..2.4, stays end of line 1 until 2.6, then hides
            kt_op = [0.0, round(2.4 / total_t, 4), round(2.55 / total_t, 4), round(2.6 / total_t, 4), 1.0]
            v_op = [1, 1, 1, 0, 0]
        elif idx == 1:
            # Line 2: hidden until 2.6, visible 2.6..4.4, holds until 4.6, then hides
            kt_op = [
                0.0,
                round(2.59 / total_t, 4),
                round(2.6 / total_t, 4),
                round(4.4 / total_t, 4),
                round(4.55 / total_t, 4),
                round(4.6 / total_t, 4),
                1.0,
            ]
            v_op = [0, 0, 1, 1, 1, 0, 0]
        else:
            # Line 3: hidden until 4.6, visible 4.6..5.6, then blinks at 0.6s period until 11.5s, then hides
            kt_op = [0.0, round(4.59 / total_t, 4), round(4.6 / total_t, 4), round(5.6 / total_t, 4)]
            v_op = [0, 0, 1, 1]
            t = 5.6
            state = 0
            while t < 11.5:
                t = round(t + 0.3, 2)
                if t < 11.5:
                    kt_op.append(round(t / total_t, 4))
                    v_op.append(state)
                    state = 1 if state == 0 else 0
            kt_op.append(round(11.5 / total_t, 4))
            v_op.append(0)
            kt_op.append(1.0)
            v_op.append(0)

        # Clean monotonicity for op
        clean_kop = [kt_op[0]]
        clean_vop = [v_op[0]]
        for k, v in zip(kt_op[1:], v_op[1:]):
            if k > clean_kop[-1]:
                clean_kop.append(k)
                clean_vop.append(v)

        return (
            ";".join(str(k) for k in clean_kx),
            ";".join(str(v) for v in clean_vx),
            ";".join(str(k) for k in clean_kop),
            ";".join(str(v) for v in clean_vop),
        )

    defs_clips = []
    lines_svg = []

    for i, (line_text, y, st, en, color, has_glow) in enumerate(lines):
        clip_id = f"hero-clip-{i}"
        clip_kt, clip_vals = make_clip_keyframes(line_text, st, en)
        defs_clips.append(
            f'<clipPath id="{clip_id}">\n'
            f'  <rect x="{text_start_x}" y="{y - 25}" width="0" height="34">\n'
            f'    <animate attributeName="width" values="{clip_vals}" keyTimes="{clip_kt}" dur="{total_t}s" repeatCount="indefinite" calcMode="discrete"/>\n'
            f"  </rect>\n"
            f"</clipPath>"
        )

        kx, vx, kop, vop = make_cursor_keyframes(i, line_text, st, en)

        # Prompt appearance
        if st == 0:
            prompt_svg = f'<text x="{left_pad}" y="{y}" font-size="30" fill="{PURPLE}">&gt; </text>'
        else:
            k_st = round((st - 0.01) / total_t, 4)
            k_st2 = round(st / total_t, 4)
            prompt_svg = (
                f'<g>\n'
                f'  <animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;{k_st};{k_st2};0.8214;0.8929;1" dur="{total_t}s" repeatCount="indefinite" calcMode="discrete"/>\n'
                f'  <text x="{left_pad}" y="{y}" font-size="30" fill="{PURPLE}">&gt; </text>\n'
                f"</g>"
            )

        glow_attr = ' filter="url(#glow)"' if has_glow else ""
        text_svg = (
            f'<text x="{text_start_x}" y="{y}" font-size="30" fill="{color}" clip-path="url(#{clip_id})"{glow_attr}>'
            f"{xml_escape(line_text)}</text>"
        )

        cursor_svg = (
            f'<rect x="{text_start_x}" y="{y - 23}" width="3" height="28" fill="{PURPLE}">\n'
            f'  <animate attributeName="x" values="{vx}" keyTimes="{kx}" dur="{total_t}s" repeatCount="indefinite" calcMode="discrete"/>\n'
            f'  <animate attributeName="opacity" values="{vop}" keyTimes="{kop}" dur="{total_t}s" repeatCount="indefinite" calcMode="discrete"/>\n'
            f"</rect>"
        )

        lines_svg.append(f"{prompt_svg}\n{text_svg}\n{cursor_svg}")

    # Right-side floating cubes cluster
    cubes_svg = (
        f'<g opacity="0.45">\n'
        f'  <g><animateTransform attributeName="transform" type="translate" values="0 0; 0 -7; 0 0" dur="4.2s" begin="0s" repeatCount="indefinite"/>\n'
        f"    {cube(740, 75, 20, LIGHT, PURPLE, DEEP)}\n"
        f"  </g>\n"
        f'  <g><animateTransform attributeName="transform" type="translate" values="0 0; 0 -5; 0 0" dur="3.6s" begin="-1.3s" repeatCount="indefinite"/>\n'
        f"    {cube(712, 52, 15, LIGHT, PURPLE, DEEP)}\n"
        f"  </g>\n"
        f'  <g><animateTransform attributeName="transform" type="translate" values="0 0; 0 -8; 0 0" dur="4.8s" begin="-2.6s" repeatCount="indefinite"/>\n'
        f"    {cube(768, 88, 14, LIGHT, PURPLE, DEEP)}\n"
        f"  </g>\n"
        f"</g>"
    )

    # Master group fading out at 11.5s-12.5s
    inner_body = (
        f"<g>\n"
        f'  <animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.8214;0.8929;0.999;1" dur="{total_t}s" repeatCount="indefinite"/>\n'
        f'  {"".join(lines_svg)}\n'
        f"</g>\n"
        f"{cubes_svg}"
    )

    all_text = " ".join([prompt] + [l[0] for l in lines])
    svg_content = svg(w, h, inner_body, text_for_font=all_text, extra_defs="\n".join(defs_clips))

    out_path = os.path.join(ASSETS_DIR, "hero.svg")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print("Wrote", out_path)


def build_tiles():
    """assets/tile-*.svg, 320x170 each. 4 category cards with block clusters and pulsing borders."""
    tiles_data = [
        (
            "tile-mods.svg",
            "Mods & plugins",
            "Minecraft, Java",
            "0s",
            (
                # Stacked blocks (1.4x larger, centered in x 28..292, y 14..90)
                f"{cube(142, 68, 20, LIGHT, PURPLE, DEEP)}\n"
                f"{cube(178, 68, 20, LIGHT, PURPLE, DEEP)}\n"
                f"{cube(160, 44, 20, LIGHT, PURPLE, DEEP)}"
            ),
        ),
        (
            "tile-server.svg",
            "Home server",
            "Raspberry Pi, self-hosted",
            "-1s",
            (
                # Flat wide slab with 3 blinking LEDs
                f"{cube(126, 56, 22, LIGHT, PURPLE, DEEP)}\n"
                f"{cube(160, 56, 22, LIGHT, PURPLE, DEEP)}\n"
                f"{cube(194, 56, 22, LIGHT, PURPLE, DEEP)}\n"
                f'<circle cx="142" cy="64" r="3" fill="{LIGHT}"><animate attributeName="opacity" values="1;0.2;1" dur="1.2s" begin="0s" repeatCount="indefinite"/></circle>\n'
                f'<circle cx="160" cy="64" r="3" fill="{PALE}"><animate attributeName="opacity" values="0.2;1;0.2" dur="0.9s" begin="0.3s" repeatCount="indefinite"/></circle>\n'
                f'<circle cx="178" cy="64" r="3" fill="{LIGHT}"><animate attributeName="opacity" values="1;0.2;1" dur="1.5s" begin="0.7s" repeatCount="indefinite"/></circle>'
            ),
        ),
        (
            "tile-bots.svg",
            "Bots & automation",
            "Discord, scripts",
            "-2s",
            (
                # Two cubes with a pulsing connecting line
                f'<line x1="120" y1="54" x2="200" y2="54" stroke="{LIGHT}" stroke-width="3" stroke-dasharray="4,4">\n'
                f'  <animate attributeName="stroke-opacity" values="0.25;1;0.25" dur="1.6s" repeatCount="indefinite"/>\n'
                f"</line>\n"
                f"{cube(120, 54, 22, LIGHT, PURPLE, DEEP)}\n"
                f"{cube(160, 54, 11, LIGHT, PURPLE, DEEP)}\n"
                f"{cube(200, 54, 22, LIGHT, PURPLE, DEEP)}"
            ),
        ),
        (
            "tile-web.svg",
            "Web & apps",
            "sites, tools, mobile",
            "-3s",
            (
                # Cube with browser-bar slab directly attached on top, all y >= 14 at float peak (-6px)
                f"{cube(160, 56, 22, LIGHT, PURPLE, DEEP)}\n"
                f'<polygon points="160.0,49.0 179.1,38.0 160.0,27.0 140.9,38.0" fill="{LIGHT}"/>\n'
                f'<polygon points="160.0,49.0 140.9,38.0 140.9,45.0 160.0,56.0" fill="{PURPLE}"/>\n'
                f'<polygon points="160.0,49.0 160.0,56.0 179.1,45.0 179.1,38.0" fill="{DEEP}"/>\n'
                f'<circle cx="146.0" cy="44.5" r="1.8" fill="{PALE}"/>\n'
                f'<circle cx="151.0" cy="47.5" r="1.8" fill="{PALE}"/>\n'
                f'<circle cx="156.0" cy="50.5" r="1.8" fill="{PALE}"/>'
            ),
        ),
    ]

    card_animate = '<animate attributeName="stroke-opacity" values="0.25;0.6;0.25" dur="5s" repeatCount="indefinite"/>'

    for fname, title, subtitle, offset, cluster_shapes in tiles_data:
        cluster_svg = (
            f"<g>\n"
            f'  <animateTransform attributeName="transform" type="translate" values="0 0; 0 -6; 0 0" '
            f'dur="4s" begin="{offset}" repeatCount="indefinite"/>\n'
            f"{cluster_shapes}\n"
            f"</g>"
        )

        text_content = (
            f'<text x="28" y="128" font-size="30" fill="{PALE}">{xml_escape(title)}</text>\n'
            f'<text x="28" y="152" font-size="16" fill="{DIM}">{xml_escape(subtitle)}</text>'
        )

        body = f"{cluster_svg}\n{text_content}"
        font_text = f"{title} {subtitle}"
        svg_content = svg(320, 170, body, text_for_font=font_text, card_attrs=card_animate)

        out_path = os.path.join(ASSETS_DIR, fname)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        print("Wrote", out_path)


def build_stack():
    """assets/stack.svg, 600x250. 4 cols x 2 rows chips with bobbing isometric cubes (no face letters)."""
    w, h = 600, 250
    chips = [
        ("Java", "#b78cf7", "#8b4cdb", "#5a259c"),
        ("TypeScript", "#9d92fc", "#6d5dfc", "#4332c8"),
        ("Python", "#c38ff7", "#9659db", "#602a9e"),
        ("C#", "#d886f0", "#b147d4", "#762294"),
        ("Swift", "#e082db", "#b742b0", "#791f74"),
        ("Blender", "#9598fa", "#5f66f5", "#383ebd"),
        ("Cloudflare", "#bf88ff", "#8d4eed", "#5927ad"),
        ("Raspberry Pi", "#d978e8", "#aa3cc0", "#6f1a82"),
    ]

    col_xs = [80, 226, 374, 520]
    row_cy = [84, 170]
    label_y = [132, 218]

    body_parts = ['<text x="28" y="44" font-size="26" fill="' + LIGHT + '">Stack</text>']

    for i, (name, top_c, left_c, right_c) in enumerate(chips):
        col = i % 4
        row = i // 4
        cx = col_xs[col]
        cy = row_cy[row]
        lbl_y = label_y[row]

        dur = round(3.0 + (i % 4) * 0.25, 2)
        begin = round(-(i * 0.45), 2)

        # Cube size ~1.25x larger (s=27 vs s=22)
        s = 27
        cube_markup = cube(cx, cy, s, top_c, left_c, right_c)

        chip_group = (
            f"<g>\n"
            f'  <g><animateTransform attributeName="transform" type="translate" values="0 0; 0 -5; 0 0" '
            f'dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>\n'
            f"    {cube_markup}\n"
            f"  </g>\n"
            f'  <text x="{cx}" y="{lbl_y}" font-size="20" fill="{PALE}" text-anchor="middle">{name}</text>\n'
            f"</g>"
        )
        body_parts.append(chip_group)

    all_text = "Stack " + " ".join([name for name, *_ in chips])
    svg_content = svg(w, h, "\n".join(body_parts), text_for_font=all_text)

    out_path = os.path.join(ASSETS_DIR, "stack.svg")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print("Wrote", out_path)


def main():
    ensure_assets_dir()
    build_hero()
    build_tiles()
    build_stack()


if __name__ == "__main__":
    main()
