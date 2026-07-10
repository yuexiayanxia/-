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
        # Normalize backslashes to forward slashes for JSON-safe paths (Windows compat)
        dp = d.replace("\\", "/")
        mock = MockLLMClient(script=[
            '{"type": "write_file", "params": {"path": "' + dp + '/src/mod.py", "content": "def f():\\n    return 42\\n"}}',
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
        # Normalize backslashes to forward slashes for JSON-safe paths (Windows compat)
        dp = d.replace("\\", "/")
        mock = MockLLMClient(script=[
            '{"type": "write_file", "params": {"path": "' + dp + '/src/mod.py", "content": "def f():\\n    return 1\\n"}}',
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
