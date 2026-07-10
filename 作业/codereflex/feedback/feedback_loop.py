from __future__ import annotations
from codereflex.config import Config
from codereflex.models import Feedback, FailureItem, Session, SessionStatus, FeedbackStatus
from codereflex.feedback.validators import ValidatorPipeline
from codereflex.feedback.classifier import FailureClassifier, failure_signature


def format_feedback_for_llm(feedback: Feedback, items: list[FailureItem]) -> str:
    if not items:
        return "All validators passed."
    lines = [f"[{feedback.validator}] FAIL — {len(items)} issue(s):"]
    for i in items:
        loc = f"{i.file}:{i.line}" if i.line else i.file
        lines.append(f"  - {i.category.value} at {loc}: {i.message}")
        if i.expected and i.actual:
            lines.append(f"      expected: {i.expected}, actual: {i.actual}")
    return "\n".join(lines)


class FeedbackLoop:
    def __init__(self, pipeline: ValidatorPipeline, config: Config):
        self._pipeline = pipeline
        self._config = config

    def run(self, project_path: str, session: Session) -> tuple[Feedback | None, bool]:
        feedbacks = self._pipeline.run(project_path)
        all_items = FailureClassifier.classify_all(feedbacks)

        has_failure = any(f.status == FeedbackStatus.FAIL for f in feedbacks)
        if not has_failure and not all_items:
            session.status = SessionStatus.COMPLETED
            return None, False

        # Merge into a single Feedback for回灌
        merged = Feedback(
            validator="pipeline",
            status=FeedbackStatus.FAIL,
            failures=all_items,
            raw_output="\n---\n".join(f.raw_output for f in feedbacks),
        )

        # Convergence detection
        sig = failure_signature(all_items)
        session.failure_signatures.append(sig)
        recent = session.failure_signatures[-self._config.convergence_threshold:]
        if len(recent) >= self._config.convergence_threshold and len(set(recent)) == 1:
            session.status = SessionStatus.CONVERGENCE_STOPPED
            return merged, False

        # Budget check
        session.retry_count += 1
        if session.retry_count >= self._config.retry_budget:
            session.status = SessionStatus.BUDGET_EXHAUSTED
            return merged, False

        return merged, True
