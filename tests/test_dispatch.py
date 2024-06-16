from collections.abc import Iterable
from concurrent import futures
import pytest
from multimethod import multidispatch, multimethod, signature, DispatchError


def test_signature():
    with pytest.raises(TypeError):
        signature([list]) <= signature([None])


# roshambo
rock, paper, scissors = (type('', (), {}) for _ in range(3))


@multimethod
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
    del roshambo[()]
    del roshambo[rock, paper]
    assert len(roshambo) == 5
    with pytest.raises(DispatchError, match="0 methods"):
        roshambo(r, r)
    r = roshambo.copy()
    assert isinstance(r, multimethod)
    assert r == roshambo


# methods
class cls:
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
    def func(a, b: int, /, c: int = 0, d=None, *, f: int): ...

    assert signature.from_hints(func) == (object, int, int)

    @multidispatch
    def func(arg: ...): ...


def test_defaults():
    def func(a: int, b: float = 0.0):
        return b

    assert signature.from_hints(func) == (int, float)
    method = multimethod(func)
    assert method(1) == 0.0
    assert method(0, 1.0) == method(0, b=1.0) == 1.0
    with pytest.raises(DispatchError, match="0 methods"):
        method(0, 0)
    assert multidispatch(func)(0, b=1)
    assert multimethod(bool)(1)


@pytest.mark.benchmark
def test_keywords():
    @multidispatch
    def func(arg):
        pass

    @func.register
    def _(arg: int):
        return int

    @func.register
    def _(arg: int, extra: float):
        return float

    assert func(0) is func(arg=0) is int
    assert func(0, 0.0) is func(arg=0, extra=0.0) is float


def test_concurrency():
    @multimethod
    def func(arg: int): ...

    submit = futures.ThreadPoolExecutor().submit
    args = [type('', (int,), {})() for _ in range(500)]
    fs = [submit(func, arg) for arg in args]
    assert all(future.result() is None for future in fs)
