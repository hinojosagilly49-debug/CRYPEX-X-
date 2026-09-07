#!/usr/bin/env python3
"""Regenerate public/og.jpg — Meridian 1200×630 share card (industrial palette)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "og.jpg"

W, H = 1200, 630
INK = (12, 14, 18)
SLATE = (70, 78, 90)
STEEL = (168, 176, 186)
ALUM = (198, 204, 212)
COPPER = (176, 104, 62)
COPPER_LT = (210, 140, 88)
PAPER = (232, 228, 220)
LEDGER = (48, 54, 62)
ACCENT = (140, 150, 162)


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
        (
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        ),
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main() -> None:
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)

    for x in range(80, W - 80, 40):
        d.line([(x, 40), (x, H - 40)], fill=LEDGER, width=1)
    for y in range(60, H - 60, 36):
        d.line([(60, y), (W - 60, y)], fill=(28, 32, 40), width=1)

    m = 28
    d.rectangle([m, m, W - m - 1, H - m - 1], outline=SLATE, width=2)
    d.rectangle(
        [m + 8, m + 8, W - m - 9, H - m - 9], outline=(40, 46, 56), width=1
    )

    ex0, ey0, ew, eh = 90, 200, 210, 140
    d.rounded_rectangle(
        [ex0, ey0, ex0 + ew, ey0 + eh],
        radius=8,
        fill=(24, 28, 34),
        outline=STEEL,
        width=2,
    )
    d.polygon(
        [(ex0, ey0 + 10), (ex0 + ew // 2, ey0 + 55), (ex0 + ew, ey0 + 10)],
        outline=COPPER,
        fill=(30, 28, 26),
    )
    d.line(
        [(ex0 + 16, ey0 + eh - 36), (ex0 + ew - 16, ey0 + eh - 36)],
        fill=COPPER,
        width=2,
    )
    d.ellipse(
        [ex0 + ew // 2 - 18, ey0 + 70, ex0 + ew // 2 + 18, ey0 + 106],
        fill=COPPER,
        outline=COPPER_LT,
    )
    d.ellipse(
        [ex0 + ew // 2 - 8, ey0 + 80, ex0 + ew // 2 + 8, ey0 + 96], fill=INK
    )

    cx0, cy0 = 340, 380
    d.rounded_rectangle(
        [cx0, cy0, cx0 + 180, cy0 + 90],
        radius=4,
        fill=COPPER,
        outline=COPPER_LT,
        width=2,
    )
    d.line([(cx0 + 12, cy0 + 22), (cx0 + 168, cy0 + 22)], fill=COPPER_LT, width=1)
    d.line([(cx0 + 12, cy0 + 45), (cx0 + 140, cy0 + 45)], fill=(120, 70, 40), width=1)
    d.line([(cx0 + 12, cy0 + 68), (cx0 + 155, cy0 + 68)], fill=(120, 70, 40), width=1)

    ax, ay, ar = 980, 320, 95
    for i, col in enumerate(
        [(90, 96, 104), (140, 148, 156), (188, 194, 202), (210, 214, 220)]
    ):
        r = ar - i * 14
        d.ellipse([ax - r, ay - r, ax + r, ay + r], outline=col, width=3)
    d.ellipse(
        [ax - 22, ay - 22, ax + 22, ay + 22], fill=INK, outline=STEEL, width=2
    )
    d.arc(
        [ax - ar + 6, ay - ar + 6, ax + ar - 6, ay + ar - 6],
        start=200,
        end=320,
        fill=ALUM,
        width=4,
    )

    title_f = font(96, bold=True)
    sub_f = font(36, bold=True)
    meta_f = font(18, bold=False)
    title, sub = "MERIDIAN", "METALS & FREIGHT"

    tb = d.textbbox((0, 0), title, font=title_f)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    tx, ty = (W - tw) // 2, 150
    pad_x, pad_y = 48, 28
    d.rounded_rectangle(
        [tx - pad_x, ty - pad_y, tx + tw + pad_x, ty + th + 70 + pad_y],
        radius=6,
        fill=(18, 20, 26),
        outline=SLATE,
        width=1,
    )
    d.text((tx, ty), title, font=title_f, fill=PAPER)
    sb = d.textbbox((0, 0), sub, font=sub_f)
    sw = sb[2] - sb[0]
    sx, sy = (W - sw) // 2, ty + th + 18
    d.line([(tx, sy - 8), (tx + tw, sy - 8)], fill=COPPER, width=2)
    d.text((sx, sy), sub, font=sub_f, fill=STEEL)
    d.text(
        (90, H - 70),
        "CRYPEX ENVELOPE  ·  SARC-DQ  ·  Preflect HOLD",
        font=meta_f,
        fill=ACCENT,
    )
    d.text((W - 280, H - 70), "DESK WINDOW 30m", font=meta_f, fill=ACCENT)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "JPEG", quality=85, optimize=True)
    print(f"wrote {OUT} {OUT.stat().st_size} bytes {img.size}")


if __name__ == "__main__":
    main()
