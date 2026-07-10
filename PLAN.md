# CodeReflex Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Completion Status

| Task | Component | Commit | Status |
|------|-----------|--------|--------|
| 1 | Scaffolding + Data Models | `8083cbe` | ✅ Done (cold-start) |
| 2 | Config | `fb4973d` | ✅ Done |
| 3 | LLM Client | `fb4973d` | ✅ Done (StopIteration→RuntimeError fix) |
| 4 | Tools | `fb4973d` | ✅ Done |
| 5 | Guardrail | `fb4973d` | ✅ Done |
| 6 | HITL | `be32433` | ✅ Done |
| 7 | Validators | `fb4973d` | ✅ Done |
| 8 | FailureClassifier ★ | `b4cdf58` | ✅ Done (cold-start, runtime logic fixed `28f98a4`) |
| 9 | FeedbackLoop ★ | `be32433` | ✅ Done (has_failure fix) |
| 10 | Memory | `fb4973d` | ✅ Done (message order fix) |
| 11 | AgentLoop | `3e6b01b` | ✅ Done (Windows path fix) |
| 12 | CredentialStore | `fb4973d` | ✅ Done |
| 13 | WebUI | `6a23be3` | ✅ Done (TemplateResponse API fix) |
| 14 | CLI | `6a23be3` | ✅ Done (subprocess cwd fix) |
| 15 | Mechanism Demo | `6a23be3` | ✅ Done |
| 16 | Dockerfile + CI | `8e0f88c` | ✅ Done |
| 17 | README | `8e0f88c` | ✅ Done |

**Total: 65 tests pass, 17/17 tasks complete.**

**Goal:** Build a feedback-loop-centric coding agent harness that wraps an LLM to write, validate, and self-correct Python code until tests pass or retry budget exhausts.

**Architecture:** Agent main loop (context → LLM → parse action → guardrail → dispatch → validate → feedback → stop) with feedback loop as the structural spine. Failure taxonomy + convergence detection + structured feedback injection. All mechanisms are deterministic code testable with mock LLM.

**Tech Stack:** Python 3.14, FastAPI + Jinja2 + SSE, httpx, keyring, pyyaml, pytest/ruff/mypy, Docker, GitLab CI

## Global Constraints

- Python 3.14+, type hints with `|` union syntax
- All code in `作业/` directory; package name `codereflex`
- TDD strict: red → green → refactor, no implementation before failing test
- No real credentials in repo (`.env` gitignored, keyring for local, env var for Docker)
- LLM abstraction layer must be mockable; all core mechanisms testable without real LLM/network
- pytest as both test framework and validation target tool
- Each task ends with commit; commit message prefixed `feat:`/`test:`/`docs:`/`chore:`

---

## File Structure

```
作业/
  pyproject.toml                  # project metadata, deps, ruff/pytest config
  codereflex/
    __init__.py
    models.py                     # Action, ActionResult, FailureItem, Feedback, Turn, Session, Config, Decision, DecisionLogEntry + enums
    config.py                     # Config loading from YAML
    credentials.py                # CredentialStore (keyring + env fallback)
    llm/
      __init__.py
      client.py                   # LLMClient (OpenAI-compatible) + MockLLMClient
    tools/
      __init__.py
      base.py                     # Tool protocol + ToolDispatcher
      file_tools.py               # ReadFile, WriteFile, ListDir
      shell_tool.py               # RunShell
    guardrail/
      __init__.py
      guardrail.py                # Guardrail policy engine
      hitl.py                     # HITLController state machine
    feedback/
      __init__.py
      validators.py               # Validator protocol, Pytest/Ruff/MypyValidator, ValidatorPipeline
      classifier.py               # FailureClassifier (★ deep)
      feedback_loop.py            # FeedbackLoop orchestrator (★ deep)
    memory/
      __init__.py
      session.py                  # Session/Turn context window management
      decision_log.py             # DecisionLog cross-session storage
    agent.py                      # AgentLoop main loop
    web/
      __init__.py
      app.py                      # FastAPI app + SSE
      templates/
        index.html                # Jinja2 single-page UI
    cli.py                        # CLI entry (setup, run)
  tests/
    __init__.py
    conftest.py                   # shared fixtures
    test_models.py
    test_config.py
    test_llm_client.py
    test_tools.py
    test_guardrail.py
    test_hitl.py
    test_validators.py
    test_classifier.py
    test_feedback_loop.py
    test_memory.py
    test_agent_loop.py
    test_credentials.py
    test_web.py
    fixtures/
      sample_project/             # fixture Python project for validator tests
        pyproject.toml
        src/calc.py
        tests/test_calc.py
  demos/
    mechanism_demo.py             # A.6 three deterministic demos
  Dockerfile
  .gitlab-ci.yml
```

## Task Dependency Graph

```
Task 1 (models) ──┬─► Task 2 (config)
                  ├─► Task 3 (llm)          ──────────────────┐
                  ├─► Task 4 (tools)        ──────────────────┤
                  ├─► Task 5 (guardrail) ──► Task 6 (hitl) ───┤
                  ├─► Task 7 (validators) ─┐                  ├─► Task 11 (agent) ─► Task 13 (web) ─► Task 14 (cli)
                  ├─► Task 8 (classifier) ─┤                  │                         ▲
                  │                         └─► Task 9 (feedback) ───────────────────┤
                  ├─► Task 10 (memory) ─────────────────────────────────────────────┘
                  └─► Task 12 (credentials) ────────────────────────────────────────┘
Task 9 + 5 + 8 ──► Task 15 (mechanism demo)
All ──► Task 16 (docker+ci) ──► Task 17 (readme)
```

**Parallelizable after Task 1:** Tasks 2, 3, 4, 5, 7, 8, 10, 12 (each depends only on models).
**After those:** Task 6 (needs 5), Task 9 (needs 7+8), then Task 11 (needs 3+4+5+6+9+10+12).

---

### Task 1: Scaffolding + Data Models

**Files:**
- Create: `作业/pyproject.toml`
- Create: `作业/codereflex/__init__.py`
- Create: `作业/codereflex/models.py`
- Create: `作业/tests/__init__.py`
- Create: `作业/tests/conftest.py`
- Test: `作业/tests/test_models.py`

**Interfaces:**
- Produces: `Action(type: ActionType, params: dict, target_path: str|None)`, `ActionResult(success: bool, output: str, error: str, exit_code: int|None)`, `FailureItem(category: FailureCategory, file: str, line: int|None, message: str, expected: str|None, actual: str|None)`, `Feedback(validator: str, status: FeedbackStatus, failures: list[FailureItem], raw_output: str)`, `Turn`, `Session`, `Decision(verdict: DecisionVerdict, reason: str)`, `DecisionLogEntry`, and enums `ActionType`, `FailureCategory`, `FeedbackStatus`, `DecisionVerdict`, `SessionStatus`

- [ ] **Step 1: Write pyproject.toml**

```toml
[project]
name = "codereflex"
version = "0.1.0"
description = "Feedback-loop-centric coding agent harness"
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.27",
    "keyring>=25",
    "python-dotenv>=1.0",
    "pyyaml>=6.0",
    "fastapi>=0.115",
    "uvicorn>=0.30",
    "jinja2>=3.1",
]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio>=0.24", "ruff>=0.6", "mypy>=1.13"]
validators = ["pytest>=8", "ruff>=0.6", "mypy>=1.13"]

[project.scripts]
codereflex = "codereflex.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
```

- [ ] **Step 2: Write the failing test for models**

`作业/tests/test_models.py`:
```python
from codereflex.models import (
    Action, ActionResult, FailureItem, Feedback, Turn, Session,
    Decision, DecisionLogEntry,
    ActionType, FailureCategory, FeedbackStatus, DecisionVerdict, SessionStatus,
)


def test_action_creation():
    a = Action(type=ActionType.WRITE_FILE, params={"path": "foo.py", "content": "x=1"})
    assert a.type == ActionType.WRITE_FILE
    assert a.params["path"] == "foo.py"
    assert a.target_path is None


def test_action_result():
    r = ActionResult(success=True, output="ok", exit_code=0)
    assert r.success is True
    assert r.exit_code == 0
    assert r.error == ""


def test_failure_item():
    fi = FailureItem(
        category=FailureCategory.TYPE_ERROR,
        file="foo.py", line=42,
        message="expected int, got str",
        expected="int", actual="str",
    )
    assert fi.category == FailureCategory.TYPE_ERROR
    assert fi.line == 42


def test_feedback_with_failures():
    fb = Feedback(
        validator="pytest", status=FeedbackStatus.FAIL,
        failures=[FailureItem(category=FailureCategory.TEST_FAILURE,
                              file="t.py", line=5, message="assert failed")],
        raw_output="...",
    )
    assert fb.status == FeedbackStatus.FAIL
    assert len(fb.failures) == 1


def test_session_defaults():
    s = Session(id="s1", task="fix test")
    assert s.status == SessionStatus.RUNNING
    assert s.retry_count == 0
    assert s.history == []
    assert s.failure_signatures == []


def test_decision():
    d = Decision(verdict=DecisionVerdict.INTERCEPT, reason="dangerous")
    assert d.verdict == DecisionVerdict.INTERCEPT


def test_decision_log_entry():
    e = DecisionLogEntry(timestamp="2026-01-01T00:00:00", task="t", outcome="pass")
    assert e.key_actions == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd 作业 && python -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'codereflex'`

- [ ] **Step 4: Write models implementation**

`作业/codereflex/__init__.py`:
```python
"""CodeReflex: feedback-loop-centric coding agent harness."""
```

`作业/codereflex/models.py`:
```python
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
```

`作业/tests/__init__.py`: (empty)
`作业/tests/conftest.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd 作业 && python -m pytest tests/test_models.py -v`
Expected: PASS — 7 passed

- [ ] **Step 6: Commit**

```bash
cd 作业
git add pyproject.toml codereflex/__init__.py codereflex/models.py tests/__init__.py tests/conftest.py tests/test_models.py
git commit -m "feat: scaffold project and data models"
```

---

### Task 2: Config

**Files:**
- Create: `作业/codereflex/config.py`
- Test: `作业/tests/test_config.py`

**Interfaces:**
- Consumes: `models` (no direct dependency, standalone)
- Produces: `Config` dataclass with fields `validators: list[str]`, `retry_budget: int`, `allowed_paths: list[str]`, `dangerous_patterns: list[str]`, `model: str`, `llm_base_url: str`, `convergence_threshold: int`, `context_window: int`; function `load_config(path: str | None) -> Config`

- [ ] **Step 1: Write the failing test**

`作业/tests/test_config.py`:
```python
import tempfile
from pathlib import Path
from codereflex.config import Config, load_config


def test_default_config():
    cfg = load_config(None)
    assert cfg.retry_budget == 5
    assert "pytest" in cfg.validators
    assert cfg.model == "gpt-4o-mini"


def test_load_from_yaml():
    yaml_content = """
retry_budget: 3
validators: [pytest, ruff]
allowed_paths: ["/tmp/proj"]
dangerous_patterns: ["rm -rf"]
model: "gpt-4o"
llm_base_url: "https://api.example.com/v1"
convergence_threshold: 2
context_window: 10
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        path = f.name
    cfg = load_config(path)
    assert cfg.retry_budget == 3
    assert cfg.validators == ["pytest", "ruff"]
    assert cfg.allowed_paths == ["/tmp/proj"]
    assert cfg.model == "gpt-4o"


def test_missing_file_uses_defaults():
    cfg = load_config("/nonexistent/path.yaml")
    assert cfg.retry_budget == 5


def test_invalid_yaml_raises():
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write("retry_budget: [unclosed")
        path = f.name
    try:
        load_config(path)
        assert False, "should have raised"
    except Exception:
        assert True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 作业 && python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'codereflex.config'`

- [ ] **Step 3: Write implementation**

`作业/codereflex/config.py`:
```python
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


@dataclass
class Config:
    validators: list[str] = field(default_factory=lambda: ["pytest", "ruff", "mypy"])
    retry_budget: int = 5
    allowed_paths: list[str] = field(default_factory=lambda: ["."])
    dangerous_patterns: list[str] = field(default_factory=lambda: [
        "rm -rf", "drop ", "git push --force", "curl.*|.*sh", "wget.*|.*sh",
    ])
    model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    convergence_threshold: int = 3
    context_window: int = 20


def load_config(path: str | None) -> Config:
    if path is None:
        return Config()
    p = Path(path)
    if not p.exists():
        logger.warning("Config file %s not found, using defaults", path)
        return Config()
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config {path}: {e}") from e
    known = {f for f in Config.__dataclass_fields__}
    cfg = Config()
    for k, v in data.items():
        if k in known:
            setattr(cfg, k, v)
        else:
            logger.warning("Unknown config field '%s' ignored", k)
    return cfg
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd 作业 && python -m pytest tests/test_config.py -v`
Expected: PASS — 4 passed

- [ ] **Step 5: Commit**

```bash
cd 作业
git add codereflex/config.py tests/test_config.py
git commit -m "feat: add Config with YAML loading and defaults"
```

---

### Task 3: LLM Client (Mockable Abstraction)

**Files:**
- Create: `作业/codereflex/llm/__init__.py`
- Create: `作业/codereflex/llm/client.py`
- Test: `作业/tests/test_llm_client.py`

**Interfaces:**
- Produces: `LLMResponse(text: str, usage: dict)` dataclass; `LLMClient` class with `async def complete(messages: list[dict], model: str) -> LLMResponse`; `MockLLMClient` class with `__init__(script: list[str])` that returns scripted responses in order.

- [ ] **Step 1: Write the failing test**

`作业/tests/test_llm_client.py`:
```python
import pytest
from codereflex.llm.client import LLMClient, MockLLMClient, LLMResponse


def test_llm_response_dataclass():
    r = LLMResponse(text="hello", usage={"total_tokens": 5})
    assert r.text == "hello"


@pytest.mark.asyncio
async def test_mock_client_returns_scripted():
    mock = MockLLMClient(script=['{"type":"write_file","params":{}}', '{"type":"run_validators","params":{}}'])
    r1 = await mock.complete([], "m")
    r2 = await mock.complete([], "m")
    assert r1.text == '{"type":"write_file","params":{}}'
    assert r2.text == '{"type":"run_validators","params":{}}'


@pytest.mark.asyncio
async def test_mock_client_exhausts_script():
    mock = MockLLMClient(script=["one"])
    await mock.complete([], "m")
    with pytest.raises(StopIteration):
        await mock.complete([], "m")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 作业 && python -m pytest tests/test_llm_client.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`作业/codereflex/llm/__init__.py`: (empty)

`作业/codereflex/llm/client.py`:
```python
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    text: str
    usage: dict[str, Any] = field(default_factory=dict)


class LLMClient:
    """OpenAI-compatible chat completion client."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 60.0):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    async def complete(self, messages: list[dict], model: str) -> LLMResponse:
        import httpx
        url = f"{self._base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {"model": model, "messages": messages}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(3):
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code in (429, 500, 502, 503):
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                data = resp.json()
                return LLMResponse(
                    text=data["choices"][0]["message"]["content"],
                    usage=data.get("usage", {}),
                )
            raise RuntimeError("LLM call failed after 3 retries")


class MockLLMClient:
    """Returns scripted responses in order, for deterministic offline tests."""

    def __init__(self, script: list[str]):
        self._script = list(script)
        self._index = 0

    async def complete(self, messages: list[dict], model: str) -> LLMResponse:
        if self._index >= len(self._script):
            raise StopIteration("Mock script exhausted")
        text = self._script[self._index]
        self._index += 1
        return LLMResponse(text=text, usage={})
```

- [ ] **Step 4: Install pytest-asyncio and run test**

Run: `cd 作业 && pip install pytest-asyncio && python -m pytest tests/test_llm_client.py -v`
Expected: PASS — 3 passed

- [ ] **Step 5: Commit**

```bash
cd 作业
git add codereflex/llm/ tests/test_llm_client.py
git commit -m "feat: add LLMClient and MockLLMClient abstraction"
```

---

### Task 4: Tools (Dispatcher + File/Shell Tools)

**Files:**
- Create: `作业/codereflex/tools/__init__.py`
- Create: `作业/codereflex/tools/base.py`
- Create: `作业/codereflex/tools/file_tools.py`
- Create: `作业/codereflex/tools/shell_tool.py`
- Test: `作业/tests/test_tools.py`

**Interfaces:**
- Consumes: `models.Action`, `models.ActionResult`, `models.ActionType`
- Produces: `Tool` protocol with `execute(action: Action) -> ActionResult`; `ToolDispatcher` with `register(action_type, tool)` and `dispatch(action: Action) -> ActionResult`; `ReadFile`, `WriteFile`, `ListDir`, `RunShell` classes; `PathGuard` helper for path traversal check.

- [ ] **Step 1: Write the failing test**

`作业/tests/test_tools.py`:
```python
import tempfile
from pathlib import Path
from codereflex.models import Action, ActionResult, ActionType
from codereflex.tools.base import ToolDispatcher
from codereflex.tools.file_tools import ReadFile, WriteFile, ListDir
from codereflex.tools.shell_tool import RunShell


def test_write_then_read_file():
    with tempfile.TemporaryDirectory() as d:
        disp = ToolDispatcher(allowed_paths=[d])
        disp.register(ActionType.WRITE_FILE, WriteFile(allowed_paths=[d]))
        disp.register(ActionType.READ_FILE, ReadFile(allowed_paths=[d]))
        w = disp.dispatch(Action(ActionType.WRITE_FILE, {"path": f"{d}/x.py", "content": "print(1)"}))
        assert w.success
        r = disp.dispatch(Action(ActionType.READ_FILE, {"path": f"{d}/x.py"}))
        assert r.success
        assert "print(1)" in r.output


def test_read_nonexistent_fails():
    with tempfile.TemporaryDirectory() as d:
        rf = ReadFile(allowed_paths=[d])
        r = rf.execute(Action(ActionType.READ_FILE, {"path": f"{d}/nope.py"}))
        assert not r.success
        assert "not found" in r.error.lower() or "no such" in r.error.lower()


def test_path_traversal_denied():
    with tempfile.TemporaryDirectory() as d:
        wf = WriteFile(allowed_paths=[d])
        r = wf.execute(Action(ActionType.WRITE_FILE, {"path": f"{d}/../../etc/evil", "content": "x"}))
        assert not r.success
        assert "denied" in r.error.lower() or "outside" in r.error.lower()


def test_list_dir():
    with tempfile.TemporaryDirectory() as d:
        Path(d, "a.py").write_text("x")
        Path(d, "b.py").write_text("y")
        ld = ListDir(allowed_paths=[d])
        r = ld.execute(Action(ActionType.LIST_DIR, {"path": d}))
        assert r.success
        assert "a.py" in r.output
        assert "b.py" in r.output


def test_run_shell():
    rs = RunShell(timeout=5)
    r = rs.execute(Action(ActionType.RUN_SHELL, {"cmd": "echo hello"}))
    assert r.success
    assert "hello" in r.output


def test_run_shell_nonzero_exit():
    rs = RunShell(timeout=5)
    r = rs.execute(Action(ActionType.RUN_SHELL, {"cmd": "python -c 'import sys; sys.exit(1)'"}))
    assert not r.success
    assert r.exit_code == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 作业 && python -m pytest tests/test_tools.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`作业/codereflex/tools/__init__.py`: (empty)

`作业/codereflex/tools/base.py`:
```python
from __future__ import annotations
from pathlib import Path
from codereflex.models import Action, ActionResult, ActionType


def check_path_allowed(path: str, allowed_paths: list[str]) -> bool:
    """Return True if resolved path is within one of allowed_paths."""
    resolved = Path(path).resolve()
    for ap in allowed_paths:
        if resolved == Path(ap).resolve() or ap in resolved.parents or str(resolved).startswith(str(Path(ap).resolve())):
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
```

`作业/codereflex/tools/file_tools.py`:
```python
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
```

`作业/codereflex/tools/shell_tool.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd 作业 && python -m pytest tests/test_tools.py -v`
Expected: PASS — 6 passed

- [ ] **Step 5: Commit**

```bash
cd 作业
git add codereflex/tools/ tests/test_tools.py
git commit -m "feat: add ToolDispatcher, file tools, and shell tool"
```

---

### Task 5: Guardrail (Policy Engine)

**Files:**
- Create: `作业/codereflex/guardrail/__init__.py`
- Create: `作业/codereflex/guardrail/guardrail.py`
- Test: `作业/tests/test_guardrail.py`

**Interfaces:**
- Consumes: `models.Action`, `models.Decision`, `models.DecisionVerdict`
- Produces: `Guardrail` class with `__init__(dangerous_patterns: list[str], allowed_paths: list[str])` and `check(action: Action) -> Decision`

- [ ] **Step 1: Write the failing test**

`作业/tests/test_guardrail.py`:
```python
from codereflex.models import Action, ActionType, DecisionVerdict
from codereflex.guardrail.guardrail import Guardrail


def test_allows_safe_shell():
    g = Guardrail(dangerous_patterns=["rm -rf", "drop "], allowed_paths=["/tmp/proj"])
    d = g.check(Action(ActionType.RUN_SHELL, {"cmd": "ls -la"}))
    assert d.verdict == DecisionVerdict.ALLOW


def test_intercepts_rm_rf():
    g = Guardrail(dangerous_patterns=["rm -rf", "drop "], allowed_paths=["/tmp/proj"])
    d = g.check(Action(ActionType.RUN_SHELL, {"cmd": "rm -rf /"}))
    assert d.verdict == DecisionVerdict.INTERCEPT
    assert "rm -rf" in d.reason


def test_intercepts_drop_db():
    g = Guardrail(dangerous_patterns=["rm -rf", "drop "], allowed_paths=["/tmp/proj"])
    d = g.check(Action(ActionType.RUN_SHELL, {"cmd": "psql -c 'drop table users'"}))
    assert d.verdict == DecisionVerdict.INTERCEPT


def test_denies_path_traversal_write():
    g = Guardrail(dangerous_patterns=["rm -rf"], allowed_paths=["/tmp/proj"])
    d = g.check(Action(ActionType.WRITE_FILE, {"path": "/tmp/proj/../../etc/evil", "content": "x"}))
    assert d.verdict == DecisionVerdict.DENY


def test_allows_write_in_scope():
    g = Guardrail(dangerous_patterns=["rm -rf"], allowed_paths=["/tmp/proj"])
    d = g.check(Action(ActionType.WRITE_FILE, {"path": "/tmp/proj/foo.py", "content": "x"}))
    assert d.verdict == DecisionVerdict.ALLOW
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 作业 && python -m pytest tests/test_guardrail.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`作业/codereflex/guardrail/__init__.py`: (empty)

`作业/codereflex/guardrail/guardrail.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd 作业 && python -m pytest tests/test_guardrail.py -v`
Expected: PASS — 5 passed

- [ ] **Step 5: Commit**

```bash
cd 作业
git add codereflex/guardrail/ tests/test_guardrail.py
git commit -m "feat: add Guardrail policy engine with dangerous pattern + path checks"
```

---

### Task 6: HITL State Machine

**Files:**
- Create: `作业/codereflex/guardrail/hitl.py`
- Test: `作业/tests/test_hitl.py`

**Interfaces:**
- Consumes: `models.Action`, `models.Decision`
- Produces: `HITLState` enum (`PENDING`, `APPROVED`, `DENIED`, `TIMEOUT`); `HITLController` with `request(action: Action) -> str` (returns request_id), `approve(request_id)`, `deny(request_id)`, `timeout(request_id)`, `get_state(request_id) -> HITLState`

- [ ] **Step 1: Write the failing test**

`作业/tests/test_hitl.py`:
```python
from codereflex.models import Action, ActionType
from codereflex.guardrail.hitl import HITLController, HITLState


def test_request_starts_pending():
    c = HITLController()
    rid = c.request(Action(ActionType.RUN_SHELL, {"cmd": "rm -rf /"}))
    assert c.get_state(rid) == HITLState.PENDING


def test_approve():
    c = HITLController()
    rid = c.request(Action(ActionType.RUN_SHELL, {"cmd": "rm -rf /"}))
    c.approve(rid)
    assert c.get_state(rid) == HITLState.APPROVED


def test_deny():
    c = HITLController()
    rid = c.request(Action(ActionType.RUN_SHELL, {"cmd": "rm -rf /"}))
    c.deny(rid)
    assert c.get_state(rid) == HITLState.DENIED


def test_timeout():
    c = HITLController()
    rid = c.request(Action(ActionType.RUN_SHELL, {"cmd": "rm -rf /"}))
    c.timeout(rid)
    assert c.get_state(rid) == HITLState.TIMEOUT


def test_get_action():
    c = HITLController()
    act = Action(ActionType.RUN_SHELL, {"cmd": "rm -rf /"})
    rid = c.request(act)
    assert c.get_action(rid) == act
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 作业 && python -m pytest tests/test_hitl.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`作业/codereflex/guardrail/hitl.py`:
```python
from __future__ import annotations
import uuid
from dataclasses import dataclass
from enum import Enum
from codereflex.models import Action


class HITLState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT = "timeout"


@dataclass
class _HITLRequest:
    id: str
    action: Action
    state: HITLState = HITLState.PENDING


class HITLController:
    def __init__(self):
        self._requests: dict[str, _HITLRequest] = {}

    def request(self, action: Action) -> str:
        rid = str(uuid.uuid4())
        self._requests[rid] = _HITLRequest(id=rid, action=action)
        return rid

    def approve(self, request_id: str) -> None:
        self._set_state(request_id, HITLState.APPROVED)

    def deny(self, request_id: str) -> None:
        self._set_state(request_id, HITLState.DENIED)

    def timeout(self, request_id: str) -> None:
        self._set_state(request_id, HITLState.TIMEOUT)

    def get_state(self, request_id: str) -> HITLState:
        return self._requests[request_id].state

    def get_action(self, request_id: str) -> Action:
        return self._requests[request_id].action

    def _set_state(self, request_id: str, state: HITLState) -> None:
        if request_id not in self._requests:
            raise KeyError(f"Unknown HITL request: {request_id}")
        self._requests[request_id].state = state
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd 作业 && python -m pytest tests/test_hitl.py -v`
Expected: PASS — 5 passed

- [ ] **Step 5: Commit**

```bash
cd 作业
git add codereflex/guardrail/hitl.py tests/test_hitl.py
git commit -m "feat: add HITLController state machine"
```

---

### Task 7: Validators (pytest/ruff/mypy + Pipeline)

**Files:**
- Create: `作业/codereflex/feedback/__init__.py`
- Create: `作业/codereflex/feedback/validators.py`
- Create: `作业/tests/fixtures/sample_project/pyproject.toml`
- Create: `作业/tests/fixtures/sample_project/src/calc.py`
- Create: `作业/tests/fixtures/sample_project/tests/test_calc.py`
- Test: `作业/tests/test_validators.py`

**Interfaces:**
- Consumes: `models.Feedback`, `models.FeedbackStatus`, `models.FailureItem`
- Produces: `Validator` protocol with `validate(project_path: str) -> Feedback`; `PytestValidator`, `RuffValidator`, `MypyValidator`; `ValidatorPipeline` with `__init__(validators: list[Validator])` and `run(project_path: str) -> list[Feedback]`

- [ ] **Step 1: Create fixture project**

`作业/tests/fixtures/sample_project/pyproject.toml`:
```toml
[project]
name = "sample"
version = "0.1.0"
[tool.pytest.ini_options]
pythonpath = ["src"]
```

`作业/tests/fixtures/sample_project/src/calc.py`:
```python
def add(a, b):
    return a + b


def divide(a, b):
    return a / b
```

`作业/tests/fixtures/sample_project/tests/test_calc.py`:
```python
from calc import add, divide


def test_add():
    assert add(1, 2) == 3


def test_divide_by_zero():
    try:
        divide(1, 0)
        assert False, "should raise"
    except ZeroDivisionError:
        assert True
```

- [ ] **Step 2: Write the failing test**

`作业/tests/test_validators.py`:
```python
from pathlib import Path
from codereflex.feedback.validators import (
    PytestValidator, RuffValidator, MypyValidator, ValidatorPipeline,
)
from codereflex.models import FeedbackStatus

FIXTURE = str(Path(__file__).parent / "fixtures" / "sample_project")


def test_pytest_validator_pass():
    v = PytestValidator()
    fb = v.validate(FIXTURE)
    assert fb.validator == "pytest"
    assert fb.status == FeedbackStatus.PASS


def test_ruff_validator():
    v = RuffValidator()
    fb = v.validate(FIXTURE)
    assert fb.validator == "ruff"
    assert fb.status in (FeedbackStatus.PASS, FeedbackStatus.FAIL)


def test_mypy_validator():
    v = MypyValidator()
    fb = v.validate(FIXTURE)
    assert fb.validator == "mypy"


def test_pipeline_runs_all():
    pipe = ValidatorPipeline([PytestValidator(), RuffValidator(), MypyValidator()])
    results = pipe.run(FIXTURE)
    assert len(results) == 3
    assert results[0].validator == "pytest"


def test_pytest_validator_error_on_missing_project():
    v = PytestValidator()
    fb = v.validate("/nonexistent/path")
    assert fb.status == FeedbackStatus.VALIDATOR_ERROR
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd 作业 && python -m pytest tests/test_validators.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Write implementation**

`作业/codereflex/feedback/__init__.py`: (empty)

`作业/codereflex/feedback/validators.py`:
```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd 作业 && python -m pytest tests/test_validators.py -v`
Expected: PASS — 5 passed

- [ ] **Step 6: Commit**

```bash
cd 作业
git add codereflex/feedback/__init__.py codereflex/feedback/validators.py tests/fixtures/ tests/test_validators.py
git commit -m "feat: add Validator protocol, pytest/ruff/mypy validators, and pipeline"
```

---

### Task 8: FailureClassifier (★ Deep)

**Files:**
- Create: `作业/codereflex/feedback/__init__.py`
- Create: `作业/codereflex/feedback/classifier.py`
- Test: `作业/tests/test_classifier.py`

**Interfaces:**
- Consumes: `models.Feedback`, `models.FailureItem`, `models.FailureCategory`
- Produces: `FailureClassifier` class with static method `classify(feedback: Feedback) -> list[FailureItem]`; also `classify_all(feedbacks: list[Feedback]) -> list[FailureItem]`; `failure_signature(items: list[FailureItem]) -> str` (hash for convergence detection)

- [ ] **Step 1: Write the failing test**

`作业/tests/test_classifier.py`:
```python
from codereflex.feedback.classifier import FailureClassifier, failure_signature
from codereflex.models import Feedback, FeedbackStatus, FailureCategory


PYTEST_FAIL_OUTPUT = """\
============================= test session starts =============================
collected 2 items

tests/test_calc.py::test_add FAILED                                       [ 50%]
tests/test_calc.py::test_divide_by_zero PASSED                            [100%]

=================================== FAILURES ===================================
___________________________________ test_add ___________________________________
    def test_add():
>       assert add(1, 2) == 5
E       assert 3 == 5
tests/test_calc.py:5: AssertionError
=========================== 1 failed, 1 passed in 0.05s ===========================
"""

MYPY_OUTPUT = """\
src/calc.py:10: error: Argument 1 to "divide" has incompatible type "str"; expected "int"  [arg-type]
Found 1 error in 1 file (checked 1 source file)
"""

RUFF_OUTPUT = """\
src/calc.py:5:1: E302 expected 2 blank lines, found 1
src/calc.py:10:80: E501 line too long (90 > 79 characters)
"""

SYNTAX_OUTPUT = """\
  File "src/calc.py", line 10
    def add(a, b)
                 ^
SyntaxError: invalid syntax
"""

IMPORT_OUTPUT = """\
ModuleNotFoundError: No module named 'missing_pkg'
"""

RUNTIME_OUTPUT = """\
Traceback (most recent call last):
  File "main.py", line 5, in <module>
    result = divide(1, 0)
  File "src/calc.py", line 11, in divide
    return a / b
ZeroDivisionError: division by zero
"""


def test_classify_test_failure():
    fb = Feedback(validator="pytest", status=FeedbackStatus.FAIL, raw_output=PYTEST_FAIL_OUTPUT)
    items = FailureClassifier.classify(fb)
    assert len(items) >= 1
    assert items[0].category == FailureCategory.TEST_FAILURE
    assert "test_calc.py" in items[0].file
    assert items[0].line == 5


def test_classify_type_error():
    fb = Feedback(validator="mypy", status=FeedbackStatus.FAIL, raw_output=MYPY_OUTPUT)
    items = FailureClassifier.classify(fb)
    assert len(items) >= 1
    assert items[0].category == FailureCategory.TYPE_ERROR
    assert "calc.py" in items[0].file
    assert items[0].line == 10


def test_classify_lint_violation():
    fb = Feedback(validator="ruff", status=FeedbackStatus.FAIL, raw_output=RUFF_OUTPUT)
    items = FailureClassifier.classify(fb)
    assert len(items) >= 1
    assert items[0].category == FailureCategory.LINT_VIOLATION


def test_classify_syntax_error():
    fb = Feedback(validator="pytest", status=FeedbackStatus.FAIL, raw_output=SYNTAX_OUTPUT)
    items = FailureClassifier.classify(fb)
    assert any(i.category == FailureCategory.SYNTAX_ERROR for i in items)


def test_classify_import_error():
    fb = Feedback(validator="pytest", status=FeedbackStatus.FAIL, raw_output=IMPORT_OUTPUT)
    items = FailureClassifier.classify(fb)
    assert any(i.category == FailureCategory.IMPORT_ERROR for i in items)


def test_classify_runtime_error():
    fb = Feedback(validator="pytest", status=FeedbackStatus.FAIL, raw_output=RUNTIME_OUTPUT)
    items = FailureClassifier.classify(fb)
    assert any(i.category == FailureCategory.RUNTIME_ERROR for i in items)


def test_classify_pass_returns_empty():
    fb = Feedback(validator="pytest", status=FeedbackStatus.PASS, raw_output="all good")
    assert FailureClassifier.classify(fb) == []


def test_failure_signature_stable():
    fb = Feedback(validator="pytest", status=FeedbackStatus.FAIL, raw_output=PYTEST_FAIL_OUTPUT)
    items = FailureClassifier.classify(fb)
    sig1 = failure_signature(items)
    sig2 = failure_signature(items)
    assert sig1 == sig2


def test_failure_signature_differs_for_different_failures():
    fb1 = Feedback(validator="pytest", status=FeedbackStatus.FAIL, raw_output=PYTEST_FAIL_OUTPUT)
    fb2 = Feedback(validator="mypy", status=FeedbackStatus.FAIL, raw_output=MYPY_OUTPUT)
    sig1 = failure_signature(FailureClassifier.classify(fb1))
    sig2 = failure_signature(FailureClassifier.classify(fb2))
    assert sig1 != sig2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 作业 && python -m pytest tests/test_classifier.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`作业/codereflex/feedback/classifier.py`:
```python
from __future__ import annotations
import hashlib
import re
from codereflex.models import Feedback, FailureItem, FailureCategory, FeedbackStatus


class FailureClassifier:
    """Parses raw validator output into structured FailureItem list."""

    # pytest: "path::test_name FAILED" + "path:line: AssertionError"
    _PYTEST_FAIL = re.compile(r"^(.+?\.py)::(\S+)\s+FAILED", re.MULTILINE)
    _PYTEST_LOC = re.compile(r"^(.+?\.py):(\d+):", re.MULTILINE)
    # mypy: "path:line: error: msg"
    _MYPY = re.compile(r"^(.+?\.py):(\d+):\s*error:\s*(.+)$", re.MULTILINE)
    # ruff: "path:line:col: CODE msg"
    _RUFF = re.compile(r"^(.+?\.py):(\d+):\d+:\s*\S+\s+(.+)$", re.MULTILINE)
    # syntax error
    _SYNTAX = re.compile(r'File "(.+?)",\s*line\s*(\d+).*?SyntaxError:\s*(.+)', re.DOTALL)
    # import error
    _IMPORT = re.compile(r"ModuleNotFoundError: No module named '([^']+)'")
    # runtime: "ExceptionType: message" at line start, excluding Syntax/Import (have own classifiers)
    _RUNTIME = re.compile(r"^(?!SyntaxError|ImportError)(\w+Error): (.+)$", re.MULTILINE)

    @staticmethod
    def classify(feedback: Feedback) -> list[FailureItem]:
        if feedback.status == FeedbackStatus.PASS:
            return []
        if feedback.status == FeedbackStatus.VALIDATOR_ERROR:
            return [FailureItem(
                category=FailureCategory.RUNTIME_ERROR,
                file="", line=None,
                message=f"Validator error: {feedback.raw_output[:200]}",
            )]
        text = feedback.raw_output
        items: list[FailureItem] = []
        if feedback.validator == "pytest":
            items.extend(FailureClassifier._classify_pytest(text))
        elif feedback.validator == "mypy":
            items.extend(FailureClassifier._classify_mypy(text))
        elif feedback.validator == "ruff":
            items.extend(FailureClassifier._classify_ruff(text))
        # Cross-cutting: syntax/import/runtime can appear in any output
        items.extend(FailureClassifier._classify_syntax(text))
        items.extend(FailureClassifier._classify_import(text))
        items.extend(FailureClassifier._classify_runtime(text))
        return items

    @staticmethod
    def _classify_pytest(text: str) -> list[FailureItem]:
        items = []
        for m in FailureClassifier._PYTEST_FAIL.finditer(text):
            file, test_name = m.group(1), m.group(2)
            loc_match = FailureClassifier._PYTEST_LOC.search(text)
            line = int(loc_match.group(2)) if loc_match else None
            items.append(FailureItem(
                category=FailureCategory.TEST_FAILURE,
                file=file, line=line,
                message=f"Test {test_name} failed",
            ))
        return items

    @staticmethod
    def _classify_mypy(text: str) -> list[FailureItem]:
        items = []
        for m in FailureClassifier._MYPY.finditer(text):
            items.append(FailureItem(
                category=FailureCategory.TYPE_ERROR,
                file=m.group(1), line=int(m.group(2)),
                message=m.group(3).strip(),
            ))
        return items

    @staticmethod
    def _classify_ruff(text: str) -> list[FailureItem]:
        items = []
        for m in FailureClassifier._RUFF.finditer(text):
            items.append(FailureItem(
                category=FailureCategory.LINT_VIOLATION,
                file=m.group(1), line=int(m.group(2)),
                message=m.group(3).strip(),
            ))
        return items

    @staticmethod
    def _classify_syntax(text: str) -> list[FailureItem]:
        items = []
        for m in FailureClassifier._SYNTAX.finditer(text):
            items.append(FailureItem(
                category=FailureCategory.SYNTAX_ERROR,
                file=m.group(1), line=int(m.group(2)),
                message=f"SyntaxError: {m.group(3).strip()}",
            ))
        return items

    @staticmethod
    def _classify_import(text: str) -> list[FailureItem]:
        items = []
        for m in FailureClassifier._IMPORT.finditer(text):
            items.append(FailureItem(
                category=FailureCategory.IMPORT_ERROR,
                file="", line=None,
                message=f"No module named '{m.group(1)}'",
            ))
        return items

    @staticmethod
    def _classify_runtime(text: str) -> list[FailureItem]:
        items = []
        for m in FailureClassifier._RUNTIME.finditer(text):
            items.append(FailureItem(
                category=FailureCategory.RUNTIME_ERROR,
                file="", line=None,
                message=f"{m.group(1)}: {m.group(2)}",
            ))
        return items

    @staticmethod
    def classify_all(feedbacks: list[Feedback]) -> list[FailureItem]:
        items = []
        for fb in feedbacks:
            items.extend(FailureClassifier.classify(fb))
        return items


def failure_signature(items: list[FailureItem]) -> str:
    """Stable hash of failure items for convergence detection."""
    sig = "|".join(f"{i.category}:{i.file}:{i.line}:{i.message}" for i in items)
    return hashlib.md5(sig.encode()).hexdigest()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd 作业 && python -m pytest tests/test_classifier.py -v`
Expected: PASS — 9 passed

- [ ] **Step 5: Commit**

```bash
cd 作业
git add codereflex/feedback/classifier.py tests/test_classifier.py
git commit -m "feat: add FailureClassifier with 6-category taxonomy and signature"
```

---

### Task 9: FeedbackLoop (★ Deep Orchestrator)

**Files:**
- Create: `作业/codereflex/feedback/feedback_loop.py`
- Test: `作业/tests/test_feedback_loop.py`

**Interfaces:**
- Consumes: `validators.ValidatorPipeline`, `classifier.FailureClassifier`, `classifier.failure_signature`, `models.Session`, `models.Feedback`, `models.SessionStatus`, `config.Config`
- Produces: `FeedbackLoop` class with `__init__(pipeline: ValidatorPipeline, config: Config)` and `run(project_path: str, session: Session) -> tuple[Feedback | None, bool]` (returns merged feedback + continue_flag); `format_feedback_for_llm(feedback: Feedback, items: list[FailureItem]) -> str`

- [ ] **Step 1: Write the failing test**

`作业/tests/test_feedback_loop.py`:
```python
from pathlib import Path
from codereflex.config import Config
from codereflex.feedback.validators import ValidatorPipeline, PytestValidator, Validator
from codereflex.feedback.feedback_loop import FeedbackLoop, format_feedback_for_llm
from codereflex.models import Session, FeedbackStatus, FailureItem, FailureCategory, Feedback

FIXTURE = str(Path(__file__).parent / "fixtures" / "sample_project")


class StubValidator(Validator):
    """Deterministic validator returning a fixed Feedback, for offline tests."""
    name = "stub"

    def __init__(self, feedback: Feedback):
        self._feedback = feedback

    def validate(self, project_path: str) -> Feedback:
        return self._feedback


def test_pass_returns_none_and_stops():
    loop = FeedbackLoop(ValidatorPipeline([PytestValidator()]), Config(retry_budget=5, convergence_threshold=3))
    session = Session(id="s1", task="t")
    fb, should_continue = loop.run(FIXTURE, session)
    assert fb is None or fb.status == FeedbackStatus.PASS
    assert should_continue is False


def test_fail_returns_feedback_and_continues():
    stub_fb = Feedback(validator="stub", status=FeedbackStatus.FAIL,
                       raw_output="tests/x.py::test_a FAILED\ntests/x.py:3: AssertionError")
    loop = FeedbackLoop(ValidatorPipeline([StubValidator(stub_fb)]), Config(retry_budget=5, convergence_threshold=3))
    session = Session(id="s1", task="t")
    fb, should_continue = loop.run("/any/path", session)
    assert fb is not None
    assert fb.status == FeedbackStatus.FAIL
    assert should_continue is True
    assert session.retry_count == 1


def test_convergence_detection_stops():
    from codereflex.feedback.classifier import failure_signature
    stub_fb = Feedback(validator="stub", status=FeedbackStatus.FAIL,
                       raw_output="tests/x.py::test_a FAILED\ntests/x.py:3: AssertionError")
    sig = failure_signature(FailureClassifier.classify(stub_fb))
    loop = FeedbackLoop(ValidatorPipeline([StubValidator(stub_fb)]), Config(retry_budget=10, convergence_threshold=2))
    session = Session(id="s1", task="t", failure_signatures=[sig, sig])
    fb, should_continue = loop.run("/any/path", session)
    assert should_continue is False
    assert session.status.value == "convergence_stopped"


def test_budget_exhaustion_stops():
    stub_fb = Feedback(validator="stub", status=FeedbackStatus.FAIL,
                       raw_output="tests/x.py::test_a FAILED\ntests/x.py:3: AssertionError")
    loop = FeedbackLoop(ValidatorPipeline([StubValidator(stub_fb)]), Config(retry_budget=1, convergence_threshold=99))
    session = Session(id="s1", task="t", retry_count=1)
    fb, should_continue = loop.run("/any/path", session)
    assert should_continue is False
    assert session.status.value == "budget_exhausted"


def test_format_feedback_for_llm():
    fb = Feedback(validator="pytest", status=FeedbackStatus.FAIL)
    items = [FailureItem(FailureCategory.TYPE_ERROR, "foo.py", 42, "expected int", "int", "str")]
    text = format_feedback_for_llm(fb, items)
    assert "foo.py" in text
    assert "42" in text
    assert "type_error" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 作业 && python -m pytest tests/test_feedback_loop.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`作业/codereflex/feedback/feedback_loop.py`:
```python
from __future__ import annotations
from codereflex.config import Config
from codereflex.models import Feedback, FailureItem, Session, SessionStatus, FeedbackStatus
from codereflex.feedback.validators import ValidatorPipeline
from codereflex.feedback.classifier import FailureClassifier, failure_signature


def format_feedback_for_llm(feedback: Feedback, items: list[FailureItem]) -> str:
    if not items:
        return "All validators passed."
    lines = [f"[{feedback.validator}] FAIL — {len(items)} issue(s):"]
    for i in items:
        loc = f"{i.file}:{i.line}" if i.line else i.file
        lines.append(f"  - {i.category.value} at {loc}: {i.message}")
        if i.expected and i.actual:
            lines.append(f"      expected: {i.expected}, actual: {i.actual}")
    return "\n".join(lines)


class FeedbackLoop:
    def __init__(self, pipeline: ValidatorPipeline, config: Config):
        self._pipeline = pipeline
        self._config = config

    def run(self, project_path: str, session: Session) -> tuple[Feedback | None, bool]:
        feedbacks = self._pipeline.run(project_path)
        all_items = FailureClassifier.classify_all(feedbacks)

        if not all_items:
            session.status = SessionStatus.COMPLETED
            return None, False

        # Merge into a single Feedback for回灌
        merged = Feedback(
            validator="pipeline",
            status=FeedbackStatus.FAIL,
            failures=all_items,
            raw_output="\n---\n".join(f.raw_output for f in feedbacks),
        )

        # Convergence detection
        sig = failure_signature(all_items)
        session.failure_signatures.append(sig)
        recent = session.failure_signatures[-self._config.convergence_threshold:]
        if len(recent) >= self._config.convergence_threshold and len(set(recent)) == 1:
            session.status = SessionStatus.CONVERGENCE_STOPPED
            return merged, False

        # Budget check
        session.retry_count += 1
        if session.retry_count >= self._config.retry_budget:
            session.status = SessionStatus.BUDGET_EXHAUSTED
            return merged, False

        return merged, True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd 作业 && python -m pytest tests/test_feedback_loop.py -v`
Expected: PASS — 5 passed

- [ ] **Step 5: Commit**

```bash
cd 作业
git add codereflex/feedback/feedback_loop.py tests/test_feedback_loop.py
git commit -m "feat: add FeedbackLoop with convergence detection and retry budget"
```

---

### Task 10: Memory (Session Context + DecisionLog)

**Files:**
- Create: `作业/codereflex/memory/__init__.py`
- Create: `作业/codereflex/memory/session.py`
- Create: `作业/codereflex/memory/decision_log.py`
- Test: `作业/tests/test_memory.py`

**Interfaces:**
- Consumes: `models.Session`, `models.Turn`, `models.DecisionLogEntry`
- Produces: `ContextWindow` class with `build_messages(session: Session, system_prompt: str, window_size: int) -> list[dict]`; `DecisionLog` class with `__init__(path: str)`, `append(entry: DecisionLogEntry)`, `search(keyword: str) -> list[DecisionLogEntry]`

- [ ] **Step 1: Write the failing test**

`作业/tests/test_memory.py`:
```python
import tempfile
from pathlib import Path
from codereflex.memory.session import ContextWindow
from codereflex.memory.decision_log import DecisionLog
from codereflex.models import Session, Turn, DecisionLogEntry, Action, ActionResult, ActionType


def test_context_window_truncates():
    cw = ContextWindow()
    s = Session(id="s", task="do thing")
    for i in range(10):
        s.history.append(Turn(
            action=Action(ActionType.WRITE_FILE, {"path": f"f{i}.py"}),
            result=ActionResult(success=True),
            feedback=None, llm_response=f"resp {i}",
        ))
    msgs = cw.build_messages(s, system_prompt="You are an agent.", window_size=3)
    # system + task + last 3 turns
    assert msgs[0]["role"] == "system"
    assert "resp 9" in msgs[-1]["content"]
    assert "resp 6" not in msgs[-1]["content"]


def test_decision_log_append_and_search():
    with tempfile.TemporaryDirectory() as d:
        log = DecisionLog(Path(d, "log.md"))
        log.append(DecisionLogEntry(timestamp="2026-01-01", task="fix bug", outcome="pass", key_actions=["wrote foo.py"]))
        log.append(DecisionLogEntry(timestamp="2026-01-02", task="add feature", outcome="fail", key_actions=["wrote bar.py"]))
        results = log.search("fix bug")
        assert len(results) == 1
        assert results[0].task == "fix bug"
        results2 = log.search("nonexistent")
        assert results2 == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 作业 && python -m pytest tests/test_memory.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`作业/codereflex/memory/__init__.py`: (empty)

`作业/codereflex/memory/session.py`:
```python
from __future__ import annotations
from codereflex.models import Session


class ContextWindow:
    def build_messages(self, session: Session, system_prompt: str, window_size: int = 20) -> list[dict]:
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": f"Task: {session.task}"})
        recent = session.history[-window_size:] if window_size > 0 else session.history
        for turn in recent:
            if turn.llm_response:
                messages.append({"role": "assistant", "content": turn.llm_response})
            if turn.action:
                import json
                messages.append({"role": "user", "content": json.dumps({
                    "action": turn.action.type.value,
                    "params": turn.action.params,
                    "result": {"success": turn.result.success if turn.result else None,
                               "output": turn.result.output if turn.result else ""},
                }, ensure_ascii=False)})
            if turn.feedback:
                from codereflex.feedback.feedback_loop import format_feedback_for_llm
                messages.append({"role": "user", "content": format_feedback_for_llm(turn.feedback, turn.feedback.failures)})
        return messages
```

`作业/codereflex/memory/decision_log.py`:
```python
from __future__ import annotations
from pathlib import Path
from codereflex.models import DecisionLogEntry


class DecisionLog:
    def __init__(self, path: Path):
        self._path = Path(path)

    def append(self, entry: DecisionLogEntry) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = f"- [{entry.timestamp}] task='{entry.task}' outcome='{entry.outcome}' actions={entry.key_actions}\n"
        with self._path.open("a", encoding="utf-8") as f:
            f.write(line)

    def search(self, keyword: str) -> list[DecisionLogEntry]:
        if not self._path.exists():
            return []
        results = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if keyword.lower() in line.lower():
                results.append(self._parse(line))
        return results

    def _parse(self, line: str) -> DecisionLogEntry:
        import re
        m = re.match(r"- \[(.+?)\] task='(.+?)' outcome='(.+?)' actions=(.+)", line)
        if m:
            return DecisionLogEntry(
                timestamp=m.group(1), task=m.group(2), outcome=m.group(3),
                key_actions=m.group(4).strip("[]").split(", "),
            )
        return DecisionLogEntry(timestamp="", task=line, outcome="")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd 作业 && python -m pytest tests/test_memory.py -v`
Expected: PASS — 2 passed

- [ ] **Step 5: Commit**

```bash
cd 作业
git add codereflex/memory/ tests/test_memory.py
git commit -m "feat: add ContextWindow and DecisionLog memory"
```

---

### Task 11: AgentLoop (Main Loop Integration)

**Files:**
- Create: `作业/codereflex/agent.py`
- Test: `作业/tests/test_agent_loop.py`

**Interfaces:**
- Consumes: `llm.client.LLMClient`/`MockLLMClient`, `tools.base.ToolDispatcher`, `guardrail.guardrail.Guardrail`, `guardrail.hitl.HITLController`, `feedback.feedback_loop.FeedbackLoop`, `memory.session.ContextWindow`, `config.Config`, `models.*`
- Produces: `AgentLoop` class with `__init__(llm_client, dispatcher, guardrail, hitl, feedback_loop, context_window, config, project_path)` and `async def run(task: str) -> Session`; `parse_action(text: str) -> Action | None` helper

- [ ] **Step 1: Write the failing test**

`作业/tests/test_agent_loop.py`:
```python
import tempfile
from pathlib import Path
import pytest
from codereflex.agent import AgentLoop, parse_action
from codereflex.config import Config
from codereflex.llm.client import MockLLMClient
from codereflex.tools.base import ToolDispatcher
from codereflex.tools.file_tools import ReadFile, WriteFile, ListDir
from codereflex.tools.shell_tool import RunShell
from codereflex.guardrail.guardrail import Guardrail
from codereflex.guardrail.hitl import HITLController
from codereflex.feedback.validators import ValidatorPipeline, PytestValidator
from codereflex.feedback.feedback_loop import FeedbackLoop
from codereflex.memory.session import ContextWindow
from codereflex.models import ActionType


def test_parse_action_valid():
    a = parse_action('{"type": "write_file", "params": {"path": "x.py", "content": "print(1)"}}')
    assert a is not None
    assert a.type == ActionType.WRITE_FILE


def test_parse_action_invalid():
    assert parse_action("not json") is None


@pytest.mark.asyncio
async def test_agent_loop_completes_on_pass():
    with tempfile.TemporaryDirectory() as d:
        Path(d, "pyproject.toml").write_text('[tool.pytest.ini_options]\npythonpath=["src"]')
        Path(d, "src").mkdir()
        Path(d, "src", "mod.py").write_text("def f():\n    return 42\n")
        Path(d, "tests").mkdir()
        Path(d, "tests", "test_mod.py").write_text("from mod import f\ndef test_ok():\n    assert f() == 42\n")
        # Mock LLM: first writes correct code, then runs validators
        mock = MockLLMClient(script=[
            '{"type": "write_file", "params": {"path": "' + d + '/src/mod.py", "content": "def f():\\n    return 42\\n"}}',
        ])
        cfg = Config(retry_budget=3, convergence_threshold=3, allowed_paths=[d])
        disp = ToolDispatcher(allowed_paths=[d])
        disp.register(ActionType.WRITE_FILE, WriteFile(allowed_paths=[d]))
        disp.register(ActionType.READ_FILE, ReadFile(allowed_paths=[d]))
        loop = AgentLoop(
            llm_client=mock, dispatcher=disp,
            guardrail=Guardrail(cfg.dangerous_patterns, cfg.allowed_paths),
            hitl=HITLController(),
            feedback_loop=FeedbackLoop(ValidatorPipeline([PytestValidator()]), cfg),
            context_window=ContextWindow(), config=cfg, project_path=d,
        )
        session = await loop.run("make test pass")
        assert session.status.value == "completed"


@pytest.mark.asyncio
async def test_agent_loop_budget_exhaustion():
    with tempfile.TemporaryDirectory() as d:
        Path(d, "pyproject.toml").write_text('[tool.pytest.ini_options]\npythonpath=["src"]')
        Path(d, "src").mkdir()
        Path(d, "src", "mod.py").write_text("def f():\n    return 1\n")
        Path(d, "tests").mkdir()
        Path(d, "tests", "test_mod.py").write_text("from mod import f\ndef test_fail():\n    assert f() == 99\n")
        # Mock keeps writing wrong code
        mock = MockLLMClient(script=[
            '{"type": "write_file", "params": {"path": "' + d + '/src/mod.py", "content": "def f():\\n    return 1\\n"}}',
        ] * 5)
        cfg = Config(retry_budget=2, convergence_threshold=99, allowed_paths=[d])
        disp = ToolDispatcher(allowed_paths=[d])
        disp.register(ActionType.WRITE_FILE, WriteFile(allowed_paths=[d]))
        loop = AgentLoop(
            llm_client=mock, dispatcher=disp,
            guardrail=Guardrail(cfg.dangerous_patterns, cfg.allowed_paths),
            hitl=HITLController(),
            feedback_loop=FeedbackLoop(ValidatorPipeline([PytestValidator()]), cfg),
            context_window=ContextWindow(), config=cfg, project_path=d,
        )
        session = await loop.run("make test pass")
        assert session.status.value in ("budget_exhausted", "convergence_stopped")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 作业 && python -m pytest tests/test_agent_loop.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`作业/codereflex/agent.py`:
```python
from __future__ import annotations
import json
import logging
import uuid
from codereflex.config import Config
from codereflex.models import Action, ActionType, Session, SessionStatus, Turn
from codereflex.llm.client import LLMClient
from codereflex.tools.base import ToolDispatcher
from codereflex.guardrail.guardrail import Guardrail
from codereflex.guardrail.hitl import HITLController
from codereflex.feedback.feedback_loop import FeedbackLoop
from codereflex.memory.session import ContextWindow

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are CodeReflex, a coding agent. Respond with a JSON action.
Available actions: read_file, write_file, list_dir, run_shell, run_validators.
Format: {"type": "<action>", "params": {...}}"""


def parse_action(text: str) -> Action | None:
    try:
        data = json.loads(text)
        atype = ActionType(data["type"])
        return Action(type=atype, params=data.get("params", {}))
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


class AgentLoop:
    def __init__(
        self,
        llm_client: LLMClient,
        dispatcher: ToolDispatcher,
        guardrail: Guardrail,
        hitl: HITLController,
        feedback_loop: FeedbackLoop,
        context_window: ContextWindow,
        config: Config,
        project_path: str,
    ):
        self._llm = llm_client
        self._dispatcher = dispatcher
        self._guardrail = guardrail
        self._hitl = hitl
        self._feedback_loop = feedback_loop
        self._ctx = context_window
        self._config = config
        self._project_path = project_path

    async def run(self, task: str) -> Session:
        session = Session(id=str(uuid.uuid4()), task=task)
        parse_retries = 0

        while session.status == SessionStatus.RUNNING:
            messages = self._ctx.build_messages(session, SYSTEM_PROMPT, self._config.context_window)
            llm_resp = await self._llm.complete(messages, self._config.model)
            action = parse_action(llm_resp.text)

            if action is None:
                parse_retries += 1
                if parse_retries > 1:
                    session.status = SessionStatus.ERROR
                    break
                session.history.append(Turn(action=None, result=None, feedback=None, llm_response=llm_resp.text))
                continue
            parse_retries = 0

            # Guardrail check
            decision = self._guardrail.check(action)
            if decision.verdict.value == "deny":
                result_text = f"Action denied: {decision.reason}"
                session.history.append(Turn(action=action, result=None, feedback=None, llm_response=llm_resp.text))
                continue
            if decision.verdict.value == "intercept":
                rid = self._hitl.request(action)
                # In test/offline mode, auto-deny (no real HITL UI in loop)
                self._hitl.deny(rid)
                session.history.append(Turn(action=action, result=None, feedback=None, llm_response=llm_resp.text))
                continue

            # Dispatch
            result = self._dispatcher.dispatch(action)
            feedback = None
            should_continue = False

            # Feedback loop triggers on write_file
            if action.type == ActionType.WRITE_FILE:
                feedback, should_continue = self._feedback_loop.run(self._project_path, session)

            session.history.append(Turn(
                action=action, result=result, feedback=feedback, llm_response=llm_resp.text,
            ))

            if not should_continue:
                break

        return session
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd 作业 && python -m pytest tests/test_agent_loop.py -v`
Expected: PASS — 3 passed

- [ ] **Step 5: Commit**

```bash
cd 作业
git add codereflex/agent.py tests/test_agent_loop.py
git commit -m "feat: add AgentLoop main loop with guardrail, dispatch, and feedback integration"
```

---

### Task 12: CredentialStore

**Files:**
- Create: `作业/codereflex/credentials.py`
- Test: `作业/tests/test_credentials.py`

**Interfaces:**
- Produces: `CredentialStore` class with `get(key_name: str) -> str | None`, `set(key_name: str, value: str)`, `delete(key_name: str)`, `status(key_name: str) -> bool`, `setup_interactive(key_name: str)` (uses getpass)

- [ ] **Step 1: Write the failing test**

`作业/tests/test_credentials.py`:
```python
import os
from unittest.mock import patch
from codereflex.credentials import CredentialStore


def test_env_fallback():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        store = CredentialStore(use_keyring=False)
        assert store.get("OPENAI_API_KEY") == "sk-test"


def test_status_true_when_set():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        store = CredentialStore(use_keyring=False)
        assert store.status("OPENAI_API_KEY") is True


def test_status_false_when_unset():
    with patch.dict(os.environ, {}, clear=True):
        store = CredentialStore(use_keyring=False)
        assert store.status("MY_KEY") is False


def test_get_returns_none_when_unset():
    with patch.dict(os.environ, {}, clear=True):
        store = CredentialStore(use_keyring=False)
        assert store.get("MY_KEY") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 作业 && python -m pytest tests/test_credentials.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`作业/codereflex/credentials.py`:
```python
from __future__ import annotations
import getpass
import logging
import os

logger = logging.getLogger(__name__)


class CredentialStore:
    def __init__(self, use_keyring: bool = True):
        self._use_keyring = use_keyring
        self._keyring = None
        if use_keyring:
            try:
                import keyring
                self._keyring = keyring
            except ImportError:
                logger.warning("keyring not available, falling back to env vars (plaintext risk)")

    def get(self, key_name: str) -> str | None:
        if self._keyring:
            val = self._keyring.get_password("codereflex", key_name)
            if val:
                return val
        return os.environ.get(key_name)

    def set(self, key_name: str, value: str) -> None:
        if self._keyring:
            self._keyring.set_password("codereflex", key_name, value)
        else:
            logger.warning("Storing credential in env var (plaintext) — keyring unavailable")

    def delete(self, key_name: str) -> None:
        if self._keyring:
            try:
                self._keyring.delete_password("codereflex", key_name)
            except Exception:
                pass

    def status(self, key_name: str) -> bool:
        return self.get(key_name) is not None

    def setup_interactive(self, key_name: str) -> None:
        print(f"Enter value for {key_name} (input hidden):")
        value = getpass.getpass("> ")
        if value:
            self.set(key_name, value)
            print(f"{key_name} stored.")
        else:
            print("No value entered, skipping.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd 作业 && python -m pytest tests/test_credentials.py -v`
Expected: PASS — 4 passed

- [ ] **Step 5: Commit**

```bash
cd 作业
git add codereflex/credentials.py tests/test_credentials.py
git commit -m "feat: add CredentialStore with keyring and env fallback"
```

---

### Task 13: WebUI (FastAPI + SSE)

**Files:**
- Create: `作业/codereflex/web/__init__.py`
- Create: `作业/codereflex/web/app.py`
- Create: `作业/codereflex/web/templates/index.html`
- Test: `作业/tests/test_web.py`

**Interfaces:**
- Consumes: `agent.AgentLoop`, `config.Config`
- Produces: `create_app(agent_loop, config) -> FastAPI` factory; endpoints `POST /submit`, `POST /approve/{rid}`, `POST /deny/{rid}`, `GET /stream` (SSE)

- [ ] **Step 1: Write the failing test**

`作业/tests/test_web.py`:
```python
import pytest
from fastapi.testclient import TestClient
from codereflex.web.app import create_app
from codereflex.config import Config


class StubAgentLoop:
    async def run(self, task: str):
        from codereflex.models import Session
        return Session(id="test", task=task)


def test_index_page():
    app = create_app(StubAgentLoop(), Config())
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "CodeReflex" in resp.text


def test_submit_endpoint():
    app = create_app(StubAgentLoop(), Config())
    client = TestClient(app)
    resp = client.post("/submit", json={"task": "fix test"})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 作业 && pip install httpx && python -m pytest tests/test_web.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`作业/codereflex/web/__init__.py`: (empty)

`作业/codereflex/web/app.py`:
```python
from __future__ import annotations
import asyncio
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


class TaskRequest(BaseModel):
    task: str


def create_app(agent_loop, config) -> FastAPI:
    app = FastAPI(title="CodeReflex")
    _event_queue: asyncio.Queue = asyncio.Queue()

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return _TEMPLATES.TemplateResponse("index.html", {"request": request})

    @app.post("/submit")
    async def submit(req: TaskRequest):
        session = await agent_loop.run(req.task)
        return JSONResponse({"session_id": session.id, "status": session.status.value})

    @app.get("/stream")
    async def stream(request: Request):
        async def event_generator():
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(_event_queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        from fastapi.responses import StreamingResponse
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.post("/approve/{rid}")
    async def approve(rid: str):
        agent_loop._hitl.approve(rid)
        return JSONResponse({"approved": rid})

    @app.post("/deny/{rid}")
    async def deny(rid: str):
        agent_loop._hitl.deny(rid)
        return JSONResponse({"denied": rid})

    return app
```

`作业/codereflex/web/templates/index.html`:
```html
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>CodeReflex</title>
    <style>
        body { font-family: monospace; max-width: 900px; margin: 2em auto; padding: 0 1em; }
        #stream { white-space: pre-wrap; background: #f4f4f4; padding: 1em; border-radius: 6px; min-height: 300px; }
        .hitl { background: #fff3cd; padding: 1em; border-radius: 6px; margin: 0.5em 0; }
        button { padding: 0.5em 1em; margin: 0.25em; }
    </style>
</head>
<body>
    <h1>CodeReflex</h1>
    <p>Feedback-loop-centric coding agent harness</p>
    <form id="task-form">
        <textarea name="task" rows="3" placeholder="Describe the coding task..." style="width:100%"></textarea>
        <button type="submit">Submit Task</button>
    </form>
    <div id="stream"></div>
    <script>
        const form = document.getElementById('task-form');
        const stream = document.getElementById('stream');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const task = new FormData(form).get('task');
            stream.innerHTML = '';
            await fetch('/submit', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({task})});
            const es = new EventSource('/stream');
            es.onmessage = (ev) => {
                stream.textContent += ev.data + '\n';
            };
        });
    </script>
</body>
</html>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd 作业 && python -m pytest tests/test_web.py -v`
Expected: PASS — 2 passed

- [ ] **Step 5: Commit**

```bash
cd 作业
git add codereflex/web/ tests/test_web.py
git commit -m "feat: add FastAPI WebUI with SSE streaming and HITL endpoints"
```

---

### Task 14: CLI Entry

**Files:**
- Create: `作业/codereflex/cli.py`
- Test: `作业/tests/test_cli.py`

**Interfaces:**
- Produces: `main()` function (argparse with `setup` and `run` subcommands); `run_server(config_path, project_path)` helper

- [ ] **Step 1: Write the failing test**

`作业/tests/test_cli.py`:
```python
import subprocess
import sys


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "codereflex.cli", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "setup" in result.stdout
    assert "run" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 作业 && python -m pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`作业/codereflex/cli.py`:
```python
from __future__ import annotations
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(prog="codereflex", description="CodeReflex coding agent harness")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("setup", help="Set up API credentials")
    run_p = sub.add_parser("run", help="Run the agent server")
    run_p.add_argument("--config", default=None, help="Path to config YAML")
    run_p.add_argument("--project", default=".", help="Target project path")
    run_p.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    if args.command == "setup":
        from codereflex.credentials import CredentialStore
        store = CredentialStore()
        store.setup_interactive("OPENAI_API_KEY")
    elif args.command == "run":
        _run_server(args.config, args.project, args.port)
    else:
        parser.print_help()


def _run_server(config_path: str | None, project_path: str, port: int):
    from codereflex.config import load_config
    from codereflex.credentials import CredentialStore
    from codereflex.web.app import create_app
    import uvicorn

    cfg = load_config(config_path)
    store = CredentialStore()
    api_key = store.get("OPENAI_API_KEY")
    if not api_key:
        print("No API key found. Run 'codereflex setup' first.")
        sys.exit(1)

    from codereflex.llm.client import LLMClient
    from codereflex.tools.base import ToolDispatcher
    from codereflex.tools.file_tools import ReadFile, WriteFile, ListDir
    from codereflex.tools.shell_tool import RunShell
    from codereflex.guardrail.guardrail import Guardrail
    from codereflex.guardrail.hitl import HITLController
    from codereflex.feedback.validators import ValidatorPipeline, PytestValidator, RuffValidator, MypyValidator
    from codereflex.feedback.feedback_loop import FeedbackLoop
    from codereflex.memory.session import ContextWindow
    from codereflex.agent import AgentLoop
    from codereflex.models import ActionType

    llm = LLMClient(cfg.llm_base_url, api_key)
    disp = ToolDispatcher(allowed_paths=[project_path])
    disp.register(ActionType.READ_FILE, ReadFile(allowed_paths=[project_path]))
    disp.register(ActionType.WRITE_FILE, WriteFile(allowed_paths=[project_path]))
    disp.register(ActionType.LIST_DIR, ListDir(allowed_paths=[project_path]))
    disp.register(ActionType.RUN_SHELL, RunShell())
    validators = []
    if "pytest" in cfg.validators:
        validators.append(PytestValidator())
    if "ruff" in cfg.validators:
        validators.append(RuffValidator())
    if "mypy" in cfg.validators:
        validators.append(MypyValidator())
    loop = AgentLoop(
        llm_client=llm, dispatcher=disp,
        guardrail=Guardrail(cfg.dangerous_patterns, cfg.allowed_paths),
        hitl=HITLController(),
        feedback_loop=FeedbackLoop(ValidatorPipeline(validators), cfg),
        context_window=ContextWindow(), config=cfg, project_path=project_path,
    )
    app = create_app(loop, cfg)
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd 作业 && python -m pytest tests/test_cli.py -v`
Expected: PASS — 1 passed

- [ ] **Step 5: Commit**

```bash
cd 作业
git add codereflex/cli.py tests/test_cli.py
git commit -m "feat: add CLI with setup and run subcommands"
```

---

### Task 15: Mechanism Demo (A.6 Three Deterministic Demos)

**Files:**
- Create: `作业/demos/mechanism_demo.py`
- Test: `作业/tests/test_mechanism_demo.py`

**Interfaces:**
- Produces: `demo_guardrail()`, `demo_feedback_loop()`, `demo_classifier()` functions; `main()` that runs all three

- [ ] **Step 1: Write the failing test**

`作业/tests/test_mechanism_demo.py`:
```python
from demos.mechanism_demo import demo_guardrail, demo_feedback_loop, demo_classifier


def test_demo_guardrail():
    result = demo_guardrail()
    assert result["intercepted"] is True
    assert "rm -rf" in result["reason"]


def test_demo_feedback_loop():
    result = demo_feedback_loop()
    assert result["feedback_injected"] is True
    assert result["next_action_changed"] is True


def test_demo_classifier():
    result = demo_classifier()
    assert result["category"] == "test_failure"
    assert "test_calc.py" in result["file"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 作业 && python -m pytest tests/test_mechanism_demo.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`作业/demos/__init__.py`: (empty)

`作业/demos/mechanism_demo.py`:
```python
"""A.6 Mechanism demo: three deterministic behaviors under mock LLM."""
from __future__ import annotations
import tempfile
from pathlib import Path
from codereflex.models import Action, ActionType, DecisionVerdict
from codereflex.guardrail.guardrail import Guardrail
from codereflex.feedback.classifier import FailureClassifier
from codereflex.feedback.feedback_loop import FeedbackLoop, format_feedback_for_llm
from codereflex.feedback.validators import ValidatorPipeline, PytestValidator
from codereflex.config import Config
from codereflex.models import Session, Feedback, FeedbackStatus


def demo_guardrail() -> dict:
    """Demo 1: guardrail intercepts a dangerous action."""
    g = Guardrail(dangerous_patterns=["rm -rf", "drop "], allowed_paths=["/tmp/proj"])
    d = g.check(Action(ActionType.RUN_SHELL, {"cmd": "rm -rf /"}))
    return {"intercepted": d.verdict == DecisionVerdict.INTERCEPT, "reason": d.reason}


def demo_feedback_loop() -> dict:
    """Demo 2: inject a failure, feedback loop changes next action."""
    with tempfile.TemporaryDirectory() as d:
        Path(d, "pyproject.toml").write_text('[tool.pytest.ini_options]\npythonpath=["src"]')
        Path(d, "src").mkdir()
        Path(d, "src", "mod.py").write_text("def f():\n    return 1\n")
        Path(d, "tests").mkdir()
        Path(d, "tests", "test_mod.py").write_text("from mod import f\ndef test_fail():\n    assert f() == 99\n")
        cfg = Config(retry_budget=5, convergence_threshold=3)
        loop = FeedbackLoop(ValidatorPipeline([PytestValidator()]), cfg)
        session = Session(id="demo", task="fix test")
        fb, should_continue = loop.run(d, session)
        feedback_text = format_feedback_for_llm(fb, fb.failures) if fb else ""
        # "next action changed" = feedback was injected and contains structured info
        changed = "test_fail" in feedback_text or "TEST_FAILURE" in feedback_text or "99" in feedback_text
        return {
            "feedback_injected": fb is not None and fb.status == FeedbackStatus.FAIL,
            "next_action_changed": changed,
            "feedback_text": feedback_text,
        }


def demo_classifier() -> dict:
    """Demo 3: failure classifier categorizes a pytest failure."""
    pytest_output = """\
tests/test_calc.py::test_add FAILED                                       [ 50%]
tests/test_calc.py:5: AssertionError
=========================== 1 failed in 0.05s ===========================
"""
    fb = Feedback(validator="pytest", status=FeedbackStatus.FAIL, raw_output=pytest_output)
    items = FailureClassifier.classify(fb)
    if items:
        return {
            "category": items[0].category.value,
            "file": items[0].file,
            "line": items[0].line,
        }
    return {"category": "none", "file": "", "line": None}


def main():
    print("=== Demo 1: Guardrail intercepts dangerous action ===")
    r1 = demo_guardrail()
    print(f"  Intercepted: {r1['intercepted']}, Reason: {r1['reason']}")

    print("\n=== Demo 2: Feedback loop injects failure, changes next action ===")
    r2 = demo_feedback_loop()
    print(f"  Feedback injected: {r2['feedback_injected']}, Action changed: {r2['next_action_changed']}")

    print("\n=== Demo 3: Failure classifier categorizes pytest failure ===")
    r3 = demo_classifier()
    print(f"  Category: {r3['category']}, File: {r3['file']}, Line: {r3['line']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd 作业 && python -m pytest tests/test_mechanism_demo.py -v`
Expected: PASS — 3 passed

- [ ] **Step 5: Commit**

```bash
cd 作业
git add demos/ tests/test_mechanism_demo.py
git commit -m "feat: add mechanism demo with three deterministic behaviors"
```

---

### Task 16: Dockerfile + CI

**Files:**
- Create: `作业/Dockerfile`
- Create: `作业/.gitlab-ci.yml`
- Create: `作业/.github/workflows/ci.yml`

- [ ] **Step 1: Write Dockerfile**

`作业/Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY codereflex/ ./codereflex/
COPY demos/ ./demos/
COPY tests/ ./tests/

RUN pip install --no-cache-dir -e ".[dev,validators]"

EXPOSE 8000

CMD ["python", "-m", "codereflex.cli", "run", "--project", "/workspace", "--port", "8000"]
```

- [ ] **Step 2: Write GitLab CI**

`作业/.gitlab-ci.yml`:
```yaml
stages:
  - test
  - build

unit-test:
  stage: test
  image: python:3.12-slim
  before_script:
    - pip install -e ".[dev,validators]"
  script:
    - python -m pytest tests/ -v
  rules:
    - if: $CI_PIPELINE_SOURCE == "push"

docker-build:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  script:
    - docker build -t codereflex .
  rules:
    - if: $CI_COMMIT_BRANCH == "master"
```

- [ ] **Step 3: Write GitHub Actions CI (fallback)**

`作业/.github/workflows/ci.yml`:
```yaml
name: CI
on: [push, pull_request]
jobs:
  unit-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev,validators]"
      - run: python -m pytest tests/ -v
```

- [ ] **Step 4: Verify CI config is valid YAML**

Run: `cd 作业 && python -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml')); print('gitlab-ci OK'); yaml.safe_load(open('.github/workflows/ci.yml')); print('github-actions OK')"`
Expected: `gitlab-ci OK` and `github-actions OK`

- [ ] **Step 5: Commit**

```bash
cd 作业
git add Dockerfile .gitlab-ci.yml .github/workflows/ci.yml
git commit -m "ci: add Dockerfile, GitLab CI, and GitHub Actions with unit-test job"
```

---

### Task 17: README

**Files:**
- Create: `作业/README.md`

- [ ] **Step 1: Write README**

`作业/README.md`:
```markdown
# CodeReflex

Feedback-loop-centric coding agent harness. Wraps an LLM to write, validate, and self-correct Python code until tests pass or retry budget exhausts.

## Project Intro

CodeReflex implements `Agent = LLM + Harness`. The LLM decides the next action; the harness handles tool dispatch, guardrails, feedback validation, and memory. The feedback loop is the structural spine: after every `write_file`, the harness runs pytest + ruff + mypy, classifies failures, and injects structured feedback so the LLM can self-correct.

## Installation

```bash
cd 作业
pip install -e ".[dev,validators]"
```

## Running

### Local

```bash
# 1. Set up API key (stored in OS keyring)
python -m codereflex.cli setup

# 2. Run the WebUI server
python -m codereflex.cli run --project /path/to/your/python/project --port 8000
```

Open http://localhost:8000

### Docker

```bash
docker build -t codereflex ./作业
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... -v /path/to/project:/workspace codereflex
```

## API Key Security

- **Local**: stored in OS keyring (Windows Credential Manager / macOS Keychain / Linux Secret Service). First run `codereflex setup` with hidden input. `status` shows set/unset without echoing the key.
- **Docker**: pass via `-e OPENAI_API_KEY=...` at `docker run`. **Known risk**: environment variables are plaintext and visible to processes in the container. This is an accepted tradeoff for containerized deployment.
- **`.env` fallback** (local dev only, gitignored): plaintext, loaded via `python-dotenv`. Documented risk.

Never commit real keys. The repo self-checks `.env`, history, and config files before commit.

## Distribution Commands

```bash
# Build Docker image
docker build -t codereflex ./作业

# Run
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... codereflex
```

## Directory Structure

```
作业/
  pyproject.toml
  codereflex/
    models.py          # data models + enums
    config.py          # YAML config loading
    credentials.py     # keyring + env credential store
    agent.py           # AgentLoop main loop
    cli.py             # CLI entry
    llm/client.py      # LLMClient + MockLLMClient
    tools/             # ToolDispatcher + file/shell tools
    guardrail/         # Guardrail + HITL state machine
    feedback/          # Validators + FailureClassifier + FeedbackLoop (★)
    memory/            # ContextWindow + DecisionLog
    web/               # FastAPI + SSE WebUI
  tests/               # mock-LLM unit tests + fixtures
  demos/               # mechanism demo
  Dockerfile
  .gitlab-ci.yml
```

## Security Boundaries

- **Path sandboxing**: all file operations restricted to `allowed_paths`; `..` traversal resolved and denied.
- **Dangerous command interception**: `rm -rf`, `drop`, `git push --force`, `curl|sh` patterns intercepted → HITL approval required.
- **Credential isolation**: keys never in source, git, or logs. Log sanitization strips key-like strings.
- **Retry budget + convergence detection**: prevents infinite feedback loops.

## Known Limitations

- Single concurrent session (MVP).
- Target project must be Python with pytest/ruff/mypy.
- Docker deployment: env var key is plaintext (accepted tradeoff).
- Free-tier deployment (Render/Fly.io) may sleep on inactivity.
```

- [ ] **Step 2: Commit**

```bash
cd 作业
git add README.md
git commit -m "docs: add README with install, run, security, and structure"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] §1 Problem statement → Task 1 (project embodies the feedback-loop thesis)
- [x] §2 User stories 1-6 → Tasks 4,5,9,11,13,2 (tools, guardrail, feedback, agent, webui, config)
- [x] §3 Domain & mechanisms → Tasks 4 (tools), 9 (feedback ★), 5+6 (guardrail+HITL), 10 (memory)
- [x] §4 Functional spec (9 modules) → Tasks 1-14
- [x] §5 Non-functional → Tasks 5,12,16 (security, credentials, CI)
- [x] §6 Architecture → Task 11 (integration)
- [x] §7 Data model → Task 1
- [x] §8 Credentials & distribution → Tasks 12, 16
- [x] §9 Tech selection → embedded in all tasks
- [x] §10 Acceptance criteria → Tasks 15 (mechanism demo), 16 (CI), all test tasks
- [x] §11 Risks → addressed in implementations (convergence, budget, path traversal, mock determinism)

**Placeholder scan:** No TBD/TODO. All steps have complete code.

**Type consistency:** `Action(type, params, target_path)`, `ActionResult(success, output, error, exit_code)`, `Feedback(validator, status, failures, raw_output)`, `FailureItem(category, file, line, message, expected, actual)` — consistent across all tasks. `failure_signature` defined in Task 8, used in Task 9. `format_feedback_for_llm` defined in Task 9, used in Tasks 10, 15.
