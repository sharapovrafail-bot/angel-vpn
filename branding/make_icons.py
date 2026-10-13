#!/usr/bin/env python3
"""Angel VPN: regenerate every app icon / logo from one source image.

Usage (from the repository root):
    python3 branding/make_icons.py                 # uses branding/logo.png
    python3 branding/make_icons.py path/to/logo.png

Optional branding/logo_square.png (logo on its own background) is used for\nAndroid legacy launcher icons.\n\nThe source should be a square PNG, ideally 1024x1024 with a transparent
background. If no logo is found, a simple placeholder logo (halo + "A")
is drawn and saved as branding/logo.png.

Requires Pillow:  pip install pillow
"""
import base64
import io
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CLIENT = ROOT / "client"
IMAGES = CLIENT / "images"
RES = CLIENT / "android" / "res"
FONT = CLIENT / "fonts" / "pt-root-ui_vf.ttf"

APP_NAME = "Angel VPN"
ACCENT_TOP = (124, 92, 255)     # violet
ACCENT_BOTTOM = (40, 120, 255)  # blue


# ---------------------------------------------------------------- placeholder
def draw_placeholder(size: int = 1024) -> Image.Image:
    s = size
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    # gradient circle
    grad = Image.new("RGBA", (s, s))
    gd = ImageDraw.Draw(grad)
    for y in range(s):
        t = y / (s - 1)
        c = tuple(int(ACCENT_TOP[i] * (1 - t) + ACCENT_BOTTOM[i] * t) for i in range(3)) + (255,)
        gd.line([(0, y), (s, y)], fill=c)
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, s - 1, s - 1], fill=255)
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img)
    white = (255, 255, 255, 255)
    u = s / 24.0  # same geometry as the 24x24 notification vector

    # halo ring
    d.ellipse([6 * u, 3.0 * u, 18 * u, 6.0 * u], outline=white, width=max(2, int(0.9 * u)))

    # letter A (outer triangle minus counter)
    outer = [(12 * u, 7.6 * u), (18.2 * u, 20.6 * u), (15.6 * u, 20.6 * u),
             (14.5 * u, 18.1 * u), (9.5 * u, 18.1 * u), (8.4 * u, 20.6 * u), (5.8 * u, 20.6 * u)]
    d.polygon(outer, fill=white)
    inner = [(10.5 * u, 15.9 * u), (13.5 * u, 15.9 * u), (12 * u, 12.3 * u)]
    hole = Image.new("L", (s, s), 0)
    ImageDraw.Draw(hole).polygon(inner, fill=255)
    img.paste(grad, (0, 0), hole)
    return img


# -------------------------------------------------------------------- helpers
def fit(img: Image.Image, size: int, scale: float = 1.0) -> Image.Image:
    """Logo centred on a transparent square canvas; `scale` = share of the canvas."""
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inner = max(1, int(round(size * scale)))
    logo = img.copy()
    logo.thumbnail((inner, inner), Image.LANCZOS)
    canvas.alpha_composite(logo, ((size - logo.width) // 2, (size - logo.height) // 2))
    return canvas


def round_mask(img: Image.Image) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, img.width - 1, img.height - 1], fill=255)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), Image.composite(img.getchannel("A"), Image.new("L", img.size, 0), mask))
    return out


def font(px: int) -> ImageFont.ImageFont:
    try:
        f = ImageFont.truetype(str(FONT), px)
        try:
            f.set_variation_by_name("Bold")
        except Exception:
            pass
        return f
    except Exception:
        return ImageFont.load_default()


def wordmark(width: int, height: int, logo: Image.Image, logo_share: float, text_px: int) -> Image.Image:
    """Logo on top, app name below, centred on transparent canvas."""
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    f = font(text_px)
    tb = d.textbbox((0, 0), APP_NAME, font=f)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    lsize = int(height * logo_share)
    l = fit(logo, lsize)
    gap = int(height * 0.05)
    total = lsize + gap + th
    top = (height - total) // 2
    canvas.alpha_composite(l, ((width - lsize) // 2, top))
    d.text(((width - tw) // 2 - tb[0], top + lsize + gap - tb[1]), APP_NAME, font=f, fill=(255, 255, 255, 255))
    return canvas


def save(img: Image.Image, path: Path, **kw):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, **kw)
    print("  wrote", path.relative_to(ROOT))


# ----------------------------------------------------------------------- main
def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "branding" / "logo.png"
    if src.exists():
        logo = Image.open(src).convert("RGBA")
        print("source:", src)
    else:
        logo = draw_placeholder()
        save(logo, ROOT / "branding" / "logo.png")
        print("source: placeholder")

    # trim transparent borders so every target is filled consistently
    bbox = logo.getchannel("A").getbbox()
    if bbox:
        logo = logo.crop(bbox)
    side = max(logo.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.alpha_composite(logo, ((side - logo.width) // 2, (side - logo.height) // 2))
    logo = sq

    # desktop / shared
    save(fit(logo, 256), IMAGES / "icon.png")
    fit(logo, 256).save(IMAGES / "app.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("  wrote", (IMAGES / "app.ico").relative_to(ROOT))
    save(wordmark(1440, 1200, logo, 0.55, 150), IMAGES / "amneziaBigLogo.png")

    small = Image.new("RGBA", (150, 22), (0, 0, 0, 0))
    sd = ImageDraw.Draw(small)
    small.alpha_composite(fit(logo, 22), (0, 0))
    sd.text((28, 1), APP_NAME, font=font(17), fill=(255, 255, 255, 255))
    save(small, IMAGES / "AmneziaVPN.png")

    buf = io.BytesIO()
    fit(logo, 88).save(buf, format="PNG")
    svg = ('<svg width="23" height="22" viewBox="0 0 23 22" xmlns="http://www.w3.org/2000/svg" '
           'xmlns:xlink="http://www.w3.org/1999/xlink">'
           '<image x="0.5" y="0" width="22" height="22" xlink:href="data:image/png;base64,%s"/></svg>\n'
           % base64.b64encode(buf.getvalue()).decode())
    (IMAGES / "controls" / "amnezia.svg").write_text(svg)
    print("  wrote", (IMAGES / "controls" / "amnezia.svg").relative_to(ROOT))

    # tray icons
    tray = fit(logo, 200, 0.92)
    grey = tray.convert("LA").convert("RGBA")
    grey.putalpha(tray.getchannel("A"))
    save(tray, IMAGES / "tray" / "active.png")
    save(grey, IMAGES / "tray" / "default.png")
    err = grey.copy()
    ImageDraw.Draw(err).ellipse([128, 128, 196, 196], fill=(235, 64, 52, 255), outline=(255, 255, 255, 255), width=6)
    save(err, IMAGES / "tray" / "error.png")

    # optional full-bleed square artwork (logo on its own background) for Android legacy icons
    square_path = ROOT / "branding" / "logo_square.png"
    square = Image.open(square_path).convert("RGBA") if square_path.exists() else None

    # android launcher icons (only overwrite files that already exist)
    for d in sorted(RES.glob("mipmap-*")):
        for name in ("icon.png", "icon_round.png", "ic_launcher_foreground.png", "ic_banner.png"):
            p = d / name
            if not p.exists():
                continue
            w, h = Image.open(p).size
            if name == "ic_launcher_foreground.png":
                img = fit(logo, w, 0.62)          # adaptive icon safe zone
            elif name == "icon_round.png":
                img = round_mask(square.resize((w, w), Image.LANCZOS) if square else fit(logo, w))
            elif name == "ic_banner.png":
                img = Image.new("RGBA", (w, h), (14, 14, 17, 255))
                img.alpha_composite(wordmark(w, h, logo, 0.55, max(10, h // 6)))
            else:
                img = square.resize((w, w), Image.LANCZOS) if square else fit(logo, w)
            save(img, p)


if __name__ == "__main__":
    main()
