from __future__ import annotations
from pathlib import Path
from codereflex.models import Action, ActionResult
from codereflex.tools.base import Tool, check_path_allowed


class ReadFile(Tool):
    def __init__(self, allowed_paths: list[str]):
        self._allowed = allowed_paths

    def execute(self, action: Action) -> ActionResult:
        path = action.params["path"]
        if not check_path_allowed(path, self._allowed):
            return ActionResult(success=False, error="Path outside allowed scope denied")
        p = Path(path)
        if not p.exists():
            return ActionResult(success=False, error=f"File not found: {path}")
        return ActionResult(success=True, output=p.read_text(encoding="utf-8"))


class WriteFile(Tool):
    def __init__(self, allowed_paths: list[str] | None = None):
        self._allowed = [Path(a).resolve() for a in (allowed_paths or ["."])]

    def execute(self, action: Action) -> ActionResult:
        path = action.params["path"]
        content = action.params["content"]
        p = Path(path).resolve()
        if not any(p == a or a in p.parents for a in self._allowed):
            return ActionResult(success=False, error="Path outside allowed scope denied")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return ActionResult(success=True, output=f"Wrote {len(content)} bytes to {path}")


class ListDir(Tool):
    def __init__(self, allowed_paths: list[str]):
        self._allowed = allowed_paths

    def execute(self, action: Action) -> ActionResult:
        path = action.params["path"]
        if not check_path_allowed(path, self._allowed):
            return ActionResult(success=False, error="Path outside allowed scope denied")
        entries = [e.name for e in Path(path).iterdir()]
        return ActionResult(success=True, output="\n".join(sorted(entries)))
