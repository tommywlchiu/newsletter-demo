# Weekly Autorun Prompt

This is the prompt handed to Claude Code by `scripts/run_weekly_newsletter.ps1`,
invoked unattended by Windows Task Scheduler every Monday at 8:50am. Nobody is
present to answer questions or approve the send — that authorization is standing,
granted once here, not re-asked each week.

Edit this file to change what the weekly issue covers or how failures are handled.
The step-by-step mechanics (research → outline → infographics → check_claims →
build → send → archive) still live in `workflows/build_newsletter.md` — this file
only supplies what a human would otherwise be asked for, plus the autorun-specific
overrides.

---

Follow `workflows/build_newsletter.md` to produce and send this week's KittyNews
issue. You are running unattended — no one will see a question or a prompt, so do
not use AskUserQuestion or otherwise wait on input. Where the workflow says "ask,"
use the answer given here instead; where it doesn't cover something, make the most
reasonable call yourself and record it in the run summary rather than stopping to
ask.

**Inputs:**
- Topic: agentic AI — whatever is most significant in agentic AI news from the
  past 7 days. No fixed angle; pick it from what the research actually turns up,
  same as issues 001 and 002.
- Recency: `week`.
- Recipient: tommychiu7060@gmail.com
- Issue number: next unused number in `archive/`.

**Standing authorization to send:** step 9 of the workflow normally requires
explicit sign-off before `--send`. For this scheduled run, that sign-off is this
document — once the local preview build completes cleanly and `check_claims.py`
passes, proceed straight to `gmail_draft.py --send`. Do not create a Gmail draft
for review at any point (see the workflow's 2026-09-15 notes on why).

**Safety gates that still apply, even unattended:**
- If research returns fewer than 5 sources even after widening `--recency` and
  raising `--preset` per the workflow's edge-case table, stop. Do not send an
  issue built on thin material.
- If `check_claims.py` flags a figure you cannot correct against a source in the
  corpus, stop. Do not `--allow` a figure just to get past the check.
- If `build_email.py` or `render_png.py` errors for any reason, stop.
- "Stop" means: do not send, leave whatever was built in `.tmp/` for later
  inspection, and go straight to the failure-notification step below instead of
  retrying indefinitely.

**On success:** after archiving and committing per step 10, append one line to
`logs/weekly-runs.log` (create the file if it doesn't exist) in the form
`<UTC timestamp> OK issue <N> "<subject>" sent to <recipient>`.

**On failure or an early stop:** append one line to `logs/weekly-runs.log` in the
form `<UTC timestamp> FAILED <short reason>`, then send a short plain-text email
(not through the newsletter template — a plain `smtplib` message is fine, same
`GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD` from `.env`) to tommychiu7060@gmail.com with
subject `KittyNews weekly run failed` explaining what happened and what's left in
`.tmp/` to look at. Do not leave a failure silent — the whole point of this file
is that no one is watching for it live.

**2026-09-17 — Failure alert verified before ever needing it.** Three real runs
had shipped clean, so this branch had never fired. Dry-ran just the alert
(same `smtplib`/`SMTP_SSL("smtp.gmail.com", 465)` call gmail_draft.py uses, same
envelope, subject suffixed `[DRY RUN — not a real failure]` so it couldn't be
mistaken for a real one) without touching `logs/weekly-runs.log`, then confirmed
via Gmail search that it actually landed in the inbox — not just that the script
exited 0. Same lesson as the dark-mode notes above: an untested code path earns
no more trust than an untested CSS rule.
