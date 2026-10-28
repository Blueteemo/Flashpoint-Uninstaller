"""Repack the existing A-style Flashpoint icon with transparent, balanced edges.

Only visual assets are changed. The utility's deletion logic is not modified.
Running this script on an already transparent icon is intentionally a no-op.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ICO = ROOT / "assets" / "icon_v2.ico"
PNG = ROOT / "assets" / "icon_v2.png"
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48),
         (64, 64), (128, 128), (256, 256)]


def build():
    source = Image.open(ICO)
    # The old ICO had an opaque square background. A newer ICO has already
    # been corrected, and must not be cropped a second time.
    if source.mode == "RGBA" and source.getpixel((0, 0))[3] == 0:
        image = Image.open(PNG).convert("RGBA")
        assert image.getpixel((0, 0))[3] == 0
        return

    source = source.convert("RGBA")
    if source.size != (256, 256):
        raise RuntimeError(f"Unexpected source icon resolution: {source.size}")

    alpha = Image.new("L", source.size, 0)
    brush = ImageDraw.Draw(alpha)
    brush.rounded_rectangle((16, 17, 241, 242), radius=40, fill=255)
    alpha = alpha.filter(ImageFilter.GaussianBlur(1.25))
    source.putalpha(alpha)

    # Keep all recognizable artwork inside a square icon, with even padding.
    art = source.crop((13, 14, 245, 246))
    art = art.resize((442, 442), Image.Resampling.LANCZOS)
    master = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    master.alpha_composite(art, (35, 35))

    master.resize((192, 192), Image.Resampling.LANCZOS).save(
        PNG, format="PNG", optimize=True)
    master.save(ICO, format="ICO", sizes=SIZES)

    png = Image.open(PNG).convert("RGBA")
    ico = Image.open(ICO)
    if png.getpixel((0, 0))[3] or ico.convert("RGBA").getpixel((0, 0))[3]:
        raise RuntimeError("Icon corners are not transparent")
    if not set(SIZES).issubset(ico.info.get("sizes", set())):
        raise RuntimeError("Required Windows icon sizes missing")
    print("Transparent icon checked: README PNG + Windows ICO")


if __name__ == "__main__":
    build()
