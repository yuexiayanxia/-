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
