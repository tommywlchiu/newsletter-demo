# workflows/

Markdown SOPs. Each file briefs the agent on one job the way you'd brief a teammate:
what the objective is, what it needs, which tools to run, what "done" looks like.

## Rules

1. **One workflow = one outcome.** Name it after the outcome: `build_newsletter.md`.
2. **Plain language.** Describe intent and decisions; leave mechanics to the tools.
3. **Name the tools explicitly.** "Run `tools/scrape_single_site.py --url <url>`" — not
   "scrape the site."
4. **Write down what you learn.** Rate limits, timing quirks, formats that break —
   they belong in the workflow's Notes so the next run doesn't rediscover them.
5. **Don't overwrite without asking.** These are standing instructions, refined over
   time, not scratch files.

## Template

Copy `_template.md` when starting a new one.

## Index

_No workflows yet._

| Workflow | Outcome | Tools used |
| -------- | ------- | ---------- |
