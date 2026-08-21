"""
Capture screenshots and GIF of the Unsaid app for the README.
Usage: python scripts/capture.py
"""
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

ASSETS = Path(__file__).parent.parent / "assets"
ASSETS.mkdir(exist_ok=True)

LANDING_URL   = "http://localhost:3001"
RESULTS_URL   = "http://localhost:3001/diff/SIVB"


def capture(pw):
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()

    frames: list[Image.Image] = []

    def snap(path: str, full_page=False) -> Image.Image:
        page.screenshot(path=str(ASSETS / path), full_page=full_page)
        img = Image.open(ASSETS / path)
        print(f"  saved {path}  ({img.size[0]}×{img.size[1]})")
        return img

    def viewport_snap() -> Image.Image:
        data = page.screenshot()
        from io import BytesIO
        return Image.open(BytesIO(data))

    # ── Landing page ────────────────────────────────────────────────────────
    print("Landing page…")
    page.goto(LANDING_URL, wait_until="networkidle")
    page.wait_for_selector("text=SIVB", timeout=15000)
    landing = snap("screenshot-landing.png")
    frames.append(landing.copy())
    time.sleep(0.5)

    # ── Hover on SVB card (adds visual feedback) ─────────────────────────
    page.hover("text=SVB Financial Group")
    time.sleep(0.3)
    frames.append(viewport_snap())

    # ── Navigate to SVB results ──────────────────────────────────────────
    print("SVB results page…")
    page.goto(RESULTS_URL, wait_until="networkidle")
    page.wait_for_selector("text=REMOVED", timeout=15000)
    time.sleep(0.8)

    # Full results page screenshot
    snap("screenshot-results.png", full_page=True)

    # Viewport-only (for GIF frames — consistent size)
    frames.append(viewport_snap())

    # ── Expand the first REMOVED card ───────────────────────────────────
    print("Expanding REMOVED card…")
    removed = page.locator("button", has_text="REMOVED").first
    removed.click()
    page.wait_for_selector("text=Year-1 Disclosure", timeout=5000)
    time.sleep(0.5)

    expanded = snap("screenshot-removed-expanded.png")
    frames.append(viewport_snap())
    # Hold on the expanded card longer in the GIF
    for _ in range(6):
        frames.append(viewport_snap())

    # ── Scroll down to show Item 7A tag ─────────────────────────────────
    page.evaluate("window.scrollBy(0, 300)")
    time.sleep(0.4)
    snap("screenshot-item7a.png")
    frames.append(viewport_snap())
    for _ in range(4):
        frames.append(viewport_snap())

    browser.close()

    # ── Build GIF ────────────────────────────────────────────────────────
    print("Building GIF…")
    # Resize all frames to consistent size
    w, h = 1280, 800
    resized = [f.resize((w, h), Image.LANCZOS).convert("RGBA").convert("P", palette=Image.ADAPTIVE, colors=256)
               for f in frames]

    gif_path = ASSETS / "demo.gif"
    resized[0].save(
        gif_path,
        save_all=True,
        append_images=resized[1:],
        loop=0,
        duration=350,   # ms per frame
        optimize=False,
    )
    print(f"  saved demo.gif  ({len(frames)} frames)")

    print(f"\nAll assets saved to {ASSETS}/")


if __name__ == "__main__":
    with sync_playwright() as pw:
        capture(pw)