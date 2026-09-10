# Build Newsletter

## Objective
Turn a topic into a researched, KittyNews-branded HTML email with custom infographics,
sitting in Gmail as a draft for review. One issue per run.

## Inputs
| Input | Required | Source / default |
| ----- | -------- | ---------------- |
| `topic` | yes | Ask me. One sentence — "the state of X", not a single word. |
| `angle` | no | Ask if the topic is broad. What should the reader take away? |
| `recency` | no | Default `month`. Use `week` for fast-moving news. |
| `to` | no | `NEWSLETTER_DEFAULT_TO` in `.env`, else ask. |
| `issue number` | no | Next unused number in `archive/`. |

Ask for anything missing before starting. Don't invent a topic or a recipient.

## Tools
| Step | Tool | Command |
| ---- | ---- | ------- |
| 2 | `tools/research_topic.py` | `python tools/research_topic.py --topic "<topic>" --preset high --recency month` |
| 5 | `tools/check_claims.py` | `python tools/check_claims.py --infographics .tmp/ig_*.json --research .tmp/research-<slug>.json` |
| 6 | `tools/render_png.py` | `python tools/render_png.py --template templates/infographics/<type>.html.j2 --out .tmp/img/<cid>.png --data-file .tmp/<cid>.json --scale 2` |
| 7 | `tools/build_email.py` | `python tools/build_email.py --data-file .tmp/issue.json --out .tmp/issue.html --text-out .tmp/issue.txt --preview-out .tmp/preview.html --images .tmp/img` |
| 9 | `tools/gmail_draft.py` | `python tools/gmail_draft.py --html .tmp/issue.html --text .tmp/issue.txt --subject "<subject>" --images .tmp/img --to <address>` |

All commands run with `.venv/Scripts/python.exe` on this machine.

## Steps

1. **Check the archive.** Read `archive/` for the last few issues. If the topic overlaps
   one, say so and ask whether to proceed, angle differently, or pick another.

2. **Research.** Run `research_topic.py`. It writes a corpus to `.tmp/research-<slug>.json`
   and always keeps the raw response beside it. Read the briefing before continuing —
   if it came back with fewer than 5 sources or reads thin, widen `--recency` or raise
   `--preset` and run again rather than writing from weak material.

3. **Outline.** Pick 3–4 stories, strongest first. For each: a heading, an optional dek,
   and 2–3 short paragraphs. Lead with the finding, never the setup.

4. **Choose infographics.** Two to four per issue, one per story at most. Match the form
   to the data — this is the decision that makes or breaks the issue:
   - `stat_card` — 1–3 headline figures. The default when there's a number worth shouting.
   - `bar_chart` — comparing magnitude across 3–6 named categories.
   - `comparison_table` — options side by side on shared criteria.
   - `timeline` — a sequence where the order carries the meaning.

   If the research has no numbers worth showing, **ship fewer infographics**. A padded
   chart is worse than none.

   Write one JSON per graphic to `.tmp/<cid>.json`. Every one needs a `source`.

5. **Check claims — before rendering, not after.** Run `check_claims.py`. It fails on any
   figure that appears nowhere in the corpus. Fix the figure against a source; only use
   `--allow` for numbers you derived yourself and can stand behind.

6. **Render.** One `render_png.py` per graphic into `.tmp/img/<cid>.png`. The filename stem
   *is* the cid — `.tmp/img/ig-stat.png` is referenced as `cid:ig-stat`. Also copy
   `brand/logo.png` to `.tmp/img/logo.png`; the masthead expects `cid:logo`.

7. **Write the issue JSON and build.** See `templates/newsletter.mjml.j2` for the shape.
   Two things that are easy to skimp and shouldn't be:
   - **Subject and preheader are different jobs.** The subject earns the open; the
     preheader (~90 chars, shown after it in the inbox list) earns the read. Never leave
     the preheader to chance.
   - **Alt text carries the graphic.** Many clients block images by default, so state
     the finding in the alt text, and restate any figure that matters in the body copy.
     The issue must still make its point with every image missing.

8. **Look at it.** Open `.tmp/preview.html` in a browser. Check the 600px column, that
   nothing overflows, and that the graphics sit as one family. Read `.tmp/issue.txt` too —
   it's what some readers actually get.

9. **Draft it.** Run `gmail_draft.py` — it creates a *draft*, it does not send. Report the
   draft link and stop. **Never pass `--send` unless I explicitly ask.**

10. **Archive.** Copy the issue JSON, built HTML, PNGs and research corpus to
    `archive/<YYYY-MM-DD>-<slug>/` and commit. That's what step 1 reads next time.

## Output
- **Deliverable:** a Gmail draft, images inline, ready to review and send.
- **Archive:** `archive/<date>-<slug>/` committed to git.
- **Intermediates:** `.tmp/` — disposable.

## Edge cases
| If this happens | Do this |
| --------------- | ------- |
| Research returns < 5 sources | Widen `--recency`, drop `--domains`, or raise `--preset`. Don't write from thin material. |
| No numbers worth charting | Ship fewer infographics. Never invent data to fill a slot. |
| `check_claims.py` flags a figure | Correct it against a source. `--allow` only for figures you derived and can defend. |
| Perplexity 429 | The tool backs off and retries 3×. If it still fails, wait and re-run — the corpus is cached in `.tmp/`. |
| Playwright first run is slow | Normal, it's a cold browser start. If it errors, run `python -m playwright install chromium`. |
| MJML reports errors | It lists all of them at once. Usually an unclosed tag or an `mj-` element nested where it can't go. |
| Gmail rejects the login | `GMAIL_APP_PASSWORD` must be the 16-char app password, not the account password. IMAP must be on in Gmail settings. |
| Message over 25MB | Re-render with a lower `--colors`. Cards should land around 25KB each. |

## Checks before "done"
- [ ] Every required input was present (nothing silently defaulted)
- [ ] `check_claims.py` passed, or every `--allow` is one I can defend
- [ ] Every infographic carries a `source`
- [ ] Subject *and* preheader are both written, and different
- [ ] Every image has alt text that states the finding
- [ ] Key figures also appear in the body copy, for images-off readers
- [ ] Preview opened in a browser and actually looked at
- [ ] A **draft** was created — nothing was sent
- [ ] Issue archived to `archive/` and committed

## Notes
_Append what you learn. Dated._

**2026-09-10 — The Gmail connector cannot deliver this.** The Gmail MCP connector runs an
HTML sanitiser that strips every `<img>` tag (both `cid:` and `https:`) and drops
background colours from inline styles. Verified by creating drafts through it and decoding
the stored MIME: only text, tables and width attributes survived. It also assigns its own
random `Content-ID` (`<ii_1a08a0cf7e8-…>`), so an authored `cid:` reference can never
match. Hence `gmail_draft.py` uses SMTP/IMAP with an app password instead.

**2026-09-10 — Dark mode doesn't touch the graphics.** Gmail and Outlook invert HTML
backgrounds but leave images alone. So the infographic palette only ever meets the sand
ground baked into each PNG, and is validated in light mode only. Dark-mode robustness is a
property of the email chrome — which is why the palette uses warm near-neutrals rather
than `#FFFFFF`/`#000000`.

**2026-09-10 — Generate the plain-text part from the data, not the HTML.** Running
html2text over compiled MJML renders the layout tables as markdown table soup
(`| | |`, `---`). `build_email.py` composes the text part from the issue JSON and applies
html2text only per paragraph, for inline markup.

**2026-09-10 — Perplexity endpoint.** Build against `POST /v1/agent`. The Sonar
`/chat/completions` endpoint was retired 2026-09-27; most tutorials online still show it.
