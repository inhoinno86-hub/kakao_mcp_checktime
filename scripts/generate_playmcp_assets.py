from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets" / "playmcp"
SVG_PATH = ASSET_DIR / "checktime-representative.svg"
PNG_PATH = ASSET_DIR / "checktime-representative.png"
SIZE = 1024


SVG_CONTENT = """<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#eef6ff"/>
      <stop offset="100%" stop-color="#d7f0e8"/>
    </linearGradient>
  </defs>
  <rect width="1024" height="1024" rx="220" fill="url(#bg)"/>
  <rect x="160" y="180" width="704" height="664" rx="96" fill="#ffffff"/>
  <path d="M292 408L512 248L732 408V456H676V760H348V456H292Z" fill="#2f6fed"/>
  <rect x="420" y="520" width="184" height="240" rx="28" fill="#ffffff"/>
  <rect x="556" y="332" width="150" height="260" rx="40" fill="#0f9d78"/>
  <rect x="588" y="392" width="72" height="18" rx="9" fill="#ffffff" opacity="0.95"/>
  <rect x="588" y="446" width="72" height="18" rx="9" fill="#ffffff" opacity="0.95"/>
  <rect x="588" y="500" width="72" height="18" rx="9" fill="#ffffff" opacity="0.95"/>
  <path d="M590 610L620 640L676 576" fill="none" stroke="#ffffff" stroke-width="26" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="398" cy="610" r="26" fill="#0f9d78"/>
  <path d="M386 610L396 620L412 600" fill="none" stroke="#ffffff" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="438" y="596" width="100" height="18" rx="9" fill="#bfd3f8"/>
  <circle cx="398" cy="678" r="26" fill="#0f9d78"/>
  <path d="M386 678L396 688L412 668" fill="none" stroke="#ffffff" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="438" y="664" width="100" height="18" rx="9" fill="#bfd3f8"/>
  <circle cx="398" cy="746" r="26" fill="#0f9d78"/>
  <path d="M386 746L396 756L412 736" fill="none" stroke="#ffffff" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="438" y="732" width="100" height="18" rx="9" fill="#bfd3f8"/>
  <text x="512" y="892" text-anchor="middle" font-family="sans-serif" font-size="72" font-weight="700" fill="#16324f">Checktime MCP</text>
</svg>
"""


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def draw_round_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill: str) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def build_png() -> None:
    image = Image.new("RGBA", (SIZE, SIZE), "#eef6ff")
    draw = ImageDraw.Draw(image)

    for y in range(SIZE):
        blend = y / (SIZE - 1)
        r = int(238 + (215 - 238) * blend)
        g = int(246 + (240 - 246) * blend)
        b = int(255 + (232 - 255) * blend)
        draw.line((0, y, SIZE, y), fill=(r, g, b, 255))

    draw_round_rect(draw, (160, 180, 864, 844), 96, "#ffffff")
    draw.polygon([(292, 408), (512, 248), (732, 408), (732, 456), (676, 456), (676, 760), (348, 760), (348, 456), (292, 456)], fill="#2f6fed")
    draw_round_rect(draw, (420, 520, 604, 760), 28, "#ffffff")
    draw_round_rect(draw, (556, 332, 706, 592), 40, "#0f9d78")

    for y in (392, 446, 500):
        draw_round_rect(draw, (588, y, 660, y + 18), 9, "#ffffff")

    draw.line((590, 610, 620, 640), fill="#ffffff", width=26)
    draw.line((620, 640, 676, 576), fill="#ffffff", width=26)

    for y in (610, 678, 746):
        draw.ellipse((372, y - 26, 424, y + 26), fill="#0f9d78")
        draw.line((386, y, 396, y + 10), fill="#ffffff", width=10)
        draw.line((396, y + 10, 412, y - 10), fill="#ffffff", width=10)
        draw_round_rect(draw, (438, y - 14, 538, y + 4), 9, "#bfd3f8")

    font = load_font(72)
    text = "Checktime MCP"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_x = (SIZE - (bbox[2] - bbox[0])) / 2
    draw.text((text_x, 844), text, font=font, fill="#16324f")

    image.save(PNG_PATH)


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    SVG_PATH.write_text(SVG_CONTENT, encoding="utf-8")
    build_png()
    print(f"wrote {SVG_PATH}")
    print(f"wrote {PNG_PATH}")


if __name__ == "__main__":
    main()
