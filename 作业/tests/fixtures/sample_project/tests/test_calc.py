from calc import add, divide


def test_add():
    assert add(1, 2) == 3


def test_divide_by_zero():
    try:
        divide(1, 0)
        assert False, "should raise"
    except ZeroDivisionError:
        assert True
