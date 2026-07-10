from __future__ import annotations
import hashlib
import re
from codereflex.models import Feedback, FailureItem, FailureCategory, FeedbackStatus


class FailureClassifier:
    """Parses raw validator output into structured FailureItem list."""

    # pytest: "path::test_name FAILED" + "path:line: AssertionError"
    _PYTEST_FAIL = re.compile(r"^(.+?\.py)::(\S+)\s+FAILED", re.MULTILINE)
    _PYTEST_LOC = re.compile(r"^(.+?\.py):(\d+):", re.MULTILINE)
    # mypy: "path:line: error: msg"
    _MYPY = re.compile(r"^(.+?\.py):(\d+):\s*error:\s*(.+)$", re.MULTILINE)
    # ruff: "path:line:col: CODE msg"
    _RUFF = re.compile(r"^(.+?\.py):(\d+):\d+:\s*\S+\s+(.+)$", re.MULTILINE)
    # syntax error
    _SYNTAX = re.compile(r'File "(.+?)",\s*line\s*(\d+).*?SyntaxError:\s*(.+)', re.DOTALL)
    # import error
    _IMPORT = re.compile(r"ModuleNotFoundError: No module named '([^']+)'")
    # runtime: "ExceptionType: message" at line start, excluding Syntax/Import (have own classifiers)
    _RUNTIME = re.compile(r"^(?!SyntaxError|ImportError)(\w+Error): (.+)$", re.MULTILINE)

    @staticmethod
    def classify(feedback: Feedback) -> list[FailureItem]:
        if feedback.status == FeedbackStatus.PASS:
            return []
        if feedback.status == FeedbackStatus.VALIDATOR_ERROR:
            return [FailureItem(
                category=FailureCategory.RUNTIME_ERROR,
                file="", line=None,
                message=f"Validator error: {feedback.raw_output[:200]}",
            )]
        text = feedback.raw_output
        items: list[FailureItem] = []
        if feedback.validator == "pytest":
            items.extend(FailureClassifier._classify_pytest(text))
        elif feedback.validator == "mypy":
            items.extend(FailureClassifier._classify_mypy(text))
        elif feedback.validator == "ruff":
            items.extend(FailureClassifier._classify_ruff(text))
        # Cross-cutting: syntax/import/runtime can appear in any output
        items.extend(FailureClassifier._classify_syntax(text))
        items.extend(FailureClassifier._classify_import(text))
        items.extend(FailureClassifier._classify_runtime(text))
        return items

    @staticmethod
    def _classify_pytest(text: str) -> list[FailureItem]:
        items = []
        for m in FailureClassifier._PYTEST_FAIL.finditer(text):
            file, test_name = m.group(1), m.group(2)
            loc_match = FailureClassifier._PYTEST_LOC.search(text)
            line = int(loc_match.group(2)) if loc_match else None
            items.append(FailureItem(
                category=FailureCategory.TEST_FAILURE,
                file=file, line=line,
                message=f"Test {test_name} failed",
            ))
        return items

    @staticmethod
    def _classify_mypy(text: str) -> list[FailureItem]:
        items = []
        for m in FailureClassifier._MYPY.finditer(text):
            items.append(FailureItem(
                category=FailureCategory.TYPE_ERROR,
                file=m.group(1), line=int(m.group(2)),
                message=m.group(3).strip(),
            ))
        return items

    @staticmethod
    def _classify_ruff(text: str) -> list[FailureItem]:
        items = []
        for m in FailureClassifier._RUFF.finditer(text):
            items.append(FailureItem(
                category=FailureCategory.LINT_VIOLATION,
                file=m.group(1), line=int(m.group(2)),
                message=m.group(3).strip(),
            ))
        return items

    @staticmethod
    def _classify_syntax(text: str) -> list[FailureItem]:
        items = []
        for m in FailureClassifier._SYNTAX.finditer(text):
            items.append(FailureItem(
                category=FailureCategory.SYNTAX_ERROR,
                file=m.group(1), line=int(m.group(2)),
                message=f"SyntaxError: {m.group(3).strip()}",
            ))
        return items

    @staticmethod
    def _classify_import(text: str) -> list[FailureItem]:
        items = []
        for m in FailureClassifier._IMPORT.finditer(text):
            items.append(FailureItem(
                category=FailureCategory.IMPORT_ERROR,
                file="", line=None,
                message=f"No module named '{m.group(1)}'",
            ))
        return items

    @staticmethod
    def _classify_runtime(text: str) -> list[FailureItem]:
        items = []
        for m in FailureClassifier._RUNTIME.finditer(text):
            items.append(FailureItem(
                category=FailureCategory.RUNTIME_ERROR,
                file="", line=None,
                message=f"{m.group(1)}: {m.group(2)}",
            ))
        return items

    @staticmethod
    def classify_all(feedbacks: list[Feedback]) -> list[FailureItem]:
        items = []
        for fb in feedbacks:
            items.extend(FailureClassifier.classify(fb))
        return items


def failure_signature(items: list[FailureItem]) -> str:
    """Stable hash of failure items for convergence detection."""
    sig = "|".join(f"{i.category}:{i.file}:{i.line}:{i.message}" for i in items)
    return hashlib.md5(sig.encode()).hexdigest()
