"""Run this once to create a placeholder Lawmens logo."""
try:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGBA', (400, 120), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Dark teal rectangle background
    draw.rounded_rectangle([0, 0, 399, 119], radius=8, fill=(13, 79, 108, 255))
    # Text
    try:
        font = ImageFont.truetype("arial.ttf", 52)
    except Exception:
        font = ImageFont.load_default()
    draw.text((20, 20), "LAWMENS", fill=(255, 255, 255, 255), font=font)
    img.save("lawmens_logo.png")
    print("Logo created: lawmens_logo.png")
except ImportError:
    print("Pillow not available — using SVG fallback")
