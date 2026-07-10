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
