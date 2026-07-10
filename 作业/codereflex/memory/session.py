from __future__ import annotations
from codereflex.models import Session


class ContextWindow:
    def build_messages(self, session: Session, system_prompt: str, window_size: int = 20) -> list[dict]:
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": f"Task: {session.task}"})
        recent = session.history[-window_size:] if window_size > 0 else session.history
        for turn in recent:
            parts: list[str] = []
            if turn.action:
                import json
                parts.append(json.dumps({
                    "action": turn.action.type.value,
                    "params": turn.action.params,
                    "result": {"success": turn.result.success if turn.result else None,
                               "output": turn.result.output if turn.result else "",
                               "error": turn.result.error if turn.result else ""},
                }, ensure_ascii=False))
            if turn.feedback:
                from codereflex.feedback.feedback_loop import format_feedback_for_llm
                parts.append(format_feedback_for_llm(turn.feedback, turn.feedback.failures))
            if parts:
                messages.append({"role": "user", "content": "\n".join(parts)})
            if turn.llm_response:
                messages.append({"role": "assistant", "content": turn.llm_response})
        return messages
