from __future__ import annotations
import subprocess
from pathlib import Path
from codereflex.models import Feedback, FeedbackStatus


class Validator:
    name: str = "base"

    def validate(self, project_path: str) -> Feedback:
        raise NotImplementedError


class _SubprocessValidator(Validator):
    def _run(self, cmd: list[str], cwd: str) -> Feedback:
        try:
            proc = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True, timeout=60,
            )
            status = FeedbackStatus.PASS if proc.returncode == 0 else FeedbackStatus.FAIL
            return Feedback(
                validator=self.name, status=status,
                raw_output=proc.stdout + proc.stderr,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return Feedback(validator=self.name, status=FeedbackStatus.VALIDATOR_ERROR,
                            raw_output=str(e))


class PytestValidator(_SubprocessValidator):
    name = "pytest"

    def validate(self, project_path: str) -> Feedback:
        if not Path(project_path).exists():
            return Feedback(validator=self.name, status=FeedbackStatus.VALIDATOR_ERROR,
                            raw_output="Project path not found")
        return self._run(["python", "-m", "pytest", "-v", "--tb=short"], project_path)


class RuffValidator(_SubprocessValidator):
    name = "ruff"

    def validate(self, project_path: str) -> Feedback:
        return self._run(["ruff", "check", "."], project_path)


class MypyValidator(_SubprocessValidator):
    name = "mypy"

    def validate(self, project_path: str) -> Feedback:
        return self._run(["mypy", "."], project_path)


class ValidatorPipeline:
    def __init__(self, validators: list[Validator]):
        self._validators = validators

    def run(self, project_path: str) -> list[Feedback]:
        return [v.validate(project_path) for v in self._validators]
