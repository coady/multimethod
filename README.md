[![image](https://img.shields.io/pypi/v/multimethod.svg)](https://pypi.org/project/multimethod/)
![image](https://img.shields.io/pypi/pyversions/multimethod.svg)
[![image](https://pepy.tech/badge/multimethod)](https://pepy.tech/project/multimethod)
![image](https://img.shields.io/pypi/status/multimethod.svg)
[![image](https://github.com/coady/multimethod/workflows/build/badge.svg)](https://github.com/coady/multimethod/actions)
[![image](https://codecov.io/gh/coady/multimethod/branch/main/graph/badge.svg)](https://codecov.io/gh/coady/multimethod/)
[![image](https://github.com/coady/multimethod/workflows/codeql/badge.svg)](https://github.com/coady/multimethod/security/code-scanning)
[![image](https://img.shields.io/badge/code%20style-black-000000.svg)](https://pypi.org/project/black/)
[![image](http://mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)

Multimethod provides a decorator for adding multiple argument dispatching to functions. The decorator creates a multimethod object as needed, and registers the function with its annotations.

There are several multiple dispatch libraries on PyPI. This one aims for simplicity and speed. With caching of argument types, it should be the fastest pure Python implementation possible.

## Usage
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

Alternatively, functions can be explicitly registered in the same style as [functools.singledispatch](https://docs.python.org/3/library/functools.html#functools.singledispatch). This syntax is also compatible with [mypy](http://mypy-lang.org), which by default checks that [each name is defined once](https://mypy.readthedocs.io/en/stable/error_code_list.html#check-that-each-name-is-defined-once-no-redef).

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

Multimethods support any types that satisfy the `issubclass` relation, including abstract base classes in `collections.abc` and `typing`. Subscripted generics are supported:
* `Union[...]`
* `Mapping[...]` - the first key-value pair is checked
* `tuple[...]` - all args are checked
* `Iterable[...]` - the first arg is checked
* `Literal[...]`
* `Callable[[...], ...]` - parameter types are contravariant, return type is covariant

Naturally checking subscripts is slower, but the implementation is optimized, cached, and bypassed if no subscripts are in use in the parameter. Empty iterables match any subscript, but don't special-case how the types are normally resolved.

Dispatch resolution details:
* If an exact match isn't registered, the next closest method is called (and cached).
* If the `issubclass` relation is ambiguous,
[mro](https://docs.python.org/3/library/stdtypes.html?highlight=mro#class.mro) position is used as a tie-breaker.
* If there are still ambiguous methods - or none - a custom `TypeError` is raised.
* Default and keyword-only parameters may be annotated, but won't affect dispatching.
* A skipped annotation is equivalent to `: object`.
* If no types are specified, it will inherently match all arguments.

`classmethod` and `staticmethod` may be used with a multimethod, but must be applied last, i.e., wrapping the final multimethod definition. For class and instance methods, `cls` and `self` participate in the dispatch as usual. They may be left blank when using annotations, otherwise use `object` as a placeholder.

```python
class Foo:
    @multimethod
    def bar(cls, x: str):
        ...

    @classmethod # <- only put this @classmethod here on the final definition
    @bar.register
    def _(cls, x: int):
        ...
```

### overload
Overloads dispatch on annotated predicates. Each predicate is checked in the reverse order of registration.

The implementation is separate from `multimethod` due to the different performance characteristics. If an annotation is a type instead of a predicate, it will be converted into an `isinstance` check.

```python
from multimethod import overload

@overload
def func(obj: str):
    ...

@overload
def func(obj: str.isalnum):
    ...

@overload
def func(obj: str.isdigit):
    ...
```

### multidispatch
`multidispatch` is a wrapper to provide compatibility with `functools.singledispatch`. It requires a base implementation and use of the `register` method instead of namespace lookup. It also provisionally supports dispatching on keyword arguments.

### multimeta

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

## Installation

```console
% pip install multimethod
```

## Tests
100% branch coverage.

```console
% pytest [--cov]
```

## Changes
dev

* Python 3.11 supported

1.8

* `Callable` checks parameters and return type
* Support for `NewType`

1.7

* `overload` allows types and converts them to an `isa` check
* Only functions with docstrings combine signatures
* Fixes for subscripted union and literal checks

1.6

* Python >=3.7 required
* Improved checking for TypeErrors
* `multidispatch` has provisional support for dispatching on keyword arguments
* `multidispatch` supports static analysis of return type 
* Fix for forward references and subscripts
* Checking type subscripts is done minimally based on each parameter
* Provisionally dispatch on `Literal` type
* Provisionally empty iterables match subscript

1.5

* Postponed evaluation of nested annotations
* Variable-length tuples of homogeneous type
* Ignore default and keyword-only parameters
* Resolved ambiguous `Union` types
* Fixed an issue with name collision when defining a multimethod
* Resolved dispatch errors when annotating parameters with meta-types such as `type`

1.4

* Python >=3.6 required
* Expanded support for subscripted type hints

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
