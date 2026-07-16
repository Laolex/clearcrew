#!/usr/bin/env python3
"""Render docs/diagrams/*.html to PNG at 2x.

    python3 docs/diagrams/render.py [name ...]      # default: architecture

The diagrams used to be exported by hand with no source in the repo, so the PNG kept
its claims long after the code changed them. Anything rendered here has its source
committed next to it — edit the .html, re-run this, commit both.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SIZE = {"architecture": (1600, 1360)}
DEFAULT = ["architecture"]


def render(name: str) -> None:
    src = HERE / f"{name}.html"
    if not src.exists():
        sys.exit(f"no source: {src}")
    w, h = SIZE.get(name, (1600, 1360))
    out = HERE / f"{name}.png"
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
        pg.goto(src.as_uri())
        pg.wait_for_timeout(250)  # let webless fonts settle before the shot
        pg.screenshot(path=str(out))
        b.close()
    print(f"{out.relative_to(HERE.parent.parent)}  {w*2}x{h*2}")


if __name__ == "__main__":
    for n in sys.argv[1:] or DEFAULT:
        render(n)
