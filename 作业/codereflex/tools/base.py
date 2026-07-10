from __future__ import annotations
from pathlib import Path
from codereflex.models import Action, ActionResult, ActionType


def check_path_allowed(path: str, allowed_paths: list[str]) -> bool:
    """Return True if resolved path is within one of allowed_paths."""
    resolved = Path(path).resolve()
    for ap in allowed_paths:
        allowed = Path(ap).resolve()
        if resolved == allowed or allowed in resolved.parents:
            return True
    return False


class Tool:
    def execute(self, action: Action) -> ActionResult:
        raise NotImplementedError


class ToolDispatcher:
    def __init__(self, allowed_paths: list[str] | None = None):
        self._tools: dict[ActionType, Tool] = {}
        self._allowed_paths = allowed_paths or ["."]

    def register(self, action_type: ActionType, tool: Tool) -> None:
        self._tools[action_type] = tool

    def dispatch(self, action: Action) -> ActionResult:
        tool = self._tools.get(action.type)
        if tool is None:
            return ActionResult(success=False, error=f"No tool registered for {action.type}")
        return tool.execute(action)
