from codereflex.feedback.classifier import FailureClassifier, failure_signature
from codereflex.models import Feedback, FeedbackStatus, FailureCategory


PYTEST_FAIL_OUTPUT = """\
============================= test session starts =============================
collected 2 items

tests/test_calc.py::test_add FAILED                                       [ 50%]
tests/test_calc.py::test_divide_by_zero PASSED                            [100%]

================================== FAILURES ===================================
___________________________________ test_add ___________________________________
    def test_add():
>       assert add(1, 2) == 5
E       assert 3 == 5
tests/test_calc.py:5: AssertionError
=========================== 1 failed, 1 passed in 0.05s ===========================
"""

MYPY_OUTPUT = """\
src/calc.py:10: error: Argument 1 to "divide" has incompatible type "str"; expected "int"  [arg-type]
Found 1 error in 1 file (checked 1 source file)
"""

RUFF_OUTPUT = """\
src/calc.py:5:1: E302 expected 2 blank lines, found 1
src/calc.py:10:80: E501 line too long (90 > 79 characters)
"""

SYNTAX_OUTPUT = """\
  File "src/calc.py", line 10
    def add(a, b)
                 ^
SyntaxError: invalid syntax
"""

IMPORT_OUTPUT = """\
ModuleNotFoundError: No module named 'missing_pkg'
"""

RUNTIME_OUTPUT = """\
Traceback (most recent call last):
  File "main.py", line 5, in <module>
    result = divide(1, 0)
  File "src/calc.py", line 11, in divide
    return a / b
ZeroDivisionError: division by zero
"""


def test_classify_test_failure():
    fb = Feedback(validator="pytest", status=FeedbackStatus.FAIL, raw_output=PYTEST_FAIL_OUTPUT)
    items = FailureClassifier.classify(fb)
    assert len(items) >= 1
    assert items[0].category == FailureCategory.TEST_FAILURE
    assert "test_calc.py" in items[0].file
    assert items[0].line == 5


def test_classify_type_error():
    fb = Feedback(validator="mypy", status=FeedbackStatus.FAIL, raw_output=MYPY_OUTPUT)
    items = FailureClassifier.classify(fb)
    assert len(items) >= 1
    assert items[0].category == FailureCategory.TYPE_ERROR
    assert "calc.py" in items[0].file
    assert items[0].line == 10


def test_classify_lint_violation():
    fb = Feedback(validator="ruff", status=FeedbackStatus.FAIL, raw_output=RUFF_OUTPUT)
    items = FailureClassifier.classify(fb)
    assert len(items) >= 1
    assert items[0].category == FailureCategory.LINT_VIOLATION


def test_classify_syntax_error():
    fb = Feedback(validator="pytest", status=FeedbackStatus.FAIL, raw_output=SYNTAX_OUTPUT)
    items = FailureClassifier.classify(fb)
    assert any(i.category == FailureCategory.SYNTAX_ERROR for i in items)


def test_classify_import_error():
    fb = Feedback(validator="pytest", status=FeedbackStatus.FAIL, raw_output=IMPORT_OUTPUT)
    items = FailureClassifier.classify(fb)
    assert any(i.category == FailureCategory.IMPORT_ERROR for i in items)


def test_classify_runtime_error():
    fb = Feedback(validator="pytest", status=FeedbackStatus.FAIL, raw_output=RUNTIME_OUTPUT)
    items = FailureClassifier.classify(fb)
    assert any(i.category == FailureCategory.RUNTIME_ERROR for i in items)


def test_classify_pass_returns_empty():
    fb = Feedback(validator="pytest", status=FeedbackStatus.PASS, raw_output="all good")
    assert FailureClassifier.classify(fb) == []


def test_failure_signature_stable():
    fb = Feedback(validator="pytest", status=FeedbackStatus.FAIL, raw_output=PYTEST_FAIL_OUTPUT)
    items = FailureClassifier.classify(fb)
    sig1 = failure_signature(items)
    sig2 = failure_signature(items)
    assert sig1 == sig2


def test_failure_signature_differs_for_different_failures():
    fb1 = Feedback(validator="pytest", status=FeedbackStatus.FAIL, raw_output=PYTEST_FAIL_OUTPUT)
    fb2 = Feedback(validator="mypy", status=FeedbackStatus.FAIL, raw_output=MYPY_OUTPUT)
    sig1 = failure_signature(FailureClassifier.classify(fb1))
    sig2 = failure_signature(FailureClassifier.classify(fb2))
    assert sig1 != sig2
