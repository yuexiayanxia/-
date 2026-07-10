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
