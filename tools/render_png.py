#!/usr/bin/env python3
"""Render a Jinja2 HTML template to PNG via headless Chromium.

Serves every raster asset in the project: the logo variants, the brand guidelines
sheet, and all four infographic types. Email clients can't render SVG (Outlook for
Windows has zero support), so everything ships as PNG at 2x for retina.

The brand tokens from brand/brand.json are injected into every template as `brand`,
so a template never hardcodes a colour.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, ToolError, emit, log, read_json, run, tmp_path

BRAND_FILE = ROOT / "brand" / "brand.json"


def load_brand() -> dict:
    if not BRAND_FILE.exists():
        raise ToolError(
            f"{BRAND_FILE} is missing. It's the single source of truth for colours "
            f"and type — every template reads it. Create it before rendering."
        )
    return read_json(BRAND_FILE)


def render_html(template: Path, context: dict) -> str:
    try:
        from jinja2 import Environment, FileSystemLoader, StrictUndefined
    except ImportError as exc:  # pragma: no cover
        raise ToolError("jinja2 is not installed. Run: pip install jinja2") from exc

    if not template.exists():
        raise ToolError(f"Template not found: {template}")

    env = Environment(
        loader=FileSystemLoader([str(ROOT), str(template.parent)]),
        undefined=StrictUndefined,  # fail loudly on a typo'd token, don't render blank
        autoescape=False,
    )
    tpl = env.get_template(template.relative_to(ROOT).as_posix())
    return tpl.render(**context)


def screenshot(
    html: str,
    out: Path,
    *,
    selector: str,
    scale: int,
    transparent: bool,
    width: int,
) -> tuple[int, int]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ToolError(
            "playwright is not installed. Run: pip install playwright "
            "&& python -m playwright install chromium"
        ) from exc

    # Chromium needs a real file URL (not set_content) for webfonts + relative assets
    # to resolve reliably, so stage the HTML next to the project root.
    staged = tmp_path(f"render-{out.stem}.html")
    staged.write_text(html, encoding="utf-8")

    out.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(
                device_scale_factor=scale, viewport={"width": width, "height": 800}
            )
            page.goto(staged.as_uri(), wait_until="networkidle")
            # Webfonts settle after networkidle; without this the first render can
            # fall back to Times and silently ship wrong-looking assets.
            page.evaluate("() => document.fonts.ready")
            page.wait_for_timeout(250)

            target = page.locator(selector)
            if target.count() == 0:
                raise ToolError(
                    f"Selector {selector!r} matched nothing in {out.name}. "
                    f"Templates must wrap their content in an element matching it."
                )
            target.first.screenshot(path=str(out), omit_background=transparent)
            box = target.first.bounding_box() or {"width": 0, "height": 0}
        finally:
            browser.close()

    return int(box["width"]), int(box["height"])


def optimise(path: Path, colors: int) -> int:
    """Palette-quantise flat-colour graphics. Cuts a typical card ~70%."""
    if colors <= 0:
        return path.stat().st_size
    try:
        from PIL import Image
    except ImportError as exc:
        raise ToolError("pillow is not installed. Run: pip install pillow") from exc

    im = Image.open(path)
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    # RGBA only supports FASTOCTREE or libimagequant — MEDIANCUT raises ValueError.
    im.quantize(colors=colors, method=Image.Quantize.FASTOCTREE).save(
        path, optimize=True
    )
    return path.stat().st_size


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, help="Jinja2 HTML template path")
    parser.add_argument("--out", required=True, help="Destination .png path")
    parser.add_argument("--data", help="Inline JSON context for the template")
    parser.add_argument("--data-file", help="Path to a JSON file with the context")
    parser.add_argument(
        "--selector", default="#card", help="Element to clip to (default: #card)"
    )
    parser.add_argument("--scale", type=int, default=2, help="Retina factor (default 2)")
    parser.add_argument("--width", type=int, default=1400, help="Viewport width")
    parser.add_argument(
        "--colors",
        type=int,
        default=64,
        help="Palette size for quantisation; 0 disables (default 64)",
    )
    parser.add_argument(
        "--opaque",
        action="store_true",
        help="Keep the page background instead of a transparent one",
    )
    args = parser.parse_args()

    context: dict = {}
    if args.data_file:
        context.update(read_json(Path(args.data_file)))
    if args.data:
        try:
            context.update(json.loads(args.data))
        except json.JSONDecodeError as exc:
            raise ToolError(f"--data is not valid JSON: {exc}") from exc

    context["brand"] = load_brand()

    template = Path(args.template).resolve()
    out = Path(args.out).resolve()

    log(f"Rendering {template.name} -> {out.name}")
    html = render_html(template, context)
    w, h = screenshot(
        html,
        out,
        selector=args.selector,
        scale=args.scale,
        transparent=not args.opaque,
        width=args.width,
    )
    size = optimise(out, args.colors)
    log(f"{out.name}: {w}x{h}pt @{args.scale}x, {size:,} bytes")

    return emit(
        {
            "output": str(out),
            "css_width": w,
            "css_height": h,
            "pixel_width": w * args.scale,
            "pixel_height": h * args.scale,
            "bytes": size,
        }
    )


if __name__ == "__main__":
    run(main)
