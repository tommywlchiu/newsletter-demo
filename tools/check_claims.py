#!/usr/bin/env python3
"""Verify every figure headed for an infographic traces back to the research corpus.

A fabricated number inside a confident-looking chart is far worse than a vague
sentence — it looks authoritative and it travels. This tool is the gate between
"the model produced a figure" and "the figure gets rendered at 76px".

Matching is deliberately loose: it normalises "$4.2B", "4.2 billion" and "4,200M"
toward a common form and looks for the digits in the corpus. It is a fabrication
detector, not a fact-checker — it catches numbers that appear from nowhere, and it
cannot tell you a sourced number was misread. Exit 1 on any orphan.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from common import ToolError, emit, log, read_json, run

# A number, optionally with currency/percent and a magnitude suffix.
NUM_RE = re.compile(
    r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(billion|million|trillion|bn|m|k|b|t)?",
    re.IGNORECASE,
)
SUFFIX = {
    "k": 1e3, "m": 1e6, "b": 1e9, "bn": 1e9, "t": 1e12,
    "million": 1e6, "billion": 1e9, "trillion": 1e12,
}
# Values that are structural rather than factual claims.
IGNORE_KEYS = {"slot", "highlight", "now", "cid"}


def variants(raw: str, suffix: str | None) -> set[str]:
    """Digit-strings this figure could plausibly appear as in prose."""
    plain = raw.replace(",", "")
    out = {plain}
    try:
        value = float(plain)
    except ValueError:
        return out
    if suffix:
        scaled = value * SUFFIX[suffix.lower()]
        # 4.2B -> "4200000000" and "4200"
        out.add(f"{scaled:.0f}")
        out.add(f"{scaled / 1e6:.0f}")
        out.add(f"{scaled / 1e9:.0f}")
    if value == int(value):
        out.add(str(int(value)))
    return {v for v in out if v and v != "0"}


def collect_figures(node, path="", found=None) -> list[dict]:
    """Walk an infographic's data and pull out every numeric claim."""
    found = [] if found is None else found
    if isinstance(node, dict):
        for key, value in node.items():
            if key in IGNORE_KEYS:
                continue
            collect_figures(value, f"{path}.{key}" if path else key, found)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            collect_figures(item, f"{path}[{i}]", found)
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        found.append({"where": path, "text": str(node), "digits": {str(node)}})
    elif isinstance(node, str):
        for match in NUM_RE.finditer(node):
            raw, suffix = match.group(1), match.group(2)
            found.append(
                {
                    "where": path,
                    "text": match.group(0).strip(),
                    "digits": variants(raw, suffix),
                }
            )
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--infographics", nargs="+", required=True, help="Infographic data JSON files"
    )
    parser.add_argument("--research", required=True, help="Corpus JSON from research_topic.py")
    parser.add_argument(
        "--allow",
        nargs="*",
        default=[],
        help="Figures to accept without a source (e.g. a count you derived yourself)",
    )
    args = parser.parse_args()

    corpus = read_json(Path(args.research))
    haystack = corpus.get("briefing", "")
    for src in corpus.get("sources", []):
        haystack += " " + " ".join(
            str(src.get(k, "")) for k in ("title", "snippet", "date")
        )
    haystack_digits = haystack.replace(",", "")
    if len(haystack_digits) < 200:
        raise ToolError(
            f"Corpus at {args.research} has almost no text ({len(haystack_digits)} chars). "
            f"Re-run research_topic.py before checking claims against it."
        )

    allow = {a.strip() for a in args.allow}
    checked = 0
    orphans: list[dict] = []
    uncited: list[str] = []

    for path_str in args.infographics:
        path = Path(path_str)
        data = read_json(path)

        source = str(data.get("source", "")).strip()
        if not source:
            uncited.append(path.name)
        if "SAMPLE DATA" in source.upper():
            log(f"{path.name}: sample data, skipping")
            continue

        for figure in collect_figures(data):
            if figure["text"] in allow:
                continue
            checked += 1
            if not any(d in haystack_digits for d in figure["digits"]):
                orphans.append(
                    {"file": path.name, "field": figure["where"], "figure": figure["text"]}
                )

    log(f"Checked {checked} figure(s) across {len(args.infographics)} infographic(s)")

    if uncited:
        raise ToolError(
            f"Infographic(s) with no source: {', '.join(uncited)}. "
            f"Every card must carry attribution."
        )

    if orphans:
        lines = "\n".join(
            f"  - {o['figure']!r} in {o['file']} ({o['field']})" for o in orphans
        )
        raise ToolError(
            f"{len(orphans)} figure(s) do not appear anywhere in the research corpus:\n"
            f"{lines}\n"
            f"Either correct them against a source, or pass --allow if you derived "
            f"them yourself and can stand behind them."
        )

    return emit({"checked": checked, "orphans": 0, "infographics": len(args.infographics)})


if __name__ == "__main__":
    run(main)
