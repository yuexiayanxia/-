from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActionType(str, Enum):
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    LIST_DIR = "list_dir"
    RUN_SHELL = "run_shell"
    RUN_VALIDATORS = "run_validators"


class FailureCategory(str, Enum):
    TEST_FAILURE = "test_failure"
    SYNTAX_ERROR = "syntax_error"
    TYPE_ERROR = "type_error"
    LINT_VIOLATION = "lint_violation"
    IMPORT_ERROR = "import_error"
    RUNTIME_ERROR = "runtime_error"


class FeedbackStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    VALIDATOR_ERROR = "validator_error"


class DecisionVerdict(str, Enum):
    ALLOW = "allow"
    INTERCEPT = "intercept"
    DENY = "deny"


class SessionStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    CONVERGENCE_STOPPED = "convergence_stopped"
    BUDGET_EXHAUSTED = "budget_exhausted"
    ERROR = "error"


@dataclass
class Action:
    type: ActionType
    params: dict[str, Any]
    target_path: str | None = None


@dataclass
class ActionResult:
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int | None = None


@dataclass
class FailureItem:
    category: FailureCategory
    file: str
    line: int | None
    message: str
    expected: str | None = None
    actual: str | None = None


@dataclass
class Feedback:
    validator: str
    status: FeedbackStatus
    failures: list[FailureItem] = field(default_factory=list)
    raw_output: str = ""


@dataclass
class Turn:
    action: Action | None = None
    result: ActionResult | None = None
    feedback: Feedback | None = None
    llm_response: str | None = None


@dataclass
class Session:
    id: str
    task: str
    history: list[Turn] = field(default_factory=list)
    status: SessionStatus = SessionStatus.RUNNING
    retry_count: int = 0
    failure_signatures: list[str] = field(default_factory=list)


@dataclass
class Decision:
    verdict: DecisionVerdict
    reason: str = ""


@dataclass
class DecisionLogEntry:
    timestamp: str
    task: str
    outcome: str
    key_actions: list[str] = field(default_factory=list)
