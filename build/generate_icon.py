from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


root = Path(__file__).resolve().parents[1]
size = 1024
base = Image.new("RGBA", (size, size), (0, 0, 0, 0))

# A subtle pre-rendered crimson halo is efficient at runtime and remains outside
# the high-contrast small-size glyph.
glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
glow_draw = ImageDraw.Draw(glow)
glow_draw.rounded_rectangle(
    (102, 102, 922, 922),
    radius=205,
    outline=(227, 24, 55, 165),
    width=34,
)
glow = glow.filter(ImageFilter.GaussianBlur(54))
base = Image.alpha_composite(base, glow)

draw = ImageDraw.Draw(base)
draw.rounded_rectangle(
    (80, 80, 944, 944),
    radius=210,
    fill=(10, 13, 17, 255),
    outline=(38, 45, 55, 255),
    width=24,
)

white = (244, 246, 248, 255)
red = (227, 24, 55, 255)
width = 72

# Plug body and prongs.
draw.line((330, 454, 330, 574), fill=white, width=width)
draw.line((694, 454, 694, 574), fill=white, width=width)
draw.arc((330, 490, 694, 790), start=0, end=180, fill=white, width=width)

# The upload arrow becomes the electrical connection through the plug.
draw.line((512, 704, 512, 244), fill=red, width=width)
draw.line((512, 244, 368, 388), fill=red, width=width)
draw.line((512, 244, 656, 388), fill=red, width=width)
draw.line((512, 774, 512, 864), fill=red, width=width)

resources = root / "resources"
resources.mkdir(parents=True, exist_ok=True)
master = base.resize((256, 256), Image.Resampling.LANCZOS)
master.save(resources / "upload_plugg.png")
master.save(
    resources / "upload_plugg.ico",
    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
