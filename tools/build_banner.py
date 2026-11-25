"""Generate the GitHub profile banner (light + dark) as self-contained SVGs.

Text is shaped with HarfBuzz (kerning included) and converted to outlines,
so the banner renders identically everywhere without loading any font.
Edit NAME, STATEMENT or TIMELINE below, then run from the repository root:

    pip install uharfbuzz fonttools brotli
    npm pack @fontsource/ibm-plex-sans@5.1.1 @fontsource/ibm-plex-mono@5.1.1
    python3 tools/build_banner.py

The script unpacks IBM Plex (SIL Open Font License) into tools/fonts on first run
and writes assets/banner-dark.svg and assets/banner-light.svg.
"""
import glob
import os
import tarfile
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

FONT_DIR = "tools/fonts"
FONTS = {
    "sans400": f"{FONT_DIR}/plex-sans-400.ttf",
    "sans500": f"{FONT_DIR}/plex-sans-500.ttf",
    "sans600": f"{FONT_DIR}/plex-sans-600.ttf",
    "mono400": f"{FONT_DIR}/plex-mono-400.ttf",
    "mono500": f"{FONT_DIR}/plex-mono-500.ttf",
}


def prepare_fonts():
    """Convert the npm-packed IBM Plex woff2 files to TTF once."""
    if all(os.path.exists(p) for p in FONTS.values()):
        return
    os.makedirs(FONT_DIR, exist_ok=True)
    for tgz in glob.glob("fontsource-ibm-plex-*.tgz"):
        family = "mono" if "mono" in tgz else "sans"
        with tarfile.open(tgz) as tar:
            for member in tar.getmembers():
                for weight in ("400", "500", "600"):
                    if member.name.endswith(f"-latin-{weight}-normal.woff2"):
                        font = TTFont(tar.extractfile(member))
                        font.flavor = None
                        font.save(f"{FONT_DIR}/plex-{family}-{weight}.ttf")
    missing = [p for p in FONTS.values() if not os.path.exists(p)]
    if missing:
        raise SystemExit(f"Missing fonts {missing}: run the npm pack command first.")
_cache = {}


def _load(key):
    if key not in _cache:
        path = FONTS[key]
        data = open(path, "rb").read()
        face = hb.Face(hb.Blob(data))
        font = hb.Font(face)
        tt = TTFont(path)
        _cache[key] = (font, tt, tt.getGlyphSet(), tt["head"].unitsPerEm)
    return _cache[key]


def _num(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def text(s, key, size, x, y, tracking=0.0):
    """Return (path_d, advance_width) for string s with baseline at (x, y)."""
    font, tt, gs, upem = _load(key)
    buf = hb.Buffer()
    buf.add_str(s)
    buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": True, "liga": True})
    order = tt.getGlyphOrder()
    k = size / upem
    pen_x = 0.0
    parts = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = order[info.codepoint]
        svg = SVGPathPen(gs, ntos=_num)
        ox = x + (pen_x + pos.x_offset) * k
        oy = y - pos.y_offset * k
        gs[name].draw(TransformPen(svg, (k, 0, 0, -k, ox, oy)))
        d = svg.getCommands()
        if d:
            parts.append(d)
        pen_x += pos.x_advance + (tracking / k if tracking else 0)
    width = pen_x * k
    return "".join(parts), width


THEMES = {
    "dark": dict(bg="#13202F", rule="#26384D", text="#EAF0F6",
                 muted="#9AAABD", accent="#FFB547"),
    "light": dict(bg="#F6F8FB", rule="#D3DCE6", text="#13202F",
                  muted="#4E6075", accent="#A35F00"),
}

NAME = "Achraf Lakdim"
STATEMENT = [
    "I build detection pipelines, investigate what they catch,",
    "and automate the repetitive parts.",
]
TIMELINE = [
    ("2024-07", "Ministry of Digital Transition", "Data-center network security and monitoring"),
    ("2025-07", "Huawei", "Built NAV, a network mapping and scanning app"),
    ("2026-02", "Sofrecom (Orange Group)", "Open-source SOC/SOAR proof of concept"),
    ("2026-09", "Lumiplan", "SIEM migration, vulnerability management, ISO 27001"),
    ("now", "Home lab", "Purple-team lab, from alert to forensic report"),
]

W = 1200
LEFT = 72
NAME_Y = 128
STATEMENT_Y = [184, 218]
RULE_Y = 262
ROW0 = 318
ROW_H = 46
MARK_X = LEFT + 6
TS_X = LEFT + 36
H = ROW0 + ROW_H * (len(TIMELINE) - 1) + 62


def build(theme):
    t = THEMES[theme]
    out = []
    # Column positions computed from real text widths
    ts_w = max(text(ts, "mono400", 16, 0, 0)[1] for ts, _, _ in TIMELINE)
    org_x = TS_X + ts_w + 30
    org_w = max(text(org, "sans600", 18, 0, 0)[1] for _, org, _ in TIMELINE)
    desc_x = org_x + org_w + 36
    desc_w = max(text(d, "sans400", 18, 0, 0)[1] for _, _, d in TIMELINE)
    W = round(desc_x + desc_w + LEFT)

    name_d, name_w = text(NAME, "sans600", 66, LEFT, NAME_Y)
    out.append(f'<path class="ink" d="{name_d}"/>')
    for line, y in zip(STATEMENT, STATEMENT_Y):
        d, _ = text(line, "sans400", 25, LEFT, y)
        out.append(f'<path class="muted" d="{d}"/>')
    out.append(f'<line class="rule" x1="{LEFT}" y1="{RULE_Y}" x2="{W - LEFT}" y2="{RULE_Y}"/>')

    first_mid = ROW0 - 6
    last_mid = ROW0 + ROW_H * (len(TIMELINE) - 1) - 6
    span = last_mid - first_mid
    out.append(
        f'<line class="spine" x1="{MARK_X}" y1="{first_mid}" x2="{MARK_X}" y2="{last_mid}" '
        f'style="stroke-dasharray:{span};stroke-dashoffset:0"/>'
    )

    for i, (ts, org, desc) in enumerate(TIMELINE):
        y = ROW0 + ROW_H * i
        mid = y - 6
        live = ts == "now"
        delay = 0.25 + 0.38 * i
        row = [f'<g class="row" style="animation-delay:{delay:.2f}s">']
        if live:
            row.append(f'<circle class="pulse" cx="{MARK_X}" cy="{mid}" r="6"/>')
            row.append(f'<circle class="dot-live" cx="{MARK_X}" cy="{mid}" r="6"/>')
        else:
            row.append(f'<circle class="dot" cx="{MARK_X}" cy="{mid}" r="5"/>')
        d, _ = text(ts, "mono500" if live else "mono400", 16, TS_X, y)
        row.append(f'<path class="{"accent" if live else "muted"}" d="{d}"/>')
        d, _ = text(org, "sans600", 18, org_x, y)
        row.append(f'<path class="ink" d="{d}"/>')
        d, _ = text(desc, "sans400", 18, desc_x, y)
        row.append(f'<path class="muted" d="{d}"/>')
        row.append("</g>")
        out.append("".join(row))

    total = 0.25 + 0.38 * (len(TIMELINE) - 1)
    css = f"""
.bg{{fill:{t['bg']}}}
.ink{{fill:{t['text']}}}
.muted{{fill:{t['muted']}}}
.accent{{fill:{t['accent']}}}
.rule{{stroke:{t['rule']};stroke-width:1}}
.spine{{stroke:{t['rule']};stroke-width:2;animation:draw {total:.2f}s linear both}}
.dot{{fill:{t['bg']};stroke:{t['muted']};stroke-width:2}}
.dot-live{{fill:{t['accent']}}}
.pulse{{fill:none;stroke:{t['accent']};stroke-width:2;transform-box:fill-box;transform-origin:center;
  opacity:0;animation:pulse 2.4s ease-out {total + 0.6:.2f}s infinite}}
.row{{animation:arrive .01s steps(1,end) both}}
@keyframes draw{{from{{stroke-dashoffset:{span}}}to{{stroke-dashoffset:0}}}}
@keyframes arrive{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes pulse{{0%{{opacity:.9;transform:scale(1)}}80%,100%{{opacity:0;transform:scale(3)}}}}
@media (prefers-reduced-motion:reduce){{.spine,.row,.pulse{{animation:none}}}}
"""
    title = "Achraf Lakdim, security engineer in training"
    desc = (
        "I build detection pipelines, investigate what they catch, and automate the repetitive parts. "
        + " ".join(f"{ts}: {org}, {d}." for ts, org, d in TIMELINE)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-labelledby="t d">'
        f"<title id=\"t\">{title}</title><desc id=\"d\">{desc}</desc>"
        f"<style>{css}</style>"
        f'<rect class="bg" width="{W}" height="{H}" rx="16"/>'
        + "".join(out)
        + "</svg>"
    )


if __name__ == "__main__":
    prepare_fonts()
    os.makedirs("assets", exist_ok=True)
    for theme in THEMES:
        svg = build(theme)
        path = f"assets/banner-{theme}.svg"
        open(path, "w").write(svg)
        print(path, len(svg), "bytes")
