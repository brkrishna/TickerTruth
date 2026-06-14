"""Generate tickertruth_og.png (1200×630) from the hero SVG using Playwright."""

from pathlib import Path

ROOT = Path(__file__).parent.parent
SVG_PATH = ROOT / "website/landing-page/assets/images/tickertruth_hero_image.svg"
OUT_PATH = ROOT / "website/landing-page/assets/images/tickertruth_og.png"

OG_W, OG_H = 1200, 630

svg_content = SVG_PATH.read_text()

# Wrap the hero SVG in a 1200×630 HTML canvas with matching dark background.
# The hero viewBox is 690×410; scale it to fill ~92% width with vertical centering.
html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{
    width: {OG_W}px;
    height: {OG_H}px;
    background: #06091a;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }}
  .hero {{
    width: {int(OG_W * 0.92)}px;
    height: auto;
  }}
</style>
</head>
<body>
  <div class="hero">{svg_content}</div>
</body>
</html>"""

from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": OG_W, "height": OG_H})
    page.set_content(html, wait_until="domcontentloaded")
    page.screenshot(
        path=str(OUT_PATH), clip={"x": 0, "y": 0, "width": OG_W, "height": OG_H}
    )
    browser.close()

print(f"Saved: {OUT_PATH}")
print(f"Size:  {OUT_PATH.stat().st_size // 1024} KB")
