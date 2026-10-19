"""Rebuilds the profile SVGs in assets/.

Visual system: an 80s machine at night. The banner is a VHS/CRT frame of a
synthwave horizon (striped sun, wireframe ridges, a neon grid rolling toward the
viewer); the stack panel is the cassette and J-card that came with it, side A
the web app and side B the API. Display lettering is Archivo Expanded Black in
chrome, terminal text is VT323 (both SIL OFL 1.1, see fonts/). All text is
converted to outlines so it renders the same everywhere. Motion is CSS inside
the SVG and stops under prefers-reduced-motion; every animated element also
carries a static transform, so a renderer without CSS animation still shows a
complete frame.

Usage:  pip install fonttools uharfbuzz
        python .github/scripts/gen.py
"""

from __future__ import annotations

import html
import random
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.basePen import BasePen
from fontTools.pens.transformPen import TransformPen

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ASSETS = ROOT / "assets"
FONTS = HERE / "fonts"

# Real text (terminal lines, track lists, labels) holds 4.5:1 or better against
# the darkest-to-lightest backdrop it sits on; chrome display type holds 3:1.
THEMES = {
    "dark": {
        "sky": ["#07031A", "#170734", "#2C0A4C", "#6A1466"],
        "floor": ["#1C0638", "#0A0220"],
        "sun": ["#F7C948", "#F0A500", "#FF6A3D", "#FF2E88", "#B8127F"],
        "sun_glow": "#FF2E88",
        "grid": "#FF3EA5",
        "grid_v": "#B44CFF",
        "horizon": "#FF8AD8",
        "ridge_fill": "#100424",
        "ridge": "#3EF2FF",
        "chrome": [("0", "#FFFFFF"), (".38", "#A8E4FF"), (".5", "#5A8CFF"), (".53", "#25093F"),
                   (".6", "#FF4FB8"), ("1", "#FFD6F2")],
        "chrome_glow": "#FF2E88",
        "text": "#F6EEFF",
        "muted": "#CDBDF5",
        "cyan": "#5CF6FF",
        "magenta": "#FF6CC8",
        "amber": "#F7C948",
        "star": "#FFFFFF",
        "scan": ("#000000", 0.28),
        "vignette": ("#000000", 0.68),
        "panel": "#140828",
        "panel_edge": "#3A1A6B",
        "shell": "#2A1352",
        "shell_hi": "#4A2585",
        "shell_lo": "#1A0A36",
        "label": "#EFE6FF",
        "label_ink": "#2B1648",
        "window": "#0C0420",
        "tape": "#6B3D5E",
        "tape_ring": "#8A5578",
        "glass": "#22104A",
        "hub": "#F6EEFF",
        "rule": "#4A2F78",
        "card": "#1A0C36",
        "card_edge": "#5B2E9C",
        "neon": "#FF4FB8",
        "bezel": "#0E0522",
    },
    "light": {
        "sky": ["#EADBFF", "#F6DDF4", "#FFD3EA", "#FFB8DA"],
        "floor": ["#DDF7F2", "#C3EEE8"],
        "sun": ["#FFD27A", "#FFB86B", "#FF94B4", "#F276C9", "#C979F0"],
        "sun_glow": "#FF8FC9",
        "grid": "#B455F2",
        "grid_v": "#3CC4D6",
        "horizon": "#FF5FAE",
        "ridge_fill": "#F3E6FF",
        "ridge": "#2BB3C7",
        "chrome": [("0", "#1D0E3A"), (".3", "#3B2380"), (".46", "#8E74E8"), (".5", "#F4EEFF"), (".54", "#FFFFFF"),
                   (".58", "#F25CA8"), ("1", "#7A0F55")],
        "chrome_glow": "#FFFFFF",
        "text": "#24123F",
        "muted": "#4E3A73",
        "cyan": "#08606F",
        "magenta": "#A3126D",
        "amber": "#7E4A00",
        "star": "#FFFFFF",
        "scan": ("#3A1D66", 0.06),
        "vignette": ("#6A3FA0", 0.26),
        "panel": "#FBF5FF",
        "panel_edge": "#D9C6F5",
        "shell": "#D9C8F7",
        "shell_hi": "#EADFFF",
        "shell_lo": "#C2ABEF",
        "label": "#FFFFFF",
        "label_ink": "#24123F",
        "window": "#3A2366",
        "tape": "#9A7AB0",
        "tape_ring": "#B79BCB",
        "glass": "#4A2F7A",
        "hub": "#FFFFFF",
        "rule": "#D9C6F5",
        "card": "#FFFFFF",
        "card_edge": "#D9C6F5",
        "neon": "#FF7AC4",
        "bezel": "#F7F0FF",
    },
}

DISPLAY = dict(font="archivo", wght=900, wdth=125)
SKEW = -9


def num(v: float) -> str:
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def kn(v: float) -> str:
    return f"{v:.4f}".rstrip("0").lstrip("0")


class RelativePathPen(BasePen):
    """Emits relative path commands in whole font units.

    Glyphs are stored once per font instance in font units (1/1000 em) and placed
    with <use>, so integer deltas are exact enough at any size and keep files small.
    After 'z' SVG returns the current point to the subpath start, so the pen does too.
    """

    def __init__(self):
        super().__init__(None)
        self.out: list[str] = []
        self.pos = (0, 0)
        self.start = (0, 0)

    def _emit(self, cmd: str, *pts):
        vals, (px, py) = [], self.pos
        for x, y in pts:
            vals += [round(x) - px, round(y) - py]
        self.out.append(cmd + "".join(f"{v}" if v < 0 or i == 0 else f" {v}" for i, v in enumerate(vals)))
        self.pos = (round(pts[-1][0]), round(pts[-1][1]))

    def _moveTo(self, pt):
        self._emit("m", pt)
        self.start = self.pos

    def _lineTo(self, pt):
        self._emit("l", pt)

    def _qCurveToOne(self, pt1, pt2):
        self._emit("q", pt1, pt2)

    def _curveToOne(self, pt1, pt2, pt3):
        self._emit("c", pt1, pt2, pt3)

    def _closePath(self):
        self.out.append("z")
        self.pos = self.start

    def d(self) -> str:
        return ("M" + self.out[0][1:] + "".join(self.out[1:])) if self.out else ""


class Face:
    def __init__(self, path: Path):
        self.face = hb.Face(hb.Blob.from_file_path(str(path)))
        self.upem = self.face.upem
        self.variable = bool(self.face.table_tags and "fvar" in self.face.table_tags)
        self._fonts: dict[tuple, hb.Font] = {}

    def font(self, wght: float, wdth: float) -> hb.Font:
        key = (wght, wdth) if self.variable else ()
        if key not in self._fonts:
            font = hb.Font(self.face)
            if self.variable:
                font.set_variations({"wght": wght, "wdth": wdth})
            self._fonts[key] = font
        return self._fonts[key]

    def shape(self, text: str, wght: float, wdth: float):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.font(wght, wdth), buf, {"kern": True, "liga": True})
        return list(zip(buf.glyph_infos, buf.glyph_positions))

    def width(self, text: str, size: float, wght=400, wdth=100, track=0.0) -> float:
        glyphs = self.shape(text, wght, wdth)
        return sum(p.x_advance for _, p in glyphs) * size / self.upem + track * size * max(len(glyphs) - 1, 0)

    def outline(self, gid: int, wght: float, wdth: float) -> str:
        pen = RelativePathPen()
        self.font(wght, wdth).draw_glyph_with_pen(gid, TransformPen(pen, (1, 0, 0, -1, 0, 0)))
        return pen.d()


FACES = {"archivo": Face(FONTS / "Archivo-subset.ttf"), "vt": Face(FONTS / "VT323-subset.ttf")}
CAP = {"archivo": 0.686, "vt": 0.56}


def width(text, size, font="vt", wght=400, wdth=100, track=0.0):
    return FACES[font].width(text, size, wght, wdth, track)


CSS = """
.hl{animation:roll 3.6s linear infinite}
.sb{animation:sink 5s linear infinite}
.cur{animation:blink 1.1s steps(1) infinite}
.band{animation:drift 7s linear infinite}
.reel{transform-box:fill-box;transform-origin:center;animation:spin 3.2s linear infinite}
.reel.r2{animation-duration:2.2s}
.tw{animation:twinkle 3.4s ease-in-out infinite}
@keyframes blink{0%{opacity:1}50%{opacity:0}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes twinkle{0%,100%{opacity:1}50%{opacity:.25}}
@media (prefers-reduced-motion:reduce){.hl,.sb,.cur,.band,.reel,.tw{animation:none}}
"""


class Canvas:
    def __init__(self, w: int, h: int, theme: str, title: str, desc: str):
        self.w, self.h = w, h
        self.theme = theme
        self.c = THEMES[theme]
        self.title, self.desc = title, desc
        self.parts: list[str] = []
        self.defs: list[str] = []
        self.css: list[str] = []
        self._ids = 0
        self._glyphs: dict[tuple, str] = {}
        self._chrome = False

    def uid(self, prefix: str) -> str:
        self._ids += 1
        return f"{prefix}{self._ids}"

    def add(self, s: str):
        self.parts.append(s)

    def _glyph(self, font: str, gid: int, wght: float, wdth: float) -> str | None:
        key = (font, gid, wght, wdth)
        if key not in self._glyphs:
            d = FACES[font].outline(gid, wght, wdth)
            gref = ""
            if d:
                gref = f"g{len(self._glyphs)}"
                self.defs.append(f'<path id="{gref}" d="{d}"/>')
            self._glyphs[key] = gref
        return self._glyphs[key] or None

    def glyphs(self, s, x, y, size, font="vt", wght=400, wdth=100, track=0.0) -> str:
        face = FACES[font]
        k = size / face.upem
        out, cursor = [], x
        for info, pos in face.shape(s, wght, wdth):
            gref = self._glyph(font, info.codepoint, wght, wdth)
            if gref:
                out.append(f'<use href="#{gref}" transform="matrix({kn(k)} 0 0 {kn(k)} {num(cursor + pos.x_offset * k)} {num(y - pos.y_offset * k)})"/>')
            cursor += pos.x_advance * k + track * size
        return "".join(out)

    def text(self, s, x, y, size, fill, font="vt", wght=400, wdth=100, track=0.0, skew=0.0,
             fit: float | None = None, attrs: str = "") -> float:
        w = width(s, size, font, wght, wdth, track)
        if fit is not None and w > fit + 0.5:
            raise ValueError(f"{s!r} is {w:.0f}px wide, space allows {fit:.0f}px")
        tf = f' transform="translate({num(x)} {num(y)}) skewX({skew}) translate({num(-x)} {num(-y)})"' if skew else ""
        self.add(f'<g fill="{fill}"{tf}{attrs}>{self.glyphs(s, x, y, size, font, wght, wdth, track)}</g>')
        return w

    def chrome(self, s, x, y, size, fit: float | None = None) -> float:
        """Chrome display lettering: a horizon-split gradient over the cap height, with a soft glow behind."""
        # The fill resolves inside each <use>d glyph, in font units, so the gradient
        # follows each glyph's box; caps share one height, which keeps the horizon level.
        if not self._chrome:
            stops = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in self.c["chrome"])
            self.defs.append(f'<linearGradient id="chrome" x1="0" y1="0" x2="0" y2="1">{stops}</linearGradient>')
            self._chrome = True
        w = width(s, size, **DISPLAY)
        if fit is not None and w > fit + 0.5:
            raise ValueError(f"{s!r} is {w:.0f}px wide, space allows {fit:.0f}px")
        tf = f' transform="translate({num(x)} {num(y)}) skewX({SKEW}) translate({num(-x)} {num(-y)})"'
        uses = self.glyphs(s, x, y, size, **DISPLAY)
        self.add(f'<g fill="{self.c["chrome_glow"]}" opacity=".55" filter="url(#glow)"{tf}>{uses}</g>')
        self.add(f'<g fill="url(#chrome)"{tf}>{uses}</g>')
        return w

    def svg(self) -> str:
        t, d = html.escape(self.title), html.escape(self.desc)
        style = f"<style>{CSS.strip()}{''.join(self.css)}</style>"
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="t d">'
            f'<title id="t">{t}</title><desc id="d">{d}</desc>{style}'
            f'<defs>{"".join(self.defs)}</defs>{"".join(self.parts)}</svg>\n'
        )


def lin(cv: Canvas, colors: list[str], y1: float, y2: float, offsets: list[float] | None = None) -> str:
    gid = cv.uid("lg")
    offsets = offsets or [i / (len(colors) - 1) for i in range(len(colors))]
    stops = "".join(f'<stop offset="{num(o * 100)}%" stop-color="{c}"/>' for o, c in zip(offsets, colors))
    cv.defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="0" y1="{num(y1)}" x2="0" y2="{num(y2)}">{stops}</linearGradient>')
    return f"url(#{gid})"


def common_defs(cv: Canvas, scan: float):
    cv.defs.append('<filter id="glow" x="-10%" y="-40%" width="120%" height="180%"><feGaussianBlur stdDeviation="5"/></filter>')
    color, alpha = cv.c["scan"]
    cv.defs.append(f'<pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="{color}" fill-opacity="{alpha * scan:.3f}"/></pattern>')


def crt_overlay(cv: Canvas, clip: str, rx: float):
    """Scanlines, a slow bright band rolling down the tube, and the vignette of a curved screen."""
    color, alpha = cv.c["vignette"]
    vid = cv.uid("vg")
    cv.defs.append(
        f'<radialGradient id="{vid}" cx="50%" cy="50%" r="75%"><stop offset="60%" stop-color="{color}" stop-opacity="0"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="{alpha}"/></radialGradient>'
    )
    bid = cv.uid("bd")
    cv.defs.append(f'<linearGradient id="{bid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
                   f'<stop offset=".5" stop-color="#fff" stop-opacity=".07"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')
    cv.css.append(f"@keyframes drift{{from{{transform:translateY(-70px)}}to{{transform:translateY({cv.h + 10}px)}}}}")
    cv.add(f'<g clip-path="url(#{clip})"><rect width="{cv.w}" height="{cv.h}" fill="url(#scan)"/>'
           f'<rect class="band" width="{cv.w}" height="60" fill="url(#{bid})" transform="translate(0 -70)"/>'
           f'<rect width="{cv.w}" height="{cv.h}" fill="url(#{vid})"/></g>')
    cv.add(f'<rect x=".5" y=".5" width="{cv.w - 1}" height="{cv.h - 1}" rx="{rx}" fill="none" stroke="{cv.c["panel_edge"]}" stroke-opacity=".6"/>')


def sky(cv: Canvas, hy: float, stars: int, seed: int, clouds: tuple[float, float, float, float]):
    """Night sky with stars (some twinkle) in dark, daytime streaks in light.

    clouds: (x0, x1, y0, y1), the daytime streaks stay inside this box so none crosses text.
    """
    c, W = cv.c, cv.w
    cv.add(f'<rect width="{W}" height="{num(hy)}" fill="{lin(cv, c["sky"], 0, hy, [0, .55, .86, 1])}"/>')
    rnd = random.Random(seed)
    if cv.theme == "dark":
        dots = []
        for i in range(stars):
            x, y, r = rnd.uniform(8, W - 8), rnd.uniform(6, hy * 0.72), rnd.choice([.6, .7, .8, 1.1])
            dots.append((x, y, r, i % 5 == 0))
        still = "".join(f'<circle cx="{num(x)}" cy="{num(y)}" r="{r}"/>' for x, y, r, tw in dots if not tw)
        twinkle = "".join(f'<circle class="tw" style="animation-delay:-{num(rnd.uniform(0, 3.4))}s" cx="{num(x)}" cy="{num(y)}" r="{r}"/>' for x, y, r, tw in dots if tw)
        cv.add(f'<g fill="{c["star"]}" opacity=".75">{still}{twinkle}</g>')
    else:
        streaks = []
        cx0, cx1, cy0, cy1 = clouds
        for _ in range(stars // 8):
            w = rnd.uniform(60, 150)
            x, y = rnd.uniform(cx0, max(cx0, cx1 - w)), rnd.uniform(cy0, cy1)
            streaks.append(f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(rnd.choice([3, 4, 6]))}" rx="3"/>')
        cv.add(f'<g fill="#FFFFFF" opacity=".55">{"".join(streaks)}</g>')


def horizon_scene(cv: Canvas, hy: float, sun: tuple[float, float, float], ridges: list[list[tuple[float, float]]],
                  stars: int, seed: int, clouds: tuple[float, float, float, float]):
    """Sky, sun, ridges and the rolling grid, everything below the text layer."""
    c, W, H = cv.c, cv.w, cv.h
    sky(cv, hy, stars, seed, clouds)

    sx, sy, sr = sun
    gid = cv.uid("sg")
    cv.defs.append(f'<radialGradient id="{gid}"><stop offset="0" stop-color="{c["sun_glow"]}" stop-opacity=".55"/>'
                   f'<stop offset="1" stop-color="{c["sun_glow"]}" stop-opacity="0"/></radialGradient>')
    cv.add(f'<circle cx="{num(sx)}" cy="{num(sy)}" r="{num(sr * 1.9)}" fill="url(#{gid})"/>')

    mid = cv.uid("sm")
    band_top, period, n = sy - sr * 0.12, 5.0, 7
    cv.css.append(
        f"@keyframes sink{{from{{transform:translateY({num(band_top)}px) scaleY(.6)}}"
        f"to{{transform:translateY({num(hy)}px) scaleY({num(sr * 0.16)})}}}}"
    )
    bands = []
    for i in range(n):
        p = i / n
        y = band_top + (hy - band_top) * p
        s = 0.6 + (sr * 0.16 - 0.6) * p
        bands.append(f'<rect class="sb" style="animation-delay:-{num(period * (1 - p))}s" x="{num(sx - sr)}" width="{num(2 * sr)}" height="1" '
                     f'transform="translate(0 {num(y)}) scale(1 {num(s)})"/>')
    cv.defs.append(f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="#fff"/>'
                   f'<g fill="#000">{"".join(bands)}</g><rect y="{num(hy)}" width="{W}" height="{num(H - hy)}" fill="#000"/></mask>')
    sun_fill = lin(cv, c["sun"], sy - sr, sy + sr * 0.6, [0, .28, .55, .8, 1])
    cv.add(f'<circle cx="{num(sx)}" cy="{num(sy)}" r="{num(sr)}" fill="{sun_fill}" mask="url(#{mid})"/>')

    for ridge in ridges:
        pts = " ".join(f"{num(x)},{num(y)}" for x, y in ridge)
        x0, x1 = ridge[0][0], ridge[-1][0]
        cv.add(f'<polygon points="{num(x0)},{num(hy)} {pts} {num(x1)},{num(hy)}" fill="{c["ridge_fill"]}"/>')
        wires = []
        for i, (x, y) in enumerate(ridge[1:-1], 1):
            a, b = ridge[i - 1][0], ridge[i + 1][0]
            wires.append(f"M{num(x)} {num(y)}L{num((x + a) / 2)} {num(hy)}M{num(x)} {num(y)}L{num((x + b) / 2)} {num(hy)}")
        cv.add(f'<path d="{"".join(wires)}" stroke="{c["ridge"]}" stroke-opacity=".35" stroke-width=".8" fill="none"/>')
        cv.add(f'<polyline points="{pts}" fill="none" stroke="{c["ridge"]}" stroke-width="5" stroke-opacity=".18" stroke-linejoin="round"/>')
        cv.add(f'<polyline points="{pts}" fill="none" stroke="{c["ridge"]}" stroke-width="1.4" stroke-linejoin="round"/>')

    floor_grid(cv, hy, H, sx, animated=True)


def floor_grid(cv: Canvas, hy: float, y_end: float, vx: float, animated: bool, strength: float = 1.0):
    """The neon floor from the horizon down to y_end, converging on vx.

    Horizontal lines sit at geometric steps below the horizon (each one a fixed
    ratio further than the last), so moving every line to its neighbour's place
    over one step loops seamlessly and starts right at the horizon line.
    """
    c, W = cv.c, cv.w
    depth = y_end - hy
    clip = cv.uid("fc")
    cv.defs.append(f'<clipPath id="{clip}"><rect y="{num(hy)}" width="{W}" height="{num(depth)}"/></clipPath>')
    cv.add(f'<rect y="{num(hy)}" width="{W}" height="{num(depth)}" fill="{lin(cv, c["floor"], hy, y_end)}"/>')

    spread = 92 * W / 840
    k_near = int(max(vx, W - vx) / spread * 2.2) + 2
    # Past k_near the steps widen: these near-horizontal rays fill the floor out to
    # the frame edges right under the horizon instead of leaving an empty wedge.
    ks = list(range(k_near + 1)) + [round(k_near * f) for f in (1.3, 1.7, 2.3, 3.2, 4.6, 7, 11)]
    verts = []
    for k in sorted(set(ks)):
        for sign in ((1,) if k == 0 else (1, -1)):
            x_far, x_near = vx + sign * k * spread * 0.06, vx + sign * k * spread
            verts.append(f"M{num(x_far)} {num(hy)}L{num(x_near)} {num(hy + depth)}")
    v = "".join(verts)
    # Rays fade in below the horizon, as a real grid thins toward its vanishing
    # point; drawn at full strength there they bunch into moire.
    fade_id, fade_mask = cv.uid("rf"), cv.uid("rm")
    cv.defs.append(f'<linearGradient id="{fade_id}" gradientUnits="userSpaceOnUse" x1="0" y1="{num(hy)}" x2="0" y2="{num(hy + depth * 0.32)}">'
                   f'<stop offset="0" stop-color="#000"/><stop offset=".25" stop-color="#555"/><stop offset="1" stop-color="#fff"/></linearGradient>')
    cv.defs.append(f'<mask id="{fade_mask}" maskUnits="userSpaceOnUse" x="0" y="{num(hy)}" width="{W}" height="{num(depth)}">'
                   f'<rect y="{num(hy)}" width="{W}" height="{num(depth)}" fill="url(#{fade_id})"/></mask>')
    g = [f'<g clip-path="url(#{clip})" opacity="{strength}">',
         f'<g mask="url(#{fade_mask})"><path d="{v}" stroke="{c["grid_v"]}" stroke-width="4" stroke-opacity=".18" fill="none"/>',
         f'<path d="{v}" stroke="{c["grid_v"]}" stroke-width="1.1" fill="none"/></g>']

    n, period, near_ratio = 12, 3.6, 1 / 40

    def offset(p: float) -> float:
        return depth * near_ratio ** (1 - p)

    def fade(p: float) -> float:
        return min(1.0, (p / 0.35) ** 1.5)

    if animated:
        frames = [f"{num(i / 16 * 100)}%{{transform:translateY({num(hy + offset(i / 16))}px);opacity:{fade(i / 16):.2f}}}" for i in range(17)]
        cv.css.append("@keyframes roll{" + "".join(frames) + "}")
    for i in range(n):
        p = i / n
        attrs = f' class="hl" style="animation-delay:-{num(period * p)}s"' if animated else ""
        g.append(f'<g{attrs} transform="translate(0 {num(hy + offset(p))})" opacity="{fade(p):.2f}">'
                 f'<path d="M0 0H{W}" stroke="{c["grid"]}" stroke-width="4" stroke-opacity=".18"/>'
                 f'<path d="M0 0H{W}" stroke="{c["grid"]}" stroke-width="1.4"/></g>')
    g.append("</g>")
    cv.add("".join(g))
    cv.add(f'<path d="M0 {num(hy)}H{W}" stroke="{c["horizon"]}" stroke-width="7" stroke-opacity=".3"/>')
    cv.add(f'<path d="M0 {num(hy)}H{W}" stroke="{c["horizon"]}" stroke-width="1.6"/>')


def ridge(x0: float, x1: float, hy: float, peaks: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """peaks: (fraction along the span, height above the horizon)."""
    return [(x0, hy)] + [(x0 + (x1 - x0) * f, hy - h) for f, h in peaks] + [(x1, hy)]


def sparkle(cv: Canvas, x: float, y: float, r: float):
    """The four-point glint that sits on chrome lettering."""
    t = r * 0.18
    d = (f"M{num(x)} {num(y - r)}L{num(x + t)} {num(y - t)}L{num(x + r)} {num(y)}L{num(x + t)} {num(y + t)}"
         f"L{num(x)} {num(y + r)}L{num(x - t)} {num(y + t)}L{num(x - r)} {num(y)}L{num(x - t)} {num(y - t)}z")
    cv.add(f'<path d="{d}" fill="#FFFFFF" opacity=".7" filter="url(#glow)"/><path d="{d}" fill="#FFFFFF"/>')


def play_osd(cv: Canvas, x: float, y: float, size: float = 22):
    cv.text("SP", x - width("SP", size * 0.8, track=0.08) - 14, y, size * 0.8, cv.c["muted"], track=0.08)
    w = cv.text("PLAY", x, y, size, cv.c["text"], track=0.08)
    s = size * 0.5
    tx = x + w + 8
    cv.add(f'<path d="M{num(tx)} {num(y - s * 1.05)}l{num(s * 0.9)} {num(s * 0.52)}l{num(-s * 0.9)} {num(s * 0.52)}z" fill="{cv.c["text"]}"/>')


def cursor(cv: Canvas, x: float, y: float, size: float):
    cv.add(f'<rect class="cur" x="{num(x)}" y="{num(y - size * 0.62)}" width="{num(size * 0.4)}" height="{num(size * 0.7)}" fill="{cv.c["magenta"]}"/>')


def frame_start(cv: Canvas, rx: float, scan: float = 1.0) -> str:
    """scan scales scanline strength: full on the screen, softer on the printed J-card."""
    common_defs(cv, scan)
    clip = cv.uid("cl")
    cv.defs.append(f'<clipPath id="{clip}"><rect width="{cv.w}" height="{cv.h}" rx="{rx}"/></clipPath>')
    cv.add(f'<g clip-path="url(#{clip})">')
    return clip


NAME = ("EDUARDO TREICHEL", "SCHELBAUER")
BANNER_TITLE = "Eduardo Treichel Schelbauer"
BANNER_DESC = ("Full-stack developer, Laravel and Nuxt, at Podtech in Santa Catarina, Brazil. "
               "Drawn as an 80s synthwave screen: a striped sunset over wireframe ridges and a neon grid.")


def name_block(cv: Canvas, x: float, top: float, block_w: float, gap: float) -> float:
    """Both name lines are set to the same measure, so the surname lands much larger: the chrome logo shape."""
    s1 = block_w / width(NAME[0], 1, **DISPLAY)
    s2 = block_w / width(NAME[1], 1, **DISPLAY)
    y1 = top + s1 * CAP["archivo"]
    y2 = y1 + gap + s2 * CAP["archivo"]
    cv.chrome(NAME[0], x, y1, s1)
    cv.chrome(NAME[1], x, y2, s2)
    sparkle(cv, x + block_w - 10, y2 - s2 * CAP["archivo"] + 3, s2 * 0.2)
    sparkle(cv, x + s1 * 0.9, y1 - s1 * CAP["archivo"] + 2, s1 * 0.22)
    return y2


def banner_wide(theme: str) -> str:
    W, H, rx = 840, 320, 16
    cv = Canvas(W, H, theme, BANNER_TITLE, BANNER_DESC)
    clip = frame_start(cv, rx)
    hy = 214
    horizon_scene(
        cv, hy, sun=(664, 146, 94),
        ridges=[ridge(486, 640, hy, [(.18, 22), (.4, 46), (.62, 30), (.8, 52)]),
                ridge(688, 840, hy, [(.15, 40), (.38, 64), (.6, 36), (.85, 58)]),
                ridge(-10, 250, hy, [(.3, 9), (.6, 15), (.85, 6)])],
        stars=56, seed=84, clouds=(520, 820, 40, 120),
    )
    x = 40
    y2 = name_block(cv, x, 30, 430, 12)
    c = cv.c
    ty = y2 + 40
    line = "> FULL-STACK DEVELOPER · LARAVEL + NUXT"
    w = cv.text(line, x, ty, 24, c["cyan"], fit=470)
    cursor(cv, x + w + 6, ty, 24)
    cv.text("PODTECH · SANTA CATARINA, BRAZIL", x, ty + 26, 20, c["muted"], fit=470)
    play_osd(cv, W - 104, 38)
    cv.add("</g>")
    crt_overlay(cv, clip, rx)
    return cv.svg()


def banner_narrow(theme: str) -> str:
    W, H, rx = 420, 440, 14
    cv = Canvas(W, H, theme, BANNER_TITLE, BANNER_DESC)
    clip = frame_start(cv, rx)
    hy = 338
    horizon_scene(
        cv, hy, sun=(236, 300, 66),
        ridges=[ridge(70, 196, hy, [(.2, 16), (.45, 34), (.75, 22)]),
                ridge(270, 430, hy, [(.2, 28), (.5, 46), (.8, 24)])],
        stars=34, seed=19, clouds=(40, 400, 252, 280),
    )
    x = 24
    y2 = name_block(cv, x, 58, 360, 10)
    c = cv.c
    ty = y2 + 38
    cv.text("> FULL-STACK DEVELOPER", x, ty, 22, c["cyan"], fit=372)
    w = cv.text("> LARAVEL + NUXT", x, ty + 24, 22, c["cyan"], fit=372)
    cursor(cv, x + w + 6, ty + 24, 22)
    cv.text("PODTECH", x, ty + 52, 19, c["muted"], fit=372)
    cv.text("SANTA CATARINA, BRAZIL", x, ty + 74, 19, c["muted"], fit=372)
    play_osd(cv, W - 92, 34, 20)
    cv.add("</g>")
    crt_overlay(cv, clip, rx)
    return cv.svg()


FRONT = ["Vue 3", "TypeScript", "PrimeVue", "Tailwind", "Vitest"]
BACK = ["PHP", "PostgreSQL / PostGIS", "Redis", "Queues", "Reverb / Pusher", "PHPUnit"]
PLATFORM = ["Docker", "Kubernetes on DigitalOcean", "AWS S3", "GitHub Actions"]
ALSO = "ALSO REACT, NEXT.JS AND NODE.JS · EXPLORING GO"
STACK_TITLE = "Stack"
STACK_DESC = (
    "Drawn as a cassette and its J-card. Side A, web app: Nuxt 4 with Vue 3, TypeScript, PrimeVue, Tailwind and Vitest. "
    "Side B, API: Laravel 12 on Octane with PHP, PostgreSQL and PostGIS, Redis, queues, Reverb and Pusher, PHPUnit. "
    "Runs on Docker, Kubernetes on DigitalOcean, AWS S3 and GitHub Actions. Also React, Next.js and Node.js; exploring Go."
)
def stripes(c: dict) -> list[str]:
    return [c["sun"][0], c["sun"][2], c["sun"][3], c["sun"][4]]


def reel(cv: Canvas, cx: float, cy: float, pack: float, cls: str):
    """Tape pack wound round a hub; the hub carries the spin so the pack edge stays still, as on a real reel."""
    c = cv.c
    cv.add(f'<circle cx="{num(cx)}" cy="{num(cy)}" r="{num(pack)}" fill="{c["tape"]}"/>'
           f'<circle cx="{num(cx)}" cy="{num(cy)}" r="{num(pack * 0.72)}" fill="none" stroke="{c["tape_ring"]}" stroke-width=".8"/>'
           f'<circle cx="{num(cx)}" cy="{num(cy)}" r="{num(pack - 1)}" fill="none" stroke="{c["tape_ring"]}" stroke-width=".8"/>')
    teeth = "".join(
        f'<rect x="{num(cx - 1.6)}" y="{num(cy - 10.5)}" width="3.2" height="4" transform="rotate({a} {num(cx)} {num(cy)})"/>'
        for a in range(0, 360, 60)
    )
    cv.add(f'<g class="{cls}"><circle cx="{num(cx)}" cy="{num(cy)}" r="9.5" fill="{c["hub"]}"/>'
           f'<circle cx="{num(cx)}" cy="{num(cy)}" r="5.2" fill="{c["glass"]}"/><g fill="{c["glass"]}">{teeth}</g></g>')


def cassette(cv: Canvas, x: float, y: float, w: float = 300, h: float = 190):
    """A compact cassette in plan view: lit shell with write-protect tabs, ruled label, clear window, head bridge."""
    c = cv.c
    cv.add(f'<rect x="{num(x)}" y="{num(y)}" width="{w}" height="{h}" rx="12" fill="none" stroke="{c["neon"]}" stroke-width="6" opacity=".55" filter="url(#glow)"/>')
    cv.add(f'<rect x="{num(x)}" y="{num(y)}" width="{w}" height="{h}" rx="12" fill="{lin(cv, [c["shell_hi"], c["shell"], c["shell_lo"]], y, y + h)}"/>')
    cv.add(f'<path d="M{num(x + 12)} {num(y + 1.2)}H{num(x + w - 12)}" stroke="#FFFFFF" stroke-opacity=".45" stroke-width="1.4"/>'
           f'<path d="M{num(x + 12)} {num(y + h - 1)}H{num(x + w - 12)}" stroke="#000000" stroke-opacity=".3" stroke-width="2"/>'
           f'<rect x="{num(x + .7)}" y="{num(y + .7)}" width="{w - 1.4}" height="{h - 1.4}" rx="11.5" fill="none" stroke="{c["neon"]}" stroke-opacity=".7" stroke-width="1.2"/>')
    for tx in (x + 36, x + w - 52):
        cv.add(f'<rect x="{num(tx)}" y="{num(y)}" width="16" height="5" fill="{c["shell_lo"]}"/>')
    for sx, sy in ((x + 12, y + 14), (x + w - 12, y + 14), (x + 12, y + h - 12), (x + w - 12, y + h - 12), (x + w / 2, y + h - 14)):
        cv.add(f'<circle cx="{num(sx)}" cy="{num(sy)}" r="4" fill="{c["shell_lo"]}"/>'
               f'<path d="M{num(sx - 2.4)} {num(sy)}h4.8M{num(sx)} {num(sy - 2.4)}v4.8" stroke="{c["shell_hi"]}" stroke-width="1.2"/>')

    lx, ly, lw, lh = x + 22, y + 16, w - 44, 120
    cv.add(f'<rect x="{num(lx)}" y="{num(ly)}" width="{num(lw)}" height="{lh}" rx="6" fill="{c["label"]}"/>')
    for i, col in enumerate(stripes(c)):
        cv.add(f'<rect x="{num(lx)}" y="{num(ly + 88 + i * 7)}" width="{num(lw)}" height="5" fill="{col}"/>')
    cv.add(f'<rect x="{num(lx + 8)}" y="{num(ly + 7)}" width="20" height="20" rx="3" fill="{c["label_ink"]}"/>')
    cv.text("A", lx + 13.6, ly + 23, 20, c["label"])
    cv.text("ACOLHER", lx + 36, ly + 22, 20, c["label_ink"], track=0.1)

    wx, wy, ww, wh = x + w / 2 - 74, ly + 40, 148, 42
    rules = (f"M{num(lx + 36)} {num(ly + 31)}H{num(lx + lw - 10)}"
             f"M{num(lx + 10)} {num(wy + wh / 2)}H{num(wx - 8)}M{num(wx + ww + 8)} {num(wy + wh / 2)}H{num(lx + lw - 10)}"
             f"M{num(lx + 10)} {num(wy + wh - 4)}H{num(wx - 8)}M{num(wx + ww + 8)} {num(wy + wh - 4)}H{num(lx + lw - 10)}")
    cv.add(f'<path d="{rules}" stroke="{c["label_ink"]}" stroke-opacity=".3" stroke-width="1"/>')
    cv.add(f'<rect x="{num(wx)}" y="{num(wy)}" width="{ww}" height="{wh}" rx="{wh / 2}" fill="{c["glass"]}"/>')
    r1, r2 = (wx + 31, wy + wh / 2), (wx + ww - 31, wy + wh / 2)
    reel(cv, *r1, 19.5, "reel")
    reel(cv, *r2, 12.5, "reel r2")
    cv.add(f'<path d="M{num(r1[0])} {num(r1[1] + 19.5)}L{num(r2[0])} {num(r2[1] + 12.5)}" stroke="{c["tape"]}" stroke-width="1.6"/>')
    cv.add(f'<path d="M{num(wx + 20)} {num(wy + wh)}L{num(wx + 44)} {num(wy)}M{num(wx + 30)} {num(wy + wh)}L{num(wx + 54)} {num(wy)}" stroke="#FFFFFF" stroke-opacity=".16" stroke-width="5"/>')
    cv.add(f'<rect x="{num(wx)}" y="{num(wy)}" width="{ww}" height="{wh}" rx="{wh / 2}" fill="none" stroke="{c["label_ink"]}" stroke-opacity=".5" stroke-width="1.2"/>')

    bx0, bx1, by0, by1 = x + 58, x + w - 58, y + h - 42, y + h
    cv.add(f'<path d="M{num(bx0 + 12)} {num(by0)}H{num(bx1 - 12)}L{num(bx1)} {num(by1)}H{num(bx0)}z" fill="{c["shell_lo"]}"/>')
    cv.add(f'<path d="M{num(bx0 + 12)} {num(by0)}H{num(bx1 - 12)}" stroke="#FFFFFF" stroke-opacity=".25"/>')
    holes = "".join(f'<circle cx="{num(hx)}" cy="{num(by0 + 22)}" r="5"/>' for hx in (bx0 + 34, bx1 - 34))
    holes += f'<rect x="{num(x + w / 2 - 9)}" y="{num(by0 + 16)}" width="18" height="12" rx="2"/>'
    cv.add(f'<g fill="{c["window"]}" stroke="{c["shell_hi"]}" stroke-width="1.2">{holes}</g>')


def jcard(cv: Canvas, x: float, y: float, w: float, h: float, spine: float = 28) -> float:
    """The printed tape insert: card stock, a sunset-striped spine and its fold. Returns where print starts."""
    c = cv.c
    cv.add(f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" rx="4" fill="none" stroke="{c["neon"]}" stroke-width="5" opacity=".3" filter="url(#glow)"/>')
    cv.add(f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" rx="4" fill="{c["card"]}" stroke="{c["card_edge"]}"/>')
    for i, col in enumerate(stripes(c)):
        cv.add(f'<rect x="{num(x + 4 + i * 5.5)}" y="{num(y + 1)}" width="3.5" height="{num(h - 2)}" fill="{col}"/>')
    cv.add(f'<path d="M{num(x + spine)} {num(y + 4)}V{num(y + h - 4)}" stroke="{c["card_edge"]}" stroke-dasharray="3 3"/>')
    return x + spine + 16


def side(cv: Canvas, letter: str, x: float, y: float, head: str, sub: str, items: list[str], fit: float,
         item_size: float = 24, sub_below: bool = False) -> float:
    """One side of the J-card: side badge, chrome headline, subtitle, track lines. Returns the last baseline."""
    c = cv.c
    cv.add(f'<rect x="{num(x)}" y="{num(y - 25)}" width="28" height="28" rx="4" fill="none" stroke="{c["magenta"]}" stroke-width="1.6"/>')
    cv.text(letter, x + 8.4, y - 4, 24, c["magenta"])
    hx = x + 42
    hw = cv.chrome(head, hx, y, 30, fit=fit - 42)
    if sub_below:
        cv.text(sub, hx, y + 26, 20, c["cyan"], track=0.04, fit=fit - 42)
        y += 26
    else:
        cv.text(sub, hx + hw + 14, y, 21, c["cyan"], track=0.04, fit=fit - (hw + 56))
    joiner = " · "
    cv.text(joiner.join(items[:3]), hx, y + 34, item_size, c["text"], fit=fit - 42)
    cv.text(joiner.join(items[3:]), hx, y + 34 + item_size + 4, item_size, c["text"], fit=fit - 42)
    return y + 34 + item_size + 4


def bezel(cv: Canvas, y: float):
    """The console's front panel under the floor: solid, so the platform lines never sit on grid lines."""
    c = cv.c
    cv.add(f'<rect y="{num(y)}" width="{cv.w}" height="{num(cv.h - y)}" fill="{c["bezel"]}"/>')
    cv.add(f'<path d="M0 {num(y)}H{cv.w}" stroke="{c["horizon"]}" stroke-width="6" stroke-opacity=".3"/>'
           f'<path d="M0 {num(y)}H{cv.w}" stroke="{c["horizon"]}" stroke-width="1.4"/>')


def platform_lines(cv: Canvas, x: float, y: float, w: float, lines: list[list[str]], size: float = 22):
    c = cv.c
    label_w = cv.text("RUNS ON", x, y, size, c["amber"], track=0.06) + 14
    for i, items in enumerate(lines):
        cv.text(" · ".join(items), x + label_w, y + i * (size + 4), size, c["text"], fit=w - label_w)


def stack_wide(theme: str) -> str:
    W, H, rx = 840, 404, 16
    cv = Canvas(W, H, theme, STACK_TITLE, STACK_DESC)
    clip = frame_start(cv, rx, scan=0.6)
    c = cv.c
    hy, bezel_y = 252, 318
    sky(cv, hy, 40, 7, clouds=(30, 330, 12, 34))
    floor_grid(cv, hy, bezel_y, 178, animated=False, strength=0.7)
    bezel(cv, bezel_y)
    cassette(cv, 28, 46)
    cx = jcard(cv, 336, 26, W - 336 - 24, 270)
    fit = W - 24 - 14 - cx
    side(cv, "A", cx, 74, "NUXT 4", "WEB APP", FRONT, fit)
    cv.add(f'<path d="M{num(cx)} 160H{W - 40}" stroke="{c["rule"]}" stroke-dasharray="2 5" stroke-width="1.4"/>')
    side(cv, "B", cx, 202, "LARAVEL 12", "API ON OCTANE", BACK, fit)
    platform_lines(cv, 28, bezel_y + 36, W - 56, [PLATFORM])
    cv.text(ALSO, 28, H - 22, 20, c["muted"], fit=W - 56)
    cv.add("</g>")
    crt_overlay(cv, clip, rx)
    return cv.svg()


def stack_narrow(theme: str) -> str:
    W, H, rx = 420, 712, 14
    cv = Canvas(W, H, theme, STACK_TITLE, STACK_DESC)
    clip = frame_start(cv, rx, scan=0.6)
    c = cv.c
    hy, bezel_y = 238, 580
    sky(cv, hy, 30, 11, clouds=(16, 404, 10, 26))
    floor_grid(cv, hy, bezel_y, 210, animated=False, strength=0.7)
    bezel(cv, bezel_y)
    cassette(cv, 60, 30)
    cx = jcard(cv, 14, 250, W - 28, 310)
    fit = W - 14 - 12 - cx
    last = side(cv, "A", cx, 292, "NUXT 4", "WEB APP", FRONT, fit, 21, sub_below=True)
    cv.add(f'<path d="M{num(cx)} {num(last + 22)}H{W - 28}" stroke="{c["rule"]}" stroke-dasharray="2 5" stroke-width="1.4"/>')
    side(cv, "B", cx, last + 66, "LARAVEL 12", "API ON OCTANE", BACK, fit, 21, sub_below=True)
    platform_lines(cv, 22, bezel_y + 36, W - 44, [PLATFORM[:2], PLATFORM[2:]], 20)
    cv.text("ALSO REACT, NEXT.JS AND NODE.JS", 22, H - 42, 19, c["muted"], fit=W - 44)
    cv.text("EXPLORING GO", 22, H - 18, 19, c["muted"], fit=W - 44)
    cv.add("</g>")
    crt_overlay(cv, clip, rx)
    return cv.svg()


BUILDERS = {
    "banner": (banner_wide, banner_narrow),
    "stack": (stack_wide, stack_narrow),
}


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    for name, (wide, narrow) in BUILDERS.items():
        for theme in THEMES:
            (ASSETS / f"{name}-{theme}.svg").write_text(wide(theme), encoding="utf-8")
            (ASSETS / f"{name}-{theme}-narrow.svg").write_text(narrow(theme), encoding="utf-8")
    for f in sorted(ASSETS.glob("*.svg")):
        print(f"{f.relative_to(ROOT)}  {f.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
