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
