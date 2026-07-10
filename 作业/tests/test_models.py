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
