from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


root = Path(__file__).resolve().parents[1]
size = 256
base = Image.new("RGBA", (size, size), (7, 8, 10, 255))
glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
draw = ImageDraw.Draw(glow)
draw.rounded_rectangle((29, 29, 227, 227), radius=50, outline=(225, 20, 52, 210), width=16)
glow = glow.filter(ImageFilter.GaussianBlur(18))
base = Image.alpha_composite(base, glow)
draw = ImageDraw.Draw(base)
draw.rounded_rectangle((28, 28, 228, 228), radius=50, fill=(16, 18, 22, 255), outline=(218, 22, 48, 255), width=8)
draw.polygon([(79, 70), (137, 70), (137, 112), (179, 112), (179, 153), (137, 153), (137, 194), (79, 194)], fill=(244, 246, 248, 255))
draw.polygon([(137, 70), (184, 70), (184, 101), (137, 101)], fill=(218, 22, 48, 255))
resources = root / "resources"
resources.mkdir(parents=True, exist_ok=True)
base.save(resources / "upload_plugg.png")
base.save(resources / "upload_plugg.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

