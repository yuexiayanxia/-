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
