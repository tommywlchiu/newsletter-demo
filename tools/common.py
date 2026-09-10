"""Shared plumbing for every tool in tools/.

Convention all tools follow:
  - Structured result goes to STDOUT as a single JSON object.
  - Human-readable progress/errors go to STDERR via log().
  - Exit 0 on success, 1 on handled failure.

That split lets the agent parse stdout reliably while still seeing what happened.

Typical tool skeleton:

    from common import log, emit, fail, require_env, tmp_path

    def main() -> int:
        p = argparse.ArgumentParser()
        p.add_argument("--url", required=True)
        args = p.parse_args()
        ...
        return emit({"url": args.url, "chars": len(text)})

    if __name__ == "__main__":
        raise SystemExit(main())
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # dotenv is optional until a tool actually needs a secret
    load_dotenv = None

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / ".tmp"
WORKFLOWS = ROOT / "workflows"

_env_loaded = False


def load_env() -> None:
    """Load .env from the project root. Safe to call repeatedly."""
    global _env_loaded
    if _env_loaded:
        return
    if load_dotenv is not None:
        load_dotenv(ROOT / ".env")
    _env_loaded = True


def require_env(name: str) -> str:
    """Fetch a required secret, failing loudly with a fixable message."""
    load_env()
    value = os.environ.get(name)
    if not value:
        raise MissingEnv(
            f"{name} is not set. Add it to {ROOT / '.env'} "
            f"(see .env.example for the expected keys)."
        )
    return value


def get_env(name: str, default: str | None = None) -> str | None:
    load_env()
    return os.environ.get(name, default)


class MissingEnv(RuntimeError):
    """Raised when a tool needs a credential that isn't configured."""


class ToolError(RuntimeError):
    """Expected, explainable failure — reported cleanly instead of a traceback."""


def log(message: str) -> None:
    """Progress line on stderr, so it never pollutes the JSON on stdout."""
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{stamp}] {message}", file=sys.stderr, flush=True)


def emit(data: dict[str, Any]) -> int:
    """Print the success payload and return the process exit code."""
    print(json.dumps({"ok": True, **data}, indent=2, default=str))
    return 0


def fail(message: str, **extra: Any) -> int:
    """Print a structured failure and return the process exit code."""
    print(json.dumps({"ok": False, "error": message, **extra}, indent=2, default=str))
    log(f"FAILED: {message}")
    return 1


def slugify(text: str, max_length: int = 60) -> str:
    """Filesystem-safe name for intermediate files."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:max_length].rstrip("-")) or "untitled"


def tmp_path(name: str, *, stamped: bool = False) -> Path:
    """Path inside .tmp/, creating the directory as needed.

    stamped=True prefixes a UTC timestamp so repeated runs don't overwrite.
    """
    TMP.mkdir(parents=True, exist_ok=True)
    if stamped:
        name = f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{name}"
    return TMP / name


def write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return path


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


BRAND_FILE = ROOT / "brand" / "brand.json"


def load_brand() -> dict[str, Any]:
    """Brand tokens, injected into every template as `brand`.

    Single source of truth for colour and type — a template should never hardcode
    a hex value.
    """
    if not BRAND_FILE.exists():
        raise ToolError(
            f"{BRAND_FILE} is missing. Every template reads it for colour and type."
        )
    return read_json(BRAND_FILE)


def render_template(template: Path, context: dict[str, Any]) -> str:
    """Render a Jinja2 template from the project root, with `brand` pre-injected.

    StrictUndefined is deliberate: a typo'd token should stop the build, not
    silently render an empty string into a published asset.
    """
    try:
        from jinja2 import Environment, FileSystemLoader, StrictUndefined
    except ImportError as exc:
        raise ToolError("jinja2 is not installed. Run: pip install jinja2") from exc

    template = Path(template).resolve()
    if not template.exists():
        raise ToolError(f"Template not found: {template}")

    env = Environment(
        loader=FileSystemLoader([str(ROOT), str(template.parent)]),
        undefined=StrictUndefined,
        autoescape=False,
    )
    context = {**context, "brand": context.get("brand") or load_brand()}
    return env.get_template(template.relative_to(ROOT).as_posix()).render(**context)


def run(main_fn) -> None:
    """Wrap a tool's main() so expected failures print cleanly.

    Unexpected exceptions still raise, because a full traceback is the useful
    output when something genuinely unforeseen breaks.
    """
    try:
        raise SystemExit(main_fn())
    except (ToolError, MissingEnv) as exc:
        raise SystemExit(fail(str(exc)))
