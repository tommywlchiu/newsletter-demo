#!/usr/bin/env python3
"""Build the KittyNews email: Jinja2 -> MJML -> table-based HTML, plus plain text.

MJML does the part that is genuinely hard: emitting nested-table, inline-CSS HTML
that survives Outlook's Word rendering engine. We never hand-write that.

Emits a multipart pair — the HTML body and a plain-text alternative. The text part
is not optional decoration: it improves deliverability and is what some clients
show, so it has to stand on its own with every image absent.
"""
from __future__ import annotations

import argparse
import io
import re
from pathlib import Path

from common import ToolError, emit, log, read_json, render_template, run, write_text

CID_RE = re.compile(r'src="cid:([^"]+)"')


def compile_mjml(source: str) -> str:
    try:
        from mjml import mjml_to_html
    except ImportError as exc:
        raise ToolError("mjml is not installed. Run: pip install mjml") from exc

    result = mjml_to_html(io.StringIO(source))
    errors = list(getattr(result, "errors", None) or [])
    if errors:
        # Surface every problem at once — fixing them one render at a time is slow.
        detail = "; ".join(str(e) for e in errors[:8])
        raise ToolError(f"MJML reported {len(errors)} error(s): {detail}")
    html = result.html
    if not html or len(html) < 200:
        raise ToolError("MJML produced no meaningful HTML — check the template.")
    return html


def to_plaintext(html: str) -> str:
    try:
        import html2text
    except ImportError as exc:
        raise ToolError("html2text is not installed. Run: pip install html2text") from exc

    h = html2text.HTML2Text()
    h.ignore_images = True   # cid: refs are meaningless in a text part
    h.body_width = 0         # let the client wrap; hard wraps look broken on mobile
    h.ignore_emphasis = True
    h.protect_links = True
    text = h.handle(html)
    # MJML's spacer tables leave runs of blank lines behind.
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-file", required=True, help="Issue JSON")
    parser.add_argument(
        "--template",
        default="templates/newsletter.mjml.j2",
        help="MJML Jinja2 template (default: templates/newsletter.mjml.j2)",
    )
    parser.add_argument("--out", required=True, help="Destination .html")
    parser.add_argument("--text-out", help="Destination .txt (plain-text alternative)")
    parser.add_argument(
        "--mjml-out", help="Also write the intermediate .mjml, for debugging"
    )
    parser.add_argument(
        "--preview-out",
        help="Browser-openable copy with cid: refs swapped for local files",
    )
    parser.add_argument(
        "--images",
        help="Directory holding <cid>.png, required by --preview-out",
    )
    args = parser.parse_args()

    data = read_json(Path(args.data_file))
    for required in ("subject", "preheader", "intro", "stories", "sources"):
        if required not in data:
            raise ToolError(
                f"Issue JSON is missing {required!r}. "
                f"Required keys: subject, preheader, intro, stories, sources."
            )

    log(f"Rendering {args.template}")
    mjml_src = render_template(Path(args.template), data)
    if args.mjml_out:
        write_text(Path(args.mjml_out), mjml_src)

    log("Compiling MJML -> HTML")
    html = compile_mjml(mjml_src)
    out = Path(args.out).resolve()
    write_text(out, html)

    text_path = None
    if args.text_out:
        text_path = Path(args.text_out).resolve()
        write_text(text_path, to_plaintext(html))

    cids = sorted(set(CID_RE.findall(html)))
    log(f"{out.name}: {len(html):,} bytes, {len(cids)} inline image(s)")

    preview_path = None
    if args.preview_out:
        if not args.images:
            raise ToolError("--preview-out also needs --images <dir>")
        img_dir = Path(args.images).resolve()
        missing = [c for c in cids if not (img_dir / f"{c}.png").exists()]
        if missing:
            raise ToolError(
                f"No PNG in {img_dir} for cid(s): {', '.join(missing)}. "
                f"Each cid needs a matching <cid>.png before preview or send."
            )
        preview_path = Path(args.preview_out).resolve()
        preview = CID_RE.sub(
            lambda m: f'src="{(img_dir / (m.group(1) + ".png")).as_uri()}"', html
        )
        write_text(preview_path, preview)
        log(f"Preview: {preview_path}")

    return emit(
        {
            "html": str(out),
            "text": str(text_path) if text_path else None,
            "preview": str(preview_path) if preview_path else None,
            "bytes": len(html),
            "cids": cids,
            "subject": data["subject"],
            "preheader": data["preheader"],
        }
    )


if __name__ == "__main__":
    run(main)
