from __future__ import annotations
import re
from pathlib import Path
from codereflex.models import Action, Decision, DecisionVerdict, ActionType


class Guardrail:
    def __init__(self, dangerous_patterns: list[str], allowed_paths: list[str]):
        self._patterns = [re.compile(p, re.IGNORECASE) for p in dangerous_patterns]
        self._allowed = [Path(a).resolve() for a in allowed_paths]

    def check(self, action: Action) -> Decision:
        if action.type == ActionType.WRITE_FILE:
            return self._check_path(action.params.get("path", ""))
        if action.type == ActionType.RUN_SHELL:
            return self._check_shell(action.params.get("cmd", ""))
        return Decision(verdict=DecisionVerdict.ALLOW)

    def _check_shell(self, cmd: str) -> Decision:
        for pat in self._patterns:
            if pat.search(cmd):
                return Decision(verdict=DecisionVerdict.INTERCEPT, reason=f"Matched dangerous pattern: {pat.pattern}")
        return Decision(verdict=DecisionVerdict.ALLOW)

    def _check_path(self, path: str) -> Decision:
        resolved = Path(path).resolve()
        if not any(resolved == a or a in resolved.parents for a in self._allowed):
            return Decision(verdict=DecisionVerdict.DENY, reason=f"Path outside allowed scope: {resolved}")
        return Decision(verdict=DecisionVerdict.ALLOW)
