#!/usr/bin/env python3
"""The Passport Page of a Country That Isn't There.

Renders one open passport spread of the Republic of Calderia — a small
volcanic island republic that does not exist — as a single PNG written to
the output directory as entry.png.

Left page: visas and border stamps telling one consistent travel history.
Right page: the data page — engraved-style portrait, the bearer's data in
three languages, and a machine-readable zone whose ICAO check digits are
computed for real, so every number on the page agrees with every other.

Everything is drawn from scratch with PIL; no image assets, no network.
The render is deterministic (all randomness is seeded) and supersampled
2x, then downscaled, so the program's two grading runs agree byte for byte.
"""

import math
import os
import random
import zlib

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------- setup

SS = 2                      # supersampling factor
W, H = 1024, 727            # final image size (an open passport spread)
CW, CH = W * SS, H * SS     # canvas size

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
SANS = f"{FONT_DIR}/DejaVuSans.ttf"
SANSB = f"{FONT_DIR}/DejaVuSans-Bold.ttf"
SERIFB = f"{FONT_DIR}/DejaVuSerif-Bold.ttf"
MONOB = f"{FONT_DIR}/DejaVuSansMono-Bold.ttf"

_fonts = {}


def F(path, size):
    """Font at `size` final pixels (scaled to the supersampled canvas)."""
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, int(round(size * SS)))
    return _fonts[key]


def u(v):
    return int(round(v * SS))


def pt(x, y):
    return (u(x), u(y))


def rc(x0, y0, x1, y1):
    return [u(x0), u(y0), u(x1), u(y1)]


# Colours
COVER = (94, 18, 36)          # burgundy booklet cover
PAPER = (246, 241, 228)       # page ivory
PAPER_D = (238, 231, 213)
NAVY = (27, 42, 74)           # header ink
INK = (33, 37, 44)            # data ink
GREY = (110, 108, 100)        # label grey
BURG = (128, 26, 48)          # accent burgundy
GOLD = (176, 141, 62)
TEAL_G = (120, 165, 160)      # guilloche inks
ROSE_G = (196, 148, 152)
BLUE_G = (130, 152, 190)
ST_BLUE = (36, 71, 143)       # stamp inks
ST_RED = (176, 58, 46)
ST_VIOLET = (108, 52, 131)


def text(d, xy, s, font, fill, anchor="la", spacing=0):
    """Draw text, optionally letterspaced (spacing in final pixels)."""
    x, y = xy
    if spacing:
        widths = [d.textlength(ch, font=font) for ch in s]
        total = sum(widths) + u(spacing) * (len(s) - 1)
        if anchor == "ma":
            x = x - total / (2 * SS)
        cx = x
        for ch, w in zip(s, widths):
            d.text(pt(cx, y), ch, font=font, fill=fill)
            cx += (w + u(spacing)) / SS
        return total / SS
    if anchor == "ma":
        w = d.textlength(s, font=font) / SS
        d.text(pt(x - w / 2, y), s, font=font, fill=fill)
        return w
    d.text(pt(x, y), s, font=font, fill=fill)
    return d.textlength(s, font=font) / SS


def rule(d, x0, x1, y, fill, w=1.0):
    d.line([pt(x0, y), pt(x1, y)], fill=fill, width=max(1, u(w)))


# ---------------------------------------------------------------- guilloche

def guilloche(img, box, colors=(TEAL_G, ROSE_G, BLUE_G), alpha=64, waves=26):
    """Interlacing sine-wave security pattern clipped to `box`."""
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w, h = x1 - x0, y1 - y0
    for k in range(waves):
        col = colors[k % len(colors)] + (alpha,)
        phase = k * 0.55
        amp = h * (0.16 + 0.05 * math.sin(k * 1.7))
        base = y0 + h * (k + 0.5) / waves
        pts = []
        for i in range(0, int(w) + 4, 4):
            xx = x0 + i
            yy = base + amp * 0.32 * math.sin(i / w * math.pi * 3 + phase) \
                + amp * 0.14 * math.sin(i / w * math.pi * 7 + phase * 2)
            pts.append(pt(xx, yy))
        d.line(pts, fill=col, width=max(1, u(0.8)))
    # a rosette of wobbly rings, lower right of the region
    cx, cy = x0 + w * 0.78, y0 + h * 0.30
    for r in range(14, 120, 9):
        pts = []
        for a in range(0, 361, 6):
            t = math.radians(a)
            rr = r * (1 + 0.09 * math.sin(t * 5 + r))
            pts.append(pt(cx + rr * math.cos(t), cy + rr * math.sin(t) * 0.82))
        d.line(pts, fill=colors[1] + (alpha - 14,), width=max(1, u(0.8)))
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rectangle(rc(*box), fill=255)
    img.paste(Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB"),
              (0, 0), mask)


# ---------------------------------------------------------------- coat of arms
# Shield of Calderia: on azure, a volcano argent smoking gules above three
# waves argent, a mullet or in chief. Drawn flat, heraldic, at any size.

def coat_of_arms(img, cx, cy, size, alpha=255):
    """Draw the shield centred at (cx, cy), `size` final px tall."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w = size * 0.82
    x0, x1 = cx - w / 2, cx + w / 2
    y0, y1 = cy - size / 2, cy + size / 2
    # shield outline: flat top, sides curving to a point at the base
    pts = [(x0, y0), (x1, y0), (x1, y0 + size * 0.52)]
    for i in range(1, 10):
        t = i / 10
        xx = x1 - (x1 - cx) * (1 - math.cos(t * math.pi / 2)) * 1.0
        yy = y0 + size * 0.52 + (y1 - y0 - size * 0.52) * math.sin(t * math.pi / 2)
        pts.append((xx, yy))
    pts.append((cx, y1))
    for i in range(9, 0, -1):
        t = i / 10
        xx = x0 + (cx - x0) * (1 - math.cos(t * math.pi / 2))
        yy = y0 + size * 0.52 + (y1 - y0 - size * 0.52) * math.sin(t * math.pi / 2)
        pts.append((xx, yy))
    pts.append((x0, y0 + size * 0.52))
    P = [pt(x, y) for x, y in pts]
    azure = (38, 74, 135, alpha)
    d.polygon(P, fill=azure)
    d.line(P + [P[0]], fill=(212, 175, 55, alpha), width=max(1, u(size * 0.035)))
    # star (mullet or) in chief
    sx, sy, sr = cx, y0 + size * 0.16, size * 0.085
    star = []
    for i in range(10):
        t = -math.pi / 2 + i * math.pi / 5
        rr = sr if i % 2 == 0 else sr * 0.45
        star.append(pt(sx + rr * math.cos(t), sy + rr * math.sin(t)))
    d.polygon(star, fill=(232, 184, 75, alpha))
    # volcano argent with smoke gules
    vy = y0 + size * 0.62
    d.polygon([pt(cx - size * 0.26, vy), pt(cx - size * 0.07, y0 + size * 0.34),
               pt(cx + size * 0.07, y0 + size * 0.34), pt(cx + size * 0.26, vy)],
              fill=(226, 228, 230, alpha))
    d.polygon([pt(cx - size * 0.07, y0 + size * 0.34), pt(cx + size * 0.07, y0 + size * 0.34),
               pt(cx + size * 0.028, y0 + size * 0.44), pt(cx - size * 0.028, y0 + size * 0.44)],
              fill=(178, 44, 44, alpha))
    for i, dx in enumerate((-0.05, 0.0, 0.05)):
        d.arc(rc(cx + size * dx - size * 0.05, y0 + size * (0.13 + i * 0.055),
                 cx + size * dx + size * 0.05, y0 + size * (0.23 + i * 0.055)),
              start=200, end=330, fill=(200, 200, 205, alpha), width=max(1, u(size * 0.02)))
    # three waves argent at the base
    for j, yy in enumerate((0.70, 0.79, 0.88)):
        pts = []
        for i in range(0, int(w * 0.62) + 2, 3):
            xx = cx - w * 0.31 + i
            pts.append(pt(xx, y0 + size * yy + size * 0.018 * math.sin(i / (w * 0.62) * math.pi * 3 + j * 1.2)))
        d.line(pts, fill=(226, 228, 230, alpha), width=max(1, u(size * 0.028)))
    img.paste(Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB"),
              (0, 0), layer)


# ---------------------------------------------------------------- portrait
# The bearer's portrait in the engraved style of a polycarbonate data page:
# grey washes, fine horizontal hatching, drawn once and reused (the small
# ghost image at the foot of the data page is the same portrait, faded).

def _hatch(base, mask, spacing, color, y0=0, y1=None, xoff=0):
    """Lay horizontal engraved lines over `base` where `mask` is set."""
    lines = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lines)
    y1 = y1 or base.size[1]
    for y in range(int(y0), int(y1), int(spacing)):
        d.line([(0, y), (base.size[0], y + int(spacing * 0.18))],
               fill=color, width=max(1, int(spacing * 0.34)))
    base.paste(Image.alpha_composite(base, lines), (0, 0), mask)


def portrait_image(w=170, h=218):
    """A front-facing portrait of the bearer, drawn at final size w x h."""
    s = SS
    img = Image.new("RGBA", (u(w), u(h)), (233, 236, 236, 255))
    d = ImageDraw.Draw(img)
    # faint security waves behind the sitter
    for k in range(9):
        pts = []
        for i in range(0, u(w) + 4, 6):
            pts.append((i, u(18 + k * 24) + int(9 * math.sin(i / u(w) * 6 + k))))
        d.line(pts, fill=(168, 188, 190, 90), width=max(1, u(1)))
    cx = w / 2
    skin = (206, 188, 172, 255)
    skin_d = (178, 156, 138, 255)
    hair = (62, 53, 48, 255)
    hair_d = (34, 30, 29, 255)
    line = (38, 40, 44, 255)
    # hair mass behind head and shoulders
    d.ellipse(rc(cx - 56, 16, cx + 56, 150), fill=hair)
    d.rectangle(rc(cx - 56, 84, cx + 56, 178), fill=hair)
    # shoulders / blouse
    d.polygon([pt(cx - 66, h), pt(cx - 58, 168), pt(cx - 20, 152),
               pt(cx + 20, 152), pt(cx + 58, 168), pt(cx + 66, h)],
              fill=(43, 74, 82, 255))
    # collar (white shirt V)
    d.polygon([pt(cx - 20, 152), pt(cx + 20, 152), pt(cx, 178)], fill=(238, 238, 236, 255))
    d.polygon([pt(cx - 20, 152), pt(cx, 178), pt(cx - 6, 154)], fill=(214, 216, 214, 255))
    # neck
    d.rectangle(rc(cx - 13, 128, cx + 13, 158), fill=skin_d)
    # face
    d.ellipse(rc(cx - 40, 30, cx + 40, 138), fill=skin)
    d.pieslice(rc(cx - 40, 30, cx + 40, 138), start=20, end=160, fill=skin)
    # ears
    d.ellipse(rc(cx - 44, 82, cx - 36, 102), fill=skin)
    d.ellipse(rc(cx + 36, 82, cx + 44, 102), fill=skin)
    # engraved shading: sides of the face and under the jaw, feathered
    # with two passes so the hatching has no hard mask edge
    shade = Image.new("L", img.size, 0)
    sd = ImageDraw.Draw(shade)
    sd.ellipse(rc(cx - 40, 30, cx + 40, 138), fill=255)
    sd.ellipse(rc(cx - 33, 35, cx + 33, 131), fill=0)
    _hatch(img, shade, u(2.8), (118, 98, 82, 70))
    shade2 = Image.new("L", img.size, 0)
    sd2 = ImageDraw.Draw(shade2)
    sd2.ellipse(rc(cx - 40, 30, cx + 40, 138), fill=255)
    sd2.ellipse(rc(cx - 26, 37, cx + 26, 129), fill=0)
    sd2.rectangle(rc(cx - 28, 124, cx + 28, 140), fill=110)
    _hatch(img, shade2, u(2.8), (118, 98, 82, 130))
    d = ImageDraw.Draw(img)
    # soft modelling on the cheeks
    d.ellipse(rc(cx - 33, 96, cx - 12, 122), fill=(196, 174, 156, 255))
    d.ellipse(rc(cx + 12, 96, cx + 33, 122), fill=(196, 174, 156, 255))
    # hair over the top of the head: the skull's outer curve, then back
    # along a gently arched hairline whose peak sits left of centre
    hair_pts = []
    for i in range(25):
        t = math.pi + math.pi * i / 24
        hair_pts.append((cx + 44 * math.cos(t), 54 + 46 * math.sin(t)))
    hair_pts.append((cx + 44, 118))
    for i in range(25):
        x = cx + 40 - i * (80 / 24)
        hair_pts.append((x, 40 + 13 * ((x - (cx - 7)) / 41) ** 2))
    hair_pts.append((cx - 44, 118))
    d.polygon([pt(x, y) for x, y in hair_pts], fill=hair)
    d.polygon([pt(cx - 43, 52), pt(cx - 43, 120), pt(cx - 33, 118), pt(cx - 34, 58)], fill=hair)
    d.polygon([pt(cx + 43, 52), pt(cx + 43, 120), pt(cx + 33, 118), pt(cx + 34, 58)], fill=hair)
    # a single sheen along the hair, and fine strands down the sides
    d.arc(rc(cx - 32, 14, cx + 28, 62), start=205, end=320,
          fill=(110, 98, 88, 255), width=u(2.2))
    for side in (-1, 1):
        for j in range(4):
            x = cx + side * (45 + j * 3)
            d.line([pt(x, 92 + j * 3), pt(x + side * 1.5, 168)],
                   fill=(88, 78, 70, 255), width=max(1, u(0.9)))
    # eyebrows
    d.arc(rc(cx - 30, 66, cx - 8, 80), start=200, end=335, fill=line, width=u(2.6))
    d.arc(rc(cx + 8, 66, cx + 30, 80), start=205, end=340, fill=line, width=u(2.6))
    # eyes, the upper lid resting over the iris
    for ex in (cx - 18, cx + 18):
        d.ellipse(rc(ex - 10, 82.5, ex + 10, 92.5), fill=(244, 244, 242, 255))
        d.ellipse(rc(ex - 4.6, 83, ex + 4.6, 92.2), fill=(74, 58, 44, 255))
        d.ellipse(rc(ex - 2.1, 85.4, ex + 2.1, 89.8), fill=(16, 14, 12, 255))
        d.ellipse(rc(ex - 0.8, 85.4, ex + 0.8, 87.2), fill=(250, 250, 250, 255))
        d.rectangle(rc(ex - 10.5, 80.5, ex + 10.5, 85), fill=skin)
        d.arc(rc(ex - 10.5, 80, ex + 10.5, 94), start=185, end=355, fill=line, width=u(2.0))
        d.arc(rc(ex - 9.5, 82, ex + 9.5, 95), start=35, end=145, fill=(150, 128, 110, 255), width=u(1.1))
    # nose: bridge shadow, a soft base line and the nostrils
    d.line([pt(cx + 1.5, 92), pt(cx - 0.5, 105)], fill=(150, 126, 106, 255), width=u(1.6))
    d.arc(rc(cx - 6.5, 104, cx + 6.5, 112), start=25, end=155, fill=(146, 120, 100, 255), width=u(1.3))
    d.ellipse(rc(cx - 7.6, 105.5, cx - 4.4, 108.5), fill=(146, 120, 100, 255))
    d.ellipse(rc(cx + 4.4, 105.5, cx + 7.6, 108.5), fill=(146, 120, 100, 255))
    # mouth: a centre line, a fuller lower lip, a shallow upper lip
    d.arc(rc(cx - 12, 110, cx + 12, 128), start=20, end=160, fill=(168, 102, 96, 255), width=u(2.2))
    d.arc(rc(cx - 12, 111, cx + 12, 125), start=200, end=340, fill=(150, 84, 78, 255), width=u(1.8))
    d.line([pt(cx - 12, 119.5), pt(cx + 12, 119.5)], fill=(110, 52, 50, 255), width=u(1.3))
    # fine print lines across the whole portrait, as if laser-engraved
    scan = Image.new("L", img.size, 0)
    ImageDraw.Draw(scan).rectangle([0, 0, img.size[0], img.size[1]], fill=255)
    _hatch(img, scan, u(4.6), (90, 90, 90, 15))
    return img


# ---------------------------------------------------------------- stamps

def stamp_tile(w, h, color, lines, shape="rect", double=False):
    """One border stamp as an RGBA tile (final px w x h), ink slightly worn."""
    t = Image.new("RGBA", (u(w), u(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(t)
    ink = color + (218,)
    if shape == "circle":
        d.ellipse(rc(3, 3, w - 3, h - 3), outline=ink, width=u(2.6))
        d.ellipse(rc(8.5, 8.5, w - 8.5, h - 8.5), outline=ink, width=u(1.1))
    else:
        d.rounded_rectangle(rc(2.5, 2.5, w - 2.5, h - 2.5), radius=u(7),
                            outline=ink, width=u(2.6))
        if double:
            d.rounded_rectangle(rc(7.5, 7.5, w - 7.5, h - 7.5), radius=u(5),
                                outline=ink, width=u(1.1))
    cy = h / 2
    total = sum(sz * 1.42 for _, sz, _ in lines)
    y = cy - total / 2
    for txt, sz, bold in lines:
        f = F(SANSB if bold else SANS, sz)
        text(d, (w / 2, y), txt, f, ink, anchor="ma", spacing=0.4)
        y += sz * 1.42
    # wear: knock out a few specks of ink
    rng = random.Random(zlib.crc32(lines[0][0].encode("utf-8")))
    px = t.load()
    for _ in range(int(w * h * 0.012)):
        x = rng.randrange(t.size[0])
        y = rng.randrange(t.size[1])
        r, g, b, a = px[x, y]
        if a:
            px[x, y] = (r, g, b, int(a * 0.35))
    return t


def place(img, tile, cx, cy, angle):
    r = tile.rotate(angle, expand=True, resample=Image.BICUBIC)
    img.paste(r, (u(cx) - r.size[0] // 2, u(cy) - r.size[1] // 2), r)


# ---------------------------------------------------------------- MRZ

def _mrz_value(ch):
    if ch == "<":
        return 0
    if ch.isdigit():
        return int(ch)
    return ord(ch) - 55  # A=10 ... Z=35


def mrz_check(field):
    weights = (7, 3, 1)
    return str(sum(_mrz_value(c) * weights[i % 3] for i, c in enumerate(field)) % 10)


def build_mrz():
    line1 = "P<CLDFERRER<VIDAL<<LUCIA"
    line1 = line1 + "<" * (44 - len(line1))
    doc = "C4819207<"
    dob, exp = "900214", "310511"
    personal = "9002144417<<<<"
    body = (doc + mrz_check(doc) + "CLD" + dob + mrz_check(dob) + "F"
            + exp + mrz_check(exp) + personal + mrz_check(personal))
    composite = mrz_check(body[0:10] + body[13:20] + body[21:43])
    line2 = body + composite
    assert len(line1) == 44 and len(line2) == 44, (line1, line2)
    return line1, line2


# ---------------------------------------------------------------- fields

def field(d, x, y, label, value, w=None, vsize=15.5):
    text(d, (x, y), label, F(SANS, 8.2), GREY, spacing=0.5)
    text(d, (x, y + 11), value, F(SANSB, vsize), INK, spacing=0.3)
    return y + 36


# ---------------------------------------------------------------- the spread

def render():
    random.seed(20211121)
    img = Image.new("RGB", (CW, CH), COVER)
    d = ImageDraw.Draw(img)

    # pages
    for x0 in (10, 512):
        d.rectangle(rc(x0, 10, x0 + 502, H - 10), fill=PAPER)
    guilloche(img, (36, 36, 486, 690))
    guilloche(img, (538, 128, 988, 600))
    d = ImageDraw.Draw(img)
    # watermark arms on the visa page
    coat_of_arms(img, 261, 420, 250, alpha=34)
    d = ImageDraw.Draw(img)
    # spine shadow: one soft, narrow gradient where the pages meet
    shade = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for i in range(17):
        a = int(46 * math.sin(math.pi * i / 16))
        sd.line([pt(512 - 8 + i, 0), pt(512 - 8 + i, H)], fill=(40, 30, 20, a), width=u(1.2))
    img = Image.alpha_composite(img.convert("RGBA"), shade).convert("RGB")
    d = ImageDraw.Draw(img)

    # ================= left page: visas & stamps =================
    text(d, (36, 38), "VISADOS", F(SANSB, 17), NAVY, spacing=3)
    text(d, (150, 38), "· VISAS · VISA", F(SANS, 12.5), GREY, spacing=2)
    rule(d, 36, 486, 66, NAVY, 1.4)
    text(d, (36, 74), "Este pasaporte contiene 32 páginas numeradas.",
         F(SANS, 9.5), GREY)
    text(d, (36, 87), "This passport contains 32 numbered pages.",
         F(SANS, 9.5), GREY)

    # --- Belmira visa sticker (the telling paperwork: its conditions) ---
    visa = Image.new("RGBA", (u(272), u(158)), (228, 238, 222, 255))
    vd = ImageDraw.Draw(visa)
    vd.rectangle(rc(0, 0, 272, 158), outline=(70, 110, 74), width=u(2))
    vd.rectangle(rc(5, 5, 267, 153), outline=(70, 110, 74), width=u(0.8))
    for k in range(7):
        pts = []
        for i in range(0, u(272) + 4, 6):
            pts.append((i, u(20 + k * 20) + int(6 * math.sin(i / u(272) * 7 + k * 2))))
        vd.line(pts, fill=(150, 180, 150, 70), width=max(1, u(0.8)))
    text(vd, (136, 12), "REINO DE BELMIRA", F(SANSB, 13), (44, 84, 52), anchor="ma", spacing=1)
    text(vd, (136, 30), "VISADO · VISA · B-771204", F(SANS, 9.5), (44, 84, 52), anchor="ma", spacing=1)
    rule(vd, 14, 258, 48, (70, 110, 74), 1)
    rows = [("Entradas / Entries", "MÚLTIPLES · MULTIPLE"),
            ("Válido / Valid", "01 JUN 2023 — 01 DIC 2023"),
            ("Titular / Bearer", "FERRER VIDAL, LUCÍA"),
            ("Condición / Condition", "SIN DERECHO A TRABAJO")]
    yy = 56
    for lab, val in rows:
        text(vd, (16, yy), lab, F(SANS, 8), (96, 110, 96))
        text(vd, (16, yy + 10), val, F(SANSB, 10.5), (30, 44, 34))
        yy += 25
    visa_r = visa.rotate(-2, expand=True, resample=Image.BICUBIC)
    img.paste(visa_r, (u(58), u(104)), visa_r)
    d = ImageDraw.Draw(img)

    # --- border stamps: one journey, told in order ---
    place(img, stamp_tile(168, 66, ST_VIOLET, [
        ("CALDERIA — SALIDA", 10.5, True), ("EXIT · PORTO CALDERA AÉREO", 8, False),
        ("03 SEP 2022", 12.5, True)]), 402, 148, 3)
    place(img, stamp_tile(238, 66, ST_BLUE, [
        ("REPÚBLICA DE SAN TEODORO", 10.5, True), ("ENTRADA · ADMITTED", 8.5, False),
        ("03 SEP 2022", 12.5, True)]), 178, 316, -4)
    place(img, stamp_tile(196, 66, ST_BLUE, [
        ("SAN TEODORO — SALIDA", 10.5, True), ("DEPARTED", 8.5, False),
        ("17 SEP 2022", 12.5, True)]), 372, 330, 2)
    place(img, stamp_tile(126, 126, ST_VIOLET, [
        ("BELMIRA", 12, True), ("ENTRADA", 10, True),
        ("28 JUN 2023", 11.5, True), ("PUERTO", 8.5, False)], shape="circle"), 128, 478, 0)
    place(img, stamp_tile(196, 66, ST_VIOLET, [
        ("BELMIRA — SALIDA", 10.5, True), ("DEPARTED", 8.5, False),
        ("02 JUL 2023", 12.5, True)]), 356, 470, -3)
    place(img, stamp_tile(238, 66, ST_BLUE, [
        ("REPÚBLICA DE SAN TEODORO", 10.5, True), ("ENTRADA · ADMITTED", 8.5, False),
        ("19 NOV 2024", 12.5, True)]), 182, 606, 2.5)
    place(img, stamp_tile(138, 58, ST_RED, [
        ("TASA PAGADA", 10.5, True), ("FEE PAID · 40 ESCUDOS", 8.5, False)],
        double=True), 408, 606, -6)
    text(d, (36, 688), "12", F(SANS, 10), GREY)

    # ================= right page: the data page =================
    coat_of_arms(img, 578, 77, 76)
    text(d, (620, 46), "REPÚBLICA DE CALDERIA", F(SERIFB, 21), NAVY, spacing=0.8)
    text(d, (621, 75), "REPUBLIC OF CALDERIA · RÉPUBLIQUE DE CALDERIA",
         F(SANS, 10), GREY, spacing=1.0)
    text(d, (621, 96), "PASAPORTE · PASSPORT · PASSEPORT", F(SANSB, 13.5), BURG, spacing=2)
    # e-passport chip mark, clear of the country name
    d.rounded_rectangle(rc(948, 44, 986, 70), radius=u(3), outline=GOLD, width=u(2))
    d.ellipse(rc(961, 50, 973, 64), outline=GOLD, width=u(2))
    rule(d, 948, 962, 57, GOLD, 1.6)
    rule(d, 972, 986, 57, GOLD, 1.6)
    rule(d, 538, 988, 124, NAVY, 1.4)
    rule(d, 538, 988, 128, BURG, 0.8)

    # portrait
    port = portrait_image()
    img.paste(port, (u(545), u(146)), port)
    d = ImageDraw.Draw(img)
    d.rectangle(rc(545, 146, 545 + 170, 146 + 218), outline=(150, 150, 148), width=u(1))
    # signature under the portrait
    sig = [(0, 14), (5, 3), (10, -7), (14, 0), (13, 10), (18, 14), (26, 6),
           (34, 12), (42, 4), (50, 10), (58, 2), (68, 8), (78, 0), (90, 6),
           (102, 2), (118, 7)]
    d.line([pt(552 + x, 386 + y) for x, y in sig], fill=(30, 40, 90),
           width=u(1.6), joint="curve")
    rule(d, 548, 700, 398, GREY, 0.7)
    text(d, (548, 402), "Firma del titular · Holder's signature", F(SANS, 8), GREY)

    # data fields, right of the portrait
    fx = 736
    y = field(d, fx, 146, "Tipo · Type", "P")
    text(d, (fx + 74, 146), "Código · Code", F(SANS, 8.2), GREY, spacing=0.5)
    text(d, (fx + 74, 157), "CLD", F(SANSB, 15.5), INK)
    y = field(d, fx, y, "Apellidos · Surname", "FERRER VIDAL")
    y = field(d, fx, y, "Nombre · Given names", "LUCÍA")
    y = field(d, fx, y, "Nacionalidad · Nationality", "CALDERIANA")
    y = field(d, fx, y, "Fecha de nacimiento · Date of birth", "14 FEB 1990")
    y = field(d, fx, y, "Sexo · Sex", "F")
    text(d, (fx + 74, y - 36), "Estatura · Height", F(SANS, 8.2), GREY, spacing=0.5)
    text(d, (fx + 74, y - 25), "1,68 M", F(SANSB, 15.5), INK)
    y = field(d, fx, y, "Lugar de nacimiento · Place of birth", "PORTO CALDERA")

    # data fields, full width below
    y = 424
    y = field(d, 545, y, "Fecha de expedición · Date of issue", "12 MAY 2021")
    text(d, (736, y - 36), "Fecha de caducidad · Date of expiry", F(SANS, 8.2), GREY, spacing=0.5)
    text(d, (736, y - 25), "11 MAY 2031", F(SANSB, 15.5), INK)
    y = field(d, 545, y, "Autoridad · Authority", "OFICINA DE PASAPORTES — PORTO CALDERA", vsize=14)
    y = field(d, 545, y, "Nº de pasaporte · Passport No.", "C4819207")
    text(d, (736, y - 36), "Nº personal · Personal No.", F(SANS, 8.2), GREY, spacing=0.5)
    text(d, (736, y - 25), "900214-4417", F(SANSB, 15.5), INK)
    text(d, (545, y + 2), "Observaciones · Observations", F(SANS, 8.2), GREY, spacing=0.5)
    text(d, (545, y + 13), "VÁLIDO PARA TODOS LOS PAÍSES · VALID FOR ALL COUNTRIES",
         F(SANSB, 10), BURG, spacing=0.2)

    # ghost image (secondary portrait, as on polycarbonate pages)
    ghost = port.resize((u(64), u(82)))
    ghost.putalpha(ghost.getchannel("A").point(lambda a: int(a * 0.30)))
    img.paste(ghost, (u(918), u(452)), ghost)
    d = ImageDraw.Draw(img)
    text(d, (950, 538), "CLD", F(SANSB, 9), GREY, anchor="ma", spacing=2)

    # microprint line
    micro = "REPÚBLICA DE CALDERIA · DOCUMENTO DE VIAJE · TRAVEL DOCUMENT · "
    text(d, (545, 592), micro * 2, F(SANS, 6.5), (150, 148, 140))
    rule(d, 538, 988, 606, (190, 186, 172), 0.8)

    # machine-readable zone
    l1, l2 = build_mrz()
    text(d, (542, 632), l1, F(MONOB, 17), (24, 24, 24), spacing=0.15)
    text(d, (542, 668), l2, F(MONOB, 17), (24, 24, 24), spacing=0.15)

    # paper grain
    rng = random.Random(7)
    noise = Image.new("RGBA", img.size, (0, 0, 0, 0))
    nd = ImageDraw.Draw(noise)
    for _ in range(2600):
        x = rng.randrange(CW)
        y = rng.randrange(CH)
        nd.point((x, y), fill=(90, 80, 60, rng.randrange(8, 22)))
    img = Image.alpha_composite(img.convert("RGBA"), noise).convert("RGB")

    return img.resize((W, H), Image.LANCZOS)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    img = render()
    path = os.path.join(out_dir, "entry.png")
    img.save(path, optimize=True)
    print(f"wrote {path}: {img.size[0]}x{img.size[1]}, {os.path.getsize(path)} bytes")


if __name__ == "__main__":
    main()
