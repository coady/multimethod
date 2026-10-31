import pytest

from multimethod import multidispatch, multimethod


class namespace: ...


@pytest.mark.parametrize("dispatcher", [multimethod, multidispatch])
def test_copy_dispatch(dispatcher):
    def func(value: int = 0):
        """Return an integer."""
        return value + 1

    method = dispatcher(func)

    @method.register
    def _(value: list[int]):
        return sum(value)

    assert method(True) == 2  # populate the type cache
    copied = method.copy()
    assert type(copied) is type(method)
    assert copied == method
    assert copied.__name__ == method.__name__
    assert copied.__doc__ == method.__doc__
    assert copied.__wrapped__ is method.__wrapped__
    assert copied() == 1
    assert copied(True) == 2
    assert copied([1, 2]) == 3

    @copied.register
    def _(value: tuple[int]):
        return value[0]

    assert copied((3,)) == 3
    assert method.generics == [(list,)]


def test_copy_pending(monkeypatch):
    @multimethod
    def method(value: "namespace.ForwardReference"):
        return value

    copied = method.copy()
    monkeypatch.setattr(namespace, "ForwardReference", int, raising=False)
    assert copied(1) == 1
    assert len(method.pending) == 1
    assert method(2) == 2
    assert not method.pending


def test_copy_parent_graph():
    class A: ...

    class B(A): ...

    class C(B): ...

    class D(C): ...

    method = multimethod(lambda value: None)
    method[A,] = lambda value: A
    method[C,] = lambda value: C
    copied = method.copy()
    copied[B,] = lambda value: B
    assert method(D()) is copied(D()) is C
    assert method(B()) is A
    assert copied(B()) is B

    del copied[C,]
    assert method(D()) is C
    assert copied(D()) is B


def test_multidispatch_copy_keywords():
    @multidispatch
    def method(value):
        return value

    @method.register
    def _(value: int):
        return value + 1

    copied = method.copy()
    assert copied(value=1) == 2

    @copied.register
    def _(value: int, extra: int):
        return value + extra

    assert copied(value=1, extra=2) == 3
    assert tuple(method.signatures) == (("value",),)
    assert method(value=1) == 2


def test_copy_after_pop():
    method = multimethod(lambda value: None)
    method[int,] = lambda value: value + 1
    method.pop(())
    copied = method.copy()
    assert copied == method
    assert copied(True) == method(True) == 2
