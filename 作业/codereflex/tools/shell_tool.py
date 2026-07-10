from __future__ import annotations
import subprocess
from codereflex.models import Action, ActionResult
from codereflex.tools.base import Tool


class RunShell(Tool):
    def __init__(self, timeout: int = 60):
        self._timeout = timeout

    def execute(self, action: Action) -> ActionResult:
        cmd = action.params["cmd"]
        try:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=self._timeout,
            )
            return ActionResult(
                success=proc.returncode == 0,
                output=proc.stdout,
                error=proc.stderr,
                exit_code=proc.returncode,
            )
        except subprocess.TimeoutExpired:
            return ActionResult(success=False, error=f"Command timed out after {self._timeout}s")
