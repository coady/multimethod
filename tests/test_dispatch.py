from collections.abc import Iterable
from concurrent import futures
from typing import Union

import pytest

from multimethod import DispatchError, get_types, multidispatch, multimethod


def test_roshambo():
    class rock: pass

    class paper: pass

    class scissors: pass

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

    assert roshambo.__name__ == 'roshambo'
    r, p, s = rock(), paper(), scissors()
    assert len(roshambo) == 7
    assert roshambo(r, p) == 'paper covers rock'
    assert roshambo(p, r) == 'paper covers rock'
    assert roshambo(r, s) == 'rock smashes scissors'
    assert roshambo(p, s) == 'scissors cut paper'
    assert roshambo(r, r) == 'tie'
    assert roshambo(p, p) == 'tie'
    assert roshambo(s, s) == 'tie'
    assert len(roshambo) == 7


def test_cls():
    class cls:
        @multidispatch
        def method(self, other: object):
            return None

        @method.register
        def iterable_object(self: Iterable, other: object):
            return 'left'

        @method.register
        def object_iterable(self: object, other: Iterable):
            return 'right'

    assert cls().method(None) is cls.method(None, None) is None
    assert cls().method('') == 'right'
    assert cls.method('', None) == 'left'
    assert cls.method('', '') == 'left'


def test_arguments():
    def func(a, b: int, /, c: int, d, e: int = 0, *, f: int):
        ...

    assert get_types(func) == (object, int, int)


def test_keywords():
    class cls: pass

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
    def int_kwonly(arg: int, *, extra: cls):
        return 4

    assert func("sth") == 0
    assert func(0) == func(arg=0) == 1
    assert func(0, 0.0) == func(arg=0, extra=0.0) == func(arg=0, extra=0.0) == 2
    assert func(0, 0) == func(0, extra=0) == func(arg=0, extra=0) == 2
    assert func(0, '') == func(0, extra='') == func(arg=0, extra='') == 3
    assert func(0, extra=cls()) == func(arg=0, extra=cls()) == 4

    with pytest.raises(DispatchError):
        func(0, cls())


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


def test_multiple_registrations_on_top_of_each_other():
    @multidispatch
    def func(left, right):
        return left + right

    @func.register(int, float)
    @func.register(float, int)
    def _(left, right):
        return (left + right) / 2

    assert func(1, 2) == 3
    assert func(1.0, 2.0) == 3.0
    assert func(1.0, 2) == 1.5
    assert func(1, 2.0) == 1.5


def test_different_signatures():
    class cls: pass

    @multidispatch
    def func():
        return 'no args'

    @func.register
    def only_int(a: int):
        return f'int: {a}'

    @func.register
    def int_float(a: int, b: float = 3.0):
        return f'int_float: {a} / {b}'

    @func.register
    def str_cls(a: str, b: cls):
        return f'str_cls: {a} / cls'

    assert func() == 'no args'
    assert func(1) == 'int: 1'
    assert func("A", cls()) == 'str_cls: A / cls'

    with pytest.raises(DispatchError, match="No matching functions found"):
        func(1, 2)

    with pytest.raises(DispatchError, match="No matching functions found"):
        func("")

    with pytest.raises(DispatchError, match="No matching functions found"):
        func("A", cls)


def test_all_possible_arguments():
    class cls1(int): pass
    class cls2(int): pass

    @multidispatch
    def func():
        return 1

    @func.register
    def _(po: int, /, pok: float, *args: str, kw: cls1, **kwargs: cls2):  # / introduced in Python 3.8
        return f"po: {po}, /, pok: {pok}, *args: {args}, kw: {kw}, **kwargs: {kwargs}"

    assert func() == 1
    assert func(1, 1.0, "1", "2", kw=cls1(5), x=cls2(6), y=cls2(7)) == "po: 1, /, pok: 1.0, *args: ('1', '2'), kw: 5, **kwargs: {'x': 6, 'y': 7}"
    assert func(1, 1.0, kw=cls1(5)) == "po: 1, /, pok: 1.0, *args: (), kw: 5, **kwargs: {}"

    with pytest.raises(DispatchError, match="No matching functions found"):
        func(1, 1.0, "1", 1.23, kw=cls1(), x=cls2(), y=cls2())

    with pytest.raises(DispatchError, match="No matching functions found"):
        func(1, 1.0, "1", 1.23, kw=cls1(), x=cls1())


@pytest.mark.skip("Skip for now. Under discussion")
def test_all_possible_arguments_with_defaults():
    class cls1(int): pass
    class cls2(int): pass

    @multidispatch
    def func():
        return 1

    @func.register
    def _(po: int, /, pok: float, pok2: float = 10.0, *args: str, kw: cls1, kw2: cls1 = cls1(11), **kwargs: cls2):  # / introduced in Python 3.8
        return f"po: {po}, /, pok: {pok}, pok2: {pok2}, *args: {args}, kw: {kw}, kw2: {kw2}, **kwargs: {kwargs}"

    assert func() == 1
    # This method fails because "1" is assigned to pok2, and args is ("2", ). Whereas we might want pok2 to be the default value 10.0, and args be ("1", "2")...
    assert func(1, 1.0, "1", "2", kw=cls1(5), x=cls2(6), y=cls2(7)) == "po: 1, /, pok: 1.0, *args: ('1', '2'), kw: 5, **kwargs: {'x': 6, 'y': 7}"
    assert func(1, 1.0, kw=cls1(5)) == "po: 1, /, pok: 1.0, *args: (), kw: 5, **kwargs: {}"

    with pytest.raises(DispatchError, match="No matching functions found"):
        func(1, 1.0, "1", 1.23, kw=cls1(), x=cls2(), y=cls2())

    with pytest.raises(DispatchError, match="No matching functions found"):
        func(1, 1.0, "1", 1.23, kw=cls1(), x=cls1())
