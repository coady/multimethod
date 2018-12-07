[![image](https://img.shields.io/pypi/v/multimethod.svg)](https://pypi.org/project/multimethod/)
[![image](https://img.shields.io/pypi/pyversions/multimethod.svg)](https://python3statement.org)
![image](https://img.shields.io/pypi/status/multimethod.svg)
![image](https://img.shields.io/pypi/dm/multimethod.svg)
[![image](https://img.shields.io/travis/coady/multimethod.svg)](https://travis-ci.org/coady/multimethod)
[![image](https://img.shields.io/codecov/c/github/coady/multimethod.svg)](https://codecov.io/github/coady/multimethod)
[![image](https://readthedocs.org/projects/multimethod/badge)](https://multimethod.readthedocs.io)
[![image](https://requires.io/github/coady/multimethod/requirements.svg)](https://requires.io/github/coady/multimethod/requirements/)
[![image](https://api.codeclimate.com/v1/badges/5a3ddcd54e550eee27f9/maintainability)](https://codeclimate.com/github/coady/multimethod/maintainability)

Multimethod provides a decorator for adding multiple argument dispatching to functions.
The decorator finds the multimethod of the same name, creating it if necessary,
and registers the function with its annotations.

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
If an exact match isn't registered, the next closest method is called (and cached).
Candidate methods are ranked based on their subclass relationships.
If no matches are found, a custom `TypeError` is raised.

A `strict` flag can also be set on the `multimethod` object,
in which case finding multiple matches also raises a `TypeError`.
Keyword arguments can be used when calling, but won't affect the dispatching.
If no annotations are specified, it will inherently match any aruments.

Multimethods are implemented as mappings from signatures to functions,
and can be introspected as such.

```python
method[type, ...]           # get registered function
method[type, ...] = func    # register function by explicit types
method.register(func)       # decorator to register annotated function (with any __name__)
```

## multidispatch
The [functools.singledispatch](https://docs.python.org/3/library/functools.html#functools.singledispatch)
style syntax is also supported. This requires creating a `multidispatch` object explicitly,
and consequently doesn't rely on the name matching.
The `register` method returns a decorator for given types,
thereby supporting [Python 2](https://python3statement.org) and stacking of multiple signatures.

```python
from multimethod import multidispatch

@multidispatch
def func(*args):
    ...

@func.register(object, int)
@func.register(int, object)
def _(*args):
    ...
```

## overload
Overloads dispatch on annotated predicates.
Each predicate is checked in the reverse order of registration.

The implementation is separate from `multimethod` due to the different performance characteristics.
Instead a simple `isa` predicate is provided for checking instance type.

```python
from multimethod import overload

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

# Installation

    $ pip install multimethod

# Tests
100% branch coverage.

    $ pytest [--cov]

# Changes
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
