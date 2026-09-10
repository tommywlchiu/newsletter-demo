# <Workflow Name>

## Objective
One or two sentences: what this produces and why it exists.

## Inputs
| Input | Required | Source / default |
| ----- | -------- | ---------------- |
| e.g. `source_urls` | yes | Ask me, or read from the sheet named below |

Ask for anything missing before starting. Don't invent inputs.

## Tools
| Step | Tool | Command |
| ---- | ---- | ------- |
| 1 | `tools/example.py` | `python tools/example.py --url <url>` |

## Steps
1. **<Step name>** — what to do, what the tool returns, and what to check before moving on.
2. **<Step name>** — ...
3. **Deliver** — where the final output goes (cloud service + location).

## Output
- **Deliverable:** where it lands (Google Sheet / Slides / Doc URL) and what it looks like.
- **Intermediates:** files written to `.tmp/` — disposable.

## Edge cases
| If this happens | Do this |
| --------------- | ------- |
| A source returns no content | Skip it, note it in the summary, continue with the rest |
| Credentials missing | Stop and tell me exactly which key is missing |
| Rate limited | Back off and retry once; if it fails again, stop and report |

## Checks before "done"
- [ ] Every required input was present (nothing silently defaulted)
- [ ] Output exists at the stated destination
- [ ] Failures and skips are reported, not swallowed

## Notes
_Append what you learn: quirks, limits, formats that break. Dated entries._
