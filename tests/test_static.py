from multimethod import multidispatch, multimethod


@multimethod
def foo(bar: int):
    """
    Argument is an integer
    """
    ...


@multimethod
def foo(bar: str):
    """
    Argument is a string
    """
    ...


@foo.register
def _(bar: float): ...


def test_docstring():
    """
    Test if multimethod collects its children's docstrings
    """
    assert "Argument is an integer" in foo.__doc__
    assert "Argument is a string" in foo.__doc__
    assert "float" not in foo.__doc__


def test_return():
    func = multidispatch.__new__.__annotations__["func"]
    assert multidispatch.__get__.__annotations__["return"] == func
    assert multidispatch.__call__.__annotations__["return"] in func.__args__
