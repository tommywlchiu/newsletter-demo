#!/usr/bin/env python3
"""Research a topic with the Perplexity Agent API and archive the citation corpus.

Targets POST /v1/agent, NOT the older /chat/completions Sonar endpoint — that one
was retired on 2026-09-27. Most tutorials online still show the dead one.

The corpus written to .tmp/ is the point of this tool as much as the prose is:
tools/check_claims.py reads it back to verify that every figure headed for an
infographic actually appears in a source. Research that isn't archived can't be
checked.

Response shapes are parsed tolerantly and the raw JSON is always kept, so a change
on Perplexity's side degrades to "fewer extracted sources" rather than a crash.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from common import (
    ToolError,
    emit,
    log,
    require_env,
    run,
    slugify,
    tmp_path,
    write_json,
)

ENDPOINT = "https://api.perplexity.ai/v1/agent"
PRESETS = ("fast", "low", "medium", "high", "xhigh", "wide-research")
RECENCY = ("hour", "day", "week", "month", "year")

PROMPT = """You are researching a single issue of a newsletter.

Topic: {topic}

Produce a briefing that a writer can turn into copy:
1. The 3-5 findings that actually matter, most significant first.
2. For each finding, the concrete numbers — with units, dates and who reported them.
3. What changed recently, and what is genuinely new versus merely recirculated.
4. Where credible sources disagree, and on what.
5. Anything widely repeated that appears to be wrong.

Prefer primary sources over coverage of them. Attribute every figure. If a number
is an estimate or a projection, say so explicitly."""


def _walk(node: Any):
    """Yield every dict in an arbitrarily nested JSON structure."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


def extract_sources(payload: dict) -> list[dict]:
    """Pull unique {url,title,snippet,date} out of wherever the response holds them."""
    seen: dict[str, dict] = {}
    for node in _walk(payload):
        url = node.get("url")
        if not isinstance(url, str) or not url.startswith("http"):
            continue
        if url in seen:
            continue
        seen[url] = {
            "url": url,
            "title": node.get("title") or node.get("name") or "",
            "snippet": node.get("snippet") or node.get("text") or "",
            "date": node.get("date") or node.get("last_updated") or None,
        }
    return list(seen.values())


def extract_text(payload: dict) -> str:
    """Collect the assistant's prose from the output items."""
    chunks: list[str] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") not in (None, "message", "output_text", "text"):
            continue
        content = item.get("content")
        if isinstance(content, str):
            chunks.append(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    chunks.append(part["text"])
                elif isinstance(part, str):
                    chunks.append(part)
    if not chunks:  # fall back to any long free text in the payload
        for node in _walk(payload):
            text = node.get("text")
            if isinstance(text, str) and len(text) > 200:
                chunks.append(text)
    return "\n\n".join(dict.fromkeys(chunks)).strip()


def call_api(body: dict, key: str, *, timeout: int) -> dict:
    import requests

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    for attempt in range(1, 4):
        response = requests.post(ENDPOINT, json=body, headers=headers, timeout=timeout)
        if response.status_code == 429:
            wait = min(2**attempt * 5, 60)
            log(f"Rate limited (429). Waiting {wait}s before retry {attempt}/3.")
            time.sleep(wait)
            continue
        if response.status_code == 401:
            raise ToolError(
                "Perplexity rejected the key (401). Check PERPLEXITY_API_KEY in .env."
            )
        if response.status_code >= 400:
            raise ToolError(
                f"Perplexity returned {response.status_code}: {response.text[:400]}"
            )
        return response.json()
    raise ToolError("Rate limited by Perplexity three times running. Try again later.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True)
    parser.add_argument(
        "--preset", default="high", choices=PRESETS, help="Agent effort (default: high)"
    )
    parser.add_argument(
        "--recency", choices=RECENCY, help="Only sources from within this window"
    )
    parser.add_argument("--domains", help="Comma-separated domain allowlist")
    parser.add_argument("--out", help="Corpus JSON path (default: .tmp/research-<slug>.json)")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()

    key = require_env("PERPLEXITY_API_KEY")

    body: dict[str, Any] = {
        "input": PROMPT.format(topic=args.topic),
        "preset": args.preset,
    }
    if args.recency:
        body["search_recency_filter"] = args.recency
    if args.domains:
        body["search_domain_filter"] = [d.strip() for d in args.domains.split(",") if d.strip()]

    log(f"Researching {args.topic!r} (preset={args.preset})")
    started = time.time()
    payload = call_api(body, key, timeout=args.timeout)
    elapsed = time.time() - started

    status = payload.get("status")
    if status and status not in ("completed", "succeeded", None):
        raise ToolError(
            f"Perplexity returned status {status!r} rather than a finished response. "
            f"Raw payload kept for inspection."
        )

    text = extract_text(payload)
    sources = extract_sources(payload)

    slug = slugify(args.topic)
    out = Path(args.out) if args.out else tmp_path(f"research-{slug}.json")
    raw_path = tmp_path(f"research-{slug}.raw.json")
    write_json(raw_path, payload)  # always keep the raw response

    corpus = {
        "topic": args.topic,
        "preset": args.preset,
        "recency": args.recency,
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "elapsed_seconds": round(elapsed, 1),
        "briefing": text,
        "sources": sources,
        "raw": str(raw_path),
    }
    write_json(out, corpus)

    log(f"{len(sources)} source(s), {len(text):,} chars of briefing in {elapsed:.0f}s")
    if len(sources) < 5:
        log(
            "WARNING: fewer than 5 sources. Widen --recency, drop --domains, "
            "or raise --preset before writing from this."
        )

    return emit(
        {
            "corpus": str(out),
            "raw": str(raw_path),
            "sources": len(sources),
            "briefing_chars": len(text),
            "elapsed_seconds": round(elapsed, 1),
        }
    )


if __name__ == "__main__":
    run(main)
