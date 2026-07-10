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
    from codereflex.feedback.classifier import failure_signature, FailureClassifier
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
