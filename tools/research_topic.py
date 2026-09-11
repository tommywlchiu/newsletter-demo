#!/usr/bin/env python3
"""Research a topic with the Perplexity Agent API and archive the citation corpus.

Uses the official SDK (`pip install perplexityai`) against POST /v1/agent, via
`client.responses.create`. Not the retired Sonar /chat/completions endpoint.

Two outputs, both load-bearing:
  - a readable briefing the writer works from
  - a corpus of sources that tools/check_claims.py reads back to verify every
    figure headed for an infographic. Research that isn't archived can't be checked.

Answers come back as structured JSON (response_format json_schema) rather than
prose, because the downstream steps need figures bound to the URL that supports
them — not a paragraph someone has to re-parse.

The API key is read from PERPLEXITY_API_KEY by the SDK itself. This tool checks
only that it is present and never reads, prints or logs the value.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time
from pathlib import Path
from typing import Any

from common import (
    ToolError,
    emit,
    load_env,
    log,
    run,
    slugify,
    tmp_path,
    write_json,
    write_text,
)

PRESETS = ("fast", "low", "medium", "high", "xhigh", "wide-research")
RECENCY = ("hour", "day", "week", "month", "year")

INSTRUCTIONS = """You are researching one issue of a newsletter.

Prefer primary sources over coverage of them. Attribute every figure to the source
that reported it. Mark projections and estimates as such rather than stating them
as measured fact. If you cannot find support for a number, omit it — do not
approximate or infer one."""

PROMPT = """Topic: {topic}

Produce a briefing a writer can turn into copy. Cover:
1. The findings that actually matter, most significant first.
2. The concrete numbers behind them, with units, dates, and who reported them.
3. What is genuinely new, versus what is merely being recirculated.
4. Where credible sources disagree, and on what.
5. Anything widely repeated that appears to be wrong."""

# Structured output. The downstream pipeline needs figures bound to sources, so
# the schema makes that binding mandatory rather than hoping prose supplies it.
SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "newsletter_research",
        "schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Two or three sentences on what this issue is about.",
                },
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "headline": {"type": "string"},
                            "detail": {"type": "string"},
                            "figures": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "value": {
                                            "type": "string",
                                            "description": "As reported, e.g. '$4.2B', '71%'.",
                                        },
                                        "what": {"type": "string"},
                                        "source_url": {"type": "string"},
                                        "is_estimate": {"type": "boolean"},
                                    },
                                    "required": ["value", "what", "source_url", "is_estimate"],
                                },
                            },
                            "source_urls": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["headline", "detail", "figures", "source_urls"],
                    },
                },
                "disagreements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "about": {"type": "string"},
                            "positions": {"type": "string"},
                        },
                        "required": ["about", "positions"],
                    },
                },
                "corrections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "widely_believed": {"type": "string"},
                            "actually": {"type": "string"},
                        },
                        "required": ["widely_believed", "actually"],
                    },
                },
            },
            "required": ["summary", "findings", "disagreements", "corrections"],
        },
    },
}


def build_tools(recency: str | None, domains: list[str]) -> list[dict] | None:
    """web_search with filters, plus fetch_url so overriding tools doesn't lose it.

    Presets already enable tools; anything passed alongside a preset overrides that
    default. So we only send `tools` when a filter actually needs setting, and we
    re-add fetch_url explicitly to avoid silently narrowing the preset's toolset.
    """
    filters: dict[str, Any] = {}
    if recency:
        filters["search_recency_filter"] = recency
    if domains:
        filters["search_domain_filter"] = domains
    if not filters:
        return None
    return [
        {"type": "web_search", "filters": filters},
        {"type": "fetch_url"},
    ]


def collect_sources(response: Any) -> list[dict]:
    """Pull search_results items out of response.output, de-duplicated by URL."""
    seen: dict[str, dict] = {}
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) != "search_results":
            continue
        for result in getattr(item, "results", None) or []:
            url = getattr(result, "url", None)
            if not url or url in seen:
                continue
            seen[url] = {
                "url": url,
                "title": getattr(result, "title", "") or "",
                "snippet": getattr(result, "snippet", "") or "",
                "date": getattr(result, "date", None),
                "last_updated": getattr(result, "last_updated", None),
            }
    return list(seen.values())


def collect_citations(response: Any) -> list[dict]:
    """url_citation annotations hanging off assistant text content."""
    out: list[dict] = []
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) != "message":
            continue
        for part in getattr(item, "content", None) or []:
            for note in getattr(part, "annotations", None) or []:
                if getattr(note, "type", None) != "url_citation":
                    continue
                out.append(
                    {
                        "url": getattr(note, "url", ""),
                        "title": getattr(note, "title", "") or "",
                        "start_index": getattr(note, "start_index", None),
                        "end_index": getattr(note, "end_index", None),
                    }
                )
    return out


def queries_used(response: Any) -> list[str]:
    out: list[str] = []
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) == "search_results":
            out.extend(getattr(item, "queries", None) or [])
    return list(dict.fromkeys(out))


def render_briefing(data: dict, topic: str) -> str:
    """Readable markdown from the structured result — for the human, not the machine."""
    lines = [f"# Research: {topic}", "", data.get("summary", ""), ""]
    for i, finding in enumerate(data.get("findings") or [], 1):
        lines += [f"## {i}. {finding.get('headline','')}", "", finding.get("detail", ""), ""]
        for fig in finding.get("figures") or []:
            flag = " *(estimate)*" if fig.get("is_estimate") else ""
            lines.append(
                f"- **{fig.get('value','')}** — {fig.get('what','')}{flag}  \n"
                f"  <{fig.get('source_url','')}>"
            )
        if finding.get("figures"):
            lines.append("")
        for url in finding.get("source_urls") or []:
            lines.append(f"  - source: <{url}>")
        lines.append("")
    if data.get("disagreements"):
        lines += ["## Where sources disagree", ""]
        for d in data["disagreements"]:
            lines.append(f"- **{d.get('about','')}** — {d.get('positions','')}")
        lines.append("")
    if data.get("corrections"):
        lines += ["## Widely repeated, apparently wrong", ""]
        for corr in data["corrections"]:
            lines.append(
                f"- Believed: {corr.get('widely_believed','')}  \n"
                f"  Actually: {corr.get('actually','')}"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def create_with_retry(client, *, attempts: int = 4, **kwargs):
    """Call the API, honouring Retry-After on 429 with exponential backoff + jitter."""
    import perplexity

    for attempt in range(1, attempts + 1):
        try:
            return client.responses.create(**kwargs)
        except perplexity.AuthenticationError as exc:
            raise ToolError(
                "Perplexity rejected the credentials (401). Create a key at "
                "https://console.perplexity.ai and set PERPLEXITY_API_KEY in .env. "
                "If the key may have leaked, rotate it in the console."
            ) from exc
        except perplexity.RateLimitError as exc:
            if attempt == attempts:
                raise ToolError(
                    f"Rate limited by Perplexity {attempts} times running. "
                    f"Requests rejected with 429 are not billed — try again shortly."
                ) from exc
            wait = None
            response = getattr(exc, "response", None)
            if response is not None:
                header = response.headers.get("retry-after")
                if header:
                    try:
                        wait = float(header)
                    except ValueError:
                        wait = None
            if wait is None:
                wait = min(2**attempt, 30) + random.uniform(0, 1)
            log(f"429 rate limited; retrying in {wait:.1f}s ({attempt}/{attempts - 1})")
            time.sleep(wait)
        except perplexity.APITimeoutError as exc:
            if attempt == attempts:
                raise ToolError(
                    "Perplexity timed out repeatedly. Lower --preset or raise --timeout."
                ) from exc
            log(f"Timed out; retrying ({attempt}/{attempts - 1})")
        except perplexity.APIConnectionError as exc:
            raise ToolError(f"Could not reach Perplexity: {exc}") from exc
        except perplexity.APIStatusError as exc:
            raise ToolError(
                f"Perplexity returned HTTP {exc.status_code}. "
                f"Check the request shape against https://docs.perplexity.ai/api-reference/agent-post"
            ) from exc
    raise ToolError("Exhausted retries against Perplexity.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True)
    parser.add_argument(
        "--preset",
        default="medium",
        choices=PRESETS,
        help="Agent effort. medium = multi-hop browsing (default); high for a "
        "flagship issue; fast for a quick check.",
    )
    parser.add_argument("--recency", choices=RECENCY, help="Only sources this recent")
    parser.add_argument("--domains", help="Comma-separated domain allowlist")
    parser.add_argument("--max-steps", type=int, help="Override the preset's step budget (min 3)")
    parser.add_argument("--out", help="Corpus path (default .tmp/research-<slug>.json)")
    parser.add_argument("--timeout", type=float, default=600.0)
    args = parser.parse_args()

    load_env()
    # Presence check only — the SDK reads the value itself; we never touch it.
    if not os.environ.get("PERPLEXITY_API_KEY"):
        raise ToolError(
            "PERPLEXITY_API_KEY is not set. Create a key at https://console.perplexity.ai "
            "and add it to .env as PERPLEXITY_API_KEY=... (the file is gitignored). "
            "Don't paste the key into chat."
        )

    if args.max_steps is not None and args.max_steps < 3:
        raise ToolError("--max-steps must be at least 3, or tools never get to run.")

    try:
        from perplexity import Perplexity
    except ImportError as exc:
        raise ToolError("perplexityai is not installed. Run: pip install perplexityai") from exc

    client = Perplexity(timeout=args.timeout)

    domains = [d.strip() for d in (args.domains or "").split(",") if d.strip()]
    tools = build_tools(args.recency, domains)

    kwargs: dict[str, Any] = {
        "preset": args.preset,
        "input": PROMPT.format(topic=args.topic),
        "instructions": INSTRUCTIONS,
        "response_format": SCHEMA,
    }
    if tools:
        kwargs["tools"] = tools
    if args.max_steps is not None:
        kwargs["max_steps"] = args.max_steps

    log(f"Researching {args.topic!r} (preset={args.preset}, filters={'yes' if tools else 'preset default'})")
    started = time.time()
    response = create_with_retry(client, **kwargs)
    elapsed = time.time() - started

    status = getattr(response, "status", None)
    if status and status != "completed":
        error = getattr(response, "error", None)
        raise ToolError(f"Agent run finished with status {status!r}: {error}")

    answer = (getattr(response, "output_text", "") or "").strip()
    if not answer:
        raise ToolError("Agent returned no text output. Raw response kept for inspection.")

    try:
        structured = json.loads(answer)
    except json.JSONDecodeError as exc:
        raise ToolError(
            f"Expected JSON matching the response_format schema, got something else "
            f"({answer[:160]!r}...). {exc}"
        ) from exc

    sources = collect_sources(response)
    citations = collect_citations(response)
    briefing = render_briefing(structured, args.topic)

    slug = slugify(args.topic)
    out = Path(args.out) if args.out else tmp_path(f"research-{slug}.json")
    raw_path = tmp_path(f"research-{slug}.raw.json")
    brief_path = tmp_path(f"research-{slug}.md")

    raw = response.model_dump() if hasattr(response, "model_dump") else str(response)
    write_json(raw_path, raw)
    write_text(brief_path, briefing)

    usage = getattr(response, "usage", None)
    write_json(
        out,
        {
            "topic": args.topic,
            "preset": args.preset,
            "recency": args.recency,
            "model": getattr(response, "model", None),
            "response_id": getattr(response, "id", None),
            "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "elapsed_seconds": round(elapsed, 1),
            "briefing": briefing,          # check_claims.py reads this
            "findings": structured.get("findings", []),
            "summary": structured.get("summary", ""),
            "disagreements": structured.get("disagreements", []),
            "corrections": structured.get("corrections", []),
            "sources": sources,            # and this
            "citations": citations,
            "queries": queries_used(response),
            "raw": str(raw_path),
        },
    )

    figures = sum(len(f.get("figures") or []) for f in structured.get("findings") or [])
    log(
        f"{len(structured.get('findings') or [])} finding(s), {figures} figure(s), "
        f"{len(sources)} source(s) in {elapsed:.0f}s"
    )
    if len(sources) < 5:
        log("WARNING: fewer than 5 sources — widen --recency or raise --preset before writing.")

    return emit(
        {
            "corpus": str(out),
            "briefing": str(brief_path),
            "raw": str(raw_path),
            "model": getattr(response, "model", None),
            "findings": len(structured.get("findings") or []),
            "figures": figures,
            "sources": len(sources),
            "citations": len(citations),
            "elapsed_seconds": round(elapsed, 1),
            "usage": usage.model_dump() if hasattr(usage, "model_dump") else None,
        }
    )


if __name__ == "__main__":
    run(main)
