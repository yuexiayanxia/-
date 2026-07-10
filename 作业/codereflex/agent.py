from __future__ import annotations
import asyncio
import json
import logging
import uuid
from codereflex.config import Config
from codereflex.models import Action, ActionResult, ActionType, Session, SessionStatus, Turn
from codereflex.llm.client import LLMClient
from codereflex.tools.base import ToolDispatcher
from codereflex.guardrail.guardrail import Guardrail
from codereflex.guardrail.hitl import HITLController
from codereflex.feedback.feedback_loop import FeedbackLoop
from codereflex.memory.session import ContextWindow

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 50
MAX_GUARDRAIL_BLOCKS = 3

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
        hitl_callback=None,
    ):
        self._llm = llm_client
        self._dispatcher = dispatcher
        self._guardrail = guardrail
        self._hitl = hitl
        self._feedback_loop = feedback_loop
        self._ctx = context_window
        self._config = config
        self._project_path = project_path
        self._hitl_callback = hitl_callback

    async def run(self, task: str) -> Session:
        session = Session(id=str(uuid.uuid4()), task=task)
        parse_retries = 0
        iteration = 0
        guardrail_blocks = 0

        while session.status == SessionStatus.RUNNING:
            iteration += 1
            if iteration > MAX_ITERATIONS:
                session.status = SessionStatus.ERROR
                logger.warning("Agent loop exceeded max iterations (%d)", MAX_ITERATIONS)
                break

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
                guardrail_blocks += 1
                if guardrail_blocks >= MAX_GUARDRAIL_BLOCKS:
                    session.status = SessionStatus.ERROR
                    logger.warning("Too many guardrail blocks (%d)", guardrail_blocks)
                    break
                denied_result = ActionResult(success=False, error=f"Action denied: {decision.reason}")
                session.history.append(Turn(action=action, result=denied_result, feedback=None, llm_response=llm_resp.text))
                continue
            if decision.verdict.value == "intercept":
                guardrail_blocks += 1
                if guardrail_blocks >= MAX_GUARDRAIL_BLOCKS:
                    session.status = SessionStatus.ERROR
                    break
                rid = self._hitl.request(action)
                approved = await self._await_hitl(rid)
                if not approved:
                    denied_result = ActionResult(success=False, error="HITL: action denied by user")
                    session.history.append(Turn(action=action, result=denied_result, feedback=None, llm_response=llm_resp.text))
                    continue
            guardrail_blocks = 0

            # Dispatch
            result = self._dispatcher.dispatch(action)
            feedback = None
            should_continue = True

            # Feedback loop triggers on write_file and run_validators
            if action.type in (ActionType.WRITE_FILE, ActionType.RUN_VALIDATORS):
                feedback, should_continue = self._feedback_loop.run(self._project_path, session)

            session.history.append(Turn(
                action=action, result=result, feedback=feedback, llm_response=llm_resp.text,
            ))

            if not should_continue:
                break

        return session

    async def _await_hitl(self, request_id: str) -> bool:
        """Wait for HITL approval. Uses callback if set, otherwise auto-deny."""
        if self._hitl_callback is not None:
            return await self._hitl_callback(request_id)
        self._hitl.deny(request_id)
        return False
