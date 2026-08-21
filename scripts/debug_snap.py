from playwright.sync_api import sync_playwright
from pathlib import Path

with sync_playwright() as pw:
    br = pw.chromium.launch(headless=True)
    ctx = br.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()

    # Capture console errors
    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}") if m.type in ("error","warning") else None)

    page.goto("http://localhost:3001", wait_until="networkidle", timeout=20000)
    page.screenshot(path="assets/debug-landing.png")
    print("Page title:", page.title())
    print("Page URL:", page.url)
    print("Body text snippet:", page.inner_text("body")[:500])
    if errors:
        print("Console errors:")
        for e in errors[:10]:
            print(" ", e)
    br.close()
