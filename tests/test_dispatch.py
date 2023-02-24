from collections.abc import Iterable
from concurrent import futures
from typing import Union

import pytest
from multimethod import get_types, multidispatch, multimethod, signature, DispatchError


def test_cls():
    class cls:
        method = multidispatch(lambda self, other: None)

        @method.register
        def iterable_object(self: Iterable, other: object):
            return 'left'

        @method.register
        def object_iterable(self: object, other: Iterable):
            return 'right'

    obj = cls()
    assert obj.method(None) is cls.method(None, None) is None
    assert obj.method('') == 'right'
    assert cls.method('', None) == 'left'
    with pytest.raises(DispatchError, match="2 methods"):
        cls.method('', '')


def test_arguments():
    def func(a, b: int, /, c: int, d, e: int = 0, *, f: int):
        ...

    assert get_types(func) == (object, int, int)


def test_keywords():
    @multidispatch
    def func(arg):
        return 0

    @func.register
    def only_int(arg: int):
        return 1

    @func.register
    def int_and_union(arg: int, extra: Union[int, float]):
        return 2

    @func.register
    def int_str(arg: int, extra: str):
        return 3

    @func.register
    def int_kwonly(arg: int, *, extra: rock):
        return 4

    assert func("sth") == 0
    assert func(0) == func(arg=0) == 1
    assert func(0, 0.0) == func(arg=0, extra=0.0) == func(arg=0, extra=0.0) == 2
    assert func(0, 0) == func(0, extra=0) == func(arg=0, extra=0) == 2
    assert func(0, '') == func(0, extra='') == func(arg=0, extra='') == 3
    assert func(0, extra=rock()) == func(arg=0, extra=rock()) == 4

    with pytest.raises(DispatchError):
        func(0, rock())


def test_keywords2():
    """Check what happens if you get an undeclared type."""

    @multidispatch
    def func(arg: int, extra: int):
        return 1

    @func.register()
    def int_str(arg: int, extra: str):
        return 2

    assert func(0, 0) == 1
    assert func(0, "") == 2
    with pytest.raises(DispatchError, match="No matching functions found"):
        func(0, tuple())


def test_keywords3():
    """Check what happens if the function signature doesn't match."""

    @multidispatch
    def func(arg: int, extra: int):
        return 1

    @func.register()
    def int_str(arg: int, *, extra: str):
        return 2

    assert func(0, 0) == 1
    with pytest.raises(DispatchError, match="No matching functions found"):
        func(0, "")


def test_concurrency():
    @multimethod
    def func(arg: int):
        ...

    submit = futures.ThreadPoolExecutor().submit
    args = [type('', (int,), {})() for _ in range(500)]
    fs = [submit(func, arg) for arg in args]
    assert all(future.result() is None for future in fs)


# Test methods below are based on the 'overload' tests of Richard Jones:
# https://pypi.org/project/overload/
def test_wrapping():
    """check that we generate a nicely-wrapped result"""

    @multidispatch
    def func(arg):
        'doc'
        pass

    @func.register
    def func(*args):
        'doc2'
        pass

    assert func.__doc__ == 'doc'


def test_var_positional():
    """Check that we can overload instance methods with variable positional arguments."""

    class cls:
        @multidispatch
        def func(self):
            return 1

        @func.register()
        def func(self, *args: object):
            return 2

    assert cls().func() == 1
    assert cls().func(1) == 2


def test_arg_pattern():
    @multidispatch
    def func(a):
        return 1

    @func.register
    def a_b(a, b):
        return 2

    assert func('a') == 1
    assert func('a', 'b') == 2

    with pytest.raises(DispatchError, match="No matching functions found"):
        func()

    with pytest.raises(DispatchError, match="No matching functions found"):
        func('a', 'b', 'c')

    with pytest.raises(DispatchError, match="No matching functions found"):
        func(b=1)


def test_two_multidispatches_are_independent():
    class cls1:
        @multidispatch
        def func(self):
            return 1

    class cls2:
        @multidispatch
        def func(self):
            return 2

    assert cls1().func() == 1
    assert cls2().func() == 2


def test_correct_dispatching_based_on_type():
    @multidispatch
    def func(a: int):
        return 1

    @func.register
    def a_as_str(a: str):
        return 2

    assert func(1) == 1
    assert func('1') == 2


def test_varargs():
    @multidispatch
    def func(a):
        return 1

    @func.register
    def var_args(*args):
        return 100 + len(args)

    assert func(1) == 1
    assert func(1, 2) == 102


def test_varargs_mixed():
    @multidispatch
    def func(a):
        return 'a'

    @func.register
    def a_with_varargs(a, *args):
        return '*args {}'.format(len(args))

    assert func(1) == 'a'
    assert func(1, 2) == '*args 1'
    assert func(1, 2, 3) == '*args 2'


def test_kw():
    @multidispatch
    def func(a):
        return 'a'

    @func.register
    def kwargs(**kw):
        return '**kw {}'.format(len(kw))

    assert func(1) == 'a'
    assert func(a=1) == 'a'
    assert func(a=1, b=2) == '**kw 2'


def test_kw_mixed():
    @multidispatch
    def func(a):
        return 'a'

    @func.register
    def a_with_kwargs(a, **kw):
        return '**kw {}'.format(len(kw))

    assert func(1) == 'a'
    assert func(a=1) == 'a'
    assert func(a=1, b=2) == '**kw 1'


def test_kw_mixed2():
    @multidispatch
    def func(a):
        return 'a'

    @func.register
    def c_with_kwargs(c=1, **kw):
        return '**kw {}'.format(len(kw))

    assert func(1) == 'a'
    assert func(a=1) == 'a'
    assert func(c=1, b=2) == '**kw 1'
