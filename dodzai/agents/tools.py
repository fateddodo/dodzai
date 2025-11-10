"""Built-in tools for the DodzAI agent runtime."""
from __future__ import annotations

import io
import textwrap
from contextlib import redirect_stdout
from typing import Dict

from .core import Tool

try:  # pragma: no cover - optional dependency
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore


class PythonTool(Tool):
    """Executes Python code in a restricted namespace."""

    def __init__(self) -> None:
        super().__init__(name="python", description="Execute Python code snippets safely.")

    def run(self, instructions: str, *, context: Dict) -> str:
        local_context: Dict[str, object] = {"context": context}
        stdout = io.StringIO()
        try:
            with redirect_stdout(stdout):
                exec(instructions, {"__builtins__": _safe_builtins()}, local_context)  # noqa: S102
        except Exception as exc:
            return f"Python tool error: {exc}"
        output = stdout.getvalue().strip()
        if "result" in local_context:
            result_str = str(local_context["result"])
            return f"{output}\n{result_str}".strip()
        return output or "Python snippet executed with no output."


class WebRequestTool(Tool):
    """Performs a simple HTTP GET request."""

    def __init__(self) -> None:
        super().__init__(name="web", description="Fetch the contents of a URL using HTTP GET.")

    def run(self, instructions: str, *, context: Dict) -> str:
        if requests is None:
            return "The 'requests' package is not available."
        url = instructions.strip()
        if not url:
            return "No URL provided."
        try:  # pragma: no cover - network interaction
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            snippet = textwrap.shorten(response.text, 500, placeholder="…")
            return snippet
        except Exception as exc:
            return f"Failed to fetch {url}: {exc}"


def _safe_builtins() -> Dict[str, object]:
    return {
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "range": range,
        "enumerate": enumerate,
        "sorted": sorted,
        "print": print,
    }
