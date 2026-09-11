#!/usr/bin/env python3
"""Put the built newsletter into Gmail as a draft (or send it), with inline images.

Why SMTP/IMAP rather than the Gmail MCP connector: the connector runs an HTML
sanitiser that strips every <img> tag and background colour. Verified 2026-09-10 by
creating drafts through it and decoding the stored MIME — a designed newsletter does
not survive. Going direct gives us the whole envelope.

Why an app password rather than OAuth: two minutes of setup instead of a Google Cloud
project, and it grants exactly SMTP/IMAP and nothing else.

Message structure, which is what makes images appear without a "show images" prompt:

    multipart/related
    |-- multipart/alternative
    |   |-- text/plain      (the alternative; must stand alone)
    |   \\-- text/html       (references cid:<name>)
    \\-- image/png ...       (one part per image, Content-ID: <name>)

Default is a DRAFT. Sending needs --send, because a newsletter should get a human
look in a real client before it goes anywhere.
"""
from __future__ import annotations

import argparse
import imaplib
import re
import smtplib
import time
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path

from common import ToolError, emit, get_env, log, require_env, run

CID_RE = re.compile(r'src="cid:([^"]+)"')
IMAP_HOST = "imap.gmail.com"
SMTP_HOST = "smtp.gmail.com"


def build_message(
    *,
    html: str,
    text: str,
    subject: str,
    sender: str,
    from_name: str,
    to: list[str],
    images: dict[str, Path],
    unsubscribe: str | None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((from_name, sender))
    msg["To"] = ", ".join(to)
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=sender.split("@")[-1])
    if unsubscribe:
        # Not required below Gmail's 5k/day bulk threshold, but it costs nothing
        # and is what keeps a growing list out of the spam folder later.
        msg["List-Unsubscribe"] = f"<mailto:{unsubscribe}?subject=unsubscribe>"

    # text/plain first — order in multipart/alternative is least- to most-preferred.
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    # add_alternative wrapped things in multipart/alternative; attaching the images
    # to that payload promotes the whole message to multipart/related.
    html_part = msg.get_payload()[-1]
    for cid, path in images.items():
        html_part.add_related(
            path.read_bytes(),
            maintype="image",
            subtype="png",
            cid=f"<{cid}>",
            filename=path.name,
            disposition="inline",
        )
    return msg


def drafts_folder(imap: imaplib.IMAP4_SSL) -> str:
    """Find the Drafts mailbox by its special-use flag — the name is localised."""
    typ, boxes = imap.list()
    if typ == "OK":
        for raw in boxes:
            line = raw.decode(errors="replace")
            if "\\Drafts" in line:
                # trailing quoted name, e.g. ... "/" "[Gmail]/Drafts"
                match = re.search(r'"([^"]+)"\s*$', line)
                if match:
                    return match.group(1)
    return "[Gmail]/Drafts"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", required=True, help="Built email HTML")
    parser.add_argument("--text", required=True, help="Plain-text alternative")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--images", required=True, help="Directory of <cid>.png")
    parser.add_argument("--to", action="append", help="Recipient (repeatable)")
    parser.add_argument("--unsubscribe", help="mailto address for List-Unsubscribe")
    parser.add_argument(
        "--send",
        action="store_true",
        help="Actually send. Without this a draft is created for review.",
    )
    args = parser.parse_args()

    sender = require_env("GMAIL_ADDRESS")
    password = require_env("GMAIL_APP_PASSWORD").replace(" ", "")
    from_name = get_env("NEWSLETTER_FROM_NAME") or "KittyNews"

    recipients = args.to or []
    if not recipients:
        default_to = get_env("NEWSLETTER_DEFAULT_TO")
        if default_to:
            recipients = [r.strip() for r in default_to.split(",") if r.strip()]
        else:
            # Addressing it to yourself is the right default for a review draft.
            recipients = [sender]
            log("No --to and no NEWSLETTER_DEFAULT_TO; addressing the draft to you.")

    html = Path(args.html).read_text(encoding="utf-8")
    text = Path(args.text).read_text(encoding="utf-8")

    img_dir = Path(args.images).resolve()
    cids = sorted(set(CID_RE.findall(html)))
    images: dict[str, Path] = {}
    for cid in cids:
        path = img_dir / f"{cid}.png"
        if not path.exists():
            raise ToolError(
                f"HTML references cid:{cid} but {path} does not exist. "
                f"Render every infographic before building the draft."
            )
        images[cid] = path

    msg = build_message(
        html=html,
        text=text,
        subject=args.subject,
        sender=sender,
        from_name=from_name,
        to=recipients,
        images=images,
        unsubscribe=args.unsubscribe,
    )
    payload = msg.as_bytes()
    size_mb = len(payload) / 1_048_576
    if size_mb > 25:
        raise ToolError(
            f"Message is {size_mb:.1f}MB, over Gmail's 25MB limit. "
            f"Reduce --colors when rendering infographics."
        )
    log(f"Built message: {len(payload):,} bytes, {len(images)} inline image(s)")

    if args.send:
        log(f"Sending to {len(recipients)} recipient(s)")
        try:
            with smtplib.SMTP_SSL(SMTP_HOST, 465, timeout=60) as smtp:
                smtp.login(sender, password)
                smtp.send_message(msg)
        except smtplib.SMTPAuthenticationError as exc:
            raise ToolError(
                "Gmail rejected the login. GMAIL_APP_PASSWORD must be a 16-character "
                "app password (https://myaccount.google.com/apppasswords), not your "
                f"account password. Server said: {exc.smtp_error!r}"
            ) from exc
        return emit(
            {
                "action": "sent",
                "to": recipients,
                "subject": args.subject,
                "images": len(images),
                "bytes": len(payload),
            }
        )

    log("Creating draft via IMAP")
    try:
        with imaplib.IMAP4_SSL(IMAP_HOST) as imap:
            imap.login(sender, password)
            folder = drafts_folder(imap)
            typ, resp = imap.append(
                f'"{folder}"',
                r"\Draft",
                imaplib.Time2Internaldate(time.time()),
                payload,
            )
            if typ != "OK":
                raise ToolError(f"IMAP APPEND failed: {typ} {resp!r}")
    except imaplib.IMAP4.error as exc:
        raise ToolError(
            "Gmail rejected the IMAP login or append. Check that GMAIL_APP_PASSWORD "
            "is a 16-character app password and that IMAP is enabled in Gmail "
            f"settings (See all settings > Forwarding and POP/IMAP). Server said: {exc}"
        ) from exc

    log(f"Draft created in {folder} — review it in Gmail, then send from there.")
    return emit(
        {
            "action": "draft",
            "folder": folder,
            "to": recipients,
            "subject": args.subject,
            "images": len(images),
            "bytes": len(payload),
            "open": "https://mail.google.com/mail/u/0/#drafts",
        }
    )


if __name__ == "__main__":
    run(main)
