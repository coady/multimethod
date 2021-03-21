import sys
from collections.abc import Iterable
import pytest
from multimethod import get_types, multidispatch, signature, DispatchError, multimethod


def test_signature():
    with pytest.raises(TypeError):
        signature([list]) <= signature([None])


# roshambo
rock, paper, scissors = (type('', (), {}) for _ in range(3))


@multidispatch
def roshambo(left, right):
    return 'tie'


@roshambo.register(scissors, rock)
@roshambo.register(rock, scissors)
def _(left, right):
    return 'rock smashes scissors'


@roshambo.register(paper, scissors)
@roshambo.register(scissors, paper)
def _(left, right):
    return 'scissors cut paper'


@roshambo.register(rock, paper)
@roshambo.register(paper, rock)
def _(left, right):
    return 'paper covers rock'


def test_roshambo():
    assert roshambo.__name__ == 'roshambo'
    r, p, s = rock(), paper(), scissors()
    assert len(roshambo) == 7
    assert roshambo(r, p) == 'paper covers rock'
    assert roshambo(p, r) == 'paper covers rock'
    assert roshambo(r, s) == 'rock smashes scissors'
    assert roshambo(p, s) == 'scissors cut paper'
    assert roshambo(r, r) == 'tie'
    assert len(roshambo) == 8
    del roshambo[object, object]
    del roshambo[rock, paper]
    assert len(roshambo) == 5
    with pytest.raises(DispatchError, match="0 methods"):
        roshambo(r, r)
    r = roshambo.copy()
    assert isinstance(r, multidispatch)
    assert r == roshambo


# methods
class cls(object):
    method = multidispatch(lambda self, other: None)

    @method.register(Iterable, object)
    def _(self, other):
        return 'left'

    @method.register(object, Iterable)
    def _(self, other):
        return 'right'


def test_cls():
    obj = cls()
    assert obj.method(None) is cls.method(None, None) is None
    assert obj.method('') == 'right'
    assert cls.method('', None) == 'left'
    with pytest.raises(DispatchError, match="2 methods"):
        cls.method('', '')
    cls.method[object, Iterable] = cls.method[Iterable, object]
    assert cls.method('', '') == 'left'


def test_arguments():
    from multimethod import VAR_ARG

    def func(a, b: int, c: int, d, e: int = 0, *, f: int):
        pass

    if sys.version_info >= (3, 8):
        exec("def func(a, b: int, /, c: int, d, e: int = 0, *, f: int): pass")

    got = list(get_types(func))
    assert got == [(object, int, int, object, int), (object, int, int, object)]

    # builtin type
    got = list(get_types(type))
    assert got == [(VAR_ARG,)]


def test_nargs_precedence():
    class AbstractFoo:
        pass

    class Foo(AbstractFoo):
        pass

    @multimethod
    def temp(a):
        return "fallback"

    @multimethod
    def temp(a: AbstractFoo, b: bool):
        return "2 args"

    @multimethod
    def temp(a: Foo):
        return "1 arg"

    assert temp(1) == "fallback"
    assert temp(Foo(), False) == "2 args"
    assert temp(Foo()) == "1 arg"


def test_kwargs():
    class Foo:
        pass

    @multimethod
    def temp(a, b=1, **kwargs):
        return f"a={a} b={b}"

    assert temp(1) == "a=1 b=1"
    assert temp(1, 2) == "a=1 b=2"
    assert temp(1, b=3, c=1) == "a=1 b=3"


def test_varargs():
    @multimethod
    def varg1(*args, **kwargs):
        return str(args)

    assert varg1(a=1) == "()"
    assert varg1(1) == "(1,)"
    assert varg1(1, 2) == "(1, 2)"

    @multimethod
    def varg2(a):
        return "fallback"

    @multimethod
    def varg2(*args, **kwargs):
        return "var"

    @multimethod
    def varg2(a: int, *args, **kwargs):
        return "int"

    @multimethod
    def varg2(a: float, *args, b: str = "foo", **kwargs):
        return "float"

    @multimethod
    def varg2(a: tuple, b: str = "foo", **kwargs):
        return "tuple"

    assert varg2("a") == "fallback"
    assert varg2("a", 2) == "var"
    assert varg2(1, 2) == "int"

    assert varg2(1.0) == "float"
    assert varg2(1.0, b="bar") == "float"
    assert varg2(1.0, "bar") == "float"
    assert varg2(1.0, True) == "float"

    assert varg2((), "bar") == "tuple"
    assert varg2((), "bar", c=1) == "tuple"

    # inconsistent behavior below expected since kwargs are not part of dispatch logic
    assert varg2((), 1.0) == "var"
    assert varg2((), b=1.0) == "tuple"


def test_div():
    from multimethod import multimethod
    import operator

    classic_div = multimethod(operator.truediv)
    classic_div[int, int] = operator.floordiv
    classic_div(3, 2) == 1
    classic_div(3.0, 2) == 1.5
