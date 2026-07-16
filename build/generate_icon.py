from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


root = Path(__file__).resolve().parents[1]
size = 1024
base = Image.new("RGBA", (size, size), (0, 0, 0, 0))

# A pre-rendered crimson halo stays visible in the title bar, taskbar and the
# in-app brand badge without relying on platform-specific effects.
glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
glow_draw = ImageDraw.Draw(glow)
glow_draw.ellipse(
    (112, 112, 912, 912),
    outline=(227, 24, 55, 165),
    width=44,
)
glow = glow.filter(ImageFilter.GaussianBlur(62))
base = Image.alpha_composite(base, glow)

draw = ImageDraw.Draw(base)
draw.ellipse(
    (76, 76, 948, 948),
    fill=(10, 13, 17, 255),
    outline=(227, 24, 55, 255),
    width=34,
)
draw.ellipse((116, 116, 908, 908), outline=(45, 52, 63, 255), width=15)

white = (244, 246, 248, 255)
red = (227, 24, 55, 255)

# An unmistakable plug: rounded body, shoulder and two downward pins.
draw.rounded_rectangle((288, 468, 736, 710), radius=82, outline=white, width=68)
draw.line((368, 696, 368, 838), fill=white, width=68)
draw.line((656, 696, 656, 838), fill=white, width=68)
draw.line((336, 596, 688, 596), fill=white, width=42)

# The crimson upload arrow rises directly out of the plug body.
arrow_width = 78
draw.line((512, 620, 512, 248), fill=red, width=arrow_width)
draw.line((512, 248, 356, 404), fill=red, width=arrow_width)
draw.line((512, 248, 668, 404), fill=red, width=arrow_width)

resources = root / "resources"
resources.mkdir(parents=True, exist_ok=True)
master = base.resize((256, 256), Image.Resampling.LANCZOS)
master.save(resources / "upload_plugg.png")
master.save(
    resources / "upload_plugg.ico",
    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
