[![image](https://img.shields.io/pypi/v/multimethod.svg)](https://pypi.org/project/multimethod/)
![image](https://img.shields.io/pypi/pyversions/multimethod.svg)
[![image](https://pepy.tech/badge/multimethod)](https://pepy.tech/project/multimethod)
![image](https://img.shields.io/pypi/status/multimethod.svg)
[![build](https://github.com/coady/multimethod/actions/workflows/build.yml/badge.svg)](https://github.com/coady/multimethod/actions/workflows/build.yml)
[![image](https://codecov.io/gh/coady/multimethod/branch/main/graph/badge.svg)](https://codecov.io/gh/coady/multimethod/)
[![CodeQL](https://github.com/coady/multimethod/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/coady/multimethod/actions/workflows/github-code-scanning/codeql)
[![CodSpeed Badge](https://img.shields.io/endpoint?url=https://codspeed.io/badge.json)](https://codspeed.io/coady/multimethod)
[![image](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![image](https://mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

Multimethod provides a decorator for adding multiple argument dispatching to functions. The decorator creates a multimethod object as needed, and registers the function with its annotations.

There are several multiple dispatch libraries on PyPI. This one aims for simplicity and speed. With caching of argument types, it should be the fastest pure Python implementation possible.

## Usage
There are a couple options which trade-off dispatch speed for flexibility.

Decorator | Speed | Dispatch | Arguments
--------- | ----- | -------- | ---------
[multimethod](#multimethod) | faster | cached lookup | positional only
[multidispatch](#multidispatch) | slower | binds to first signature + cached lookup | positional + keywords

Dispatching on simple types which use `issubclass` is cached. Advanced types which use `isinstance` require a linear scan.

### multimethod
```python
from multimethod import multimethod

@multimethod
def func(x: int, y: float):
    ...
```

`func` is now a `multimethod` which will delegate to the above function, when called with arguments of the specified types. Subsequent usage will register new types and functions to the existing multimethod of the same name.

```python
@multimethod
def func(x: float, y: int):
    ...
```

Alternatively, functions can be explicitly registered in the same style as [functools.singledispatch](https://docs.python.org/3/library/functools.html#functools.singledispatch). This syntax is also compatible with [mypy](https://mypy-lang.org), which by default checks that [each name is defined once](https://mypy.readthedocs.io/en/stable/error_code_list.html#check-that-each-name-is-defined-once-no-redef).

```python
@func.register
def _(x: bool, y: bool):
    ...


@func.register(object, bool)
@func.register(bool, object)
def _(x, y):  # stackable without annotations
    ...
```

Multimethods are implemented as mappings from signatures to functions, and can be introspected as such.

```python
method[type, ...]           # get registered function
method[type, ...] = func    # register function by explicit types
```

Multimethods support any types that satisfy the `issubclass` relation, including abstract base classes in `collections.abc`. Note `typing` aliases do not support `issubclass` consistently, and are no longer needed for subscripts. Using ABCs instead is recommended. Subscripted generics are supported:
* `Union[...]` or `... | ...`
* `Mapping[...]` - the first key-value pair is checked
* `tuple[...]` - all args are checked
* `Iterable[...]` - the first arg is checked
* `Type[...]`
* `Literal[...]`
* `Callable[[...], ...]` - parameter types are contravariant, return type is covariant

Naturally checking subscripts is slower, but the implementation is optimized, cached, and bypassed if no subscripts are in use in the parameter. Empty iterables match any subscript, but don't special-case how the types are normally resolved.

Dispatch resolution details:
* If an exact match isn't registered, the next closest method is called (and cached).
* If there are ambiguous methods - or none - a custom `TypeError` is raised.
* Keyword-only parameters may be annotated, but won't affect dispatching.
* A skipped annotation is equivalent to `: object`.
* If no types are specified, it will inherently match all arguments.

### multidispatch
`multidispatch` is a wrapper to provide compatibility with `functools.singledispatch`. It requires a base implementation and use of the `register` method instead of namespace lookup. It also supports dispatching on keyword arguments.

### instance checks
`subtype` provisionally provides `isinstance` and `issubclass` checks for generic types. When called on a non-generic, it will return the origin type.

```python
from multimethod import subtype

cls = subtype(int | list[int])

for obj in (0, False, [0], [False], []):
    assert isinstance(obj, cls)
for obj in (0.0, [0.0], (0,)):
    assert not isinstance(obj, cls)

for subclass in (int, bool, list[int], list[bool]):
    assert issubclass(subclass, cls)
for subclass in (float, list, list[float], tuple[int]):
    assert not issubclass(subclass, cls)
```

If a type implements a custom `__instancecheck__`, it can opt-in to dispatch (without caching) by registering its metaclass and bases with `subtype.origins`. `parametric` provides a convenient constructor, which will match the base class, predicate functions, and check attributes.

```python
from multimethod import parametric

Coroutine = parametric(Callable, inspect.iscoroutinefunction)
IntArray = parametric(array, typecode='i')
```

### classes
`classmethod` and `staticmethod` may be used with a multimethod, but must be applied _last_, i.e., wrapping the final multimethod definition after all functions are registered. For class and instance methods, `cls` and `self` participate in the dispatch as usual. They may be left blank when using annotations, otherwise use `object` as a placeholder.

```python
class Cls:
    # @classmethod: only works here if there are no more functions
    @multimethod
    def meth(cls, arg: str): ...

    # @classmethod: can not be used with `register` because `_` is not the multimethod
    @meth.register
    def _(cls, arg: int): ...

    meth = classmethod(meth)  # done with registering
```

If a method spans multiple classes, then the namespace lookup can not work. The `register` method can be used instead.

```python
class Base:
    @multimethod
    def meth(self, arg: str): ...

class Subclass(Base):
    @Base.meth.register
    def _(self, arg: int): ...
```

If the base class can not be modified, the decorator - like any - can be called explicitly.

```python
class Subclass(Base):
    meth = multimethod(Base.meth)
    ...
```

`multimeta` creates a class with a special namespace which converts callables to multimethods, and registers duplicate callables with the original.

```python
class Cls(metaclass=multimeta):
    ... # all methods are multimethods
```

## Installation
```console
% pip install multimethod
```

## Tests
100% branch coverage.

```console
% pytest [--cov]
```
