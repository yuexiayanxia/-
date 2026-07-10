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
