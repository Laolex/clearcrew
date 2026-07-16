#!/usr/bin/env python3
"""Render the diagrams in this directory from their sources.

    python3 docs/diagrams/render.py                 # everything
    python3 docs/diagrams/render.py devto-cover     # one target

Every target is <source> -> docs/diagrams/<name>.png at 2x. Targets with a `sync`
path are also copied there, because a second hand-kept copy is how these drift.

Why this exists: docs/diagrams/architecture.png was hand-exported with no source in
the repo, so it kept asserting a JSONL event store long after the writer became
SQLite, and three superseded copies of it survived elsewhere claiming a trust model
this system had already replaced. A diagram nobody can regenerate is a claim nobody
can update. Edit the source, run this, commit both.

The devto images are hot-linked by the published dev.to article via
clearcrew.verasettle.com/img/*, so their `sync` copy is load-bearing: it is what the
article actually serves. Rendering is not byte-reproducible (text antialiasing varies
by chromium build, ~2% of pixels, visually identical), so expect a diff on every
re-render even with an unchanged source. Fonts resolve to DejaVu/Liberation here; the
devto SVGs ask for IBM Plex Mono and fall back, which is how the committed PNGs were
made too.
"""
import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SERVED = "src/clearcrew/static/img"

# name -> (source, css size; the PNG lands at 2x this, sync destination or None)
TARGETS = {
    "architecture": ("architecture.html", (1600, 1360), None),
    "devto-cover": ("devto-cover.svg", (1000, 420), f"{SERVED}/devto-cover.png"),
    "devto-caught-lie": ("devto-caught-lie.svg", (960, 620), f"{SERVED}/devto-caught-lie.png"),
}


def render(name: str) -> None:
    try:
        source, (w, h), sync = TARGETS[name]
    except KeyError:
        sys.exit(f"unknown target {name!r}; known: {', '.join(TARGETS)}")
    src = HERE / source
    if not src.exists():
        sys.exit(f"no source: {src}")

    out = HERE / f"{name}.png"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
        page.goto(src.as_uri())
        page.wait_for_timeout(250)  # let fallback fonts settle before the shot
        page.screenshot(path=str(out))
        browser.close()
    print(f"  {source} -> {out.relative_to(ROOT)}  ({w * 2}x{h * 2})")

    if sync:
        shutil.copyfile(out, ROOT / sync)
        print(f"  {' ' * len(source)}    synced -> {sync}")


if __name__ == "__main__":
    for target in sys.argv[1:] or TARGETS:
        render(target)
