# tools/

Deterministic Python scripts. One job per script, no reasoning, no guessing.

## Rules

1. **One tool = one job.** `scrape_single_site.py`, not `do_newsletter_stuff.py`.
2. **CLI in, JSON out.** Arguments via `argparse`; a single JSON object on stdout.
3. **Logs to stderr.** Use `common.log()` so stdout stays parseable.
4. **Secrets from `.env` only.** Via `common.require_env()` — never hardcoded, never
   passed as a CLI argument (they leak into shell history).
5. **Fail explainably.** Raise `common.ToolError("what broke and how to fix it")`.
6. **Idempotent where possible.** Re-running a tool shouldn't duplicate work.

## Skeleton

```python
#!/usr/bin/env python3
"""One-line description of what this tool does."""
import argparse
from common import ToolError, emit, log, require_env, run, tmp_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Page to fetch")
    args = parser.parse_args()

    log(f"Fetching {args.url}")
    # ... do the work ...

    return emit({"url": args.url, "output_file": str(path)})


if __name__ == "__main__":
    run(main)
```

## Running

```bash
python tools/your_tool.py --url https://example.com
```

Tools import `common` as a sibling module, so run them from anywhere —
`common.py` resolves the project root from its own location.

## Index

_No tools yet. Add each one here with a one-line description as it's built._

| Tool | Does | Used by |
| ---- | ---- | ------- |
