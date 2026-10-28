"""One-off icon asset correction for the selected 2.0 exit-door concept.

Keeps the original artwork while eliminating the opaque dark outer square.
This script is idempotent: assets with transparent corners are left unchanged.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ICO = ROOT / "assets" / "icon_v2.ico"
PNG = ROOT / "assets" / "icon_v2.png"

img = Image.open(ICO).convert("RGBA")
if img.getpixel((0, 0))[3] == 0:
    raise SystemExit("Icon already has a transparent outer margin; leaving assets unchanged.")

# Source is a 256x256 crop of the approved exit-door illustration.
# The visible rounded tile is around x=30..241, y=19..229.
mask = Image.new("L", (256, 256), 0)
ImageDraw.Draw(mask).rounded_rectangle((30, 19, 241, 229), radius=47, fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(0.65))
img.putalpha(mask)
img = img.crop((7, 1, 251, 245)).resize((256, 256), Image.Resampling.LANCZOS)

# Export README art with transparency (no surrounding opaque square).
img.resize((128, 128), Image.Resampling.LANCZOS).save(PNG, optimize=True)

# Export a true multi-size Windows icon using the same alpha-masked artwork.
img.save(ICO, format="ICO", sizes=[
    (16, 16), (24, 24), (32, 32), (48, 48),
    (64, 64), (128, 128), (256, 256),
])
print("Updated icon_v2.png and icon_v2.ico")
