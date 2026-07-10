from pathlib import Path
from codereflex.feedback.validators import (
    PytestValidator, RuffValidator, MypyValidator, ValidatorPipeline,
)
from codereflex.models import FeedbackStatus

FIXTURE = str(Path(__file__).parent / "fixtures" / "sample_project")


def test_pytest_validator_pass():
    v = PytestValidator()
    fb = v.validate(FIXTURE)
    assert fb.validator == "pytest"
    assert fb.status == FeedbackStatus.PASS


def test_ruff_validator():
    v = RuffValidator()
    fb = v.validate(FIXTURE)
    assert fb.validator == "ruff"
    assert fb.status in (FeedbackStatus.PASS, FeedbackStatus.FAIL)


def test_mypy_validator():
    v = MypyValidator()
    fb = v.validate(FIXTURE)
    assert fb.validator == "mypy"


def test_pipeline_runs_all():
    pipe = ValidatorPipeline([PytestValidator(), RuffValidator(), MypyValidator()])
    results = pipe.run(FIXTURE)
    assert len(results) == 3
    assert results[0].validator == "pytest"


def test_pytest_validator_error_on_missing_project():
    v = PytestValidator()
    fb = v.validate("/nonexistent/path")
    assert fb.status == FeedbackStatus.VALIDATOR_ERROR
