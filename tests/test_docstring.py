from multimethod import multimethod


@multimethod
def foo(bar: int):
    """
    Argument is an integer
    """
    pass


@multimethod
def foo(bar: str):
    """
    Argument is a string
    """
    pass


@foo.register
def _(bar: float):
    pass


def test_docstring():
    """
    Test if multimethod collects its children's docstrings
    """
    assert "Argument is an integer" in foo.__doc__
    assert "Argument is a string" in foo.__doc__
    assert "float" not in foo.__doc__
