[![image](https://img.shields.io/pypi/v/multimethod.svg)](https://pypi.org/project/multimethod/)
![image](https://img.shields.io/pypi/pyversions/multimethod.svg)
[![image](https://pepy.tech/badge/multimethod)](https://pepy.tech/project/multimethod)
![image](https://img.shields.io/pypi/status/multimethod.svg)
[![image](https://img.shields.io/travis/coady/multimethod.svg)](https://travis-ci.org/coady/multimethod)
[![image](https://img.shields.io/codecov/c/github/coady/multimethod.svg)](https://codecov.io/github/coady/multimethod)
[![image](https://readthedocs.org/projects/multimethod/badge)](https://multimethod.readthedocs.io)
[![image](https://requires.io/github/coady/multimethod/requirements.svg)](https://requires.io/github/coady/multimethod/requirements/)
[![image](https://api.codeclimate.com/v1/badges/5a3ddcd54e550eee27f9/maintainability)](https://codeclimate.com/github/coady/multimethod/maintainability)
[![image](https://img.shields.io/badge/code%20style-black-000000.svg)](https://pypi.org/project/black/)
[![image](http://mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)

Multimethod provides a decorator for adding multiple argument dispatching to functions.
The decorator creates a multimethod object as needed, and registers the function with its annotations.

There are several multiple dispatch libraries on PyPI.
This one aims for simplicity and speed. With caching of argument types,
it should be the fastest pure Python implementation possible.

# Usage
## multimethod
```python
from multimethod import multimethod

@multimethod
def func(x: int, y: float):
    ...
```

`func` is now a `multimethod` which will delegate to the above function,
when called with arguments of the specified types.
Subsequent usage will register new types and functions to the existing multimethod of the same name.

```python
@multimethod
def func(x: float, y: int):
    ...
```

Alternatively, functions can be explicitly registered in the same style as
[functools.singledispatch](https://docs.python.org/3/library/functools.html#functools.singledispatch).

```python
@func.register
def _(x: bool, y: bool):
    ...


@func.register(object, bool)
@func.register(bool, object)
def _(x, y):  # stackable without annotations
    ...
```

Multimethods are implemented as mappings from signatures to functions,
and can be introspected as such.

```python
method[type, ...]           # get registered function
method[type, ...] = func    # register function by explicit types
```

Multimethods support any types that satisfy the `issubclass` relation,
including abstract base classes in `collections.abc` and `typing`.
Subscripted generics are provisionally supported:
* `Union[...]`
* `Mapping[...]` - the first key-value pair is checked
* `Tuple[...]` - all args are checked
* `Iterable[...]` - the first arg is checked

Naturally checking subscripts is slower, but the implementation is optimized, cached,
and bypassed if no subscripts are in use in the multimethod.

Dispatch resolution details:
* If an exact match isn't registered, the next closest method is called (and cached).
* If the `issubclass` relation is ambiguous,
[mro](https://docs.python.org/3/library/stdtypes.html?highlight=mro#class.mro) position is used as a tie-breaker.
* If there are still ambiguous methods - or none - a custom `TypeError` is raised.
* Additional `*args` or `**kwargs` may be used when calling, but won't affect the dispatching.
* A skipped annotation is equivalent to `: object`, which implicitly supports methods by leaving `self` blank.
* If no types are specified, it will inherently match all arguments.

## overload
Overloads dispatch on annotated predicates.
Each predicate is checked in the reverse order of registration.

The implementation is separate from `multimethod` due to the different performance characteristics.
Instead a simple `isa` predicate is provided for checking instance type.

```python
from multimethod import isa, overload

@overload
def func(obj: isa(str)):
    ...

@overload
def func(obj: str.isalnum):
    ...

@overload
def func(obj: str.isdigit):
    ...
```

## multimeta

Use `metaclass=multimeta` to create a class with a special namespace which converts callables to multimethods, and registers duplicate callables with the original.

```python
from multimethod import multimeta

class Foo(metaclass=multimeta):
    def bar(self, x: str):
        ...
        
    def bar(self, x: int):
        ...
```

Equivalent to:

```python
from multimethod import multimethod

class Foo:
    @multimethod
    def bar(self, x: str):
        ...
        
    @bar.register
    def bar(self, x: int):
        ...
```

# Installation

```console
% pip install multimethod
```

# Tests
100% branch coverage.

```console
% pytest [--cov]
```

# Changes
1.3
* Python 3 required
* Support for subscripted ABCs

1.2
* Support for typing generics
* Stricter dispatching consistent with singledispatch

1.1
* Fix for Python 2 typing backport
* Metaclass for automatic multimethods

1.0
* Missing annotations default to object
* Removed deprecated dispatch stacking

0.7
* Forward references allowed in type hints
* Register method
* Overloads with predicate dispatch

0.6
* Multimethods can be defined inside a class

0.5
* Optimized dispatching
* Support for `functools.singledispatch` syntax

0.4
* Dispatch on Python 3 annotations
